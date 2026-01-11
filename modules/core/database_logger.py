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
from datetime import datetime
from typing import Optional


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
            # Ordner erstellen falls nicht existent
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        module TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Index für Performance
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON system_logs(timestamp DESC)
                ''')

                # Auto-Cleanup: Behalte nur die letzten 1000 Einträge
                conn.execute("""
                    DELETE FROM system_logs
                    WHERE id NOT IN (
                        SELECT id FROM system_logs
                        ORDER BY id DESC
                        LIMIT 1000
                    )
                """)

        except Exception as e:
            print(f"!!! LOGGING DATABASE ERROR: {e}")

    def emit(self, record: logging.LogRecord):
        """Schreibt Log-Eintrag in Datenbank"""
        # Nur WARNING und höher speichern
        if record.levelno >= logging.WARNING:
            try:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = self.format(record)

                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO system_logs (timestamp, level, module, message) VALUES (?, ?, ?, ?)",
                        (ts, record.levelname, record.name, msg)
                    )

            except Exception:
                self.handleError(record)


class DatabaseLogger:
    """
    Database Logger Manager

    Verwaltet SQLite-Handler für das Root-Logger.
    Wird einmal beim Start initialisiert.
    """

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
