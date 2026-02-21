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
import signal
from typing import Tuple


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
    def is_container_runtime() -> bool:
        """Erkennt Docker/Kubernetes Laufzeitumgebungen robust."""
        if os.path.exists('/.dockerenv'):
            return True
        if os.environ.get('KUBERNETES_SERVICE_HOST'):
            return True
        try:
            with open('/proc/1/cgroup', 'r', encoding='utf-8') as f:
                cgroup = f.read().lower()
            return ('docker' in cgroup) or ('kubepods' in cgroup) or ('containerd' in cgroup)
        except Exception:
            return False

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
            cwd = os.getcwd()

            if ServiceManager.is_container_runtime():
                logger.warning("Container-Runtime erkannt: sende SIGTERM fuer orchestrator-konformen Neustart")
                os.kill(os.getpid(), signal.SIGTERM)
                return True

            # Robuster Restart über separaten Prozess:
            # vermeidet Socket-FD-Vererbung/Port-Konflikte bei execv.
            if system_platform == "Windows":
                process = subprocess.Popen(
                    [python] + args,
                    cwd=cwd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True
                )
            else:
                process = subprocess.Popen(
                    [python] + args,
                    cwd=cwd,
                    start_new_session=True,
                    close_fds=True
                )

            logger.info(f"Neuer Prozess gestartet (PID: {process.pid}). Beende alten Prozess...")
            time.sleep(0.5)
            os._exit(0)

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
            'pid': os.getpid(),
            'is_container_runtime': ServiceManager.is_container_runtime(),
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

    @staticmethod
    def _ctl_script_path() -> str:
        """Absoluter Pfad zum lokalen Service-Control-Script."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(project_root, 'scripts', 'web_server_ctl.sh')

    @staticmethod
    def schedule_ctl_restart(delay_seconds: int = 1) -> Tuple[bool, str]:
        """
        Plant einen Neustart über scripts/web_server_ctl.sh restart.

        Returns:
            (success, message)
        """
        if ServiceManager.is_container_runtime():
            return False, "Dienst-Neustart via daemon-Script ist im Container deaktiviert (nutze Container-Restart-Policy)"

        script_path = ServiceManager._ctl_script_path()
        if not os.path.exists(script_path):
            return False, f"Control-Script nicht gefunden: {script_path}"

        delay = max(0, min(int(delay_seconds), 30))
        import threading

        def delayed_restart():
            logger = logging.getLogger("ServiceManager")
            logger.warning(f"🔄 SERVICE CTL RESTART geplant in {delay}s via {script_path}")
            time.sleep(delay)
            try:
                subprocess.Popen(
                    ['bash', script_path, 'restart'],
                    cwd=os.path.dirname(script_path),
                    start_new_session=True,
                    close_fds=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                logger.error(f"CTL-Restart konnte nicht gestartet werden: {e}", exc_info=True)

        restart_thread = threading.Thread(target=delayed_restart, daemon=True)
        restart_thread.start()
        return True, f"Dienst-Neustart via Script in {delay}s geplant"


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
