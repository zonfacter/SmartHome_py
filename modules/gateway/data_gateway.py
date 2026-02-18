"""
Data Gateway Module v5.0.0
Universal Data Router für alle Datenquellen

📁 SPEICHERORT: modules/gateway/data_gateway.py

Features v5.0:
- ⭐ Universal Data Router mit route_data()
- ⭐ Routing-Engine mit deklarativen Regeln (routing.json)
- ⭐ Spam-Protection & Circuit Breaker
- Environment Detection (VM vs Docker)
- 512MB Blob-Cache mit FIFO
- Telemetrie-Cache für Echtzeit-Daten
- Integration mit bestehenden Kommunikationsmodulen
- WebSocket Event Broadcasting
"""

from module_manager import BaseModule
from typing import Any, Dict, Optional, List, Callable
import threading
import time
import platform
import os
import json
from collections import OrderedDict, defaultdict
from datetime import datetime


class DataGateway(BaseModule):
    """
    Data Gateway v5.0.0

    Universal Data Router für alle Datenquellen:
    - ADS (TwinCAT PLC)
    - MQTT (Home Assistant, etc.)
    - Modbus (Wechselrichter)
    - Bluetooth BMS
    - RS485/CAN
    - Plugins

    Features v5.0:
    - Universal Data Router mit route_data()
    - Routing-Engine mit deklarativen Regeln
    - Spam-Protection & Circuit Breaker
    - 512MB RAM-Cache für Blobs (SPS-Bilder)
    - Telemetrie-Cache für Echtzeit-Daten
    - Environment-Awareness (VM/Docker)
    - WebSocket Broadcasting
    """

    NAME = "data_gateway"
    VERSION = "5.0.0"
    DESCRIPTION = "Universal Data Router für alle Datenquellen"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = []  # Optionale Dependencies werden zur Laufzeit geprüft

    # Cache-Limits
    BLOB_CACHE_LIMIT = 512 * 1024 * 1024  # 512 MB
    TELEMETRY_CACHE_SIZE = 10000  # Max Anzahl Telemetrie-Einträge

    # Spam-Protection Limits
    DEFAULT_MAX_PPS = 500  # Max Packets Per Second pro Source
    SPAM_CHECK_WINDOW = 1.0  # Zeitfenster in Sekunden

    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()

        # Environment Detection
        self.platform = platform.system().lower()
        self.is_docker = self._detect_docker()
        self.capabilities = self._detect_capabilities()

        # Caches
        self.blob_cache = OrderedDict()  # key -> (data, timestamp, size)
        self.blob_cache_size = 0
        self.telemetry_cache = {}  # key -> value

        # ⭐ v5.0: Routing-Engine
        self.routing_engine = None
        self.routes = []
        self.subscribers = defaultdict(list)  # pattern -> [callbacks]

        # ⭐ v5.0: Spam-Protection
        self.source_stats = defaultdict(lambda: {
            'packet_count': 0,
            'last_reset': time.time(),
            'status': 'active',
            'total_packets': 0
        })

        # Module-Referenzen (werden in initialize() gesetzt)
        self.plc = None
        self.mqtt = None
        self.modbus = None
        self.web_manager = None

        # Statistik
        self.stats = {
            'blob_hits': 0,
            'blob_misses': 0,
            'blob_evictions': 0,
            'telemetry_updates': 0,
            'routes_processed': 0,
            'routes_blocked': 0,
            'spam_events': 0
        }

        # Missing-symbol protection: track missing symbol warnings to avoid log spam
        # key -> {'count': int, 'last_log': float, 'suspended_until': float}
        self.missing_symbol_stats = {}

    def initialize(self, app_context: Any):
        """Initialisiert Data Gateway"""
        super().initialize(app_context)

        # Save app_context for later operations (widget sync, etc.)
        self._app_context = app_context

        # Hole optionale Module
        mm = app_context.module_manager
        self.plc = mm.get_module('plc_communication')
        self.mqtt = mm.get_module('mqtt_integration')
        self.modbus = mm.get_module('modbus_integration')

        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
        print(f"     🖥️  Platform: {self.platform}")
        print(f"     🐳 Docker: {self.is_docker}")
        print(f"     🎮 GPU: {self.capabilities.get('gpu_available', False)}")
        print(f"     💾 Blob-Cache: {self.BLOB_CACHE_LIMIT // (1024*1024)} MB")

        # ⭐ v5.0: Lade Routing-Konfiguration
        self._load_routing_config()

        # Synchronisiere Widget-Subscriptions (behebt UNKNOWN-Variablen)
        self.sync_widget_subscriptions()

    def _load_routing_config(self):
        """Lädt routing.json Konfiguration"""
        routing_file = os.path.join('config', 'routing.json')

        if not os.path.exists(routing_file):
            print(f"  ℹ️  Keine routing.json gefunden - erstelle Standard-Konfiguration")
            self._create_default_routing_config(routing_file)

        try:
            with open(routing_file, 'r', encoding='utf-8') as f:
                routing_config = json.load(f)

            self.routes = routing_config.get('routes', [])
            print(f"  ✅ Routing-Engine geladen: {len(self.routes)} Routen")

            # Validiere Routen
            self._validate_routes()

        except Exception as e:
            print(f"  ⚠️  Fehler beim Laden der routing.json: {e}")
            self.routes = []

    def _create_default_routing_config(self, filepath: str):
        """Erstellt Standard routing.json Template"""
        default_config = {
            "version": "1.0",
            "description": "Routing-Konfiguration für SmartHome Edge OS v5.0",
            "routes": [
                {
                    "id": "example_passthrough",
                    "description": "Beispiel: Alle Daten durchleiten",
                    "from": "*",
                    "to": ["unified_data_space"],
                    "enabled": True
                }
            ],
            "settings": {
                "max_pps_per_source": self.DEFAULT_MAX_PPS,
                "enable_spam_protection": True,
                "log_all_routes": False
            }
        }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Standard routing.json erstellt: {filepath}")

    def _validate_routes(self):
        """Validiert Routing-Regeln"""
        valid_routes = []
        for route in self.routes:
            if not isinstance(route, dict):
                print(f"  ⚠️  Ungültige Route (kein Dict): {route}")
                continue

            if 'from' not in route or 'to' not in route:
                print(f"  ⚠️  Route fehlt 'from' oder 'to': {route.get('id', 'unknown')}")
                continue

            valid_routes.append(route)

        removed = len(self.routes) - len(valid_routes)
        if removed > 0:
            print(f"  ⚠️  {removed} ungültige Routen entfernt")

        self.routes = valid_routes

    def _detect_docker(self) -> bool:
        """Erkennt ob wir in Docker laufen"""
        if os.path.exists('/.dockerenv'):
            return True

        try:
            with open('/proc/1/cgroup', 'r') as f:
                return 'docker' in f.read()
        except:
            return False

    def _detect_capabilities(self) -> Dict[str, Any]:
        """Erkennt System-Capabilities"""
        caps = {
            'platform': self.platform,
            'is_docker': self.is_docker,
            'gpu_available': False,
            'has_quicksync': False,
            'has_vaapi': False,
            'has_nvenc': False,
            'gpu_vendor': None
        }

        # GPU-Detection
        if self.platform == 'linux':
            # Intel QuickSync / VAAPI (Linux)
            if os.path.exists('/dev/dri/renderD128'):
                caps['gpu_available'] = True
                caps['has_quicksync'] = True
                caps['has_vaapi'] = True
                caps['gpu_vendor'] = 'Intel'

        elif self.platform == 'windows':
            # Windows GPU Detection - Erkennt ALLE GPUs
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

                # Parse alle GPU-Namen
                gpu_lines = [line.strip() for line in result.stdout.split('\n') if line.strip() and line.strip() != 'Name']
                caps['gpu_list'] = gpu_lines
                caps['gpu_count'] = len(gpu_lines)

                # Erkenne GPU-Features
                has_intel = False
                has_nvidia = False
                has_amd = False

                for gpu in gpu_lines:
                    gpu_lower = gpu.lower()
                    if 'intel' in gpu_lower:
                        has_intel = True
                        caps['has_quicksync'] = True
                    elif 'nvidia' in gpu_lower:
                        has_nvidia = True
                        caps['has_nvenc'] = True
                    elif 'amd' in gpu_lower or 'radeon' in gpu_lower:
                        has_amd = True

                # Setze primäre GPU (NVIDIA > AMD > Intel für Encoding)
                if has_nvidia:
                    caps['gpu_available'] = True
                    caps['gpu_vendor'] = 'NVIDIA'
                    caps['primary_gpu'] = next((g for g in gpu_lines if 'nvidia' in g.lower()), 'NVIDIA')
                elif has_amd:
                    caps['gpu_available'] = True
                    caps['gpu_vendor'] = 'AMD'
                    caps['primary_gpu'] = next((g for g in gpu_lines if 'amd' in g.lower() or 'radeon' in g.lower()), 'AMD')
                elif has_intel:
                    caps['gpu_available'] = True
                    caps['gpu_vendor'] = 'Intel'
                    caps['primary_gpu'] = next((g for g in gpu_lines if 'intel' in g.lower()), 'Intel')

            except:
                # Fallback
                caps['gpu_available'] = True
                caps['gpu_vendor'] = 'Unknown'
                caps['gpu_list'] = []
                caps['gpu_count'] = 0

        # Deployment-Mode
        if self.is_docker and caps['gpu_available']:
            caps['mode'] = f"Docker ({caps['gpu_vendor']} GPU)"
        elif self.is_docker:
            caps['mode'] = 'Docker (CPU)'
        elif caps['gpu_available']:
            caps['mode'] = f"Windows ({caps['gpu_vendor']} GPU)"
        else:
            caps['mode'] = f"{self.platform.title()} (CPU)"

        return caps

    # ========================================================================
    # ⭐ v5.0: UNIVERSAL DATA ROUTER
    # ========================================================================

    def route_data(self, source_id: str, tag: str, value: Any, metadata: Dict = None) -> bool:
        """
        Universal Data Router - Herzstück des v5.0 Systems

        Empfängt Datenpunkte von beliebigen Quellen und routet sie gemäß
        der Routing-Konfiguration (routing.json) an Ziele.

        Args:
            source_id: Quelle (z.B. "plc_001", "bt.bms_001", "mqtt.broker_1", "MyPlugin")
            tag: Datenpunkt-Tag (z.B. "MAIN.temperature", "voltage", "sensors/temp1")
            value: Wert (any serializable type)
            metadata: Optional - zusätzliche Metadaten (timestamp, quality, etc.)

        Returns:
            True wenn erfolgreich geroutet, False bei Spam-Block

        Example:
            # Von Plugin:
            gateway.route_data("MyPlugin", "sensors/temperature", 23.5)

            # Von PLC:
            gateway.route_data("plc_001", "MAIN.bAlarm", True, {"quality": "good"})

            # Von Bluetooth BMS:
            gateway.route_data("bt.bms_001", "voltage", 52.3, {"rssi": -45})
        """
        with self.lock:
            # 1. Spam-Protection Check
            if not self._check_spam_protection(source_id):
                self.stats['routes_blocked'] += 1
                return False

            # 2. Normalisierung in Unified Data Space
            datapoint = self._normalize_datapoint(source_id, tag, value, metadata)

            # 3. Aktualisiere Telemetrie-Cache
            unified_key = f"{source_id}.{tag}"
            self.update_telemetry(unified_key, value)

            # 4. Route-Matching und Weiterleitung
            matched_routes = self._match_routes(datapoint)

            for route in matched_routes:
                try:
                    self._execute_route(route, datapoint)
                except Exception as e:
                    print(f"  ⚠️  Routing-Fehler in Route '{route.get('id', 'unknown')}': {e}")

            # 5. Notify Subscribers
            self._notify_subscribers(datapoint)

            self.stats['routes_processed'] += 1
            return True

    def _check_spam_protection(self, source_id: str) -> bool:
        """
        Prüft ob Source die Spam-Grenzen überschreitet

        Returns:
            True wenn OK, False wenn geblockt
        """
        # FIX: Initialisiere Stats falls nicht vorhanden
        if source_id not in self.source_stats:
            self.source_stats[source_id] = {
                'packet_count': 0,
                'total_packets': 0,
                'last_reset': time.time(),
                'status': 'active'
            }

        stats = self.source_stats[source_id]

        # Status-Check
        if stats['status'] == 'suspended_spam':
            return False

        # Reset Counter bei neuem Zeitfenster
        current_time = time.time()
        elapsed = current_time - stats['last_reset']

        if elapsed >= self.SPAM_CHECK_WINDOW:
            stats['packet_count'] = 0
            stats['last_reset'] = current_time

        # Inkrementiere Counter
        stats['packet_count'] += 1
        stats['total_packets'] += 1

        # Check Limit
        pps = stats['packet_count'] / max(elapsed, 0.001)

        if pps > self.DEFAULT_MAX_PPS:
            print(f"  🚫 SPAM DETECTED: Source '{source_id}' überschreitet Limit ({pps:.1f} pps > {self.DEFAULT_MAX_PPS} pps)")
            print(f"     Status: SUSPENDED - Manuelle Reaktivierung erforderlich")

            stats['status'] = 'suspended_spam'
            stats['suspended_at'] = current_time

            self.stats['spam_events'] += 1

            # Broadcast Spam-Event an WebUI
            if self.web_manager:
                self.web_manager.broadcast_system_event({
                    'type': 'spam_protection',
                    'source_id': source_id,
                    'pps': round(pps, 1),
                    'limit': self.DEFAULT_MAX_PPS,
                    'action': 'suspended'
                })

            return False

        return True

    def _normalize_datapoint(self, source_id: str, tag: str, value: Any, metadata: Dict = None) -> Dict:
        """
        Normalisiert Datenpunkt in einheitliches Format

        Returns:
            {
                'source_id': str,
                'tag': str,
                'value': any,
                'timestamp': float,
                'quality': str,
                'metadata': dict
            }
        """
        return {
            'source_id': source_id,
            'tag': tag,
            'value': value,
            'timestamp': metadata.get('timestamp', time.time()) if metadata else time.time(),
            'quality': metadata.get('quality', 'good') if metadata else 'good',
            'metadata': metadata or {}
        }

    def _match_routes(self, datapoint: Dict) -> List[Dict]:
        """
        Matched Datenpunkt gegen alle Routing-Regeln

        Returns:
            Liste der matchenden Routen
        """
        matched = []
        source_id = datapoint['source_id']
        tag = datapoint['tag']
        full_path = f"{source_id}.{tag}"

        for route in self.routes:
            # Skip disabled routes
            if not route.get('enabled', True):
                continue

            # Pattern matching
            pattern = route.get('from', '')

            # Wildcard: * matched alles
            if pattern == '*':
                matched.append(route)
                continue

            # Exact match
            if pattern == full_path or pattern == tag or pattern == source_id:
                matched.append(route)
                continue

            # Prefix match (z.B. "plc_001.*")
            if pattern.endswith('*') and full_path.startswith(pattern[:-1]):
                matched.append(route)
                continue

        return matched

    def _execute_route(self, route: Dict, datapoint: Dict):
        """
        Führt eine Route aus - sendet Daten an Ziel(e)

        Args:
            route: Routing-Regel
            datapoint: Normalisierter Datenpunkt
        """
        targets = route.get('to', [])
        if isinstance(targets, str):
            targets = [targets]

        for target in targets:
            self._send_to_target(target, datapoint, route)

    def _send_to_target(self, target: str, datapoint: Dict, route: Dict):
        """
        Sendet Datenpunkt an spezifisches Ziel

        Targets:
            - "unified_data_space" -> Nur Telemetrie-Cache
            - "plc_001.MAIN.variable" -> PLC-Variable schreiben
            - "mqtt.broker_local.topic/path" -> MQTT Publish
            - "log.system" -> Logging
            - "widgets" -> Broadcast an UI
        """
        # Unified Data Space (default)
        if target == "unified_data_space":
            # Bereits im Telemetrie-Cache durch route_data()
            pass

        # PLC Target
        elif target.startswith("plc"):
            self._route_to_plc(target, datapoint, route)

        # MQTT Target
        elif target.startswith("mqtt"):
            self._route_to_mqtt(target, datapoint, route)

        # Log Target
        elif target.startswith("log"):
            self._route_to_log(target, datapoint, route)

        # Widget Broadcast
        elif target == "widgets":
            self._route_to_widgets(datapoint)

        else:
            print(f"  ⚠️  Unbekanntes Routing-Ziel: {target}")

    def _route_to_plc(self, target: str, datapoint: Dict, route: Dict):
        """Routet Daten zur PLC"""
        # Format: "plc_001.MAIN.variable"
        parts = target.split('.', 1)
        if len(parts) < 2:
            return

        plc_id = parts[0]
        symbol = parts[1]

        # TODO: Multi-PLC Support (Phase 2)
        # Aktuell: Nutze self.plc (einzelne PLC)
        if self.plc and self.plc.connected:
            try:
                # Auto-detect PLC type
                value = datapoint['value']
                self.plc.write_by_name(symbol, value)
            except Exception as e:
                print(f"  ⚠️  PLC-Write Fehler ({symbol}): {e}")

    def _route_to_mqtt(self, target: str, datapoint: Dict, route: Dict):
        """Routet Daten zu MQTT"""
        # Format: "mqtt.broker_local.topic/path"
        parts = target.split('.', 2)
        if len(parts) < 3:
            return

        broker_id = parts[1]
        topic = parts[2]

        # TODO: Multi-MQTT Support (Phase 2)
        # Aktuell: Nutze self.mqtt (einzelner Broker)
        if self.mqtt:
            try:
                import json
                payload = json.dumps({
                    'value': datapoint['value'],
                    'timestamp': datapoint['timestamp'],
                    'source': datapoint['source_id']
                })
                # self.mqtt.publish(topic, payload)  # TODO: Implementierung in mqtt_module
            except Exception as e:
                print(f"  ⚠️  MQTT-Publish Fehler ({topic}): {e}")

    def _route_to_log(self, target: str, datapoint: Dict, route: Dict):
        """Routet Daten zum Logging-System"""
        print(f"  📝 LOG [{datapoint['source_id']}] {datapoint['tag']} = {datapoint['value']}")

    def _route_to_widgets(self, datapoint: Dict):
        """Broadcast Datenpunkt an alle WebSocket-Clients (Widgets)"""
        if self.web_manager:
            unified_key = f"{datapoint['source_id']}.{datapoint['tag']}"
            self.web_manager.broadcast_telemetry(unified_key, datapoint['value'])

    def _notify_subscribers(self, datapoint: Dict):
        """Benachrichtigt registrierte Subscriber"""
        full_path = f"{datapoint['source_id']}.{datapoint['tag']}"

        # FIX: Thread-safe subscriber iteration
        with self.lock:
            # Exact match subscribers
            for callback in list(self.subscribers.get(full_path, [])):
                try:
                    callback(datapoint)
                except Exception as e:
                    print(f"  ⚠️  Subscriber-Fehler: {e}")

            # Wildcard subscribers
            for pattern, callbacks in list(self.subscribers.items()):
                if '*' in pattern:
                    # Simple wildcard matching
                    if pattern.endswith('*') and full_path.startswith(pattern[:-1]):
                        for callback in list(callbacks):
                            try:
                                callback(datapoint)
                            except Exception as e:
                                print(f"  ⚠️  Subscriber-Fehler: {e}")

    def subscribe(self, pattern: str, callback: Callable):
        """
        Registriert Callback für Datenpunkte

        Args:
            pattern: Pattern (z.B. "plc_001.MAIN.*", "bt.bms_001.voltage")
            callback: Callback-Funktion callback(datapoint: Dict)

        Example:
            def on_alarm(dp):
                print(f"Alarm: {dp['value']}")

            gateway.subscribe("plc_001.MAIN.bAlarm", on_alarm)
        """
        self.subscribers[pattern].append(callback)

    def unsubscribe(self, pattern: str, callback: Callable):
        """Entfernt Callback für Pattern"""
        if pattern in self.subscribers:
            try:
                self.subscribers[pattern].remove(callback)
            except ValueError:
                pass

    def reset_spam_protection(self, source_id: str):
        """
        Setzt Spam-Protection für eine Source zurück (Admin-Funktion)

        Args:
            source_id: Source-ID die reaktiviert werden soll
        """
        if source_id in self.source_stats:
            stats = self.source_stats[source_id]
            stats['status'] = 'active'
            stats['packet_count'] = 0
            stats['last_reset'] = time.time()

            print(f"  ✅ Spam-Protection zurückgesetzt für: {source_id}")

            # Broadcast an WebUI
            if self.web_manager:
                self.web_manager.broadcast_system_event({
                    'type': 'spam_protection',
                    'source_id': source_id,
                    'action': 'reset'
                })

    def get_routing_stats(self) -> Dict:
        """Liefert Routing-Statistiken für Admin-UI"""
        return {
            'routes_loaded': len(self.routes),
            'routes_processed': self.stats['routes_processed'],
            'routes_blocked': self.stats['routes_blocked'],
            'spam_events': self.stats['spam_events'],
            'sources': {
                source_id: {
                    'total_packets': stats['total_packets'],
                    'status': stats['status'],
                    'pps_current': stats['packet_count'] / max(time.time() - stats['last_reset'], 0.001)
                }
                for source_id, stats in self.source_stats.items()
            }
        }

    # ========================================================================
    # BLOB-CACHE (für SPS-Bilder, etc.)
    # ========================================================================

    def store_blob(self, key: str, data: bytes) -> bool:
        """
        Speichert Blob im RAM-Cache (512MB FIFO)

        Args:
            key: Eindeutiger Schlüssel (z.B. 'plc_image_1')
            data: Binärdaten

        Returns:
            True wenn erfolgreich gespeichert
        """
        with self.lock:
            size = len(data)

            # Prüfe ob zu groß
            if size > self.BLOB_CACHE_LIMIT:
                return False

            # FIFO: Entferne älteste Einträge bis genug Platz
            while self.blob_cache_size + size > self.BLOB_CACHE_LIMIT:
                if not self.blob_cache:
                    break
                oldest_key = next(iter(self.blob_cache))
                self._evict_blob(oldest_key)

            # Speichere
            timestamp = time.time()
            self.blob_cache[key] = (data, timestamp, size)
            self.blob_cache_size += size

            # Broadcast Update
            self._broadcast_blob_update(key)

            return True

    def get_blob(self, key: str) -> Optional[bytes]:
        """
        Holt Blob aus Cache

        Args:
            key: Blob-Schlüssel

        Returns:
            Binärdaten oder None
        """
        with self.lock:
            if key in self.blob_cache:
                self.stats['blob_hits'] += 1
                return self.blob_cache[key][0]
            else:
                self.stats['blob_misses'] += 1
                return None

    def _evict_blob(self, key: str):
        """Entfernt Blob aus Cache"""
        if key in self.blob_cache:
            _, _, size = self.blob_cache[key]
            del self.blob_cache[key]
            self.blob_cache_size -= size
            self.stats['blob_evictions'] += 1

    def get_blob_stats(self) -> Dict[str, Any]:
        """Statistik über Blob-Cache"""
        with self.lock:
            return {
                'count': len(self.blob_cache),
                'total_size': self.blob_cache_size,
                'cache_limit': self.BLOB_CACHE_LIMIT,
                'utilization': round(self.blob_cache_size / self.BLOB_CACHE_LIMIT * 100, 2),
                'hits': self.stats['blob_hits'],
                'misses': self.stats['blob_misses'],
                'evictions': self.stats['blob_evictions']
            }

    # ========================================================================
    # TELEMETRIE-CACHE (für Echtzeit-Werte)
    # ========================================================================

    def update_telemetry(self, key: str, value: Any):
        """
        Aktualisiert Telemetrie-Wert und broadcastet an WebSocket-Clients

        Args:
            key: Telemetrie-Key (z.B. 'PLC.MAIN.temperature')
            value: Wert (int, float, bool, str)
        """
        with self.lock:
            # Speichere
            self.telemetry_cache[key] = value
            self.stats['telemetry_updates'] += 1

            # LRU: Begrenze Cache-Größe
            if len(self.telemetry_cache) > self.TELEMETRY_CACHE_SIZE:
                # Entferne älteste Hälfte (einfache Strategie)
                keys_to_remove = list(self.telemetry_cache.keys())[:self.TELEMETRY_CACHE_SIZE // 2]
                for k in keys_to_remove:
                    del self.telemetry_cache[k]

            # Broadcast Update
            self._broadcast_telemetry_update(key, value)

            # Optionaler Hook (z. B. Kamera-Trigger-Regeln im WebManager)
            if self.web_manager and hasattr(self.web_manager, 'handle_telemetry_update'):
                try:
                    self.web_manager.handle_telemetry_update(key, value)
                except Exception:
                    pass

    def get_telemetry(self, key: str) -> Optional[Any]:
        """
        Holt Telemetrie-Wert aus Cache

        Args:
            key: Telemetrie-Key

        Returns:
            Wert oder None
        """
        with self.lock:
            return self.telemetry_cache.get(key)

    def get_all_telemetry(self) -> Dict[str, Any]:
        """Gibt alle Telemetrie-Werte zurück"""
        with self.lock:
            return dict(self.telemetry_cache)

    # ========================================================================
    # WIDGET SUBSCRIPTION SYNC (behebt UNKNOWN-Variablen)
    # ========================================================================

    def sync_widget_subscriptions(self):
        """
        Synchronisiert Widget-Variablen mit PLC-Treiber.
        Behebt UNKNOWN-Variable-Problem durch explizites Subscription.

        Diese Methode wird beim Start aufgerufen und liest alle Widget-Konfigurationen
        aus, um die PLC-Variablen vorab zu registrieren.
        """
        try:
            # FIX: Prüfe ob app_context vorhanden ist
            if not hasattr(self, '_app_context') or self._app_context is None:
                print("  ⚠️  Widget-Sync: app_context nicht initialisiert")
                return

            # Hole Config Manager
            config_mgr = self._app_context.module_manager.get_module('config_manager')
            if not config_mgr:
                print("  ⚠️  Widget-Sync: Config Manager nicht verfügbar")
                return

            # Hole alle Widgets (nutze neue get_widgets() Methode)
            widgets = config_mgr.get_widgets() if hasattr(config_mgr, 'get_widgets') else config_mgr.get_config_value('widgets', {})
            if not widgets:
                print("  ℹ️  Widget-Sync: Keine Widgets konfiguriert (wird beim ersten Widget-Erstellen angelegt)")
                return

            # Prüfe ob PLC verfügbar
            if not self.plc:
                print("  ⚠️  Widget-Sync: PLC-Modul nicht verfügbar")
                return

            # FIX: Prüfe ob PLC VERBUNDEN ist (sonst sinnlos)
            if not self.plc.connected:
                print(f"  ⚠️  Widget-Sync: PLC nicht verbunden - überspringe {len(widgets)} Widgets")
                print("     Sync wird automatisch nach PLC-Connect ausgeführt")
                return

            print(f"  🔄 Synchronisiere {len(widgets)} Widgets mit PLC...")

            synced_count = 0
            for widget_id, widget_config in widgets.items():
                bindings = widget_config.get('bindings', {})

                for binding_key, binding_config in bindings.items():
                    variable = binding_config.get('variable')
                    plc_type_str = binding_config.get('plc_type', 'BOOL')

                    if variable:
                        # Konvertiere PLC-Typ zu pyads Konstante
                        try:
                            import pyads
                            plc_type_map = {
                                'BOOL': pyads.PLCTYPE_BOOL,
                                'INT': pyads.PLCTYPE_INT,
                                'DINT': pyads.PLCTYPE_DINT,
                                'REAL': pyads.PLCTYPE_REAL,
                                'LREAL': pyads.PLCTYPE_LREAL,
                                'STRING': pyads.PLCTYPE_STRING
                            }
                            plc_type = plc_type_map.get(plc_type_str, pyads.PLCTYPE_BOOL)

                            # Vorab-Lesen um Variable zu "subsciben"
                            # (PLC-Cache wird hierdurch initialisiert)
                            if self.plc.connected:
                                self.plc.read_by_name(variable, plc_type)
                                synced_count += 1

                        except Exception as e:
                            print(f"  ⚠️  Widget-Sync-Fehler ({variable}): {e}")

            print(f"  ✅ Widget-Sync abgeschlossen: {synced_count} Variablen registriert")

        except Exception as e:
            print(f"  ✗ Widget-Sync fehlgeschlagen: {e}")

    # ========================================================================
    # PLC INTEGRATION
    # ========================================================================

    def read_plc(self, symbol: str) -> Optional[Any]:
        """
        Liest PLC-Variable (mit Caching)

        Args:
            symbol: PLC-Symbol (z.B. 'MAIN.temperature')

        Returns:
            Wert oder None
        """
        if not self.plc:
            return None

        try:
            # Try to resolve plc_type from registered symbol info
            plc_type = None
            try:
                symbol_info = self.variable_manager.get_symbol_info(symbol)
                if symbol_info and isinstance(symbol_info.symbol_type, str):
                    import pyads
                    type_map = {
                        'BOOL': pyads.PLCTYPE_BOOL,
                        'INT': pyads.PLCTYPE_INT,
                        'DINT': pyads.PLCTYPE_DINT,
                        'REAL': pyads.PLCTYPE_REAL,
                        'LREAL': pyads.PLCTYPE_LREAL,
                        'STRING': pyads.PLCTYPE_STRING,
                        'BYTE': pyads.PLCTYPE_BYTE
                    }
                    plc_type = type_map.get(symbol_info.symbol_type.upper(), None)
            except Exception:
                plc_type = None

            # PLCCommunication.read_by_name requires plc_type positional arg
            if plc_type is None:
                import pyads
                plc_type = pyads.PLCTYPE_BYTE

            value = self.plc.read_by_name(symbol, plc_type)

            # Cache Update
            cache_key = f"PLC.{symbol}"
            self.update_telemetry(cache_key, value)

            return value
        except Exception as e:
            print(f"  ✗ PLC read error ({symbol}): {e}")
            return None

    def write_plc(self, symbol: str, value: Any, plc_type: int = None) -> bool:
        """
        Schreibt PLC-Variable

        Args:
            symbol: PLC-Symbol
            value: Wert
            plc_type: pyads.PLCTYPE_* (optional, wird automatisch erkannt)

        Returns:
            True wenn erfolgreich
        """
        if not self.plc:
            return False

        try:
            # Auto-Detect PLC-Typ falls nicht angegeben
            if plc_type is None:
                import pyads
                if isinstance(value, bool):
                    plc_type = pyads.PLCTYPE_BOOL
                elif isinstance(value, int):
                    plc_type = pyads.PLCTYPE_DINT
                elif isinstance(value, float):
                    plc_type = pyads.PLCTYPE_REAL
                elif isinstance(value, str):
                    plc_type = pyads.PLCTYPE_STRING
                else:
                    plc_type = pyads.PLCTYPE_BOOL  # Fallback

            self.plc.write_by_name(symbol, value, plc_type)

            # Cache Update
            cache_key = f"PLC.{symbol}"
            self.update_telemetry(cache_key, value)

            return True
        except Exception as e:
            print(f"  ✗ PLC write error ({symbol}): {e}")
            return False

    # ========================================================================
    # WEBSOCKET BROADCASTING
    # ========================================================================

    def _broadcast_telemetry_update(self, key: str, value: Any):
        """Sendet Telemetrie-Update an alle WebSocket-Clients"""
        if self.web_manager:
            self.web_manager.broadcast_telemetry(key, value)

    def _broadcast_blob_update(self, key: str):
        """Sendet Blob-Update-Notification an alle WebSocket-Clients"""
        if self.web_manager:
            self.web_manager.broadcast_blob_update(key)

    def set_web_manager(self, web_manager):
        """Setzt WebManager-Referenz (wird von WebManager aufgerufen)"""
        self.web_manager = web_manager

    # ========================================================================
    # SYSTEM
    # ========================================================================

    def get_system_status(self) -> Dict[str, Any]:
        """System-Status für Web-API"""
        # PLC-Verbindungsstatus prüfen
        plc_connected = False
        if self.plc:
            try:
                plc_status = self.plc.get_connection_status()
                plc_connected = plc_status.get('connected', False)
            except Exception:
                pass

        # Gesamt-Systemstatus
        status = 'connected' if plc_connected else 'disconnected'

        return {
            'status': status,
            'plc': {
                'connected': plc_connected
            },
            'capabilities': self.capabilities,
            'blob_stats': self.get_blob_stats(),
            'telemetry_count': len(self.telemetry_cache),
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }

    # ============================================================
    # VARIABLE POLLING SYSTEM (v5.1.0)
    # ============================================================

    def start_variable_polling(self, variable_manager, socketio, poll_interval=0.5):
        """
        Startet Background Polling Thread für Widget-Variables

        Args:
            variable_manager: VariableManager Instanz
            socketio: Socket.IO Instanz für Broadcasting
            poll_interval: Polling-Intervall in Sekunden (Standard: 0.5s = 2 Hz)
        """
        self.variable_manager = variable_manager
        self.socketio = socketio
        self.poll_interval = poll_interval
        self.polling_active = False
        self.polling_thread = None

        # Starte Thread
        self.polling_active = True
        self.polling_thread = threading.Thread(
            target=self._variable_poll_loop,
            daemon=True,
            name="VariablePollingThread"
        )
        self.polling_thread.start()

        print(f"  ✅ Variable Polling gestartet (Intervall: {poll_interval}s)")

    def stop_variable_polling(self):
        """Stoppt Background Polling Thread"""
        if hasattr(self, 'polling_active'):
            self.polling_active = False

            if hasattr(self, 'polling_thread') and self.polling_thread:
                self.polling_thread.join(timeout=2.0)

            print("  ⏹️  Variable Polling gestoppt")

    def _variable_poll_loop(self):
        """Polling-Loop (läuft im Background)"""
        import logging
        import time
        logger = logging.getLogger(__name__)

        logger.info("🔄 Variable Polling Loop gestartet")

        while self.polling_active:
            try:
                # Hole alle abonnierten Variablen
                subscribed_vars = self.variable_manager.get_all_subscribed_variables()

                if not subscribed_vars:
                    # Keine Subscriptions -> Sleep länger
                    time.sleep(1.0)
                    continue

                # Lese Werte von PLC(s)
                updates = self._read_subscribed_variables(subscribed_vars)

                if updates:
                    # Broadcast Update (Safe-Implementation)
                    socket_instance = getattr(self, 'socketio', None)
                    if socket_instance is not None:
                        try:
                            socket_instance.emit('variable_updates', updates)
                        except Exception as e:
                            logger.debug(f"Broadcast temporär nicht möglich: {e}")

                # Sleep bis nächster Poll
                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"❌ Polling-Fehler: {e}", exc_info=True)
                time.sleep(1.0)  # Längerer Sleep nach Fehler

        logger.info("🛑 Variable Polling Loop beendet")
    def _read_subscribed_variables(self, subscribed_vars: list) -> dict:
        """
        Liest alle abonnierten Variablen von PLC(s)

        Args:
            subscribed_vars: Liste von (plc_id, variable_name) Tupeln

        Returns:
            Dictionary mit Updates: {plc_id: {variable_name: {...}}}
        """
        import logging
        logger = logging.getLogger(__name__)

        updates = {}

        # Gruppiere nach PLC
        by_plc = {}
        for plc_id, var_name in subscribed_vars:
            if plc_id not in by_plc:
                by_plc[plc_id] = []
            by_plc[plc_id].append(var_name)

        # Lese von jeder PLC
        for plc_id, var_names in by_plc.items():
            if plc_id not in updates:
                updates[plc_id] = {}

            for var_name in var_names:
                try:
                    # Hole Symbol-Info
                    symbol_info = self.variable_manager.get_symbol_info(var_name, plc_id)
                    if not symbol_info:
                        # Missing symbol - apply backoff to avoid spam
                        key = f"{plc_id}/{var_name}"
                        now = time.time()
                        ms = self.missing_symbol_stats.get(key, {'count': 0, 'last_log': 0, 'suspended_until': 0})

                        # If currently suspended, skip without logging
                        if ms.get('suspended_until', 0) > now:
                            continue

                        ms['count'] = ms.get('count', 0) + 1
                        ms['last_log'] = now

                        # Escalate suspension window: after 3 warnings suspend for 60s
                        if ms['count'] >= 3:
                            ms['suspended_until'] = now + 60.0
                            # Reset count to avoid overflow
                            ms['count'] = 0

                        self.missing_symbol_stats[key] = ms

                        # Log warning only for first 3 times, then suppressed for 60s
                        logger_warning = ms.get('count', 0) <= 3
                        if logger_warning:
                            logger.warning(f"⚠️  Symbol-Info nicht gefunden: {plc_id}/{var_name} (warn {ms['count']})")

                        # Notify UI but rate-limit these notifications
                        if self.web_manager and ms.get('count', 0) == 1:
                            try:
                                self.web_manager.broadcast_system_event({
                                    'type': 'symbol_missing',
                                    'plc_id': plc_id,
                                    'variable': var_name,
                                    'message': 'Symbol-Info nicht gefunden'
                                })
                            except Exception:
                                pass

                        continue

                    # Lese Wert von PLC
                    if self.plc and getattr(self.plc, 'connected', False):
                        # Resolve plc_type from symbol_info
                        plc_type = None
                        try:
                            if symbol_info and isinstance(symbol_info.symbol_type, str):
                                import pyads
                                type_map = {
                                    'BOOL': pyads.PLCTYPE_BOOL,
                                    'INT': pyads.PLCTYPE_INT,
                                    'DINT': pyads.PLCTYPE_DINT,
                                    'REAL': pyads.PLCTYPE_REAL,
                                    'LREAL': pyads.PLCTYPE_LREAL,
                                    'STRING': pyads.PLCTYPE_STRING,
                                    'BYTE': pyads.PLCTYPE_BYTE
                                }
                                plc_type = type_map.get(symbol_info.symbol_type.upper(), None)
                        except Exception:
                            plc_type = None

                        # If PLCCommunication expects plc_type, provide a safe default
                        if plc_type is None:
                            import pyads
                            plc_type = pyads.PLCTYPE_BYTE

                        value = self.plc.read_by_name(var_name, plc_type)

                        # Prüfe ob Wert sich geändert hat
                        cached = self.variable_manager.get_cached_value(var_name, plc_id)
                        if not cached or cached[0] != value:
                            # Wert hat sich geändert → Update
                            self.variable_manager.update_value(var_name, value, plc_id)
                            # Spiegel in Telemetrie-Cache für Regel-Engine/Frontend
                            self.update_telemetry(f"PLC.{var_name}", value)

                            updates[plc_id][var_name] = {
                                'value': value,
                                'timestamp': time.time(),
                                'type': symbol_info.symbol_type,
                                'plc_id': plc_id
                            }

                            logger.debug(f"📊 {plc_id}/{var_name} = {value}")

                except Exception as e:
                    logger.error(f"❌ Fehler beim Lesen von {plc_id}/{var_name}: {e}")
                    continue

        return updates

    def write_variable(self, variable_name: str, value: Any, plc_id: str = 'plc_001') -> bool:
        """
        Schreibt Wert zur PLC

        Args:
            variable_name: Symbol-Name
            value: Neuer Wert
            plc_id: PLC-ID

        Returns:
            True bei Erfolg, False bei Fehler
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Hole Symbol-Info
            symbol_info = self.variable_manager.get_symbol_info(variable_name, plc_id)
            if not symbol_info:
                logger.error(f"❌ Symbol nicht gefunden: {plc_id}/{variable_name}")
                return False

            # Schreibe zu PLC
            if self.plc and getattr(self.plc, 'connected', False):
                # ⭐ v5.1.2: plc_type aus Symbol-Info verwenden
                plc_type = symbol_info.symbol_type

                # Wenn type als String vorliegt, mappe zu pyads PLCTYPE Konstanten
                try:
                    import pyads
                    if isinstance(plc_type, str):
                        type_map = {
                            'BOOL': pyads.PLCTYPE_BOOL,
                            'INT': pyads.PLCTYPE_INT,
                            'DINT': pyads.PLCTYPE_DINT,
                            'REAL': pyads.PLCTYPE_REAL,
                            'LREAL': pyads.PLCTYPE_LREAL,
                            'STRING': pyads.PLCTYPE_STRING,
                            'BYTE': pyads.PLCTYPE_BYTE
                        }
                        plc_type = type_map.get(plc_type.upper(), None)
                except Exception:
                    plc_type = None

                # Fallback: wenn plc_type None, lasse PLC-Connection auto-detect verwenden
                if plc_type is None:
                    self.plc.write_by_name(variable_name, value)
                else:
                    self.plc.write_by_name(variable_name, value, plc_type)

                # Update Cache
                self.variable_manager.update_value(variable_name, value, plc_id)

                # Broadcast Update
                # Prüfe sicher, ob das Attribut existiert UND nicht None ist
                socket_instance = getattr(self, 'socketio', None) 

                if socket_instance is not None:
                    try:
                        socket_instance.emit('variable_updates', {
                            plc_id: {
                                variable_name: {
                                    'value': value,
                                    'timestamp': time.time(),
                                    'type': symbol_info.symbol_type,
                                    'plc_id': plc_id
                                }
                            }
                        })
                    except Exception as e:
                        # Verhindert, dass ein fehlerhafter Broadcast den ganzen Loop reißt
                        logger.debug(f"Broadcast temporär nicht möglich: {e}") 

                logger.info(f"✍️  {plc_id}/{variable_name} = {value}")
                return True

        except Exception as e:
            logger.error(f"❌ Fehler beim Schreiben von {plc_id}/{variable_name}: {e}", exc_info=True)
            return False

    # ============================================================
    # END VARIABLE POLLING SYSTEM
    # ============================================================

    def shutdown(self):
        """Cleanup"""
        # Stoppe Polling-Thread
        self.stop_variable_polling()

        with self.lock:
            self.blob_cache.clear()
            self.telemetry_cache.clear()
            self.blob_cache_size = 0


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        DataGateway.NAME,
        DataGateway.VERSION,
        DataGateway.DESCRIPTION,
        DataGateway,
        author=DataGateway.AUTHOR,
        dependencies=DataGateway.DEPENDENCIES
    )
