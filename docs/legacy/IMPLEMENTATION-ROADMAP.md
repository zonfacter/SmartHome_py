# SmartHome Edge OS v4.6.0 - Implementierungs-Roadmap
## Fehlende Features & Priorisierung

**Datum:** 2026-01-05
**Status:** In Arbeit

---

## Übersicht fehlende Features

| Feature | Priorität | Aufwand | Status |
|---------|-----------|---------|--------|
| Phase 7: Instanzen-Manager UI | Hoch | 4-5h | ⏳ Geplant |
| Phase 9: Sentry Error-Tracking | Mittel | 2-3h | ⏳ Geplant |
| Phase 10: CPU-Throttling | Mittel | 3-4h | ⏳ Geplant |
| Phase 6: Plugin-Manager Backend | Niedrig | 5-6h | ⏳ Geplant |

**Total:** ~15 Stunden Entwicklungszeit

---

## Phase 7: Instanzen-Manager UI
**Priorität:** HOCH (Backend bereits fertig)
**Aufwand:** 4-5 Stunden

### Ziel:
UI zur Verwaltung von Connection-Instanzen (Multi-PLC, Multi-Bluetooth) mit Live-Monitoring.

### Implementierung:

#### 7.1 Backend-API Routes (1h)
**Datei:** `modules/gateway/web_manager.py`

```python
# Connection Management API
@self.app.route('/api/connections')
def get_all_connections():
    """Liste aller Connections mit Status"""

@self.app.route('/api/connections/<connection_id>/stats')
def get_connection_stats(connection_id):
    """Detaillierte Statistiken einer Connection"""

@self.app.route('/api/connections', methods=['POST'])
def create_connection():
    """Erstellt neue Connection-Instanz"""

@self.app.route('/api/connections/<connection_id>', methods=['DELETE'])
def delete_connection(connection_id):
    """Löscht Connection-Instanz"""

@self.app.route('/api/connections/<connection_id>/connect', methods=['POST'])
def connect_connection(connection_id):
    """Verbindet Connection"""

@self.app.route('/api/connections/<connection_id>/disconnect', methods=['POST'])
def disconnect_connection(connection_id):
    """Trennt Connection"""
```

#### 7.2 Frontend UI (3-4h)
**Datei:** `web/static/js/instance-manager-v5.js`

**Features:**
- Connection-Liste mit Status-Badges (connected/disconnected/error)
- Live-Statistiken (packets/s, bytes/s, errors)
- Add/Remove Connection Dialog
- Connection-Type Auswahl (PLC, Bluetooth, MQTT)
- Health-Status Monitoring
- Ressourcen-Graphen (optional mit Chart.js)

**UI-Layout:**
```
┌─────────────────────────────────────────┐
│ 📡 Connection Manager          [+ Add]  │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ PLC_001 (TwinCAT)    ● Connected   │ │
│ │ 192.168.2.162:801                   │ │
│ │ ↑ 120 pkt/s  ↓ 85 pkt/s            │ │
│ │ [Disconnect] [Stats] [Delete]      │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ BLE_BMS_01 (Bluetooth) ○ Disc.    │ │
│ │ AA:BB:CC:DD:EE:FF                   │ │
│ │ Last: 2m ago                        │ │
│ │ [Connect] [Stats] [Delete]         │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## Phase 9: Sentry Error-Tracking
**Priorität:** MITTEL
**Aufwand:** 2-3 Stunden

### Ziel:
Zentrales Error-Tracking mit Sentry für Production-Monitoring.

### Implementierung:

#### 9.1 Sentry SDK Integration (1h)
**Datei:** `requirements.txt`
```txt
sentry-sdk==1.40.0
```

**Datei:** `module_manager.py`
```python
import sentry_sdk
import os

class BaseModule:
    def __init__(self):
        # Sentry init
        self.sentry_enabled = False
        self._init_sentry()

    def _init_sentry(self):
        """Initialisiert Sentry wenn DSN vorhanden"""
        dsn = os.getenv('SENTRY_DSN')
        if dsn:
            sentry_sdk.init(
                dsn=dsn,
                traces_sample_rate=1.0,
                environment=os.getenv('ENVIRONMENT', 'production'),
                release=f"{self.NAME}@{self.VERSION}"
            )
            self.sentry_enabled = True
            print(f"  🔍 Sentry aktiviert für {self.NAME}")

    def log_error(self, error: Exception, context: dict = None):
        """Loggt Error zu Sentry mit Context"""
        if self.sentry_enabled:
            with sentry_sdk.push_scope() as scope:
                scope.set_context("module", {
                    "name": self.NAME,
                    "version": self.VERSION
                })
                if context:
                    scope.set_context("additional", context)
                sentry_sdk.capture_exception(error)

        # Lokales Logging
        print(f"  ✗ [{self.NAME}] Error: {error}")
        if context:
            print(f"     Context: {context}")
```

#### 9.2 Error-Wrapper in kritischen Modulen (1-2h)
**Dateien:**
- `modules/core/connection_manager.py`
- `modules/gateway/data_gateway.py`
- `modules/gateway/web_manager.py`

**Pattern:**
```python
def critical_operation(self):
    try:
        # ... operation
    except Exception as e:
        self.log_error(e, {
            'operation': 'critical_operation',
            'connection_id': self.connection_id
        })
        raise  # Re-raise für normale Error-Behandlung
```

#### 9.3 Environment-Config (15min)
**Datei:** `.env.example`
```env
SENTRY_DSN=https://[your-key]@[org].ingest.sentry.io/[project-id]
ENVIRONMENT=production  # oder development/staging
```

---

## Phase 10: CPU-Throttling
**Priorität:** MITTEL
**Aufwand:** 3-4 Stunden

### Ziel:
Automatisches CPU-Throttling für ressourcenintensive Plugins/Connections.

### Implementierung:

#### 10.1 ResourceLimiter Klasse (2h)
**Datei:** `modules/core/resource_limiter.py`

```python
import psutil
import threading
import time
from typing import Dict, Optional

class ResourceLimiter:
    """
    CPU-Throttling für Prozesse/Threads
    """

    def __init__(self, cpu_limit_percent: int = 50, check_interval: int = 5):
        self.cpu_limit = cpu_limit_percent
        self.check_interval = check_interval
        self.monitored_processes: Dict[int, dict] = {}
        self.throttled_processes: Dict[int, dict] = {}

        # Monitoring Thread
        self.running = False
        self.monitor_thread = None

    def start_monitoring(self):
        """Startet Resource-Monitoring"""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        print("  ⚡ Resource Limiter gestartet")

    def add_process(self, pid: int, name: str):
        """Fügt Prozess zum Monitoring hinzu"""
        self.monitored_processes[pid] = {
            'name': name,
            'added_at': time.time(),
            'cpu_history': []
        }

    def remove_process(self, pid: int):
        """Entfernt Prozess aus Monitoring"""
        if pid in self.monitored_processes:
            del self.monitored_processes[pid]
        if pid in self.throttled_processes:
            del self.throttled_processes[pid]

    def _monitor_loop(self):
        """Monitoring Loop"""
        while self.running:
            for pid, info in list(self.monitored_processes.items()):
                try:
                    self._check_and_throttle(pid, info)
                except psutil.NoSuchProcess:
                    self.remove_process(pid)

            time.sleep(self.check_interval)

    def _check_and_throttle(self, pid: int, info: dict):
        """Prüft CPU-Nutzung und throttled bei Bedarf"""
        try:
            process = psutil.Process(pid)
            cpu_percent = process.cpu_percent(interval=1.0)

            # CPU-History
            info['cpu_history'].append(cpu_percent)
            if len(info['cpu_history']) > 10:
                info['cpu_history'].pop(0)

            # Durchschnitt letzte 10 Messungen
            avg_cpu = sum(info['cpu_history']) / len(info['cpu_history'])

            if avg_cpu > self.cpu_limit:
                # Throttle via nice value
                current_nice = process.nice()
                new_nice = min(current_nice + 5, 19)
                process.nice(new_nice)

                self.throttled_processes[pid] = {
                    'name': info['name'],
                    'cpu': avg_cpu,
                    'throttled_at': time.time(),
                    'nice_value': new_nice
                }

                print(f"  ⚠️  Process {info['name']} (PID {pid}) throttled: {avg_cpu:.1f}% CPU")

            elif pid in self.throttled_processes and avg_cpu < self.cpu_limit * 0.8:
                # Un-throttle wenn CPU wieder niedrig
                process.nice(0)  # Reset to default
                del self.throttled_processes[pid]
                print(f"  ✅ Process {info['name']} (PID {pid}) un-throttled")

        except Exception as e:
            print(f"  ⚠️  Throttling Error für PID {pid}: {e}")

    def get_stats(self) -> dict:
        """Liefert Monitoring-Statistiken"""
        return {
            'monitored': len(self.monitored_processes),
            'throttled': len(self.throttled_processes),
            'cpu_limit': self.cpu_limit,
            'processes': {
                pid: {
                    'name': info['name'],
                    'throttled': pid in self.throttled_processes
                }
                for pid, info in self.monitored_processes.items()
            }
        }

    def shutdown(self):
        """Stoppt Monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

        # Reset all nice values
        for pid in self.throttled_processes:
            try:
                psutil.Process(pid).nice(0)
            except:
                pass
```

#### 10.2 Integration in BaseModule (1h)
**Datei:** `module_manager.py`

```python
from modules.core.resource_limiter import ResourceLimiter

class ModuleManager:
    def __init__(self):
        # ...
        self.resource_limiter = ResourceLimiter(
            cpu_limit_percent=50,
            check_interval=5
        )
        self.resource_limiter.start_monitoring()
```

#### 10.3 Plugin-Integration (1h)
Plugins registrieren ihre Prozesse beim ResourceLimiter:

```python
class BasePlugin(BaseModule):
    def initialize(self, app_context):
        super().initialize(app_context)

        # Registriere bei Resource Limiter
        import os
        pid = os.getpid()
        app_context.module_manager.resource_limiter.add_process(
            pid,
            self.NAME
        )
```

#### 10.4 API Endpoint (30min)
**Datei:** `modules/gateway/web_manager.py`

```python
@self.app.route('/api/system/resources')
def get_resource_stats():
    """Resource-Monitoring Statistiken"""
    mm = self.app_context.module_manager
    return jsonify({
        'limiter': mm.resource_limiter.get_stats(),
        'system': {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent
        }
    })
```

---

## Phase 6: Plugin-Manager Backend (Optional)
**Priorität:** NIEDRIG
**Aufwand:** 5-6 Stunden

### Ziel:
Vollständiger Plugin-Manager mit Install/Uninstall/Lifecycle.

### Implementierung:

#### 6.1 Plugin-Manager Modul (3h)
**Datei:** `modules/core/plugin_manager.py`

```python
class PluginManager(BaseModule):
    def __init__(self):
        self.installed_plugins = {}
        self.available_plugins = {}
        self.plugin_processes = {}

    def get_installed_plugins(self) -> list:
        """Liste installierter Plugins"""
        pass

    def get_available_plugins(self) -> list:
        """Liste verfügbarer Plugins (npm-style registry)"""
        pass

    def install_plugin(self, plugin_id: str) -> bool:
        """Installiert Plugin"""
        pass

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Deinstalliert Plugin"""
        pass

    def start_plugin(self, plugin_id: str) -> bool:
        """Startet Plugin-Prozess"""
        pass

    def stop_plugin(self, plugin_id: str) -> bool:
        """Stoppt Plugin-Prozess"""
        pass
```

#### 6.2 Plugin-Registry (2h)
**Datei:** `config/plugin_registry.json`

#### 6.3 Plugin-Lifecycle (1h)
Integration mit Resource Limiter und Health-Check.

---

## Implementierungs-Reihenfolge

### Sprint 1: Kritische Features (6-8h)
1. ✅ **Phase 7.1:** Connection Management API (1h)
2. ✅ **Phase 7.2:** Instanzen-Manager UI (3-4h)
3. ✅ **Phase 9:** Sentry Error-Tracking (2-3h)

### Sprint 2: Performance & Monitoring (3-4h)
4. ✅ **Phase 10:** CPU-Throttling (3-4h)

### Sprint 3: Plugin-System (Optional, 5-6h)
5. ⏸️ **Phase 6:** Plugin-Manager Backend (5-6h)

---

## Nächste Schritte

1. **Jetzt starten:** Phase 7.1 - Connection Management API
2. **Dann:** Phase 7.2 - Instanzen-Manager UI
3. **Dann:** Phase 9 - Sentry Integration
4. **Dann:** Phase 10 - CPU-Throttling
5. **Optional:** Phase 6 - Plugin-Manager Backend

**Geschätzte Gesamt-Zeit:** 10-15 Stunden

---

**Erstellt:** 2026-01-05
**Autor:** SmartHome Edge OS Team
