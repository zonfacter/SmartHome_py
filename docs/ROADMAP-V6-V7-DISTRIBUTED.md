# SmartHome Edge OS - Roadmap v6.0 & v7.0
## Distributed Satellite-Core Architecture

**Datum:** 2026-01-05
**Status:** Planung
**Basis:** v5.0.0 (Production Ready)

---

## Executive Summary

Nach Abschluss von v5.0 (lokales Gateway mit Multi-Instance Support) folgt nun der Schritt zum **verteilten Edge-Betriebssystem**:

- **v6.0:** Distributed Architecture (Satellite-Core Mode)
- **v7.0:** Advanced Performance & Logic Engines

**Ziel:** Aus einem zentralen System wird ein **skalierbares Netzwerk** aus günstigen Headless-Satelliten (Raspberry Pi Zero, Docker-Container) und leistungsstarken Central-Cores (NAS, Desktop).

**Gesamtaufwand:** ~60-80 Stunden (8-10 Wochen bei 1 Tag/Woche)

---

## Architektur-Konzept

### Aktuell (v5.0):
```
┌─────────────────────────────────┐
│  SmartHome Edge OS (Monolith)   │
│                                 │
│  ┌──────────┐  ┌──────────┐   │
│  │ PLC Conn │  │ BLE Conn │   │
│  └──────────┘  └──────────┘   │
│                                 │
│  ┌──────────────────────────┐  │
│  │   Data Gateway (Local)   │  │
│  └──────────────────────────┘  │
│                                 │
│  ┌──────────────────────────┐  │
│  │  Web UI + Video Stream   │  │
│  └──────────────────────────┘  │
└─────────────────────────────────┘
```

### Ziel (v6.0):
```
┌─────────────────────────────────────────────────────────────┐
│                    CENTRAL CORE (NAS/Desktop)               │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │        Distributed Data Gateway (gRPC/MQTT)        │   │
│  │  - Empfängt Remote-Events von Satelliten          │   │
│  │  - Routing & Aggregation                           │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │             Web UI + Video Transcoding             │   │
│  │  - Hochauflösende Visualisierung                   │   │
│  │  - Resource-intensive Operationen                  │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             ▲
                             │ gRPC/MQTT (verschlüsselt)
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌────────▼──────┐   ┌────────▼──────┐
│ SATELLITE #1  │   │ SATELLITE #2  │   │ SATELLITE #3  │
│ (Pi Zero)     │   │ (Docker)      │   │ (Pi 1)        │
│               │   │               │   │               │
│ ┌───────────┐ │   │ ┌───────────┐ │   │ ┌───────────┐ │
│ │ BMS BLE   │ │   │ │ RS485     │ │   │ │ PLC ADS   │ │
│ │ Plugin    │ │   │ │ Plugin    │ │   │ │ Plugin    │ │
│ └───────────┘ │   │ └───────────┘ │   │ └───────────┘ │
│               │   │               │   │               │
│ HEADLESS MODE │   │ HEADLESS MODE │   │ HEADLESS MODE │
│ - Kein Web UI │   │ - Kein Web UI │   │ - Kein Web UI │
│ - Kein ffmpeg │   │ - Kein ffmpeg │   │ - Kein ffmpeg │
│ - Nur Plugins │   │ - Nur Plugins │   │ - Nur Plugins │
└───────────────┘   └───────────────┘   └───────────────┘
```

**Vorteile:**
- ✅ **Ausfallsicherheit:** BMS-Pi im Keller fällt aus → HMI läuft weiter
- ✅ **Skalierbarkeit:** Pro Akku-Pack ein eigener Pi Zero (~10€)
- ✅ **Performance:** Pi 1/Zero verbraucht <100 MB RAM im Headless-Mode
- ✅ **Flexibilität:** Docker-Container für temporäre Datenquellen

---

## Phase 13: Distributed Architecture (Satellite Mode)

**Priorität:** 🔴 HOCH
**Aufwand:** ~30-40 Stunden
**Version:** v6.0.0

### Ziel:
Ermöglichung eines **Headless-Modus** für ressourcenarme Geräte und **Remote-Routing** von Daten zu einem zentralen Core-Server.

---

### 13.1: Headless-Mode Implementation (8-10h)

#### Komponenten:

**1. Startup-Parameter (2h)**

**Datei:** `main.py`

```python
import argparse

def parse_args():
    """Parse Command-Line Arguments"""
    parser = argparse.ArgumentParser(description='SmartHome Edge OS v6.0')

    # Headless Mode
    parser.add_argument('--headless', action='store_true',
                        help='Headless-Modus (kein Web-Server, kein Video)')

    # Satellite Mode
    parser.add_argument('--satellite', action='store_true',
                        help='Satellite-Modus (leitet Daten an Remote-Core)')

    # Core-Server Adresse (für Satellites)
    parser.add_argument('--core-host', type=str,
                        help='Central Core Host (z.B. 192.168.2.50)')

    parser.add_argument('--core-port', type=int, default=50051,
                        help='Central Core gRPC Port (Default: 50051)')

    # Performance-Profil Override
    parser.add_argument('--performance', type=str,
                        choices=['LOW_POWER', 'BALANCED', 'HIGH_PERFORMANCE'],
                        help='Performance-Profil manuell setzen')

    return parser.parse_args()

def main():
    args = parse_args()

    # Setze Global Config
    app_config = {
        'headless': args.headless,
        'satellite_mode': args.satellite,
        'core_host': args.core_host,
        'core_port': args.core_port,
        'performance_profile': args.performance
    }

    print("=" * 60)
    print("SmartHome Edge OS v6.0")
    print("=" * 60)

    if args.headless:
        print("🔇 HEADLESS MODE aktiv - Web-Server deaktiviert")

    if args.satellite:
        print(f"🛰️  SATELLITE MODE - Core-Server: {args.core_host}:{args.core_port}")

    # Module Manager mit Config starten
    module_manager = ModuleManager(app_config)
    # ...
```

**2. Conditional Module Loading (3h)**

**Datei:** `module_manager.py`

```python
class ModuleManager:
    def __init__(self, app_config: dict = None):
        self.app_config = app_config or {}
        self.headless_mode = self.app_config.get('headless', False)
        self.satellite_mode = self.app_config.get('satellite_mode', False)

        # Module Registry (wird gefiltert nach Modus)
        self.available_modules = self._get_module_registry()

    def _get_module_registry(self) -> dict:
        """Dynamischer Module-Registry basierend auf Modus"""

        # Basis-Module (immer geladen)
        base_modules = {
            'config_manager': 'modules.core.config_manager.ConfigManager',
            'connection_manager': 'modules.core.connection_manager.ConnectionManager',
            'data_gateway': 'modules.gateway.data_gateway.DataGateway'
        }

        # Performance-Module (immer geladen)
        performance_modules = {
            'resource_limiter': 'modules.core.resource_limiter.ResourceLimiter'
        }

        # Web-Module (nur im Normal-Mode)
        web_modules = {}
        if not self.headless_mode:
            web_modules = {
                'web_manager': 'modules.gateway.web_manager.WebManager',
                'socketio_manager': 'modules.gateway.socketio_manager.SocketIOManager'
            }

        # Satellite-spezifische Module
        satellite_modules = {}
        if self.satellite_mode:
            satellite_modules = {
                'remote_gateway': 'modules.gateway.remote_gateway.RemoteGatewayConnector'
            }

        # Merge all
        all_modules = {
            **base_modules,
            **performance_modules,
            **web_modules,
            **satellite_modules
        }

        return all_modules

    def load_modules(self):
        """Lädt nur relevante Module basierend auf Modus"""
        print("\n📦 Lade Module...")

        if self.headless_mode:
            print("  🔇 Headless-Mode: Web-Module übersprungen")

        if self.satellite_mode:
            print("  🛰️  Satellite-Mode: Remote-Gateway wird geladen")

        for name, class_path in self.available_modules.items():
            # ... load module
```

**3. RAM-Optimierung für Headless (2h)**

**Datei:** `modules/core/config_manager.py`

```python
class ConfigManager(BaseModule):
    def __init__(self):
        super().__init__()

        # RAM-Optimierungen für Headless
        if self._is_headless():
            # Reduziere Cache-Sizes
            self.cache_limit = 50 * 1024 * 1024  # 50 MB statt 512 MB
            self.log_buffer_size = 100  # statt 1000
            print("  💾 Headless-Optimierung: Cache auf 50 MB reduziert")
```

**4. Environment-Detection Erweiterung (1-2h)**

**Datei:** `modules/gateway/data_gateway.py`

```python
def _detect_capabilities(self):
    """Erweiterte Hardware-Erkennung"""
    import psutil

    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq().max if psutil.cpu_freq() else 700
    total_ram = psutil.virtual_memory().total / (1024**3)  # GB

    # Performance-Profil
    if cpu_count <= 1 and cpu_freq < 1000 and total_ram < 1.0:
        profile = "LOW_POWER"
        print(f"  🐢 Low-End Hardware erkannt (Pi Zero/1)")
    elif cpu_count <= 4 and total_ram < 4.0:
        profile = "BALANCED"
        print(f"  ⚖️  Balanced Hardware (Pi 3/4)")
    else:
        profile = "HIGH_PERFORMANCE"
        print(f"  🚀 High-Performance Hardware (Desktop/NAS)")

    return {
        'cpu_count': cpu_count,
        'cpu_freq': cpu_freq,
        'total_ram_gb': total_ram,
        'profile': profile,
        'gpu_available': self._detect_gpu(),
        'docker': self.is_docker,
        'headless': self.app_context.module_manager.headless_mode
    }
```

---

### 13.2: Remote-Gateway Connector (12-15h)

**Ziel:** Ermöglicht Satelliten, `route_data()` Events verschlüsselt an einen Central Core zu senden.

**Technologie:** gRPC (performanter als REST, Bi-Directional Streaming)

#### Komponenten:

**1. gRPC Service Definition (2h)**

**Datei:** `protos/remote_gateway.proto`

```protobuf
syntax = "proto3";

package smarthome_edge;

// Remote Data Gateway Service
service RemoteDataGateway {
    // Single Event (unary)
    rpc RouteEvent(DataEvent) returns (RouteResponse);

    // Batch Events (stream)
    rpc StreamEvents(stream DataEvent) returns (stream RouteResponse);

    // Satellite Health-Check
    rpc HealthCheck(SatelliteInfo) returns (HealthResponse);
}

message DataEvent {
    string satellite_id = 1;      // z.B. "pi_bms_keller"
    string tag = 2;               // z.B. "bms/voltage"
    bytes value = 3;              // JSON-serialized value
    int64 timestamp = 4;          // Unix timestamp (ms)
    string source_type = 5;       // "bluetooth", "plc", "mqtt", etc.
    map<string, string> metadata = 6;  // Zusätzliche Context-Daten
}

message RouteResponse {
    bool success = 1;
    string message = 2;
    int64 server_timestamp = 3;
}

message SatelliteInfo {
    string satellite_id = 1;
    string version = 2;
    string hardware_profile = 3;  // "LOW_POWER", "BALANCED", etc.
    map<string, string> stats = 4;
}

message HealthResponse {
    bool healthy = 1;
    string status = 2;
}
```

**Kompilieren:**
```bash
python -m grpc_tools.protoc -I protos --python_out=. --grpc_python_out=. protos/remote_gateway.proto
```

**2. Remote Gateway Client (Satellite-Side) (5-6h)**

**Datei:** `modules/gateway/remote_gateway.py`

```python
"""
Remote Gateway Connector v6.0.0
Verbindet Satelliten mit Central Core via gRPC
"""

from module_manager import BaseModule
import grpc
import time
import threading
from typing import Any, Optional
from collections import deque
import json

# Auto-generiert von protoc
import remote_gateway_pb2
import remote_gateway_pb2_grpc


class RemoteGatewayConnector(BaseModule):
    """
    Remote Gateway Connector für Satelliten

    Sendet route_data() Events an Central Core via gRPC.
    Features:
    - Auto-Reconnect
    - Event-Batching für Performance
    - TLS-Verschlüsselung
    - Failover-Queue
    """

    NAME = "remote_gateway"
    VERSION = "6.0.0"
    DESCRIPTION = "gRPC Remote Gateway für Satellite-Mode"

    BATCH_SIZE = 100  # Events pro Batch
    BATCH_INTERVAL = 1.0  # Sekunden

    def __init__(self):
        super().__init__()
        self.core_host = None
        self.core_port = None
        self.satellite_id = None

        # gRPC Channel
        self.channel = None
        self.stub = None
        self.connected = False

        # Event-Queue
        self.event_queue = deque(maxlen=10000)  # Max 10k Events
        self.batch_thread = None
        self.running = False

        # Stats
        self.stats = {
            'events_sent': 0,
            'events_failed': 0,
            'reconnects': 0,
            'last_send': None
        }

    def initialize(self, app_context: Any):
        """Initialisiert Remote Gateway"""
        super().initialize(app_context)

        # Hole Config
        config = app_context.module_manager.app_config
        self.core_host = config.get('core_host')
        self.core_port = config.get('core_port', 50051)
        self.satellite_id = config.get('satellite_id', f"satellite_{int(time.time())}")

        if not self.core_host:
            print("  ⚠️  Remote Gateway: Keine core_host konfiguriert!")
            return

        print(f"  🛰️  Remote Gateway verbindet zu {self.core_host}:{self.core_port}")

        # Connect
        self._connect()

        # Starte Batch-Worker
        self._start_batch_worker()

    def _connect(self):
        """Stellt gRPC-Verbindung zum Core her"""
        try:
            # TODO: TLS-Support hinzufügen
            target = f"{self.core_host}:{self.core_port}"
            self.channel = grpc.insecure_channel(target)
            self.stub = remote_gateway_pb2_grpc.RemoteDataGatewayStub(self.channel)

            # Health-Check
            self._health_check()

            self.connected = True
            print(f"  ✅ Remote Gateway verbunden mit {target}")

        except Exception as e:
            self.connected = False
            print(f"  ⚠️  Remote Gateway Verbindung fehlgeschlagen: {e}")
            self.stats['reconnects'] += 1

    def _health_check(self):
        """Sendet Health-Check an Core"""
        import psutil

        hardware_profile = self._detect_hardware_profile()

        satellite_info = remote_gateway_pb2.SatelliteInfo(
            satellite_id=self.satellite_id,
            version=self.VERSION,
            hardware_profile=hardware_profile,
            stats={
                'cpu_percent': str(psutil.cpu_percent()),
                'memory_percent': str(psutil.virtual_memory().percent),
                'events_queued': str(len(self.event_queue))
            }
        )

        response = self.stub.HealthCheck(satellite_info, timeout=5)

        if not response.healthy:
            raise Exception(f"Core-Server unhealthy: {response.status}")

    def route_data(self, tag: str, value: Any, source_type: str = "unknown", metadata: dict = None):
        """
        Sendet Data-Event an Central Core

        Args:
            tag: Data-Tag (z.B. "bms/voltage")
            value: Wert (wird JSON-serialized)
            source_type: Typ der Quelle ("bluetooth", "plc", etc.)
            metadata: Zusätzliche Context-Daten
        """
        # Erstelle Event
        event = {
            'satellite_id': self.satellite_id,
            'tag': tag,
            'value': json.dumps(value),
            'timestamp': int(time.time() * 1000),
            'source_type': source_type,
            'metadata': metadata or {}
        }

        # In Queue
        self.event_queue.append(event)

    def _start_batch_worker(self):
        """Startet Background-Thread für Batch-Sending"""
        self.running = True
        self.batch_thread = threading.Thread(target=self._batch_worker, daemon=True)
        self.batch_thread.start()
        print("  ⚡ Batch-Worker gestartet")

    def _batch_worker(self):
        """Background-Worker für Event-Batching"""
        while self.running:
            time.sleep(self.BATCH_INTERVAL)

            if not self.connected:
                # Try reconnect
                self._connect()
                continue

            # Hole Events aus Queue
            batch = []
            while len(batch) < self.BATCH_SIZE and self.event_queue:
                batch.append(self.event_queue.popleft())

            if not batch:
                continue

            # Sende Batch
            try:
                self._send_batch(batch)
            except Exception as e:
                print(f"  ⚠️  Batch-Send fehlgeschlagen: {e}")
                # Events zurück in Queue
                for event in reversed(batch):
                    self.event_queue.appendleft(event)

                self.connected = False

    def _send_batch(self, batch: list):
        """Sendet Event-Batch via gRPC Streaming"""

        def event_generator():
            for event in batch:
                yield remote_gateway_pb2.DataEvent(
                    satellite_id=event['satellite_id'],
                    tag=event['tag'],
                    value=event['value'].encode('utf-8'),
                    timestamp=event['timestamp'],
                    source_type=event['source_type'],
                    metadata=event['metadata']
                )

        # Streaming Call
        responses = self.stub.StreamEvents(event_generator())

        success_count = 0
        for response in responses:
            if response.success:
                success_count += 1

        self.stats['events_sent'] += success_count
        self.stats['events_failed'] += (len(batch) - success_count)
        self.stats['last_send'] = time.time()

        print(f"  📤 Batch gesendet: {success_count}/{len(batch)} erfolgreich")

    def _detect_hardware_profile(self) -> str:
        """Erkennt Hardware-Profil"""
        import psutil

        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq().max if psutil.cpu_freq() else 700

        if cpu_count <= 1 and cpu_freq < 1000:
            return "LOW_POWER"
        elif cpu_count <= 4:
            return "BALANCED"
        else:
            return "HIGH_PERFORMANCE"

    def shutdown(self):
        """Stoppt Remote Gateway"""
        self.running = False

        if self.batch_thread:
            self.batch_thread.join(timeout=5)

        if self.channel:
            self.channel.close()

        print("  🛑 Remote Gateway gestoppt")
```

**3. Remote Gateway Server (Core-Side) (5-6h)**

**Datei:** `modules/gateway/remote_gateway_server.py`

```python
"""
Remote Gateway Server v6.0.0
Empfängt Events von Satelliten (läuft nur auf Central Core)
"""

from module_manager import BaseModule
import grpc
from concurrent import futures
import time
import threading
import json

import remote_gateway_pb2
import remote_gateway_pb2_grpc


class RemoteGatewayServicer(remote_gateway_pb2_grpc.RemoteDataGatewayServicer):
    """gRPC Service Implementation"""

    def __init__(self, data_gateway):
        self.data_gateway = data_gateway
        self.stats = {
            'events_received': 0,
            'satellites_connected': set()
        }

    def RouteEvent(self, request, context):
        """Unary Event (einzelnes Event)"""
        try:
            # Parse Value
            value = json.loads(request.value.decode('utf-8'))

            # Tag mit Satellite-Prefix
            tag = f"remote/{request.satellite_id}/{request.tag}"

            # Route in lokales Data Gateway
            self.data_gateway.route_data(
                tag=tag,
                value=value,
                source_id=f"satellite:{request.satellite_id}"
            )

            self.stats['events_received'] += 1
            self.stats['satellites_connected'].add(request.satellite_id)

            return remote_gateway_pb2.RouteResponse(
                success=True,
                message="OK",
                server_timestamp=int(time.time() * 1000)
            )

        except Exception as e:
            return remote_gateway_pb2.RouteResponse(
                success=False,
                message=str(e),
                server_timestamp=int(time.time() * 1000)
            )

    def StreamEvents(self, request_iterator, context):
        """Stream Events (Batch)"""
        for request in request_iterator:
            response = self.RouteEvent(request, context)
            yield response

    def HealthCheck(self, request, context):
        """Health-Check von Satellite"""
        print(f"  🛰️  Health-Check von {request.satellite_id} (HW: {request.hardware_profile})")

        self.stats['satellites_connected'].add(request.satellite_id)

        return remote_gateway_pb2.HealthResponse(
            healthy=True,
            status="OK"
        )


class RemoteGatewayServer(BaseModule):
    """
    Remote Gateway Server (nur auf Central Core)
    Empfängt Events von Satelliten via gRPC
    """

    NAME = "remote_gateway_server"
    VERSION = "6.0.0"
    DESCRIPTION = "gRPC Server für Remote Satellites"

    DEFAULT_PORT = 50051

    def __init__(self):
        super().__init__()
        self.server = None
        self.servicer = None

    def initialize(self, app_context: Any):
        """Initialisiert gRPC Server"""
        super().initialize(app_context)

        # Hole Data Gateway
        data_gateway = app_context.module_manager.get_module('data_gateway')

        # Erstelle Servicer
        self.servicer = RemoteGatewayServicer(data_gateway)

        # Erstelle Server
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        remote_gateway_pb2_grpc.add_RemoteDataGatewayServicer_to_server(
            self.servicer, self.server
        )

        # Bind Port
        port = self.DEFAULT_PORT
        self.server.add_insecure_port(f'[::]:{port}')

        # Start
        self.server.start()

        print(f"  🛰️  Remote Gateway Server läuft auf Port {port}")

    def shutdown(self):
        """Stoppt Server"""
        if self.server:
            self.server.stop(grace=5)
            print("  🛑 Remote Gateway Server gestoppt")
```

---

### 13.3: Discovery Service (mDNS/Bonjour) (6-8h)

**Ziel:** Automatische Erkennung von Satelliten im Netzwerk.

**Technologie:** Zeroconf/mDNS (wie AirPlay, Chromecast)

**Datei:** `modules/core/discovery_service.py`

```python
"""
Discovery Service v6.0.0
Automatische Erkennung von Satelliten via mDNS
"""

from module_manager import BaseModule
from zeroconf import Zeroconf, ServiceBrowser, ServiceInfo
import socket
import threading
import time


class SatelliteListener:
    """Listener für mDNS Service Discovery"""

    def __init__(self, callback):
        self.callback = callback
        self.discovered_satellites = {}

    def add_service(self, zeroconf, service_type, name):
        """Neuer Service entdeckt"""
        info = zeroconf.get_service_info(service_type, name)

        if info:
            satellite_info = {
                'name': name,
                'host': socket.inet_ntoa(info.addresses[0]),
                'port': info.port,
                'properties': {k.decode(): v.decode() for k, v in info.properties.items()}
            }

            self.discovered_satellites[name] = satellite_info
            self.callback('add', satellite_info)

    def remove_service(self, zeroconf, service_type, name):
        """Service entfernt"""
        if name in self.discovered_satellites:
            satellite_info = self.discovered_satellites.pop(name)
            self.callback('remove', satellite_info)


class DiscoveryService(BaseModule):
    """
    Discovery Service für Satellite-Erkennung

    Features:
    - Automatische Satellite-Erkennung via mDNS
    - Registration von Satelliten beim Core
    - Health-Monitoring
    """

    NAME = "discovery_service"
    VERSION = "6.0.0"
    DESCRIPTION = "mDNS Discovery für Satelliten"

    SERVICE_TYPE = "_smarthome-edge._tcp.local."

    def __init__(self):
        super().__init__()
        self.zeroconf = None
        self.browser = None
        self.listener = None
        self.satellites = {}

    def initialize(self, app_context: Any):
        """Initialisiert Discovery Service"""
        super().initialize(app_context)

        # Starte mDNS Browser
        self.zeroconf = Zeroconf()
        self.listener = SatelliteListener(self._on_satellite_change)
        self.browser = ServiceBrowser(self.zeroconf, self.SERVICE_TYPE, self.listener)

        # Registriere eigenen Service (wenn Core-Mode)
        if not app_context.module_manager.satellite_mode:
            self._register_core_service()

        print(f"  🔍 Discovery Service gestartet")

    def _register_core_service(self):
        """Registriert Core als mDNS Service"""
        import psutil

        hostname = socket.gethostname()
        local_ip = self._get_local_ip()

        info = ServiceInfo(
            self.SERVICE_TYPE,
            f"SmartHome-Core-{hostname}.{self.SERVICE_TYPE}",
            addresses=[socket.inet_aton(local_ip)],
            port=50051,
            properties={
                'version': '6.0.0',
                'mode': 'core',
                'cpu_count': str(psutil.cpu_count()),
                'hostname': hostname
            }
        )

        self.zeroconf.register_service(info)
        print(f"  📡 Core registriert als {hostname} ({local_ip}:50051)")

    def _on_satellite_change(self, event_type: str, satellite_info: dict):
        """Callback für Satellite-Changes"""
        if event_type == 'add':
            print(f"  🛰️  Satellite entdeckt: {satellite_info['name']} @ {satellite_info['host']}:{satellite_info['port']}")
            self.satellites[satellite_info['name']] = satellite_info

        elif event_type == 'remove':
            print(f"  🔌 Satellite getrennt: {satellite_info['name']}")
            if satellite_info['name'] in self.satellites:
                del self.satellites[satellite_info['name']]

    def _get_local_ip(self) -> str:
        """Holt lokale IP-Adresse"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def get_satellites(self) -> dict:
        """Gibt alle entdeckten Satelliten zurück"""
        return self.satellites

    def shutdown(self):
        """Stoppt Discovery Service"""
        if self.zeroconf:
            self.zeroconf.close()

        print("  🛑 Discovery Service gestoppt")
```

---

### 13.4: Integration & Testing (4-5h)

**1. Data Gateway Integration (2h)**

**Datei:** `modules/gateway/data_gateway.py`

Erweitere `route_data()` um `remote_origin` Parameter:

```python
def route_data(self, tag: str, value: Any, source_id: str = "unknown", remote_origin: str = None):
    """
    Universal Data Router

    Args:
        tag: Data-Tag (z.B. "plc/temperature")
        value: Daten-Wert
        source_id: Quelle (z.B. "plc_001")
        remote_origin: Satellite-ID (falls Event von Remote)
    """
    # Spam-Check
    if not self._check_spam_protection(source_id):
        self.stats['routes_blocked'] += 1
        return

    # Remote-Event Tracking
    if remote_origin:
        print(f"  📡 Remote-Event von {remote_origin}: {tag} = {value}")
        # Statistik
        if 'remote_events' not in self.stats:
            self.stats['remote_events'] = 0
        self.stats['remote_events'] += 1

    # Normale Routing-Logik
    datapoint = {
        'tag': tag,
        'value': value,
        'source_id': source_id,
        'remote_origin': remote_origin,
        'timestamp': time.time()
    }

    # ... Rest der Logik
```

**2. Startup-Script Anpassung (1h)**

Erstelle Helper-Scripts für einfachen Start:

**Datei:** `start_satellite.sh`

```bash
#!/bin/bash
# Startet SmartHome Edge OS im Satellite-Mode

# Konfiguration
CORE_HOST="192.168.2.50"
CORE_PORT=50051
SATELLITE_ID="pi_bms_keller"

python3 main.py \
    --headless \
    --satellite \
    --core-host $CORE_HOST \
    --core-port $CORE_PORT \
    --satellite-id $SATELLITE_ID \
    --performance LOW_POWER
```

**Datei:** `start_core.sh`

```bash
#!/bin/bash
# Startet SmartHome Edge OS als Central Core

python3 main.py --performance HIGH_PERFORMANCE
```

**3. Testing (1-2h)**

Test-Szenarien:
- Pi Zero als BMS-Satellite
- Docker-Container als Test-Satellite
- Desktop als Central Core
- Discovery-Test (Satellite findet Core automatisch)

---

### Dependencies für Phase 13:

**Datei:** `requirements.txt` (Update)

```txt
# Bestehende Dependencies
Flask==3.0.0
Flask-SocketIO==5.3.5
pyads==3.3.13
bleak==0.21.1
influxdb==5.3.1
psutil==5.9.6
sentry-sdk==1.40.0
requests==2.31.0

# NEU: Phase 13 (Distributed)
grpcio==1.60.0
grpcio-tools==1.60.0
protobuf==4.25.1
zeroconf==0.131.0
```

---

## Phase 14: Advanced Performance Engine

**Priorität:** 🟡 MITTEL
**Aufwand:** ~20-25 Stunden
**Version:** v6.5.0

### Ziel:
Automatische Performance-Optimierung basierend auf Hardware-Profil und Multiprocessing-Support für CPU-intensive Operationen.

---

### 14.1: Auto-Hardware-Profiling (6-8h)

**Erweiterung von BaseModule mit adaptivem Verhalten**

**Datei:** `module_manager.py`

```python
class BaseModule:
    """Basis-Klasse für alle Module (v6.5 mit Performance-Profiling)"""

    def __init__(self):
        # ... (bestehender Code)

        # ⭐ NEU: Performance-Profiling
        self.performance_profile = self._detect_hardware_profile()
        self._apply_performance_settings()

    def _detect_hardware_profile(self) -> str:
        """
        Erkennt Hardware-Leistung automatisch

        Returns:
            "LOW_POWER", "BALANCED", oder "HIGH_PERFORMANCE"
        """
        import psutil

        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq().max if psutil.cpu_freq() else 700
        total_ram = psutil.virtual_memory().total / (1024**3)  # GB

        # Manual Override via ENV
        manual_profile = os.getenv('PERFORMANCE_PROFILE')
        if manual_profile:
            return manual_profile

        # Auto-Detection
        if cpu_count <= 1 and cpu_freq < 1000:
            # Raspberry Pi Zero/1
            return "LOW_POWER"

        elif cpu_count <= 2 and total_ram < 2.0:
            # Raspberry Pi 2/3
            return "BALANCED"

        elif cpu_count <= 4 and total_ram < 4.0:
            # Raspberry Pi 4
            return "BALANCED"

        else:
            # Desktop/NAS
            return "HIGH_PERFORMANCE"

    def _apply_performance_settings(self):
        """Wendet Performance-Settings basierend auf Profil an"""
        if self.performance_profile == "LOW_POWER":
            # Low-End Optimierungen
            self.poll_interval_multiplier = 2.0  # Verdopple Poll-Intervalle
            self.cache_size_multiplier = 0.5     # Halbiere Caches
            self.thread_pool_size = 2            # Minimal Threads

            print(f"  🐢 {self.NAME}: LOW_POWER Profil aktiv")

        elif self.performance_profile == "BALANCED":
            self.poll_interval_multiplier = 1.0
            self.cache_size_multiplier = 1.0
            self.thread_pool_size = 4

            print(f"  ⚖️  {self.NAME}: BALANCED Profil aktiv")

        else:  # HIGH_PERFORMANCE
            self.poll_interval_multiplier = 0.5  # Schnellere Polls
            self.cache_size_multiplier = 2.0     # Größere Caches
            self.thread_pool_size = 8            # Mehr Threads

            print(f"  🚀 {self.NAME}: HIGH_PERFORMANCE Profil aktiv")

    def adaptive_sleep(self, base_seconds: float):
        """
        Adaptive Sleep basierend auf Hardware-Profil

        Verwendung:
            # Statt: time.sleep(5)
            self.adaptive_sleep(5)
        """
        adjusted_sleep = base_seconds * self.poll_interval_multiplier
        time.sleep(adjusted_sleep)

    def get_cache_size(self, base_size: int) -> int:
        """
        Berechnet Cache-Size basierend auf Profil

        Args:
            base_size: Basis-Größe in Bytes

        Returns:
            Angepasste Cache-Größe
        """
        return int(base_size * self.cache_size_multiplier)
```

**Beispiel-Integration in Plugin:**

```python
class BMSPlugin(BasePlugin):
    def run(self):
        """Haupt-Loop"""
        while self.running:
            # BMS auslesen
            voltage = self.read_bms_voltage()

            # Publish
            self.publish("bms/voltage", voltage)

            # Adaptive Sleep (5s auf High-Perf, 10s auf Low-Power)
            self.adaptive_sleep(5.0)
```

---

### 14.2: Multiprocessing Bridge (8-10h)

**Ziel:** Umgehung des Python GIL für CPU-intensive Operationen.

**Use Cases:**
- BMS-Parser mit komplexen CAN-Protokollen
- Video-Encoding (falls nicht headless)
- Komplexe Regel-Engines

**Datei:** `modules/core/multiprocess_bridge.py`

```python
"""
Multiprocess Bridge v6.5.0
Erlaubt Auslagerung von CPU-intensiven Tasks in separate Prozesse
"""

from module_manager import BaseModule
import multiprocessing as mp
from multiprocessing import Queue, Process
import time
import threading
from typing import Callable, Any, Optional
import pickle


class ProcessWorker:
    """Worker-Prozess für CPU-intensive Tasks"""

    def __init__(self, task_queue: Queue, result_queue: Queue):
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self):
        """Worker Loop"""
        while True:
            try:
                task = self.task_queue.get(timeout=1)

                if task is None:
                    # Shutdown Signal
                    break

                task_id, func, args, kwargs = task

                # Execute
                try:
                    result = func(*args, **kwargs)
                    self.result_queue.put((task_id, 'success', result))
                except Exception as e:
                    self.result_queue.put((task_id, 'error', str(e)))

            except:
                continue


class MultiprocessBridge(BaseModule):
    """
    Multiprocess Bridge

    Verwaltet Pool von Worker-Prozessen für CPU-intensive Operationen.
    """

    NAME = "multiprocess_bridge"
    VERSION = "6.5.0"
    DESCRIPTION = "Multiprocessing für CPU-intensive Tasks"

    def __init__(self):
        super().__init__()
        self.task_queue = None
        self.result_queue = None
        self.workers = []
        self.running = False

        # Result-Callbacks
        self.pending_tasks = {}
        self.next_task_id = 0

        # Result-Handler Thread
        self.result_thread = None

    def initialize(self, app_context: Any):
        """Initialisiert Multiprocess Bridge"""
        super().initialize(app_context)

        # Worker-Count basierend auf CPU-Cores
        import psutil
        cpu_count = psutil.cpu_count()

        if self.performance_profile == "LOW_POWER":
            worker_count = 1
        elif self.performance_profile == "BALANCED":
            worker_count = max(2, cpu_count // 2)
        else:
            worker_count = cpu_count

        # Queues
        self.task_queue = mp.Queue()
        self.result_queue = mp.Queue()

        # Starte Workers
        for i in range(worker_count):
            worker = ProcessWorker(self.task_queue, self.result_queue)
            process = mp.Process(target=worker.run, daemon=True)
            process.start()
            self.workers.append(process)

        # Starte Result-Handler
        self.running = True
        self.result_thread = threading.Thread(target=self._result_handler, daemon=True)
        self.result_thread.start()

        print(f"  ⚡ Multiprocess Bridge gestartet ({worker_count} Worker)")

    def submit_task(self, func: Callable, *args, callback: Optional[Callable] = None, **kwargs) -> int:
        """
        Submitted Task an Worker-Pool

        Args:
            func: Funktion (muss pickleable sein!)
            args: Argumente
            callback: Callback-Funktion für Result
            kwargs: Keyword-Args

        Returns:
            Task-ID
        """
        task_id = self.next_task_id
        self.next_task_id += 1

        # Registriere Callback
        if callback:
            self.pending_tasks[task_id] = callback

        # Submit
        self.task_queue.put((task_id, func, args, kwargs))

        return task_id

    def _result_handler(self):
        """Background-Thread für Result-Handling"""
        while self.running:
            try:
                result = self.result_queue.get(timeout=0.1)

                task_id, status, data = result

                # Callback
                if task_id in self.pending_tasks:
                    callback = self.pending_tasks.pop(task_id)

                    if status == 'success':
                        callback(data)
                    else:
                        print(f"  ⚠️  Task {task_id} failed: {data}")

            except:
                continue

    def shutdown(self):
        """Stoppt Worker-Pool"""
        self.running = False

        # Shutdown-Signal an Workers
        for _ in self.workers:
            self.task_queue.put(None)

        # Warte auf Workers
        for worker in self.workers:
            worker.join(timeout=2)

        print("  🛑 Multiprocess Bridge gestoppt")
```

**Beispiel-Verwendung:**

```python
# CPU-intensive Funktion (MUSS pickleable sein!)
def parse_complex_bms_data(raw_data: bytes) -> dict:
    """Parst komplexes BMS-Protokoll"""
    # ... komplexe Berechnungen
    return {'voltage': 54.2, 'current': 12.3}


class BMSPlugin(BasePlugin):
    def initialize(self, app_context):
        super().initialize(app_context)

        # Hole Multiprocess Bridge
        self.mp_bridge = app_context.module_manager.get_module('multiprocess_bridge')

    def on_ble_data(self, raw_data: bytes):
        """BLE-Daten empfangen"""

        # Submit zu Worker-Prozess (non-blocking!)
        self.mp_bridge.submit_task(
            parse_complex_bms_data,
            raw_data,
            callback=self._on_parsed_data
        )

    def _on_parsed_data(self, data: dict):
        """Callback wenn Parsing fertig"""
        self.publish("bms/voltage", data['voltage'])
        self.publish("bms/current", data['current'])
```

---

### 14.3: Zero-Copy Routing (6-7h)

**Ziel:** Optimierung des DataGateway für große Datenmengen (z.B. SPS-Bilder).

**Konzept:** Statt Daten zu kopieren, werden Referenzen/Pointer übergeben.

**Datei:** `modules/gateway/data_gateway.py`

```python
class DataGateway(BaseModule):
    """Data Gateway v6.5 mit Zero-Copy Optimierung"""

    def route_data(self, tag: str, value: Any, source_id: str = "unknown",
                   zero_copy: bool = False):
        """
        Universal Data Router (v6.5 mit Zero-Copy)

        Args:
            tag: Data-Tag
            value: Daten (wird kopiert, außer zero_copy=True)
            source_id: Quelle
            zero_copy: Wenn True, wird value NICHT kopiert (Performance)
        """
        # Spam-Check
        if not self._check_spam_protection(source_id):
            return

        # Datapoint (Zero-Copy wenn enabled)
        if zero_copy:
            # WARNUNG: value darf nicht mehr verändert werden!
            datapoint = {
                'tag': tag,
                'value': value,  # Keine Kopie!
                'source_id': source_id,
                'timestamp': time.time(),
                '_zero_copy': True
            }
        else:
            # Sichere Kopie
            import copy
            datapoint = {
                'tag': tag,
                'value': copy.deepcopy(value),
                'source_id': source_id,
                'timestamp': time.time(),
                '_zero_copy': False
            }

        # ... Rest der Routing-Logik
```

**Verwendung:**

```python
# Normales Routing (sicher, aber langsamer)
self.data_gateway.route_data("plc/temperature", 23.5)

# Zero-Copy Routing (schnell, aber value darf nicht mehr verändert werden!)
large_image = read_plc_image()  # 1 MB Bild
self.data_gateway.route_data("plc/image", large_image, zero_copy=True)
# ACHTUNG: large_image NICHT mehr verändern!
```

---

## Phase 15: External Logic Engines

**Priorität:** 🟢 NIEDRIG
**Aufwand:** ~10-15 Stunden
**Version:** v7.0.0

### Ziel:
Integration mit Node-RED und Logic-Mirroring für High Availability.

---

### 15.1: Node-RED Palette (6-8h)

**Ziel:** Erstellung einer Node-RED "Palette" mit Custom Nodes für SmartHome Edge OS.

**Node-Typen:**
- `smarthome-in`: Empfängt Daten vom Edge OS
- `smarthome-out`: Sendet Daten ans Edge OS
- `smarthome-satellite`: Verbindet sich mit Satellite

**Datei:** `node-red-contrib-smarthome-edge/package.json`

```json
{
  "name": "node-red-contrib-smarthome-edge",
  "version": "1.0.0",
  "description": "Node-RED nodes for SmartHome Edge OS v6.0",
  "main": "index.js",
  "node-red": {
    "nodes": {
      "smarthome-in": "nodes/smarthome-in.js",
      "smarthome-out": "nodes/smarthome-out.js",
      "smarthome-satellite": "nodes/smarthome-satellite.js"
    }
  }
}
```

**Beispiel Node:** `nodes/smarthome-in.js`

```javascript
module.exports = function(RED) {
    const grpc = require('@grpc/grpc-js');
    const protoLoader = require('@grpc/proto-loader');

    function SmartHomeInNode(config) {
        RED.nodes.createNode(this, config);

        const node = this;
        node.tag = config.tag;
        node.coreHost = config.coreHost;
        node.corePort = config.corePort || 50051;

        // gRPC Connection
        const packageDefinition = protoLoader.loadSync('remote_gateway.proto');
        const proto = grpc.loadPackageDefinition(packageDefinition).smarthome_edge;

        const client = new proto.RemoteDataGateway(
            `${node.coreHost}:${node.corePort}`,
            grpc.credentials.createInsecure()
        );

        // Subscribe to Tag
        node.status({fill:"green", shape:"dot", text:"connected"});

        // Polling (TODO: Streaming)
        node.interval = setInterval(() => {
            // Request Data
            client.GetData({tag: node.tag}, (err, response) => {
                if (!err && response.success) {
                    node.send({
                        payload: JSON.parse(response.value),
                        topic: node.tag
                    });
                }
            });
        }, 1000);

        node.on('close', () => {
            clearInterval(node.interval);
        });
    }

    RED.nodes.registerType("smarthome-in", SmartHomeInNode);
};
```

---

### 15.2: Logic-Mirroring (4-7h)

**Ziel:** Redundante Ausführung von Logik-Plugins auf zwei Geräten.

**Datei:** `modules/core/logic_mirror.py`

```python
"""
Logic Mirror v7.0.0
High-Availability durch redundante Plugin-Ausführung
"""

from module_manager import BaseModule
import threading
import time


class LogicMirror(BaseModule):
    """
    Logic Mirror

    Führt kritische Logik-Plugins redundant auf zwei Systemen aus.
    Bei Ausfall eines Systems übernimmt das andere automatisch.
    """

    NAME = "logic_mirror"
    VERSION = "7.0.0"
    DESCRIPTION = "HA durch Logic-Mirroring"

    def __init__(self):
        super().__init__()
        self.mirror_pairs = []  # (primary_plugin, secondary_host)
        self.active_plugins = {}  # plugin_name -> "primary" or "secondary"

    def add_mirror(self, plugin_name: str, secondary_host: str):
        """
        Fügt Plugin-Mirror hinzu

        Args:
            plugin_name: Name des Plugins
            secondary_host: IP des Secondary-Systems
        """
        self.mirror_pairs.append((plugin_name, secondary_host))
        self.active_plugins[plugin_name] = "primary"

        print(f"  🔄 Mirror aktiviert: {plugin_name} -> {secondary_host}")

    def check_health(self, plugin_name: str) -> bool:
        """Prüft Health eines Plugins"""
        # TODO: Implementierung
        pass

    def failover(self, plugin_name: str):
        """Führt Failover zu Secondary durch"""
        if plugin_name in self.active_plugins:
            if self.active_plugins[plugin_name] == "primary":
                self.active_plugins[plugin_name] = "secondary"
                print(f"  ⚠️  FAILOVER: {plugin_name} -> Secondary")

                # Benachrichtige Secondary
                # TODO: gRPC Call an Secondary
```

---

## Aufwandsschätzung Gesamt

| Phase | Feature | Aufwand | Priorität |
|-------|---------|---------|-----------|
| **13.1** | Headless-Mode | 8-10h | 🔴 Hoch |
| **13.2** | Remote Gateway Connector | 12-15h | 🔴 Hoch |
| **13.3** | Discovery Service (mDNS) | 6-8h | 🔴 Hoch |
| **13.4** | Integration & Testing | 4-5h | 🔴 Hoch |
| **14.1** | Auto-Hardware-Profiling | 6-8h | 🟡 Mittel |
| **14.2** | Multiprocessing Bridge | 8-10h | 🟡 Mittel |
| **14.3** | Zero-Copy Routing | 6-7h | 🟡 Mittel |
| **15.1** | Node-RED Palette | 6-8h | 🟢 Niedrig |
| **15.2** | Logic-Mirroring | 4-7h | 🟢 Niedrig |

**Total Phase 13 (v6.0):** ~30-38 Stunden
**Total Phase 14 (v6.5):** ~20-25 Stunden
**Total Phase 15 (v7.0):** ~10-15 Stunden

**Gesamt:** ~60-78 Stunden

---

## Implementierungs-Reihenfolge

### Sprint 1: Headless Foundation (10-15h)
**Ziel:** Headless-Mode funktioniert auf Pi Zero/1

1. ✅ Startup-Parameter & Argument-Parsing (2h)
2. ✅ Conditional Module Loading (3h)
3. ✅ RAM-Optimierung (2h)
4. ✅ Performance-Profiling (3-5h)
5. ✅ Testing auf Pi Zero (2-3h)

**Deliverable:** Pi Zero läuft mit <100 MB RAM

---

### Sprint 2: Remote Connectivity (14-18h)
**Ziel:** Satellite kann Daten an Core senden

1. ✅ gRPC Proto-Definition (2h)
2. ✅ Remote Gateway Client (5-6h)
3. ✅ Remote Gateway Server (5-6h)
4. ✅ Data Gateway Integration (2h)
5. ✅ Testing (2-4h)

**Deliverable:** Satellite sendet BMS-Daten an Core

---

### Sprint 3: Discovery & Auto-Config (8-10h)
**Ziel:** Satelliten werden automatisch erkannt

1. ✅ mDNS Service (6-8h)
2. ✅ Auto-Registration (2h)
3. ✅ Testing (2h)

**Deliverable:** Core erkennt Satelliten automatisch

---

### Sprint 4: Performance Optimierung (20-25h)
**Ziel:** Multiprocessing für CPU-intensive Tasks

1. ✅ Adaptive Sleep & Cache-Sizing (6-8h)
2. ✅ Multiprocessing Bridge (8-10h)
3. ✅ Zero-Copy Routing (6-7h)

**Deliverable:** BMS-Parser läuft in separatem Prozess

---

### Sprint 5: External Integration (Optional, 10-15h)
**Ziel:** Node-RED Integration

1. ✅ Node-RED Palette (6-8h)
2. ✅ Logic-Mirroring (4-7h)

**Deliverable:** Node-RED kann mit Edge OS kommunizieren

---

## Hardware-Anforderungen

### Satellite (Headless):
- **Raspberry Pi Zero W:** 512 MB RAM (€10)
- **Raspberry Pi 1 Model B+:** 512 MB RAM (€15 gebraucht)
- **Docker Container:** 256 MB RAM (auf NAS/Desktop)

**RAM-Verbrauch (geschätzt):**
- Python Runtime: ~30 MB
- BaseModules: ~20 MB
- Single Plugin (BLE/RS485): ~20 MB
- Overhead: ~10 MB
- **Total:** ~80-100 MB

### Central Core:
- **UGREEN NAS:** 8 GB RAM (empfohlen)
- **Desktop/Laptop:** 4 GB+ RAM
- **Raspberry Pi 4:** 4 GB RAM (minimum)

**RAM-Verbrauch (geschätzt):**
- Full Stack + Web UI: ~200-300 MB
- Video Transcoding: ~500 MB+
- **Total:** ~800 MB - 1 GB

---

## Testing-Plan

### Unit-Tests:
```python
# test_remote_gateway.py
def test_satellite_connection():
    """Testet Satellite -> Core Verbindung"""
    # Start Mock Core
    # Start Satellite
    # Sende Test-Event
    # Verify Event empfangen

def test_headless_ram_usage():
    """Testet RAM-Verbrauch im Headless-Mode"""
    # Start Headless
    # Messe RAM
    # Assert < 150 MB

def test_discovery_service():
    """Testet mDNS Discovery"""
    # Start Core mit mDNS
    # Start Satellite
    # Verify Auto-Discovery
```

### Integration-Tests:
- Pi Zero als BMS-Satellite
- Desktop als Core
- 3x Docker-Container als Test-Satellites
- Load-Test: 100 Events/sec von 10 Satellites

---

## Bekannte Limitierungen

1. **gRPC Overhead:** ~5-10% Performance-Overhead vs. direkter Kommunikation
2. **mDNS Discovery:** Funktioniert nur im lokalen Netzwerk (keine WAN-Discovery)
3. **Multiprocessing:** Funktionen müssen pickleable sein (keine Lambdas, Closures)
4. **Zero-Copy:** Erfordert sorgfältige Programmierung (keine Mutationen nach Routing)

---

## Migration von v5.0 → v6.0

### Rückwärtskompatibilität:
✅ **100% kompatibel**

v6.0 ist ein **reines Add-On** zu v5.0. Bestehende Installationen laufen ohne Änderungen weiter.

### Opt-In Features:
- Headless-Mode: `--headless` Flag
- Satellite-Mode: `--satellite` Flag
- Performance-Profil: Auto-Detection (kann via ENV überschrieben werden)

**Kein Breaking Change!**

---

## Dokumentation

### Neue Dokumentation:
1. **SATELLITE-SETUP.md** - Guide für Satellite-Installation
2. **GRPC-API.md** - gRPC API-Dokumentation
3. **PERFORMANCE-TUNING.md** - Performance-Optimierung Guide
4. **NODE-RED-INTEGRATION.md** - Node-RED Palette Guide

### Updates:
- **README.md** - v6.0 Features
- **INSTALLATION.md** - Headless-Installation
- **ARCHITECTURE.md** - Distributed Architecture

---

## Nächste Schritte

**Empfohlener Start:** Phase 13.1 (Headless-Mode)

**Begründung:**
- Schnellster Quick-Win (~8-10h)
- Sofort testbar auf Pi Zero
- Keine externen Dependencies
- Bildet Basis für alle weiteren Phasen

**Soll ich mit Phase 13.1 starten?**

---

**Erstellt:** 2026-01-05
**Version:** 1.0.0
**Autor:** SmartHome Edge OS Team
