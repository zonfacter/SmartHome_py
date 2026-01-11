"""
Service Manager Module
Version: 1.0.0
Verwaltet den Lebenszyklus des Hauptprozesses

Features:
- Hot-Restart ohne Reboot
- Windows & Linux Support
- Docker-Container-freundlich
- Process-Argument-Preservation
"""

import sys
import os
import subprocess
import platform
import logging
import time


class ServiceManager:
    """
    Verwaltet den Lebenszyklus des Hauptprozesses.
    Erlaubt 'Hot-Restarts' um Plugins neu zu laden oder Konfiguration anzuwenden.

    Platform Support:
    - Windows: Startet neuen Prozess mit subprocess
    - Linux: Nutzt os.execv (behält PID)
    - Docker: Nutzt os.execv (Container-freundlich)
    """

    @staticmethod
    def restart_service() -> bool:
        """
        Startet den Service neu

        Returns:
            False bei Fehler, sonst erfolgt Neustart (keine Rückkehr)
        """
        logger = logging.getLogger("ServiceManager")
        logger.warning("🔄 SYSTEM RESTART INITIATED via Web-Admin")

        try:
            # Aktuellen Python-Interpreter und Argumente holen
            python = sys.executable
            args = sys.argv[:]

            # Flag hinzufügen, damit wir im Log sehen, dass es ein Restart war
            if "--restarted" not in args:
                args.append("--restarted")

            # Buffer flushen
            sys.stdout.flush()
            sys.stderr.flush()

            system_platform = platform.system()

            if system_platform == "Windows":
                logger.info("Windows-Umgebung erkannt. Starte subprocess...")

                # Windows benötigt einen neuen Prozess
                # CREATE_NEW_CONSOLE = Neues Konsolenfenster (sichtbar)
                # DETACHED_PROCESS = Kein Konsolenfenster (unsichtbar, aber funktioniert nicht immer)
                # Wir verwenden CREATE_NEW_CONSOLE für Debugging
                import subprocess

                # Working Directory beibehalten
                cwd = os.getcwd()

                # Neuen Prozess starten (mit SICHTBAREM Konsolenfenster für Debugging)
                # CREATE_NEW_CONSOLE = 0x00000010
                process = subprocess.Popen(
                    [python] + args,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,  # Sichtbares Fenster!
                    cwd=cwd
                )

                logger.info(f"Neuer Prozess gestartet (PID: {process.pid}). Beende alten Prozess...")

                # Kleiner Delay für sauberen Shutdown
                time.sleep(0.5)

                # Alten Prozess hart beenden
                os._exit(0)

            else:
                # Linux/Docker: Wir ersetzen den aktuellen Prozess (behält PID)
                logger.info("Linux/Docker-Umgebung erkannt. Führe execv aus...")

                # execv ersetzt den aktuellen Prozess komplett
                # Wichtig: Der erste Argument muss der Programm-Name sein
                os.execv(python, [python] + args)

                # Diese Zeile wird NIE erreicht (Prozess wurde ersetzt)

        except Exception as e:
            logger.error(f"❌ CRITICAL: Restart failed: {e}", exc_info=True)
            return False

    @staticmethod
    def get_restart_info() -> dict:
        """
        Gibt Informationen über den letzten Restart zurück

        Returns:
            Dictionary mit Restart-Informationen
        """
        return {
            'platform': platform.system(),
            'python': sys.executable,
            'args': sys.argv,
            'is_restarted': '--restarted' in sys.argv,
            'pid': os.getpid()
        }

    @staticmethod
    def schedule_restart(delay_seconds: int = 2):
        """
        Plant einen verzögerten Restart

        Args:
            delay_seconds: Verzögerung in Sekunden

        Nützlich um HTTP-Response noch zu senden bevor Restart erfolgt.
        """
        import threading

        def delayed_restart():
            logger = logging.getLogger("ServiceManager")
            logger.info(f"Restart in {delay_seconds} Sekunden geplant...")
            time.sleep(delay_seconds)
            ServiceManager.restart_service()

        restart_thread = threading.Thread(target=delayed_restart, daemon=True)
        restart_thread.start()

        return True


# Test-Code
if __name__ == '__main__':
    # Setup Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)-8s [%(name)s] %(message)s'
    )

    logger = logging.getLogger("Test")

    # Zeige Restart-Info
    info = ServiceManager.get_restart_info()
    logger.info(f"Platform: {info['platform']}")
    logger.info(f"Python: {info['python']}")
    logger.info(f"Args: {info['args']}")
    logger.info(f"Is Restarted: {info['is_restarted']}")
    logger.info(f"PID: {info['pid']}")

    # Test Restart (nur wenn explizit gewünscht)
    if '--test-restart' in sys.argv:
        logger.warning("⚠️ Test-Restart wird in 3 Sekunden durchgeführt...")
        time.sleep(3)
        ServiceManager.restart_service()
    else:
        logger.info("Kein Test-Restart durchgeführt (verwende --test-restart)")
