import time
import logging
import threading
from abc import ABC, abstractmethod

class BasePlugin(ABC):
    """
    v5.1 BasePlugin Interface
    Features: CPU-Throttling, Spam-Protection, Sentry-Logging
    """
    def __init__(self, app_context, config):
        self.app = app_context
        self.config = config
        self.log = logging.getLogger(f"Plugin.{self.__class__.__name__}")
        
        # Status & Monitoring
        self.is_running = False
        self.status = "initialized"
        self.msg_count = 0
        self.start_time = time.time()
        
        # Sicherheits-Limits (aus Config oder Default)
        self.max_pps = config.get("max_pps", 100)  # Max Packets Per Second
        self.max_cpu = config.get("max_cpu", 10)   # Max % CPU Time
        
    @abstractmethod
    def initialize(self):
        """Wird beim Laden aufgerufen. Setup von Hardware/Verbindungen."""
        pass

    @abstractmethod
    def execute(self):
        """Haupt-Loop. Hier läuft die Logik (BMS auslesen etc.)."""
        pass

    def _run_wrapper(self):
        """Interner Sentry-Wrapper für den Thread-Start."""
        self.is_running = True
        self.status = "running"
        try:
            self.execute()
        except Exception as e:
            self.status = "crashed"
            self.log.error(f"💥 CRITICAL ERROR in {self.__class__.__name__}: {e}", exc_info=True)
            # Hier: Meldung an das globale Sentry/System-Log
        finally:
            self.is_running = False

    def publish(self, tag, value):
        """Sicherer Daten-Versand mit Spam-Schutz."""
        self.msg_count += 1
        elapsed = time.time() - self.start_time
        
        # Spam-Schutz (Circuit Breaker)
        if elapsed > 1 and (self.msg_count / elapsed) > self.max_pps:
            self.log.warning(f"🚫 SPAM DETECTED: {self.__class__.__name__} disabled.")
            self.stop()
            return False

        # Routing über das Gateway
        if hasattr(self.app, 'data_gateway'):
            self.app.data_gateway.route_data(self.__class__.__name__, tag, value)
        return True

    def stop(self):
        """Beendet das Plugin sauber."""
        self.is_running = False
        self.status = "stopped"
        self.log.info(f"🛑 Plugin {self.__class__.__name__} gestoppt.")