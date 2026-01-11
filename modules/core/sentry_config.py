"""
Sentry Configuration Module
Zentrale Sentry-Integration für Error Tracking

📁 SPEICHERORT: modules/core/sentry_config.py
"""

import os
import sys
import platform
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration
from typing import Optional


class SentryManager:
    """
    Verwaltet Sentry-Integration für das gesamte System
    """

    def __init__(self):
        self.initialized = False
        self.dsn = None
        self.environment = "production"
        self.release = None

    def initialize(
        self,
        dsn: Optional[str] = None,
        environment: str = "production",
        release: Optional[str] = None,
        traces_sample_rate: float = 0.1,
        profiles_sample_rate: float = 0.1,
        enable_tracing: bool = True
    ):
        """
        Initialisiert Sentry SDK

        Args:
            dsn: Sentry DSN (falls None, wird aus Umgebungsvariable gelesen)
            environment: Umgebung (production, development, testing)
            release: Release-Version
            traces_sample_rate: Sampling-Rate für Performance-Traces (0.0-1.0)
            profiles_sample_rate: Sampling-Rate für Profiling (0.0-1.0)
            enable_tracing: Performance Monitoring aktivieren
        """
        # DSN aus Umgebungsvariable oder Parameter
        self.dsn = dsn or os.getenv('SENTRY_DSN')

        if not self.dsn:
            print("  [WARNING] Sentry DSN nicht gesetzt - Error Tracking deaktiviert")
            print("  [INFO] Setze SENTRY_DSN Umgebungsvariable oder übergebe DSN an initialize()")
            return False

        self.environment = environment
        self.release = release or self._get_version()

        try:
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                release=self.release,
                traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
                profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
                integrations=[
                    FlaskIntegration(
                        transaction_style="url"
                    ),
                    ThreadingIntegration(
                        propagate_hub=True
                    )
                ],
                # Zusätzliche Konfiguration
                attach_stacktrace=True,
                send_default_pii=False,  # Keine persönlichen Daten senden
                before_send=self._before_send,
                before_breadcrumb=self._before_breadcrumb
            )

            # Setze globale Tags
            sentry_sdk.set_tag("platform", platform.system())
            sentry_sdk.set_tag("python_version", platform.python_version())
            sentry_sdk.set_tag("architecture", platform.machine())

            self.initialized = True
            print(f"  [OK] Sentry initialisiert (Environment: {self.environment}, Release: {self.release})")
            return True

        except Exception as e:
            print(f"  [ERROR] Sentry Initialisierung fehlgeschlagen: {e}")
            return False

    def _get_version(self) -> str:
        """Ermittelt die Projekt-Version"""
        try:
            # Versuche Version aus version.txt zu lesen
            version_file = os.path.join(os.getcwd(), 'version.txt')
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    return f.read().strip()
        except:
            pass

        return "dev-unknown"

    def _before_send(self, event, hint):
        """
        Filter-Funktion die vor dem Senden eines Events aufgerufen wird
        Kann verwendet werden um sensible Daten zu entfernen
        """
        # Entferne potentiell sensible Request-Header
        if 'request' in event:
            if 'headers' in event['request']:
                sensitive_headers = ['Authorization', 'Cookie', 'X-Api-Key']
                for header in sensitive_headers:
                    if header in event['request']['headers']:
                        event['request']['headers'][header] = '[Filtered]'

        return event

    def _before_breadcrumb(self, crumb, hint):
        """
        Filter-Funktion für Breadcrumbs
        """
        # Filtere sensible Query-Parameter
        if crumb.get('category') == 'httplib':
            if 'data' in crumb:
                if 'url' in crumb['data']:
                    # Entferne Passwörter aus URLs
                    crumb['data']['url'] = crumb['data']['url'].replace(
                        'password=', 'password=[Filtered]'
                    )

        return crumb

    def capture_exception(self, exception: Exception, **kwargs):
        """
        Sendet eine Exception an Sentry

        Args:
            exception: Die Exception
            **kwargs: Zusätzliche Kontext-Daten
        """
        if not self.initialized:
            return

        with sentry_sdk.push_scope() as scope:
            # Füge zusätzlichen Kontext hinzu
            for key, value in kwargs.items():
                scope.set_extra(key, value)

            sentry_sdk.capture_exception(exception)

    def capture_message(self, message: str, level: str = "info", **kwargs):
        """
        Sendet eine Nachricht an Sentry

        Args:
            message: Die Nachricht
            level: Log-Level (debug, info, warning, error, fatal)
            **kwargs: Zusätzliche Kontext-Daten
        """
        if not self.initialized:
            return

        with sentry_sdk.push_scope() as scope:
            for key, value in kwargs.items():
                scope.set_extra(key, value)

            sentry_sdk.capture_message(message, level=level)

    def set_user(self, user_id: Optional[str] = None, **kwargs):
        """
        Setzt User-Kontext für Sentry

        Args:
            user_id: User-ID
            **kwargs: Zusätzliche User-Daten (username, email, ip_address)
        """
        if not self.initialized:
            return

        user_data = {}
        if user_id:
            user_data['id'] = user_id

        user_data.update(kwargs)
        sentry_sdk.set_user(user_data)

    def set_context(self, key: str, value: dict):
        """
        Setzt zusätzlichen Kontext für Sentry

        Args:
            key: Kontext-Key
            value: Kontext-Daten (dict)
        """
        if not self.initialized:
            return

        sentry_sdk.set_context(key, value)

    def add_breadcrumb(self, message: str, category: str = "default", level: str = "info", **data):
        """
        Fügt einen Breadcrumb hinzu (für Event-Trace)

        Args:
            message: Breadcrumb-Nachricht
            category: Kategorie (z.B. "auth", "query", "navigation")
            level: Level (debug, info, warning, error, fatal)
            **data: Zusätzliche Daten
        """
        if not self.initialized:
            return

        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            level=level,
            data=data
        )

    def start_transaction(self, name: str, op: str = "task"):
        """
        Startet eine Performance-Transaction

        Args:
            name: Transaction-Name
            op: Operation-Type (task, http, db, etc.)

        Returns:
            Transaction-Objekt (use as context manager)
        """
        if not self.initialized:
            return None

        return sentry_sdk.start_transaction(name=name, op=op)


# Globale Sentry-Instanz
_sentry_manager = None


def get_sentry_manager() -> SentryManager:
    """
    Holt die globale Sentry-Manager Instanz

    Returns:
        SentryManager Singleton
    """
    global _sentry_manager
    if _sentry_manager is None:
        _sentry_manager = SentryManager()
    return _sentry_manager


def init_sentry(**kwargs):
    """
    Convenience-Funktion zum Initialisieren von Sentry

    Args:
        **kwargs: Parameter für SentryManager.initialize()

    Returns:
        bool: True wenn erfolgreich
    """
    manager = get_sentry_manager()
    return manager.initialize(**kwargs)
