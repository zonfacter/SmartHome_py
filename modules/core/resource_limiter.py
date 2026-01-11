"""
Resource Limiter v1.0.0
CPU-Throttling für ressourcenintensive Prozesse/Threads

📁 SPEICHERORT: modules/core/resource_limiter.py

Features:
- CPU-Monitoring pro Prozess
- Automatisches Throttling bei Überlast
- Nice-Value basierte Drosselung
- Monitoring-Statistiken
- Thread-safe
"""

import psutil
import threading
import time
import os
from typing import Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class ProcessInfo:
    """Process Monitoring Info"""
    pid: int
    name: str
    added_at: float = field(default_factory=time.time)
    cpu_history: List[float] = field(default_factory=list)
    throttled: bool = False
    throttled_at: Optional[float] = None
    nice_value: int = 0


class ResourceLimiter:
    """
    CPU-Throttling für Prozesse/Threads

    Überwacht Prozesse und throttled automatisch bei Überschreitung
    des CPU-Limits via nice-Value Anpassung.
    """

    def __init__(self, cpu_limit_percent: int = 50, check_interval: int = 5,
                 history_size: int = 10):
        """
        Args:
            cpu_limit_percent: CPU-Limit in Prozent (Default: 50%)
            check_interval: Prüf-Intervall in Sekunden (Default: 5s)
            history_size: Anzahl CPU-Messungen für Durchschnitt (Default: 10)
        """
        self.cpu_limit = cpu_limit_percent
        self.check_interval = check_interval
        self.history_size = history_size

        # Monitored Processes
        self.monitored_processes: Dict[int, ProcessInfo] = {}

        # Monitoring Thread
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()

        # Statistics
        self.stats = {
            'checks_total': 0,
            'throttles_total': 0,
            'unthrottles_total': 0
        }

    def start_monitoring(self):
        """Startet Resource-Monitoring Thread"""
        if self.running:
            print("  ⚠️  Resource Limiter läuft bereits")
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ResourceLimiter"
        )
        self.monitor_thread.start()

        print(f"  ⚡ Resource Limiter gestartet (CPU-Limit: {self.cpu_limit}%, Intervall: {self.check_interval}s)")

    def stop_monitoring(self):
        """Stoppt Resource-Monitoring"""
        if not self.running:
            return

        self.running = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=self.check_interval + 2)

        # Reset all throttled processes
        with self.lock:
            for pid, info in list(self.monitored_processes.items()):
                if info.throttled:
                    try:
                        process = psutil.Process(pid)
                        process.nice(0)  # Reset to default
                        print(f"  ✅ Process {info.name} (PID {pid}) reset zu default nice")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

        print("  🛑 Resource Limiter gestoppt")

    def add_process(self, pid: int, name: str):
        """
        Fügt Prozess zum Monitoring hinzu

        Args:
            pid: Process ID
            name: Process Name (für Logging)
        """
        with self.lock:
            if pid in self.monitored_processes:
                print(f"  ⚠️  Process {name} (PID {pid}) bereits im Monitoring")
                return

            self.monitored_processes[pid] = ProcessInfo(
                pid=pid,
                name=name
            )

            print(f"  📊 Process {name} (PID {pid}) zum Resource-Monitoring hinzugefügt")

    def remove_process(self, pid: int):
        """
        Entfernt Prozess aus Monitoring

        Args:
            pid: Process ID
        """
        with self.lock:
            if pid in self.monitored_processes:
                info = self.monitored_processes[pid]

                # Reset nice wenn throttled
                if info.throttled:
                    try:
                        process = psutil.Process(pid)
                        process.nice(0)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                del self.monitored_processes[pid]
                print(f"  📊 Process {info.name} (PID {pid}) aus Monitoring entfernt")

    def _monitor_loop(self):
        """Monitoring Loop"""
        while self.running:
            with self.lock:
                for pid, info in list(self.monitored_processes.items()):
                    try:
                        self._check_and_throttle(pid, info)
                        self.stats['checks_total'] += 1

                    except psutil.NoSuchProcess:
                        # Process existiert nicht mehr
                        del self.monitored_processes[pid]
                        print(f"  ℹ️  Process {info.name} (PID {pid}) nicht mehr existent")

                    except psutil.AccessDenied:
                        # Keine Berechtigung
                        print(f"  ⚠️  Keine Berechtigung für Process {info.name} (PID {pid})")

                    except Exception as e:
                        print(f"  ⚠️  Monitoring-Fehler für PID {pid}: {e}")

            time.sleep(self.check_interval)

    def _check_and_throttle(self, pid: int, info: ProcessInfo):
        """
        Prüft CPU-Nutzung und throttled bei Bedarf

        Args:
            pid: Process ID
            info: ProcessInfo
        """
        try:
            process = psutil.Process(pid)

            # CPU-Messung (über 1 Sekunde)
            cpu_percent = process.cpu_percent(interval=1.0)

            # CPU-History aktualisieren
            info.cpu_history.append(cpu_percent)
            if len(info.cpu_history) > self.history_size:
                info.cpu_history.pop(0)

            # Durchschnitt letzte N Messungen
            avg_cpu = sum(info.cpu_history) / len(info.cpu_history)

            # CPU-Limit überschritten?
            if avg_cpu > self.cpu_limit and not info.throttled:
                self._throttle_process(process, info, avg_cpu)

            # CPU wieder niedrig? Un-throttle
            elif avg_cpu < self.cpu_limit * 0.8 and info.throttled:
                self._unthrottle_process(process, info, avg_cpu)

        except Exception as e:
            raise  # Re-raise für Handler in _monitor_loop

    def _throttle_process(self, process: psutil.Process, info: ProcessInfo, cpu_percent: float):
        """
        Throttled Process via nice-Value

        Args:
            process: psutil Process
            info: ProcessInfo
            cpu_percent: Aktuelle CPU-Auslastung
        """
        try:
            # Hole aktuellen nice-Value
            current_nice = process.nice()

            # Erhöhe nice (niedrigere Priorität)
            # Linux: -20 (höchste) bis 19 (niedrigste)
            # Windows: IDLE_PRIORITY_CLASS, BELOW_NORMAL_PRIORITY_CLASS, etc.
            if os.name == 'posix':  # Linux/Unix
                new_nice = min(current_nice + 5, 19)
                process.nice(new_nice)
            else:  # Windows
                # Windows: psutil.BELOW_NORMAL_PRIORITY_CLASS
                try:
                    process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    new_nice = psutil.BELOW_NORMAL_PRIORITY_CLASS
                except:
                    new_nice = current_nice

            # Update Info
            info.throttled = True
            info.throttled_at = time.time()
            info.nice_value = new_nice

            self.stats['throttles_total'] += 1

            print(f"  ⚠️  THROTTLED: {info.name} (PID {info.pid}) - CPU: {cpu_percent:.1f}% → nice: {new_nice}")

        except Exception as e:
            print(f"  ⚠️  Throttling fehlgeschlagen für {info.name} (PID {info.pid}): {e}")

    def _unthrottle_process(self, process: psutil.Process, info: ProcessInfo, cpu_percent: float):
        """
        Un-throttled Process (Reset nice-Value)

        Args:
            process: psutil Process
            info: ProcessInfo
            cpu_percent: Aktuelle CPU-Auslastung
        """
        try:
            # Reset nice zu default (0 / NORMAL_PRIORITY_CLASS)
            if os.name == 'posix':
                process.nice(0)
            else:
                try:
                    process.nice(psutil.NORMAL_PRIORITY_CLASS)
                except:
                    pass

            # Update Info
            info.throttled = False
            info.throttled_at = None
            info.nice_value = 0

            self.stats['unthrottles_total'] += 1

            print(f"  ✅ UN-THROTTLED: {info.name} (PID {info.pid}) - CPU: {cpu_percent:.1f}%")

        except Exception as e:
            print(f"  ⚠️  Un-Throttling fehlgeschlagen für {info.name} (PID {info.pid}): {e}")

    def get_stats(self) -> dict:
        """
        Liefert Monitoring-Statistiken

        Returns:
            Dictionary mit Stats
        """
        with self.lock:
            monitored = len(self.monitored_processes)
            throttled = sum(1 for info in self.monitored_processes.values() if info.throttled)

            processes = {}
            for pid, info in self.monitored_processes.items():
                avg_cpu = sum(info.cpu_history) / len(info.cpu_history) if info.cpu_history else 0

                processes[pid] = {
                    'name': info.name,
                    'throttled': info.throttled,
                    'cpu_avg': round(avg_cpu, 2),
                    'nice_value': info.nice_value,
                    'throttled_duration': time.time() - info.throttled_at if info.throttled_at else None
                }

            return {
                'cpu_limit': self.cpu_limit,
                'check_interval': self.check_interval,
                'monitored': monitored,
                'throttled': throttled,
                'checks_total': self.stats['checks_total'],
                'throttles_total': self.stats['throttles_total'],
                'unthrottles_total': self.stats['unthrottles_total'],
                'processes': processes
            }

    def get_process_info(self, pid: int) -> Optional[dict]:
        """
        Holt Info über einen Prozess

        Args:
            pid: Process ID

        Returns:
            Process Info oder None
        """
        with self.lock:
            if pid not in self.monitored_processes:
                return None

            info = self.monitored_processes[pid]
            avg_cpu = sum(info.cpu_history) / len(info.cpu_history) if info.cpu_history else 0

            return {
                'pid': pid,
                'name': info.name,
                'throttled': info.throttled,
                'cpu_avg': round(avg_cpu, 2),
                'cpu_history': info.cpu_history,
                'nice_value': info.nice_value,
                'added_at': info.added_at,
                'throttled_at': info.throttled_at
            }


# ========================================================================
# HELPER FUNCTION
# ========================================================================

def get_current_process_id() -> int:
    """Liefert PID des aktuellen Prozesses"""
    return os.getpid()


def is_process_running(pid: int) -> bool:
    """Prüft ob Prozess läuft"""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
