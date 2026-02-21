"""
Bluetooth Manager v4.6.0
Multi-Instance Bluetooth-Verbindung für Connection Manager

📁 SPEICHERORT: modules/bluetooth/bluetooth_manager.py

Features v4.6.0:
- ⭐ Multi-Instance Support (mehrere BLE-Geräte parallel)
- ⭐ Integration mit Connection Manager
- ⭐ BaseConnection Interface
- BLE (Bluetooth Low Energy) mit bleak
- Auto-Reconnect via Connection Manager
- Health-Check
- Characteristic Read/Write/Notify
- RSSI-Monitoring
"""

import sys
import os

# Fix: Korrekte Import-Pfade
try:
    from modules.core.connection_manager import BaseConnection, ConnectionStatus
except ImportError:
    # Fallback für direkten Import
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
    from connection_manager import BaseConnection, ConnectionStatus
from typing import Any, Dict, Optional, Callable, List
import threading
import time
import asyncio

# bleak Import (optional)
try:
    import bleak
    from bleak import BleakClient, BleakScanner
    from bleak.backends.characteristic import BleakGATTCharacteristic
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("  ⚠️  bleak nicht verfügbar - Bluetooth-Verbindungen deaktiviert")


class BluetoothConnection(BaseConnection):
    """
    Bluetooth Connection v4.6.0

    Implementiert BaseConnection für BLE-Verbindungen.
    Unterstützt mehrere parallele BLE-Geräte über Connection Manager.

    Features:
    - Multi-Instance (mehrere BLE-Geräte)
    - Characteristic Read/Write/Notify
    - Auto-Scan & Discovery
    - RSSI-Monitoring
    - Health-Check via Connectivity
    - Statistik-Tracking
    """

    def __init__(self, connection_id: str, config: Dict, app_context: Any):
        """
        Args:
            connection_id: Eindeutige ID (z.B. "bt_bms_001", "bt_scale")
            config: {
                'address': str,             # BLE MAC-Adresse (z.B. "AA:BB:CC:DD:EE:FF")
                'name': str,                # Gerätename (optional, für Discovery)
                'timeout': float,           # Connection-Timeout in Sekunden
                'auto_reconnect': bool,     # Auto-Reconnect aktivieren
                'scan_timeout': float,      # Scan-Timeout bei Discovery
                'notify_characteristics': List[str]  # UUIDs für Auto-Notify
            }
            app_context: Application Context
        """
        super().__init__(connection_id, config, app_context)

        if not BLEAK_AVAILABLE:
            raise ImportError("bleak nicht installiert! pip install bleak")

        # BLE Config
        self.address = config.get('address')  # MAC-Adresse
        self.device_name = config.get('name')  # Gerätename
        self.timeout = config.get('timeout', 10.0)
        self.scan_timeout = config.get('scan_timeout', 5.0)
        self.notify_characteristics = config.get('notify_characteristics', [])

        # BLE Client
        self.client: Optional[BleakClient] = None

        # Event Loop für async
        self.loop = None
        self.loop_thread = None

        # Notify Callbacks
        self.notify_callbacks = {}  # characteristic_uuid -> callback

        # RSSI & Device Info
        self.rssi = None
        self.device_info = {}

        # Thread-Safe Lock
        self.ble_lock = threading.RLock()

    def connect(self) -> bool:
        """
        Stellt BLE-Verbindung her

        Returns:
            True wenn erfolgreich
        """
        if not self.address and not self.device_name:
            print(f"  ✗ [{self.connection_id}] Keine Adresse oder Name konfiguriert!")
            self.status = ConnectionStatus.ERROR
            self.last_error = "Address/Name fehlt"
            return False

        try:
            print(f"  📡 [{self.connection_id}] Verbinde zu BLE-Gerät...")

            self.status = ConnectionStatus.CONNECTING

            # Discovery falls nur Name vorhanden
            if not self.address and self.device_name:
                print(f"     Suche nach '{self.device_name}'...")
                self.address = self._discover_device_by_name(self.device_name)

                if not self.address:
                    raise Exception(f"Gerät '{self.device_name}' nicht gefunden")

            # Starte Event-Loop Thread
            self._start_event_loop()

            # Verbinde (async)
            connected = self._connect_sync()

            if connected:
                # Erfolgreich
                self.status = ConnectionStatus.CONNECTED
                self.connected_at = time.time()
                self.reconnect_attempts = 0
                self.last_error = None

                print(f"  ✅ [{self.connection_id}] Verbunden mit {self.address}")

                # Lese Device-Info
                self._read_device_info()

                # Setup Notifications
                self._setup_notifications()

                # Route Status an DataGateway
                self._publish_status("connected")

                return True
            else:
                raise Exception("Connection fehlgeschlagen")

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.last_error = str(e)
            self.stats['errors'] += 1

            print(f"  ✗ [{self.connection_id}] Verbindungsfehler: {e}")
            self._publish_status("error")

            return False

    def disconnect(self) -> bool:
        """
        Trennt BLE-Verbindung

        Returns:
            True wenn erfolgreich
        """
        try:
            if self.client:
                # Disconnect (async)
                self._disconnect_sync()
                self.client = None

            # Stoppe Event-Loop
            self._stop_event_loop()

            self.status = ConnectionStatus.DISCONNECTED
            self.connected_at = None

            print(f"  📡 [{self.connection_id}] Getrennt von {self.address}")

            # Route Status an DataGateway
            self._publish_status("disconnected")

            return True

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Fehler beim Trennen: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Prüft ob Verbindung aktiv ist

        Returns:
            True wenn verbunden
        """
        if self.status != ConnectionStatus.CONNECTED:
            return False

        if not self.client:
            return False

        # Prüfe BLE-Connection Status
        try:
            return self.client.is_connected
        except:
            return False

    def health_check(self) -> bool:
        """
        Führt Health-Check durch

        Returns:
            True wenn gesund
        """
        if not self.is_connected():
            return False

        try:
            # Methode 1: Prüfe Connection-Status
            if not self.client.is_connected:
                return False

            # Methode 2: Lese RSSI (optional)
            # rssi = self._read_rssi()
            # return rssi is not None

            return True

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Health-Check Fehler: {e}")
            return False

    # ========================================================================
    # BLE READ/WRITE METHODS
    # ========================================================================

    def read_characteristic(self, characteristic_uuid: str) -> Optional[bytes]:
        """
        Liest BLE-Characteristic

        Args:
            characteristic_uuid: UUID des Characteristics

        Returns:
            Bytes oder None bei Fehler
        """
        if not self.is_connected():
            return None

        try:
            data = self._read_characteristic_sync(characteristic_uuid)

            # Statistik
            if data:
                self.update_stats(packets_received=1, bytes_received=len(data))

            return data

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Read-Fehler ({characteristic_uuid}): {e}")
            self.stats['errors'] += 1
            return None

    def write_characteristic(self, characteristic_uuid: str, data: bytes, response: bool = True) -> bool:
        """
        Schreibt BLE-Characteristic

        Args:
            characteristic_uuid: UUID des Characteristics
            data: Daten als bytes
            response: Mit Response? (True = write_with_response, False = write_without_response)

        Returns:
            True wenn erfolgreich
        """
        if not self.is_connected():
            return False

        try:
            self._write_characteristic_sync(characteristic_uuid, data, response)

            # Statistik
            self.update_stats(packets_sent=1, bytes_sent=len(data))

            return True

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Write-Fehler ({characteristic_uuid}): {e}")
            self.stats['errors'] += 1
            return False

    def start_notify(self, characteristic_uuid: str, callback: Callable[[bytes], None]) -> bool:
        """
        Startet Notifications für Characteristic

        Args:
            characteristic_uuid: UUID des Characteristics
            callback: Callback-Funktion (wird bei jedem Notify aufgerufen)

        Returns:
            True wenn erfolgreich
        """
        if not self.is_connected():
            return False

        try:
            # Speichere Callback
            self.notify_callbacks[characteristic_uuid] = callback

            # Starte Notify (async)
            self._start_notify_sync(characteristic_uuid, self._notify_handler)

            print(f"  📡 [{self.connection_id}] Notifications gestartet: {characteristic_uuid}")
            return True

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Start-Notify Fehler: {e}")
            return False

    def stop_notify(self, characteristic_uuid: str) -> bool:
        """
        Stoppt Notifications

        Args:
            characteristic_uuid: UUID des Characteristics

        Returns:
            True wenn erfolgreich
        """
        if not self.is_connected():
            return False

        try:
            # Stoppe Notify (async)
            self._stop_notify_sync(characteristic_uuid)

            # Entferne Callback
            if characteristic_uuid in self.notify_callbacks:
                del self.notify_callbacks[characteristic_uuid]

            print(f"  📡 [{self.connection_id}] Notifications gestoppt: {characteristic_uuid}")
            return True

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Stop-Notify Fehler: {e}")
            return False

    # ========================================================================
    # ASYNC HELPERS (sync wrappers)
    # ========================================================================

    def _connect_sync(self) -> bool:
        """Synchroner Wrapper für async connect"""
        future = asyncio.run_coroutine_threadsafe(
            self._connect_async(),
            self.loop
        )
        return future.result(timeout=self.timeout)

    def _disconnect_sync(self):
        """Synchroner Wrapper für async disconnect"""
        future = asyncio.run_coroutine_threadsafe(
            self._disconnect_async(),
            self.loop
        )
        future.result(timeout=5.0)

    def _read_characteristic_sync(self, uuid: str) -> bytes:
        """Synchroner Wrapper für async read"""
        future = asyncio.run_coroutine_threadsafe(
            self.client.read_gatt_char(uuid),
            self.loop
        )
        return future.result(timeout=self.timeout)

    def _write_characteristic_sync(self, uuid: str, data: bytes, response: bool):
        """Synchroner Wrapper für async write"""
        future = asyncio.run_coroutine_threadsafe(
            self.client.write_gatt_char(uuid, data, response),
            self.loop
        )
        future.result(timeout=self.timeout)

    def _start_notify_sync(self, uuid: str, callback: Callable):
        """Synchroner Wrapper für async start_notify"""
        future = asyncio.run_coroutine_threadsafe(
            self.client.start_notify(uuid, callback),
            self.loop
        )
        future.result(timeout=self.timeout)

    def _stop_notify_sync(self, uuid: str):
        """Synchroner Wrapper für async stop_notify"""
        future = asyncio.run_coroutine_threadsafe(
            self.client.stop_notify(uuid),
            self.loop
        )
        future.result(timeout=self.timeout)

    # ========================================================================
    # ASYNC OPERATIONS
    # ========================================================================

    async def _connect_async(self) -> bool:
        """Async BLE Connect"""
        self.client = BleakClient(self.address, timeout=self.timeout)
        await self.client.connect()
        return self.client.is_connected

    async def _disconnect_async(self):
        """Async BLE Disconnect"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    # ========================================================================
    # DISCOVERY
    # ========================================================================

    def _discover_device_by_name(self, name: str) -> Optional[str]:
        """
        Sucht BLE-Gerät nach Name

        Args:
            name: Gerätename

        Returns:
            MAC-Adresse oder None
        """
        try:
            print(f"     Scanne BLE-Geräte (Timeout: {self.scan_timeout}s)...")

            # Scan (async)
            devices = asyncio.run(BleakScanner.discover(timeout=self.scan_timeout))

            for device in devices:
                if device.name and name.lower() in device.name.lower():
                    print(f"     ✅ Gefunden: {device.name} ({device.address})")
                    return device.address

            return None

        except Exception as e:
            print(f"     ✗ Scan-Fehler: {e}")
            return None

    # ========================================================================
    # DEVICE INFO
    # ========================================================================

    def _read_device_info(self):
        """Liest Device-Informationen (optional)"""
        try:
            # Standard BLE Device Info Service: 0x180A
            # - Model Number: 0x2A24
            # - Serial Number: 0x2A25
            # - Firmware Version: 0x2A26
            # - Hardware Version: 0x2A27
            # - Manufacturer: 0x2A29

            device_info = {}

            # Versuche Standard-Characteristics zu lesen
            try:
                manufacturer = self.read_characteristic("00002a29-0000-1000-8000-00805f9b34fb")
                if manufacturer:
                    device_info['manufacturer'] = manufacturer.decode('utf-8', errors='ignore')
            except:
                pass

            try:
                model = self.read_characteristic("00002a24-0000-1000-8000-00805f9b34fb")
                if model:
                    device_info['model'] = model.decode('utf-8', errors='ignore')
            except:
                pass

            try:
                firmware = self.read_characteristic("00002a26-0000-1000-8000-00805f9b34fb")
                if firmware:
                    device_info['firmware'] = firmware.decode('utf-8', errors='ignore')
            except:
                pass

            self.device_info = device_info

            if device_info:
                print(f"     Device-Info: {device_info}")

        except Exception as e:
            # Device Info Service nicht verfügbar
            pass

    def _setup_notifications(self):
        """Richtet konfigurierte Notifications ein"""
        if not self.notify_characteristics:
            return

        for char_uuid in self.notify_characteristics:
            try:
                # Default-Callback: Route zu DataGateway
                callback = lambda data, uuid=char_uuid: self._default_notify_callback(uuid, data)
                self.start_notify(char_uuid, callback)
            except Exception as e:
                print(f"  ⚠️  Notify-Setup Fehler ({char_uuid}): {e}")

    def _notify_handler(self, characteristic: BleakGATTCharacteristic, data: bytes):
        """
        Notify-Handler (wird von bleak aufgerufen)

        Args:
            characteristic: Characteristic-Objekt
            data: Empfangene Daten
        """
        uuid = characteristic.uuid

        # Statistik
        self.update_stats(packets_received=1, bytes_received=len(data))

        # Rufe registrierten Callback auf
        if uuid in self.notify_callbacks:
            try:
                self.notify_callbacks[uuid](data)
            except Exception as e:
                print(f"  ⚠️  Notify-Callback Fehler: {e}")

    def _default_notify_callback(self, uuid: str, data: bytes):
        """Standard-Callback: Route Daten zu DataGateway"""
        # Route zu DataGateway
        self._route_to_gateway(uuid, data)

    # ========================================================================
    # EVENT LOOP
    # ========================================================================

    def _start_event_loop(self):
        """Startet Event-Loop Thread für async operations"""
        if self.loop_thread and self.loop_thread.is_alive():
            return  # Already running

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

        # Warte bis Loop bereit ist
        time.sleep(0.1)

    def _stop_event_loop(self):
        """Stoppt Event-Loop Thread"""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop = None

        if self.loop_thread:
            self.loop_thread.join(timeout=2.0)
            self.loop_thread = None

    # ========================================================================
    # HELPERS
    # ========================================================================

    def get_services(self) -> List[Any]:
        """
        Liefert alle verfügbaren BLE-Services

        Returns:
            Liste von Services
        """
        if not self.is_connected():
            return []

        try:
            return list(self.client.services)
        except:
            return []

    def get_characteristics(self) -> List[str]:
        """
        Liefert alle verfügbaren Characteristics (UUIDs)

        Returns:
            Liste von UUIDs
        """
        if not self.is_connected():
            return []

        try:
            chars = []
            for service in self.client.services:
                for char in service.characteristics:
                    chars.append(char.uuid)
            return chars
        except:
            return []

    def _route_to_gateway(self, tag: str, value: Any):
        """Routet Wert an DataGateway"""
        # Hole DataGateway
        if hasattr(self.app_context, 'module_manager'):
            data_gateway = self.app_context.module_manager.get_module('data_gateway')

            if data_gateway:
                # Route mit connection_id als source
                data_gateway.route_data(
                    source_id=self.connection_id,
                    tag=tag,
                    value=value
                )

    def _publish_status(self, status: str):
        """Publiziert Status-Änderung"""
        if hasattr(self.app_context, 'module_manager'):
            data_gateway = self.app_context.module_manager.get_module('data_gateway')

            if data_gateway:
                data_gateway.route_data(
                    source_id=self.connection_id,
                    tag="_status",
                    value=status
                )


# ========================================================================
# REGISTRATION
# ========================================================================

def register_bluetooth_connection(connection_manager):
    """
    Registriert BluetoothConnection im Connection Manager

    Usage:
        conn_mgr = app_context.module_manager.get_module('connection_manager')
        register_bluetooth_connection(conn_mgr)
    """
    if not BLEAK_AVAILABLE:
        print("  ⚠️  BluetoothConnection nicht registriert: bleak fehlt")
        return

    connection_manager.register_connection_type(
        'bluetooth',
        BluetoothConnection
    )

    print("  ✅ BluetoothConnection registriert als 'bluetooth'")
