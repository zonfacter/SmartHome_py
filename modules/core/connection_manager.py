"""
Connection Manager Module v4.6.0
Verwaltet beliebig viele parallele Verbindungen

📁 SPEICHERORT: modules/core/connection_manager.py

Features v4.6.0:
- ⭐ Multi-Instance Support (mehrere PLCs, MQTT-Broker, etc.)
- ⭐ Einheitliches Lifecycle-Management
- ⭐ Health-Monitoring pro Verbindung
- ⭐ Hot-Reload von Konfigurationen
- Automatisches Reconnect
- Status-Tracking & Events
"""

from module_manager import BaseModule
from typing import Any, Dict, Optional, List, Type
import threading
import time
import json
import os
from abc import ABC, abstractmethod
from enum import Enum


class ConnectionStatus(Enum):
    """Verbindungsstatus-Enum"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    SUSPENDED = "suspended"


class BaseConnection(ABC):
    """
    Abstrakte Basisklasse für alle Verbindungen

    Jeder Verbindungstyp (PLC, MQTT, Bluetooth, etc.) erbt von dieser Klasse
    und implementiert die abstrakten Methoden.
    """

    def __init__(self, connection_id: str, config: Dict, app_context: Any):
        """
        Args:
            connection_id: Eindeutige ID (z.B. "plc_001", "mqtt_broker_local")
            config: Verbindungs-Konfiguration
            app_context: Application Context für Module-Zugriff
        """
        self.connection_id = connection_id
        self.config = config
        self.app_context = app_context

        self.status = ConnectionStatus.DISCONNECTED
        self.last_error = None
        self.connected_at = None
        self.reconnect_attempts = 0

        # Statistik
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'last_activity': None
        }

        # Lifecycle
        self._running = False
        self._lock = threading.RLock()

    @abstractmethod
    def connect(self) -> bool:
        """
        Stellt Verbindung her

        Returns:
            True wenn erfolgreich
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Trennt Verbindung sauber

        Returns:
            True wenn erfolgreich
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Prüft ob Verbindung aktiv ist

        Returns:
            True wenn verbunden
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Führt Health-Check durch

        Returns:
            True wenn gesund
        """
        pass

    def get_status(self) -> Dict:
        """Liefert Status-Informationen"""
        with self._lock:
            return {
                'connection_id': self.connection_id,
                'type': self.__class__.__name__,
                'status': self.status.value,
                'connected_at': self.connected_at,
                'last_error': self.last_error,
                'reconnect_attempts': self.reconnect_attempts,
                'stats': self.stats.copy()
            }

    def update_stats(self, packets_sent: int = 0, packets_received: int = 0,
                     bytes_sent: int = 0, bytes_received: int = 0):
        """Aktualisiert Statistiken"""
        with self._lock:
            self.stats['packets_sent'] += packets_sent
            self.stats['packets_received'] += packets_received
            self.stats['bytes_sent'] += bytes_sent
            self.stats['bytes_received'] += bytes_received
            self.stats['last_activity'] = time.time()


class ConnectionManager(BaseModule):
    """
    Connection Manager v4.6.0

    Verwaltet beliebig viele parallele Verbindungen:
    - PLCs (mehrere AMS-Verbindungen)
    - MQTT Broker (lokal, extern, Home Assistant)
    - Bluetooth BMS (mehrere Geräte)
    - Modbus (mehrere Wechselrichter/Slaves)
    - RS485/CAN
    - Custom Connections

    Features:
    - Einheitliches Lifecycle-Management
    - Health-Monitoring mit Auto-Reconnect
    - Hot-Reload von Konfigurationen
    - Event-System für Status-Änderungen
    """

    NAME = "connection_manager"
    VERSION = "4.6.0"
    DESCRIPTION = "Multi-Connection Manager"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['data_gateway']

    # Health-Check Intervall
    HEALTH_CHECK_INTERVAL = 30.0  # Sekunden

    # Reconnect-Strategie
    RECONNECT_DELAY_BASE = 5.0     # Basis-Verzögerung in Sekunden
    RECONNECT_MAX_ATTEMPTS = 10    # Max Versuche
    RECONNECT_BACKOFF = 1.5        # Exponential Backoff Factor

    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()

        # Verbindungen: {connection_id: BaseConnection}
        self.connections = {}

        # Registered Connection Types: {type_name: Class}
        self.connection_types = {}

        # Health-Check Thread
        self.health_check_thread = None
        self.health_check_running = False

        # Event-Callbacks: {event_type: [callbacks]}
        self.event_callbacks = {
            'connected': [],
            'disconnected': [],
            'error': [],
            'health_check_failed': []
        }

        # Module-Referenzen
        self.data_gateway = None

    def initialize(self, app_context: Any):
        """Initialisiert Connection Manager"""
        super().initialize(app_context)

        # Hole DataGateway
        mm = app_context.module_manager
        self.data_gateway = mm.get_module('data_gateway')

        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")

        # Registriere eingebaute Connection-Typen
        self._register_builtin_types()

        # Lade Verbindungs-Konfiguration
        self._load_connections_config()

        # Starte Health-Check Thread
        self._start_health_check()

    def _register_builtin_types(self):
        """Registriert eingebaute Verbindungstypen"""
        # PLC Connection (TwinCAT/ADS)
        try:
            from modules.core.plc_connection import register_plc_connection
            register_plc_connection(self)
        except ImportError as e:
            print(f"  ⚠️  PLC-Connection nicht verfügbar: {e}")

        # Bluetooth Connection (BLE)
        try:
            from modules.bluetooth.bluetooth_manager import register_bluetooth_connection
            register_bluetooth_connection(self)
        except ImportError as e:
            print(f"  ⚠️  Bluetooth-Connection nicht verfügbar: {e}")

        # Weitere Typen werden in späteren Phasen hinzugefügt:
        # - MQTT (später)
        # - Modbus (später)

        print(f"  📋 Registrierte Connection-Typen: {list(self.connection_types.keys())}")

    def register_connection_type(self, type_name: str, connection_class: Type[BaseConnection]):
        """
        Registriert einen neuen Verbindungstyp

        Args:
            type_name: Name des Typs (z.B. "plc", "mqtt", "bluetooth")
            connection_class: Klasse die von BaseConnection erbt
        """
        if not issubclass(connection_class, BaseConnection):
            raise ValueError(f"Connection class must inherit from BaseConnection")

        self.connection_types[type_name] = connection_class
        print(f"  ✅ Connection-Typ registriert: {type_name} -> {connection_class.__name__}")

    def _load_connections_config(self):
        """Lädt connections.json Konfiguration"""
        config_file = os.path.join('config', 'connections.json')

        if not os.path.exists(config_file):
            print(f"  ℹ️  Keine connections.json gefunden - erstelle Standard-Konfiguration")
            self._create_default_connections_config(config_file)
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            connections_config = config.get('connections', {})
            print(f"  📡 Lade {len(connections_config)} Verbindungen...")

            for conn_id, conn_config in connections_config.items():
                if conn_config.get('enabled', True):
                    self._create_connection(conn_id, conn_config)

            print(f"  ✅ {len(self.connections)} Verbindungen geladen")

        except Exception as e:
            print(f"  ⚠️  Fehler beim Laden der connections.json: {e}")

    def _create_default_connections_config(self, filepath: str):
        """Erstellt Standard connections.json Template"""
        default_config = {
            "version": "1.0",
            "description": "Verbindungs-Konfiguration für SmartHome Edge OS v4.6.0",
            "connections": {
                "plc_001": {
                    "type": "plc",
                    "name": "PLC Keller",
                    "enabled": True,
                    "config": {
                        "ams_net_id": "192.168.2.162.1.1",
                        "ams_port": 801,
                        "ip_address": "192.168.2.162",
                        "timeout": 5000,
                        "auto_reconnect": True
                    }
                },
                "mqtt_local": {
                    "type": "mqtt",
                    "name": "MQTT Broker (Lokal)",
                    "enabled": False,
                    "config": {
                        "host": "localhost",
                        "port": 1883,
                        "username": null,
                        "password": null,
                        "client_id": "smarthome_edge_os"
                    }
                },
                "bt_bms_001": {
                    "type": "bluetooth",
                    "name": "Bluetooth BMS #1",
                    "enabled": False,
                    "config": {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "device_type": "jbd_bms",
                        "poll_interval": 5.0
                    }
                }
            },
            "settings": {
                "health_check_interval": self.HEALTH_CHECK_INTERVAL,
                "reconnect_enabled": True,
                "reconnect_max_attempts": self.RECONNECT_MAX_ATTEMPTS
            }
        }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Standard connections.json erstellt: {filepath}")

    def _create_connection(self, connection_id: str, config: Dict) -> Optional[BaseConnection]:
        """
        Erstellt eine Verbindung

        Args:
            connection_id: Eindeutige ID
            config: Verbindungs-Konfiguration

        Returns:
            BaseConnection Instanz oder None
        """
        conn_type = config.get('type')

        if conn_type not in self.connection_types:
            print(f"  ⚠️  Unbekannter Verbindungstyp: {conn_type} (für {connection_id})")
            print(f"     Verfügbare Typen: {list(self.connection_types.keys())}")
            return None

        try:
            # Erstelle Connection-Instanz
            connection_class = self.connection_types[conn_type]
            connection = connection_class(
                connection_id=connection_id,
                config=config.get('config', {}),
                app_context=self._app_context
            )

            # Registriere
            self.connections[connection_id] = connection

            # Auto-Connect wenn konfiguriert
            if config.get('config', {}).get('auto_reconnect', False):
                threading.Thread(
                    target=self._delayed_connect,
                    args=(connection,),
                    daemon=True
                ).start()

            return connection

        except Exception as e:
            print(f"  ✗ Fehler beim Erstellen der Verbindung {connection_id}: {e}")
            return None

    def _delayed_connect(self, connection: BaseConnection):
        """Verzögerter Connect (in eigenem Thread)"""
        time.sleep(1.0)  # Kurze Verzögerung für System-Init

        if connection.connect():
            print(f"  ✅ Auto-Connect erfolgreich: {connection.connection_id}")
            self._fire_event('connected', connection)
        else:
            print(f"  ⚠️  Auto-Connect fehlgeschlagen: {connection.connection_id}")
            self._fire_event('error', connection)

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def get_connection(self, connection_id: str) -> Optional[BaseConnection]:
        """
        Holt eine Verbindung

        Args:
            connection_id: Verbindungs-ID

        Returns:
            BaseConnection oder None
        """
        return self.connections.get(connection_id)

    def get_all_connections(self) -> Dict[str, BaseConnection]:
        """Liefert alle Verbindungen"""
        return self.connections.copy()

    def _save_connections_config(self):
        """Speichert aktuelle Connections in connections.json"""
        try:
            config_file = os.path.join('config', 'connections.json')

            # Lese existierende Config
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {
                    "version": "1.0",
                    "description": "Verbindungs-Konfiguration",
                    "connections": {},
                    "settings": {}
                }

            # Update connections
            connections_config = {}
            for conn_id, conn in self.connections.items():
                connections_config[conn_id] = {
                    'type': conn.connection_type if hasattr(conn, 'connection_type') else 'unknown',
                    'enabled': True,
                    **conn.config
                }

            config['connections'] = connections_config

            # Speichern
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"  ✅ Connections gespeichert: {config_file}")
            return True

        except Exception as e:
            print(f"  ✗ Fehler beim Speichern der Connections: {e}")
            return False

    def connect_all(self):
        """Verbindet alle Verbindungen"""
        for connection in self.connections.values():
            if not connection.is_connected():
                threading.Thread(
                    target=connection.connect,
                    daemon=True
                ).start()

    def disconnect_all(self):
        """Trennt alle Verbindungen"""
        for connection in self.connections.values():
            if connection.is_connected():
                connection.disconnect()

    def get_status_summary(self) -> Dict:
        """Liefert Status-Übersicht aller Verbindungen"""
        return {
            'total_connections': len(self.connections),
            'connected': sum(1 for c in self.connections.values() if c.is_connected()),
            'disconnected': sum(1 for c in self.connections.values() if not c.is_connected()),
            'connections': {
                conn_id: conn.get_status()
                for conn_id, conn in self.connections.items()
            }
        }

    def reload_config(self):
        """Lädt Konfiguration neu (Hot-Reload)"""
        print(f"  🔄 Hot-Reload: Lade connections.json neu...")

        # Speichere alte Verbindungen
        old_connections = set(self.connections.keys())

        # Lade neue Config
        self._load_connections_config()

        # Identifiziere Änderungen
        new_connections = set(self.connections.keys())

        added = new_connections - old_connections
        removed = old_connections - new_connections

        print(f"  ✅ Hot-Reload abgeschlossen:")
        print(f"     Hinzugefügt: {len(added)}")
        print(f"     Entfernt: {len(removed)}")
        print(f"     Aktuell: {len(self.connections)}")

    # ========================================================================
    # HEALTH-CHECK & RECONNECT
    # ========================================================================

    def _start_health_check(self):
        """Startet Health-Check Thread"""
        self.health_check_running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        print(f"  ✅ Health-Check Thread gestartet (Intervall: {self.HEALTH_CHECK_INTERVAL}s)")

    def _health_check_loop(self):
        """Health-Check Loop"""
        while self.health_check_running:
            try:
                for conn_id, connection in list(self.connections.items()):
                    if connection.is_connected():
                        # Health-Check durchführen
                        if not connection.health_check():
                            print(f"  ⚠️  Health-Check fehlgeschlagen: {conn_id}")
                            self._fire_event('health_check_failed', connection)

                            # Optional: Reconnect auslösen
                            if connection.config.get('auto_reconnect', False):
                                self._attempt_reconnect(connection)

                time.sleep(self.HEALTH_CHECK_INTERVAL)

            except Exception as e:
                print(f"  ✗ Fehler im Health-Check Loop: {e}")
                time.sleep(5.0)

    def _attempt_reconnect(self, connection: BaseConnection):
        """
        Versucht Verbindung wiederherzustellen

        Args:
            connection: Verbindung die neu verbunden werden soll
        """
        if connection.reconnect_attempts >= self.RECONNECT_MAX_ATTEMPTS:
            print(f"  ⚠️  Max Reconnect-Versuche erreicht für: {connection.connection_id}")
            connection.status = ConnectionStatus.SUSPENDED
            return

        # Exponential Backoff
        delay = self.RECONNECT_DELAY_BASE * (self.RECONNECT_BACKOFF ** connection.reconnect_attempts)

        print(f"  🔄 Reconnect-Versuch #{connection.reconnect_attempts + 1} für {connection.connection_id} in {delay:.1f}s...")

        time.sleep(delay)

        connection.reconnect_attempts += 1

        if connection.connect():
            print(f"  ✅ Reconnect erfolgreich: {connection.connection_id}")
            connection.reconnect_attempts = 0
            self._fire_event('connected', connection)
        else:
            print(f"  ✗ Reconnect fehlgeschlagen: {connection.connection_id}")
            # Nächster Versuch beim nächsten Health-Check

    # ========================================================================
    # EVENT-SYSTEM
    # ========================================================================

    def on_event(self, event_type: str, callback):
        """
        Registriert Callback für Events

        Args:
            event_type: 'connected', 'disconnected', 'error', 'health_check_failed'
            callback: Funktion callback(connection: BaseConnection)
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)

    def _fire_event(self, event_type: str, connection: BaseConnection):
        """Feuert Event"""
        for callback in self.event_callbacks.get(event_type, []):
            try:
                callback(connection)
            except Exception as e:
                print(f"  ⚠️  Event-Callback Fehler ({event_type}): {e}")

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    def shutdown(self):
        """Cleanup"""
        print(f"  🛑 {self.NAME} fährt herunter...")

        # Stoppe Health-Check
        self.health_check_running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=2.0)

        # Trenne alle Verbindungen
        self.disconnect_all()

        print(f"  ✅ {self.NAME} heruntergefahren")


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        ConnectionManager.NAME,
        ConnectionManager.VERSION,
        ConnectionManager.DESCRIPTION,
        ConnectionManager,
        author=ConnectionManager.AUTHOR,
        dependencies=ConnectionManager.DEPENDENCIES
    )
