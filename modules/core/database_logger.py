"""
Database Logger Module
Version: 1.0.0
SQLite-basiertes Logging-System für strukturierte Fehleraufzeichnung

Ersetzt print() durch persistentes Logging.
Speichert WARNING, ERROR und CRITICAL in SQLite-Datenbank.
"""

import sqlite3
import logging
import os
import threading
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List


class SQLiteHandler(logging.Handler):
    """
    Logging-Handler, der kritische Meldungen in eine SQLite-DB schreibt.
    Filtert INFO/DEBUG automatisch heraus.

    Features:
    - Speichert nur WARNING, ERROR, CRITICAL
    - Auto-Cleanup: Behält nur letzte 1000 Einträge
    - Thread-safe
    - Automatische Tabellenerstellung
    """

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self._ensure_table()

        # Setze Level auf WARNING (filtert INFO/DEBUG aus)
        self.setLevel(logging.WARNING)

    def _ensure_table(self):
        """Erstellt Tabelle falls nicht vorhanden"""
        try:
            DatabaseLogger.ensure_schema(self.db_path)
            policy = DatabaseLogger.get_retention_policy()
            DatabaseLogger.enforce_retention(
                self.db_path,
                max_entries=policy['max_entries'],
                max_age_days=policy['max_age_days']
            )

        except Exception as e:
            print(f"!!! LOGGING DATABASE ERROR: {e}")

    def emit(self, record: logging.LogRecord):
        """Schreibt Log-Eintrag in Datenbank"""
        # Nur WARNING und höher speichern
        if record.levelno >= logging.WARNING:
            try:
                ts = DatabaseLogger._utc_timestamp()
                msg = self.format(record)
                DatabaseLogger._insert_log_entry(
                    self.db_path,
                    timestamp=ts,
                    level=record.levelname,
                    module=record.name,
                    message=msg
                )

            except Exception:
                self.handleError(record)


class DatabaseLogger:
    """
    Database Logger Manager

    Verwaltet SQLite-Handler für das Root-Logger.
    Wird einmal beim Start initialisiert.
    """

    _db_lock = threading.Lock()

    @staticmethod
    def _utc_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def get_retention_policy() -> Dict[str, int]:
        max_entries = int(os.getenv('SMARTHOME_AUDIT_RETENTION_MAX_ENTRIES', '20000'))
        max_age_days = int(os.getenv('SMARTHOME_AUDIT_RETENTION_DAYS', '90'))
        return {
            'max_entries': max(1000, max_entries),
            'max_age_days': max(1, max_age_days)
        }

    @staticmethod
    def ensure_schema(db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    message TEXT NOT NULL,
                    prev_hash TEXT,
                    entry_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Migration für ältere DBs
            columns = {row[1] for row in conn.execute("PRAGMA table_info(system_logs)")}
            if 'prev_hash' not in columns:
                conn.execute("ALTER TABLE system_logs ADD COLUMN prev_hash TEXT")
            if 'entry_hash' not in columns:
                conn.execute("ALTER TABLE system_logs ADD COLUMN entry_hash TEXT")

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON system_logs(timestamp DESC)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_entry_hash
                ON system_logs(entry_hash)
            ''')

    @staticmethod
    def _insert_log_entry(db_path: str, timestamp: str, level: str, module: str, message: str) -> int:
        with DatabaseLogger._db_lock:
            DatabaseLogger.ensure_schema(db_path)
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                prev_hash_row = conn.execute(
                    "SELECT entry_hash FROM system_logs ORDER BY id DESC LIMIT 1"
                ).fetchone()
                prev_hash = prev_hash_row['entry_hash'] if prev_hash_row and prev_hash_row['entry_hash'] else ''
                payload = f"{timestamp}|{level}|{module}|{message}|{prev_hash}"
                entry_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
                cursor = conn.execute(
                    """
                    INSERT INTO system_logs (timestamp, level, module, message, prev_hash, entry_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (timestamp, level, module, message, prev_hash, entry_hash)
                )
                return int(cursor.lastrowid or 0)

    @staticmethod
    def setup(db_path: Optional[str] = None, console_level: int = logging.INFO):
        """
        Konfiguriert globales Logging-System

        Args:
            db_path: Pfad zur SQLite-Datenbank (default: config/system_logs.db)
            console_level: Log-Level für Console-Output (default: INFO)
        """
        # Default-Pfad falls nicht angegeben
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'config', 'system_logs.db')
        DatabaseLogger.ensure_schema(db_path)

        # Root-Logger konfigurieren
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Fange alles ab

        # Entferne alte Handler
        root_logger.handlers.clear()

        # 1. Console-Handler (für INFO und höher)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter(
            '%(levelname)-8s [%(name)s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # 2. SQLite-Handler (für WARNING und höher)
        db_handler = SQLiteHandler(db_path)
        db_formatter = logging.Formatter(
            '%(levelname)s [%(name)s] %(message)s'
        )
        db_handler.setFormatter(db_formatter)
        root_logger.addHandler(db_handler)

        policy = DatabaseLogger.get_retention_policy()
        DatabaseLogger.enforce_retention(
            db_path,
            max_entries=policy['max_entries'],
            max_age_days=policy['max_age_days']
        )

        # Bestätigung
        logging.info(f"Database Logger initialisiert: {db_path}")

        return db_path

    @staticmethod
    def get_recent_logs(db_path: str, limit: int = 100) -> list:
        """
        Holt die neuesten Log-Einträge aus der Datenbank

        Args:
            db_path: Pfad zur Datenbank
            limit: Maximale Anzahl Einträge

        Returns:
            Liste von Dictionaries mit Log-Einträgen
        """
        logs = []

        try:
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM system_logs ORDER BY id DESC LIMIT ?",
                        (limit,)
                    )
                    logs = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Logs: {e}")

        return logs

    @staticmethod
    def clear_old_logs(db_path: str, keep_count: int = 1000):
        """
        Löscht alte Log-Einträge

        Args:
            db_path: Pfad zur Datenbank
            keep_count: Anzahl der neuesten Einträge, die behalten werden
        """
        try:
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    deleted = conn.execute("""
                        DELETE FROM system_logs
                        WHERE id NOT IN (
                            SELECT id FROM system_logs
                            ORDER BY id DESC
                            LIMIT ?
                        )
                    """, (keep_count,))

                    if deleted.rowcount > 0:
                        logging.info(f"Alte Logs gelöscht: {deleted.rowcount} Einträge")
        except Exception as e:
            logging.error(f"Fehler beim Löschen alter Logs: {e}")

    @staticmethod
    def clear_logs_with_audit_protection(
        db_path: str,
        keep_count: int = 100,
        preserve_keywords: Optional[list] = None
    ) -> int:
        """
        Löscht alte Log-Einträge, schützt aber Audit-relevante Meldungen.

        Args:
            db_path: Pfad zur Datenbank
            keep_count: Anzahl neuester Logs, die unabhängig erhalten bleiben
            preserve_keywords: Stichwörter, die im Message-Text immer erhalten bleiben

        Returns:
            Anzahl gelöschter Zeilen
        """
        if preserve_keywords is None:
            preserve_keywords = ["restart", "neustart", "unauthorized", "forbidden", "rate limit", "audit"]

        deleted_rows = 0
        try:
            if not os.path.exists(db_path):
                return 0

            keep_count = max(10, int(keep_count))
            with sqlite3.connect(db_path) as conn:
                where_keep = " OR ".join(["lower(message) LIKE ?"] * len(preserve_keywords))
                params = tuple(f"%{kw.lower()}%" for kw in preserve_keywords)
                query = f"""
                    DELETE FROM system_logs
                    WHERE id NOT IN (
                        SELECT id FROM system_logs
                        ORDER BY id DESC
                        LIMIT ?
                    )
                    AND level != 'AUDIT'
                    AND NOT ({where_keep})
                """
                cursor = conn.execute(query, (keep_count, *params))
                deleted_rows = int(getattr(cursor, "rowcount", 0) or 0)
        except Exception as e:
            logging.error(f"Fehler bei clear_logs_with_audit_protection: {e}")

        return deleted_rows

    @staticmethod
    def enforce_retention(db_path: str, max_entries: int = 20000, max_age_days: int = 90) -> Dict[str, int]:
        stats = {'deleted_age': 0, 'deleted_count': 0}
        if not os.path.exists(db_path):
            return stats

        with DatabaseLogger._db_lock:
            DatabaseLogger.ensure_schema(db_path)
            with sqlite3.connect(db_path) as conn:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
                deleted_age = conn.execute(
                    "DELETE FROM system_logs WHERE timestamp < ?",
                    (cutoff,)
                ).rowcount
                deleted_count = conn.execute(
                    """
                    DELETE FROM system_logs
                    WHERE id NOT IN (
                        SELECT id FROM system_logs ORDER BY id DESC LIMIT ?
                    )
                    """,
                    (max_entries,)
                ).rowcount
                stats['deleted_age'] = max(0, int(deleted_age or 0))
                stats['deleted_count'] = max(0, int(deleted_count or 0))
        return stats

    @staticmethod
    def audit_event(db_path: str, action: str, actor: str, details: Optional[Dict[str, Any]] = None) -> int:
        payload = {
            'action': action,
            'actor': actor,
            'details': details or {}
        }
        message = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        return DatabaseLogger._insert_log_entry(
            db_path=db_path,
            timestamp=DatabaseLogger._utc_timestamp(),
            level='AUDIT',
            module='audit',
            message=message
        )

    @staticmethod
    def verify_chain(db_path: str, limit: Optional[int] = None) -> Dict[str, Any]:
        if not os.path.exists(db_path):
            return {'ok': True, 'checked': 0, 'broken_at_id': None}

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT id, timestamp, level, module, message, prev_hash, entry_hash FROM system_logs ORDER BY id ASC"
            params: tuple = ()
            if limit is not None:
                query += " LIMIT ?"
                params = (int(limit),)
            rows: List[sqlite3.Row] = conn.execute(query, params).fetchall()

        prev_hash = ''
        checked = 0
        for row in rows:
            checked += 1
            row_prev_hash = row['prev_hash'] or ''
            row_entry_hash = row['entry_hash'] or ''
            if not row_entry_hash:
                continue
            source = f"{row['timestamp']}|{row['level']}|{row['module']}|{row['message']}|{row_prev_hash}"
            expected = hashlib.sha256(source.encode('utf-8')).hexdigest()
            if row_prev_hash != prev_hash or row_entry_hash != expected:
                return {'ok': False, 'checked': checked, 'broken_at_id': row['id']}
            prev_hash = row_entry_hash
        return {'ok': True, 'checked': checked, 'broken_at_id': None}

    @staticmethod
    def export_logs(db_path: str, limit: int = 1000) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 50000))
        return DatabaseLogger.get_recent_logs(db_path, limit=limit)


# Beispiel-Usage
if __name__ == '__main__':
    # Setup
    db_path = DatabaseLogger.setup()

    # Test-Logs
    logger = logging.getLogger("TestModule")
    logger.debug("Debug-Nachricht (wird nicht in DB gespeichert)")
    logger.info("Info-Nachricht (wird nicht in DB gespeichert)")
    logger.warning("Test-Warning (wird gespeichert)")
    logger.error("Test-Error (wird gespeichert)")

    # Logs abrufen
    logs = DatabaseLogger.get_recent_logs(db_path)
    print(f"\nGespeicherte Logs: {len(logs)}")
    for log in logs:
        print(f"  [{log['level']}] {log['module']}: {log['message']}")
