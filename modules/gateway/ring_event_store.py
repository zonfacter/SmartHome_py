"""
Configurable storage backend for Ring event history.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

import requests


class RingEventStore:
    SUPPORTED_BACKENDS = {"memory", "sqlite", "influxdb"}
    CONFIGURABLE_BACKENDS = ("memory", "sqlite", "mysql", "influxdb")

    def __init__(self, project_root: str, config_dir: str):
        self.project_root = os.path.abspath(project_root)
        self.config_dir = os.path.abspath(config_dir)
        self.default_sqlite_path = os.path.join(self.config_dir, "ring_events.db")
        self._memory_lock = threading.Lock()
        self._sqlite_lock = threading.Lock()
        self._memory = deque(maxlen=2000)
        self._memory_meta: Dict[str, Any] = {}
        self._status_note = ""

    @classmethod
    def default_config(cls) -> Dict[str, Any]:
        return {
            "backend": "sqlite",
            "max_entries": 2000,
            "sqlite": {
                "mode": "internal",
                "path": "config/ring_events.db",
            },
            "mysql": {
                "host": "127.0.0.1",
                "port": 3306,
                "database": "smarthome",
                "user": "",
                "password": "",
                "table": "ring_events",
                "ssl": False,
            },
            "influxdb": {
                "url": "http://127.0.0.1:8086",
                "org": "smarthome",
                "bucket": "ring_events",
                "token": "",
                "measurement": "ring_events",
            },
        }

    @classmethod
    def normalize_config(cls, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        source = payload if isinstance(payload, dict) else {}
        defaults = cls.default_config()

        backend = str(source.get("backend", defaults["backend"]) or defaults["backend"]).strip().lower()
        if backend not in cls.CONFIGURABLE_BACKENDS:
            backend = defaults["backend"]

        try:
            max_entries = int(source.get("max_entries", defaults["max_entries"]))
        except Exception:
            max_entries = defaults["max_entries"]
        max_entries = max(100, min(max_entries, 50000))

        sqlite_cfg = source.get("sqlite") if isinstance(source.get("sqlite"), dict) else {}
        sqlite_mode = str(sqlite_cfg.get("mode", defaults["sqlite"]["mode"]) or defaults["sqlite"]["mode"]).strip().lower()
        if sqlite_mode not in {"internal", "external"}:
            sqlite_mode = defaults["sqlite"]["mode"]
        sqlite_path = str(sqlite_cfg.get("path", defaults["sqlite"]["path"]) or defaults["sqlite"]["path"]).strip()
        if not sqlite_path:
            sqlite_path = defaults["sqlite"]["path"]

        mysql_cfg = source.get("mysql") if isinstance(source.get("mysql"), dict) else {}
        influx_cfg = source.get("influxdb") if isinstance(source.get("influxdb"), dict) else {}

        return {
            "backend": backend,
            "max_entries": max_entries,
            "sqlite": {
                "mode": sqlite_mode,
                "path": sqlite_path,
            },
            "mysql": {
                "host": str(mysql_cfg.get("host", defaults["mysql"]["host"]) or defaults["mysql"]["host"]).strip(),
                "port": max(1, min(int(mysql_cfg.get("port", defaults["mysql"]["port"]) or defaults["mysql"]["port"]), 65535)),
                "database": str(mysql_cfg.get("database", defaults["mysql"]["database"]) or defaults["mysql"]["database"]).strip(),
                "user": str(mysql_cfg.get("user", defaults["mysql"]["user"]) or defaults["mysql"]["user"]).strip(),
                "password": str(mysql_cfg.get("password", defaults["mysql"]["password"]) or defaults["mysql"]["password"]),
                "table": str(mysql_cfg.get("table", defaults["mysql"]["table"]) or defaults["mysql"]["table"]).strip() or defaults["mysql"]["table"],
                "ssl": bool(mysql_cfg.get("ssl", defaults["mysql"]["ssl"])),
            },
            "influxdb": {
                "url": str(influx_cfg.get("url", defaults["influxdb"]["url"]) or defaults["influxdb"]["url"]).strip(),
                "org": str(influx_cfg.get("org", defaults["influxdb"]["org"]) or defaults["influxdb"]["org"]).strip(),
                "bucket": str(influx_cfg.get("bucket", defaults["influxdb"]["bucket"]) or defaults["influxdb"]["bucket"]).strip(),
                "token": str(influx_cfg.get("token", defaults["influxdb"]["token"]) or defaults["influxdb"]["token"]),
                "measurement": str(influx_cfg.get("measurement", defaults["influxdb"]["measurement"]) or defaults["influxdb"]["measurement"]).strip() or defaults["influxdb"]["measurement"],
            },
        }

    def configure(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = self.normalize_config(config)
        self._ensure_memory_capacity(normalized["max_entries"])
        active_backend = self._resolve_runtime_backend(normalized)
        if active_backend == "sqlite":
            self._init_sqlite_schema(self._resolve_sqlite_path(normalized))
            self._enforce_sqlite_retention(normalized)
        elif active_backend == "mysql":
            self._init_mysql_schema(normalized)
        return self.get_status(normalized)

    def get_status(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = self.normalize_config(config)
        requested = normalized["backend"]
        active = self._resolve_runtime_backend(normalized)
        sqlite_path = self._resolve_sqlite_path(normalized)
        runtime_supported = requested == active
        note = self._status_note
        if not runtime_supported and not note:
            note = f"{requested} ist vorbereitet, aktuell aber noch nicht als Laufzeit-Backend aktiviert. Fallback: {active}."

        return {
            "requested_backend": requested,
            "active_backend": active,
            "runtime_supported": runtime_supported,
            "persistent": active in {"sqlite", "mysql", "influxdb"},
            "max_entries": normalized["max_entries"],
            "sqlite": {
                "mode": normalized["sqlite"]["mode"],
                "path": sqlite_path,
            },
            "location_label": (
                self._describe_location(active, normalized)
            ),
            "note": note,
            "available_backends": [
                {
                    "id": "memory",
                    "label": "Memory",
                    "runtime_supported": True,
                    "description": "Schnell, aber nur bis zum Dienstneustart.",
                },
                {
                    "id": "sqlite",
                    "label": "SQLite",
                    "runtime_supported": True,
                    "description": "Persistente lokale oder externe SQLite-Datei.",
                },
                {
                    "id": "mysql",
                    "label": "MySQL",
                    "runtime_supported": self._mysql_connector_available(),
                    "description": "Persistente externe MySQL-Datenbank, wenn ein Connector installiert ist.",
                },
                {
                    "id": "influxdb",
                    "label": "InfluxDB",
                    "runtime_supported": True,
                    "description": "Persistente externe InfluxDB ueber HTTP API.",
                },
            ],
        }

    def record_event(self, event: Dict[str, Any], config: Optional[Dict[str, Any]]) -> bool:
        normalized = self.normalize_config(config)
        active = self._resolve_runtime_backend(normalized)
        entry = self._normalize_event(event)
        if not entry.get("id"):
            return False

        try:
            if active == "sqlite":
                self._write_sqlite_event(entry, normalized)
                return True
            if active == "mysql":
                self._write_mysql_event(entry, normalized)
                return True
            if active == "influxdb":
                self._write_influxdb_event(entry, normalized)
                return True
            self._write_memory_event(entry, normalized)
        except Exception as exc:
            fallback = self._fallback_backend_after_runtime_error(active)
            self._status_note = f"{active} ist derzeit nicht erreichbar ({exc}). Fallback: {fallback}."
            if fallback == "sqlite":
                self._write_sqlite_event(entry, normalized)
            elif fallback == "memory":
                self._write_memory_event(entry, normalized)
        return True

    def list_events(
        self,
        limit: int,
        kinds: Optional[Iterable[str]],
        config: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalized = self.normalize_config(config)
        requested_limit = max(1, min(int(limit), 100))
        kind_filter = {str(item or "").strip().lower() for item in (kinds or set()) if str(item or "").strip()}
        active = self._resolve_runtime_backend(normalized)
        try:
            if active == "sqlite":
                return self._read_sqlite_events(requested_limit, kind_filter, normalized)
            if active == "mysql":
                return self._read_mysql_events(requested_limit, kind_filter, normalized)
            if active == "influxdb":
                return self._read_influxdb_events(requested_limit, kind_filter, normalized)
            return self._read_memory_events(requested_limit, kind_filter)
        except Exception as exc:
            fallback = self._fallback_backend_after_runtime_error(active)
            self._status_note = f"{active} ist derzeit nicht erreichbar ({exc}). Fallback: {fallback}."
            if fallback == "sqlite":
                return self._read_sqlite_events(requested_limit, kind_filter, normalized)
            return self._read_memory_events(requested_limit, kind_filter)

    def record_health_status(self, snapshot: Dict[str, Any], config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = self.normalize_config(config)
        active = self._resolve_runtime_backend(normalized)
        payload = self._normalize_health_snapshot(snapshot)
        try:
            if active == "sqlite":
                self._write_sqlite_health(payload, normalized)
            elif active == "mysql":
                self._write_mysql_health(payload, normalized)
            else:
                self._write_memory_health(payload)
        except Exception as exc:
            fallback = self._fallback_backend_after_runtime_error(active)
            self._status_note = f"{active} Statusspeicher derzeit nicht erreichbar ({exc}). Fallback: {fallback}."
            if fallback == "sqlite":
                self._write_sqlite_health(payload, normalized)
            else:
                self._write_memory_health(payload)
        return self.get_health_status(normalized)

    def get_health_status(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = self.normalize_config(config)
        active = self._resolve_runtime_backend(normalized)
        try:
            if active == "sqlite":
                raw = self._read_sqlite_health(normalized)
            elif active == "mysql":
                raw = self._read_mysql_health(normalized)
            else:
                raw = self._read_memory_health()
        except Exception as exc:
            fallback = self._fallback_backend_after_runtime_error(active)
            self._status_note = f"{active} Statusspeicher derzeit nicht erreichbar ({exc}). Fallback: {fallback}."
            raw = self._read_sqlite_health(normalized) if fallback == "sqlite" else self._read_memory_health()
        return self._finalize_health_status(raw, active)

    def _resolve_runtime_backend(self, config: Dict[str, Any]) -> str:
        requested = str(config.get("backend") or "sqlite").strip().lower()
        self._status_note = ""
        if requested in {"memory", "sqlite"}:
            return requested
        if requested == "mysql":
            if self._mysql_connector_available():
                return "mysql"
            self._status_note = "MySQL konfiguriert, aber es ist kein Python-MySQL-Connector installiert. Fallback: sqlite."
            return "sqlite"
        if requested == "influxdb":
            return "influxdb"
        return "sqlite"

    def _normalize_health_snapshot(self, snapshot: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        source = snapshot if isinstance(snapshot, dict) else {}
        now = float(source.get("updated_at") or time.time())
        last_success = self._parse_float(source.get("last_successful_pull_at"))
        last_attempt = self._parse_float(source.get("last_pull_attempt_at")) or now
        last_error_at = self._parse_float(source.get("last_error_at"))
        estimated_reauth_by = self._parse_float(source.get("estimated_reauth_by"))
        if last_success and not estimated_reauth_by:
            estimated_reauth_by = last_success + (30 * 24 * 60 * 60)
        return {
            "last_pull_attempt_at": last_attempt,
            "last_successful_pull_at": last_success,
            "last_error_at": last_error_at,
            "last_error_message": str(source.get("last_error_message") or "").strip(),
            "last_error_code": str(source.get("last_error_code") or "").strip(),
            "estimated_reauth_by": estimated_reauth_by,
            "reauth_recommended": bool(source.get("reauth_recommended")),
            "updated_at": now,
        }

    def _finalize_health_status(self, raw: Dict[str, Any], backend: str) -> Dict[str, Any]:
        payload = self._normalize_health_snapshot(raw)
        now = time.time()
        estimated_reauth_by = payload.get("estimated_reauth_by")
        days_until = None
        if estimated_reauth_by:
            days_until = round((float(estimated_reauth_by) - now) / 86400, 1)
        payload.update({
            "storage_backend": backend,
            "persistent": backend in {"sqlite", "mysql"},
            "estimated_reauth_window_days": 30,
            "days_until_estimated_reauth": days_until,
        })
        return payload

    def _write_memory_health(self, snapshot: Dict[str, Any]) -> None:
        with self._memory_lock:
            self._memory_meta = dict(snapshot)

    def _read_memory_health(self) -> Dict[str, Any]:
        with self._memory_lock:
            return dict(self._memory_meta)

    def _describe_location(self, active: str, config: Dict[str, Any]) -> str:
        if active == "sqlite":
            return self._resolve_sqlite_path(config)
        if active == "mysql":
            mysql_cfg = config.get("mysql") if isinstance(config.get("mysql"), dict) else {}
            return f"{mysql_cfg.get('host', '127.0.0.1')}:{mysql_cfg.get('port', 3306)} / {mysql_cfg.get('database', 'smarthome')}.{mysql_cfg.get('table', 'ring_events')}"
        if active == "influxdb":
            influx_cfg = config.get("influxdb") if isinstance(config.get("influxdb"), dict) else {}
            return f"{influx_cfg.get('url', '')} / bucket={influx_cfg.get('bucket', '')} / measurement={influx_cfg.get('measurement', '')}"
        return "Nur im laufenden Prozessspeicher"

    @staticmethod
    def _fallback_backend_after_runtime_error(active: str) -> str:
        if active in {"mysql", "influxdb"}:
            return "sqlite"
        return "memory"

    @staticmethod
    def _mysql_connector_available() -> bool:
        try:
            import pymysql  # type: ignore
            return bool(pymysql)
        except Exception:
            pass
        try:
            import mysql.connector  # type: ignore
            return True
        except Exception:
            return False

    def _connect_mysql(self, config: Dict[str, Any]):
        mysql_cfg = config.get("mysql") if isinstance(config.get("mysql"), dict) else {}
        connection_args = {
            "host": mysql_cfg.get("host") or "127.0.0.1",
            "port": int(mysql_cfg.get("port") or 3306),
            "user": mysql_cfg.get("user") or "",
            "password": mysql_cfg.get("password") or "",
            "database": mysql_cfg.get("database") or "smarthome",
            "autocommit": True,
        }
        try:
            import pymysql  # type: ignore
            conn = pymysql.connect(
                cursorclass=pymysql.cursors.DictCursor,
                charset="utf8mb4",
                **connection_args,
            )
            return conn, "pymysql"
        except Exception:
            import mysql.connector  # type: ignore
            conn = mysql.connector.connect(**connection_args)
            return conn, "mysql.connector"

    def _mysql_table_name(self, config: Dict[str, Any]) -> str:
        mysql_cfg = config.get("mysql") if isinstance(config.get("mysql"), dict) else {}
        table = str(mysql_cfg.get("table") or "ring_events").strip() or "ring_events"
        return "".join(ch for ch in table if ch.isalnum() or ch == "_") or "ring_events"

    def _init_mysql_schema(self, config: Dict[str, Any]) -> None:
        conn, driver = self._connect_mysql(config)
        table = self._mysql_table_name(config)
        meta_table = f"{table}_meta"
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS `{table}` (
                    id VARCHAR(191) PRIMARY KEY,
                    cam_id VARCHAR(191) NOT NULL,
                    camera_name VARCHAR(255) NOT NULL,
                    device_id VARCHAR(191) NOT NULL,
                    kind VARCHAR(64) NOT NULL,
                    trigger_name VARCHAR(64) NOT NULL,
                    created_at VARCHAR(64) NULL,
                    created_at_local VARCHAR(64) NULL,
                    ding_ts DOUBLE NULL,
                    answered TINYINT NULL,
                    state VARCHAR(64) NULL,
                    source VARCHAR(64) NOT NULL,
                    payload_json LONGTEXT NOT NULL,
                    stored_at DOUBLE NOT NULL,
                    INDEX idx_ring_events_ding_ts (ding_ts),
                    INDEX idx_ring_events_kind (kind),
                    INDEX idx_ring_events_stored_at (stored_at)
                ) CHARACTER SET utf8mb4
                """
            )
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS `{meta_table}` (
                    meta_key VARCHAR(191) PRIMARY KEY,
                    meta_value LONGTEXT NOT NULL,
                    updated_at DOUBLE NOT NULL,
                    INDEX idx_ring_event_meta_updated_at (updated_at)
                ) CHARACTER SET utf8mb4
                """
            )
            if driver == "mysql.connector":
                conn.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()

    def _resolve_sqlite_path(self, config: Dict[str, Any]) -> str:
        sqlite_cfg = config.get("sqlite") if isinstance(config.get("sqlite"), dict) else {}
        mode = str(sqlite_cfg.get("mode") or "internal").strip().lower()
        raw_path = str(sqlite_cfg.get("path") or "config/ring_events.db").strip()
        if mode != "external":
            return self.default_sqlite_path
        expanded = os.path.expanduser(raw_path)
        if os.path.isabs(expanded):
            return expanded
        return os.path.abspath(os.path.join(self.project_root, expanded))

    def _ensure_memory_capacity(self, max_entries: int) -> None:
        max_entries = max(100, min(int(max_entries), 50000))
        with self._memory_lock:
            if self._memory.maxlen == max_entries:
                return
            existing = list(self._memory)[:max_entries]
            self._memory = deque(existing, maxlen=max_entries)

    @staticmethod
    def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
        entry = dict(event or {})
        entry["id"] = str(entry.get("id") or "").strip()
        entry["cam_id"] = str(entry.get("cam_id") or "").strip()
        entry["camera_name"] = str(entry.get("camera_name") or "").strip()
        entry["device_id"] = str(entry.get("device_id") or "").strip()
        entry["kind"] = str(entry.get("kind") or "unknown").strip() or "unknown"
        entry["trigger"] = str(entry.get("trigger") or entry["kind"]).strip() or entry["kind"]
        entry["created_at"] = entry.get("created_at")
        entry["created_at_local"] = entry.get("created_at_local")
        entry["ding_ts"] = entry.get("ding_ts")
        entry["answered"] = entry.get("answered")
        entry["state"] = entry.get("state")
        entry["source"] = str(entry.get("source") or "ring_api").strip() or "ring_api"
        return entry

    def _write_memory_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        self._ensure_memory_capacity(config["max_entries"])
        with self._memory_lock:
            event_id = str(event.get("id") or "")
            if any(str(item.get("id") or "") == event_id for item in self._memory):
                return
            self._memory.appendleft(dict(event))

    def _read_memory_events(self, limit: int, kind_filter: Set[str]) -> List[Dict[str, Any]]:
        with self._memory_lock:
            items = list(self._memory)
        result: List[Dict[str, Any]] = []
        for item in items:
            kind = str(item.get("kind") or "").lower()
            if kind_filter and kind not in kind_filter:
                continue
            result.append(dict(item))
            if len(result) >= limit:
                break
        return result

    def _write_mysql_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        self._init_mysql_schema(config)
        conn, driver = self._connect_mysql(config)
        table = self._mysql_table_name(config)
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT IGNORE INTO `{table}` (
                    id, cam_id, camera_name, device_id, kind, trigger_name,
                    created_at, created_at_local, ding_ts, answered, state, source,
                    payload_json, stored_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event["id"],
                    event.get("cam_id") or "",
                    event.get("camera_name") or "",
                    event.get("device_id") or "",
                    event.get("kind") or "unknown",
                    event.get("trigger") or event.get("kind") or "unknown",
                    event.get("created_at"),
                    event.get("created_at_local"),
                    event.get("ding_ts"),
                    self._to_nullable_int(event.get("answered")),
                    str(event.get("state")) if event.get("state") is not None else None,
                    event.get("source") or "ring_api",
                    json.dumps(event, ensure_ascii=False),
                    time.time(),
                ),
            )
            if driver == "mysql.connector":
                conn.commit()
            self._enforce_mysql_retention(config, conn=conn, cursor=cursor, driver=driver)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()

    def _enforce_mysql_retention(self, config: Dict[str, Any], conn=None, cursor=None, driver: str = "") -> None:
        own_connection = conn is None or cursor is None
        if own_connection:
            conn, driver = self._connect_mysql(config)
            cursor = conn.cursor()
        table = self._mysql_table_name(config)
        max_entries = max(100, min(int(config.get("max_entries") or 2000), 50000))
        try:
            cursor.execute(f"SELECT COUNT(*) AS count FROM `{table}`")
            row = cursor.fetchone()
            total = int((row.get("count") if isinstance(row, dict) else row[0]) or 0)
            if total > max_entries:
                cursor.execute(
                    f"""
                    DELETE FROM `{table}`
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id FROM `{table}`
                            ORDER BY COALESCE(ding_ts, 0) DESC, COALESCE(created_at, '') DESC, stored_at DESC
                            LIMIT %s
                        ) keep_rows
                    )
                    """,
                    (max_entries,),
                )
                if driver == "mysql.connector":
                    conn.commit()
        finally:
            if own_connection:
                try:
                    cursor.close()
                except Exception:
                    pass
                conn.close()

    def _read_mysql_events(self, limit: int, kind_filter: Set[str], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        conn, _driver = self._connect_mysql(config)
        table = self._mysql_table_name(config)
        result: List[Dict[str, Any]] = []
        try:
            cursor = conn.cursor()
            query = f"SELECT payload_json FROM `{table}`"
            params: List[Any] = []
            if kind_filter:
                placeholders = ", ".join(["%s"] * len(kind_filter))
                query += f" WHERE LOWER(kind) IN ({placeholders})"
                params.extend(sorted(kind_filter))
            query += " ORDER BY COALESCE(ding_ts, 0) DESC, COALESCE(created_at, '') DESC, stored_at DESC LIMIT %s"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for row in rows:
                payload_json = row.get("payload_json") if isinstance(row, dict) else row[0]
                try:
                    item = json.loads(payload_json) if payload_json else {}
                except Exception:
                    item = {}
                if isinstance(item, dict) and item.get("id"):
                    result.append(self._normalize_event(item))
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()
        return result

    def _write_mysql_health(self, snapshot: Dict[str, Any], config: Dict[str, Any]) -> None:
        self._init_mysql_schema(config)
        conn, driver = self._connect_mysql(config)
        meta_table = f"{self._mysql_table_name(config)}_meta"
        try:
            cursor = conn.cursor()
            for key, value in snapshot.items():
                cursor.execute(
                    f"""
                    INSERT INTO `{meta_table}` (meta_key, meta_value, updated_at)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value), updated_at = VALUES(updated_at)
                    """,
                    (key, json.dumps(value, ensure_ascii=False), time.time()),
                )
            if driver == "mysql.connector":
                conn.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()

    def _read_mysql_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        self._init_mysql_schema(config)
        conn, _driver = self._connect_mysql(config)
        meta_table = f"{self._mysql_table_name(config)}_meta"
        result: Dict[str, Any] = {}
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT meta_key, meta_value FROM `{meta_table}`")
            rows = cursor.fetchall()
            for row in rows:
                key = row.get("meta_key") if isinstance(row, dict) else row[0]
                value = row.get("meta_value") if isinstance(row, dict) else row[1]
                try:
                    result[str(key)] = json.loads(value)
                except Exception:
                    result[str(key)] = value
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()
        return result

    def _influx_headers(self, config: Dict[str, Any], content_type: str) -> Dict[str, str]:
        token = str((config.get("influxdb") or {}).get("token") or "")
        headers = {"Content-Type": content_type}
        if token:
            headers["Authorization"] = f"Token {token}"
        return headers

    @staticmethod
    def _escape_influx_string(value: Any) -> str:
        return str(value or "").replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _escape_influx_tag(value: Any) -> str:
        return str(value or "").replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def _event_to_influx_line(self, event: Dict[str, Any], config: Dict[str, Any]) -> str:
        influx_cfg = config.get("influxdb") if isinstance(config.get("influxdb"), dict) else {}
        measurement = self._escape_influx_tag(influx_cfg.get("measurement") or "ring_events")
        tags = {
            "id": event.get("id") or "",
            "cam_id": event.get("cam_id") or "",
            "device_id": event.get("device_id") or "",
            "kind": event.get("kind") or "unknown",
            "source": event.get("source") or "ring_api",
        }
        tag_part = ",".join(f"{key}={self._escape_influx_tag(value)}" for key, value in tags.items())
        fields = {
            "camera_name": f"\"{self._escape_influx_string(event.get('camera_name') or '')}\"",
            "trigger": f"\"{self._escape_influx_string(event.get('trigger') or event.get('kind') or 'unknown')}\"",
            "created_at": f"\"{self._escape_influx_string(event.get('created_at') or '')}\"",
            "created_at_local": f"\"{self._escape_influx_string(event.get('created_at_local') or '')}\"",
            "state": f"\"{self._escape_influx_string(event.get('state') or '')}\"",
            "answered": f"{1 if bool(event.get('answered')) else 0}i",
            "payload_json": f"\"{self._escape_influx_string(json.dumps(event, ensure_ascii=False))}\"",
        }
        if event.get("ding_ts") is not None:
            try:
                fields["ding_ts"] = f"{int(float(event.get('ding_ts')))}i"
            except Exception:
                pass
        field_part = ",".join(f"{key}={value}" for key, value in fields.items())
        timestamp_ns = self._event_timestamp_ns(event)
        return f"{measurement},{tag_part} {field_part} {timestamp_ns}"

    def _event_timestamp_ns(self, event: Dict[str, Any]) -> int:
        ding_ts = event.get("ding_ts")
        if ding_ts is not None:
            try:
                return int(float(ding_ts) * 1_000_000_000)
            except Exception:
                pass
        created_at = event.get("created_at")
        if created_at:
            try:
                return int(datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).timestamp() * 1_000_000_000)
            except Exception:
                pass
        return int(time.time() * 1_000_000_000)

    def _write_influxdb_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        influx_cfg = config.get("influxdb") if isinstance(config.get("influxdb"), dict) else {}
        url = str(influx_cfg.get("url") or "").rstrip("/")
        org = str(influx_cfg.get("org") or "").strip()
        bucket = str(influx_cfg.get("bucket") or "").strip()
        if not url or not org or not bucket:
            raise RuntimeError("InfluxDB Konfiguration ist unvollständig")
        response = requests.post(
            f"{url}/api/v2/write",
            params={"org": org, "bucket": bucket, "precision": "ns"},
            headers=self._influx_headers(config, "text/plain; charset=utf-8"),
            data=self._event_to_influx_line(event, config).encode("utf-8"),
            timeout=8,
        )
        response.raise_for_status()

    def _read_influxdb_events(self, limit: int, kind_filter: Set[str], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        influx_cfg = config.get("influxdb") if isinstance(config.get("influxdb"), dict) else {}
        url = str(influx_cfg.get("url") or "").rstrip("/")
        org = str(influx_cfg.get("org") or "").strip()
        bucket = str(influx_cfg.get("bucket") or "").strip()
        measurement = str(influx_cfg.get("measurement") or "ring_events").strip() or "ring_events"
        if not url or not org or not bucket:
            return []

        filters = [f'r._measurement == "{measurement}"']
        if kind_filter:
            filters.append("(" + " or ".join(f'r.kind == "{self._escape_influx_string(kind)}"' for kind in sorted(kind_filter)) + ")")
        filter_expr = " and ".join(filters)
        flux = f'''
from(bucket: "{bucket}")
  |> range(start: -3650d)
  |> filter(fn: (r) => {filter_expr})
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {int(limit)})
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
        response = requests.post(
            f"{url}/api/v2/query",
            params={"org": org},
            headers={
                **self._influx_headers(config, "application/vnd.flux"),
                "Accept": "application/csv",
            },
            data=flux.encode("utf-8"),
            timeout=12,
        )
        response.raise_for_status()
        return self._parse_influx_csv(response.text)

    def _parse_influx_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        lines = [line for line in str(csv_text or "").splitlines() if line.strip()]
        if not lines:
            return []
        header = None
        rows: List[Dict[str, Any]] = []
        for line in lines:
            if line.startswith("#"):
                continue
            parts = self._split_csv_line(line)
            if header is None:
                header = parts
                continue
            if len(parts) != len(header):
                continue
            row = dict(zip(header, parts))
            payload_json = row.get("payload_json") or ""
            try:
                payload = json.loads(payload_json) if payload_json else {}
            except Exception:
                payload = {}
            if isinstance(payload, dict) and payload.get("id"):
                rows.append(self._normalize_event(payload))
                continue
            event = {
                "id": row.get("id"),
                "cam_id": row.get("cam_id"),
                "camera_name": row.get("camera_name"),
                "device_id": row.get("device_id"),
                "kind": row.get("kind"),
                "trigger": row.get("trigger"),
                "created_at": row.get("created_at"),
                "created_at_local": row.get("created_at_local"),
                "ding_ts": self._parse_float(row.get("ding_ts")),
                "answered": self._parse_bool(row.get("answered")),
                "state": row.get("state"),
                "source": row.get("source") or "ring_api",
            }
            if event.get("id"):
                rows.append(self._normalize_event(event))
        return rows

    @staticmethod
    def _split_csv_line(line: str) -> List[str]:
        result: List[str] = []
        current = []
        in_quotes = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                    current.append('"')
                    i += 1
                else:
                    in_quotes = not in_quotes
            elif ch == "," and not in_quotes:
                result.append("".join(current))
                current = []
            else:
                current.append(ch)
            i += 1
        result.append("".join(current))
        return result

    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _parse_bool(value: Any) -> Optional[bool]:
        text = str(value or "").strip().lower()
        if text in {"1", "true", "t", "yes"}:
            return True
        if text in {"0", "false", "f", "no"}:
            return False
        return None

    def _connect_sqlite(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_schema(self, db_path: str) -> None:
        with self._sqlite_lock, self._connect_sqlite(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ring_events (
                    id TEXT PRIMARY KEY,
                    cam_id TEXT NOT NULL,
                    camera_name TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    created_at TEXT NULL,
                    created_at_local TEXT NULL,
                    ding_ts REAL NULL,
                    answered INTEGER NULL,
                    state TEXT NULL,
                    source TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    stored_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ring_events_ding_ts ON ring_events(ding_ts DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ring_events_kind ON ring_events(kind)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ring_events_stored_at ON ring_events(stored_at DESC)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ring_event_meta (
                    meta_key TEXT PRIMARY KEY,
                    meta_value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ring_event_meta_updated_at ON ring_event_meta(updated_at DESC)")
            conn.commit()

    def _write_sqlite_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        db_path = self._resolve_sqlite_path(config)
        self._init_sqlite_schema(db_path)
        with self._sqlite_lock, self._connect_sqlite(db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO ring_events (
                    id, cam_id, camera_name, device_id, kind, trigger,
                    created_at, created_at_local, ding_ts, answered, state, source,
                    payload_json, stored_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event.get("cam_id") or "",
                    event.get("camera_name") or "",
                    event.get("device_id") or "",
                    event.get("kind") or "unknown",
                    event.get("trigger") or event.get("kind") or "unknown",
                    event.get("created_at"),
                    event.get("created_at_local"),
                    event.get("ding_ts"),
                    self._to_nullable_int(event.get("answered")),
                    str(event.get("state")) if event.get("state") is not None else None,
                    event.get("source") or "ring_api",
                    json.dumps(event, ensure_ascii=False),
                    time.time(),
                ),
            )
            conn.commit()
        self._enforce_sqlite_retention(config)

    @staticmethod
    def _to_nullable_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        return 1 if bool(value) else 0

    def _enforce_sqlite_retention(self, config: Dict[str, Any]) -> None:
        db_path = self._resolve_sqlite_path(config)
        max_entries = max(100, min(int(config.get("max_entries") or 2000), 50000))
        with self._sqlite_lock, self._connect_sqlite(db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM ring_events").fetchone()
            total = int(row["count"] or 0)
            if total <= max_entries:
                return
            conn.execute(
                """
                DELETE FROM ring_events
                WHERE id IN (
                    SELECT id FROM ring_events
                    ORDER BY COALESCE(ding_ts, 0) DESC, COALESCE(created_at, '') DESC, stored_at DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (max_entries,),
            )
            conn.commit()

    def _read_sqlite_events(self, limit: int, kind_filter: Set[str], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        db_path = self._resolve_sqlite_path(config)
        if not os.path.exists(db_path):
            return []
        self._init_sqlite_schema(db_path)

        query = """
            SELECT payload_json
            FROM ring_events
        """
        params: List[Any] = []
        if kind_filter:
            placeholders = ", ".join("?" for _ in kind_filter)
            query += f" WHERE lower(kind) IN ({placeholders})"
            params.extend(sorted(kind_filter))
        query += " ORDER BY COALESCE(ding_ts, 0) DESC, COALESCE(created_at, '') DESC, stored_at DESC LIMIT ?"
        params.append(limit)

        with self._sqlite_lock, self._connect_sqlite(db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            try:
                item = json.loads(row["payload_json"]) if row["payload_json"] else {}
            except Exception:
                item = {}
            if isinstance(item, dict) and item.get("id"):
                result.append(self._normalize_event(item))
        return result

    def _write_sqlite_health(self, snapshot: Dict[str, Any], config: Dict[str, Any]) -> None:
        db_path = self._resolve_sqlite_path(config)
        self._init_sqlite_schema(db_path)
        with self._sqlite_lock, self._connect_sqlite(db_path) as conn:
            for key, value in snapshot.items():
                conn.execute(
                    """
                    INSERT INTO ring_event_meta (meta_key, meta_value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(meta_key) DO UPDATE SET
                        meta_value = excluded.meta_value,
                        updated_at = excluded.updated_at
                    """,
                    (key, json.dumps(value, ensure_ascii=False), time.time()),
                )
            conn.commit()

    def _read_sqlite_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        db_path = self._resolve_sqlite_path(config)
        if not os.path.exists(db_path):
            return {}
        self._init_sqlite_schema(db_path)
        result: Dict[str, Any] = {}
        with self._sqlite_lock, self._connect_sqlite(db_path) as conn:
            rows = conn.execute("SELECT meta_key, meta_value FROM ring_event_meta").fetchall()
        for row in rows:
            try:
                result[str(row["meta_key"])] = json.loads(row["meta_value"])
            except Exception:
                result[str(row["meta_key"])] = row["meta_value"]
        return result
