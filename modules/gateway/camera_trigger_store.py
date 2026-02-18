"""
SQLite-backed store for camera trigger rules.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, List


class CameraTriggerStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trigger_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    variable TEXT NOT NULL,
                    operator TEXT NOT NULL DEFAULT 'eq',
                    on_value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    tags TEXT NOT NULL DEFAULT '[]',
                    camera_id TEXT NOT NULL,
                    camera_type TEXT NOT NULL DEFAULT 'ring',
                    duration_seconds INTEGER NOT NULL DEFAULT 30,
                    cooldown_seconds INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            # Migrations for existing DBs
            cols = {row[1] for row in conn.execute("PRAGMA table_info(trigger_rules)").fetchall()}
            if "category" not in cols:
                conn.execute("ALTER TABLE trigger_rules ADD COLUMN category TEXT NOT NULL DEFAULT 'general'")
            if "tags" not in cols:
                conn.execute("ALTER TABLE trigger_rules ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")

    @staticmethod
    def _decode_value(raw: str) -> Any:
        try:
            return json.loads(raw)
        except Exception:
            return raw

    @staticmethod
    def _encode_value(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    def list_rules(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, enabled, variable, operator, on_value, category, tags, camera_id, camera_type,
                       duration_seconds, cooldown_seconds, created_at, updated_at
                FROM trigger_rules
                ORDER BY updated_at DESC, id ASC
                """
            ).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            tags = self._decode_value(row["tags"]) if row["tags"] else []
            if not isinstance(tags, list):
                tags = []
            result.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "enabled": bool(row["enabled"]),
                    "variable": row["variable"],
                    "operator": row["operator"],
                    "on_value": self._decode_value(row["on_value"]),
                    "category": (row["category"] or "general"),
                    "tags": tags,
                    "camera_id": row["camera_id"],
                    "camera_type": row["camera_type"],
                    "duration_seconds": int(row["duration_seconds"]),
                    "cooldown_seconds": int(row["cooldown_seconds"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return result

    def replace_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = time.time()
        with self._connect() as conn:
            conn.execute("DELETE FROM trigger_rules")
            for r in rules:
                rule_id = str(r.get("id") or "").strip()
                if not rule_id:
                    continue
                conn.execute(
                    """
                    INSERT INTO trigger_rules (
                        id, name, enabled, variable, operator, on_value, category, tags, camera_id, camera_type,
                        duration_seconds, cooldown_seconds, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rule_id,
                        str(r.get("name") or rule_id),
                        1 if bool(r.get("enabled", True)) else 0,
                        str(r.get("variable") or ""),
                        str(r.get("operator") or "eq"),
                        self._encode_value(r.get("on_value", True)),
                        str(r.get("category") or "general"),
                        self._encode_value(r.get("tags") if isinstance(r.get("tags"), list) else []),
                        str(r.get("camera_id") or ""),
                        str(r.get("camera_type") or "ring"),
                        max(5, min(int(r.get("duration_seconds", 30)), 300)),
                        max(0, min(int(r.get("cooldown_seconds", 0)), 3600)),
                        float(r.get("created_at") or now),
                        now,
                    ),
                )
        return self.list_rules()

    def is_empty(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM trigger_rules").fetchone()
            return int(row["c"]) == 0

    def import_legacy_json(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            rules = data.get("rules")
            if not isinstance(rules, list):
                return False
            self.replace_rules(rules)
            return True
        except Exception:
            return False
