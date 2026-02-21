"""
PLC Connection Module v4.6.0
Multi-Instance PLC-Verbindung für Connection Manager

📁 SPEICHERORT: modules/core/plc_connection.py

Features v4.6.0:
- ⭐ Multi-Instance Support (mehrere PLCs parallel)
- ⭐ Integration mit Connection Manager
- ⭐ BaseConnection Interface
- ADS (TwinCAT) Support
- Auto-Reconnect via Connection Manager
- Health-Check
- Read/Write mit Caching
"""

import sys
import os

# Fix: Korrekte Import-Pfade
try:
    from modules.core.connection_manager import BaseConnection, ConnectionStatus
except ImportError:
    # Fallback für direkten Import
    sys.path.append(os.path.dirname(__file__))
    from connection_manager import BaseConnection, ConnectionStatus
from typing import Any, Dict, Optional
import threading
import time

# PyADS Import (optional)
try:
    import pyads
    PYADS_AVAILABLE = True
except ImportError:
    PYADS_AVAILABLE = False
    print("  ⚠️  pyads nicht verfügbar - PLC-Verbindungen deaktiviert")


class PLCConnection(BaseConnection):
    """
    PLC Connection v4.6.0

    Implementiert BaseConnection für TwinCAT/ADS-Verbindungen.
    Unterstützt mehrere parallele PLC-Verbindungen über Connection Manager.

    Features:
    - Multi-Instance (mehrere PLCs)
    - Read/Write mit Type-Auto-Detection
    - Symbol-Caching
    - Health-Check via Test-Read
    - Statistik-Tracking
    """

    def __init__(self, connection_id: str, config: Dict, app_context: Any):
        """
        Args:
            connection_id: Eindeutige ID (z.B. "plc_001", "plc_garage")
            config: {
                'ams_net_id': str,      # z.B. "192.168.2.162.1.1"
                'ams_port': int,        # z.B. 801
                'ip_address': str,      # z.B. "192.168.2.162"
                'timeout': int,         # Millisekunden
                'auto_reconnect': bool
            }
            app_context: Application Context
        """
        super().__init__(connection_id, config, app_context)

        if not PYADS_AVAILABLE:
            raise ImportError("pyads nicht installiert! pip install pyads")

        # PLC Config
        self.ams_net_id = config.get('ams_net_id')
        self.ams_port = config.get('ams_port', pyads.PORT_TC2PLC1)
        self.ip_address = config.get('ip_address')
        self.timeout = config.get('timeout', 5000)

        # ADS Connection
        self.plc = None

        # Read-Cache
        self.cache = {}
        self.cache_timeout = 0.1  # 100ms
        self.cache_max_entries = max(100, int(os.getenv('SMARTHOME_PLC_CONNECTION_CACHE_MAX_ENTRIES', '5000')))
        self.cache_lock = threading.RLock()
        self.stats['cache_evictions'] = 0

        # Health-Check Variable (optional)
        self.health_check_variable = config.get('health_check_variable', None)

    def connect(self) -> bool:
        """
        Stellt ADS-Verbindung her

        Returns:
            True wenn erfolgreich
        """
        if not self.ams_net_id:
            print(f"  ✗ [{self.connection_id}] Keine AMS NetID konfiguriert!")
            self.status = ConnectionStatus.ERROR
            self.last_error = "AMS NetID fehlt"
            return False

        try:
            print(f"  🔌 [{self.connection_id}] Verbinde zu {self.ams_net_id}:{self.ams_port}...")

            self.status = ConnectionStatus.CONNECTING

            # Schließe alte Verbindung
            if self.plc:
                try:
                    self.plc.close()
                except:
                    pass

            # Erstelle neue Verbindung
            self.plc = pyads.Connection(
                self.ams_net_id,
                self.ams_port
            )

            # Öffne Verbindung
            self.plc.open()

            # Test-Read um Verbindung zu verifizieren
            try:
                state = self.plc.read_state()
                print(f"     PLC-State: {state}")
            except:
                pass

            # Erfolgreich
            self.status = ConnectionStatus.CONNECTED
            self.connected_at = time.time()
            self.reconnect_attempts = 0
            self.last_error = None

            # Cache leeren
            with self.cache_lock:
                self.cache.clear()

            print(f"  ✅ [{self.connection_id}] Verbunden mit {self.ams_net_id}")

            # Route Status an DataGateway
            self._publish_status("connected")

            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.last_error = str(e)
            self.stats['errors'] += 1

            print(f"  ✗ [{self.connection_id}] Verbindungsfehler: {e}")
            self._publish_status("error")

            return False

    def disconnect(self) -> bool:
        """
        Trennt ADS-Verbindung

        Returns:
            True wenn erfolgreich
        """
        try:
            if self.plc:
                self.plc.close()
                self.plc = None

            self.status = ConnectionStatus.DISCONNECTED
            self.connected_at = None

            # Cache leeren
            with self.cache_lock:
                self.cache.clear()

            print(f"  🔌 [{self.connection_id}] Getrennt von {self.ams_net_id}")

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

        if not self.plc:
            return False

        # Optional: Prüfe ADS-State
        try:
            state = self.plc.read_state()
            return state is not None
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
            # Methode 1: Nutze konfigurierte Health-Check Variable
            if self.health_check_variable:
                try:
                    self.read_by_name(self.health_check_variable)
                    return True
                except:
                    return False

            # Methode 2: Lese PLC-State
            state = self.plc.read_state()
            return state is not None

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Health-Check Fehler: {e}")
            return False

    # ========================================================================
    # PLC READ/WRITE METHODS
    # ========================================================================

    def read_by_name(self, symbol: str, plc_type: int = None, use_cache: bool = True) -> Any:
        """
        Liest PLC-Variable nach Name

        Args:
            symbol: PLC-Symbol (z.B. "MAIN.temperature")
            plc_type: pyads.PLCTYPE_* (optional, wird auto-detected)
            use_cache: Cache nutzen?

        Returns:
            Wert oder None bei Fehler
        """
        if not self.is_connected():
            return None

        # Cache-Check
        if use_cache:
            cached = self._get_from_cache(symbol)
            if cached is not None:
                return cached

        try:
            # Auto-detect Type wenn nicht angegeben
            if plc_type is None:
                # Nutze read_by_name ohne Type (pyads auto-detect)
                value = self.plc.read_by_name(symbol)
            else:
                value = self.plc.read_by_name(symbol, plc_type)

            # Statistik
            self.update_stats(packets_received=1, bytes_received=8)  # Geschätzt

            # Cache
            if use_cache:
                self._put_to_cache(symbol, value)

            # Route zu DataGateway
            self._route_to_gateway(symbol, value)

            return value

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Read-Fehler ({symbol}): {e}")
            self.stats['errors'] += 1
            return None

    def write_by_name(self, symbol: str, value: Any, plc_type: int = None) -> bool:
        """
        Schreibt PLC-Variable

        Args:
            symbol: PLC-Symbol
            value: Wert
            plc_type: pyads.PLCTYPE_* (optional)

        Returns:
            True wenn erfolgreich
        """
        if not self.is_connected():
            return False

        try:
            # Auto-detect Type
            if plc_type is None:
                plc_type = self._detect_plc_type(value)

            self.plc.write_by_name(symbol, value, plc_type)

            # Statistik
            self.update_stats(packets_sent=1, bytes_sent=8)  # Geschätzt

            # Cache invalidieren
            with self.cache_lock:
                if symbol in self.cache:
                    del self.cache[symbol]

            # Route zu DataGateway
            self._route_to_gateway(symbol, value)

            return True

        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Write-Fehler ({symbol}): {e}")
            self.stats['errors'] += 1
            return False

    def read_state(self) -> Optional[tuple]:
        """
        Liest PLC-State (ADS State + Device State)

        Returns:
            (ads_state, device_state) oder None
        """
        if not self.is_connected():
            return None

        try:
            state = self.plc.read_state()
            return state
        except:
            return None

    def read_device_info(self) -> Optional[Any]:
        """
        Liest Device-Info.
        In pyads 3.5.0 liefert client.read_device_info() ein Tuple zurück:
        (String 'DeviceName', AdsVersion-Objekt)
        """
        if not self.is_connected():
            return None

        try:
            # Wir entfernen die Abhängigkeit von pyads.structs.AdsDeviceInfo
            # da diese Struktur intern anders gehandhabt wird.
            name, version = self.plc.read_device_info()

            # version ist hier ein Objekt der Klasse AdsVersion (siehe oben in deinem Snippet)
            print(f"  ℹ️  PLC Name: {name}, Version: {version.version}.{version.revision}.{version.build}")

            return {"name": name, "version": f"{version.version}.{version.revision}.{version.build}"}
        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Device-Info konnte nicht gelesen werden: {e}")
            return None

    # ========================================================================
    # CACHE
    # ========================================================================

    def _get_from_cache(self, symbol: str) -> Optional[Any]:
        """Holt Wert aus Cache"""
        with self.cache_lock:
            if symbol in self.cache:
                value, timestamp = self.cache[symbol]
                age = time.time() - timestamp

                if age < self.cache_timeout:
                    return value
                else:
                    # Cache abgelaufen
                    del self.cache[symbol]

            return None

    def _put_to_cache(self, symbol: str, value: Any):
        """Speichert Wert im Cache"""
        with self.cache_lock:
            if symbol not in self.cache and len(self.cache) >= self.cache_max_entries:
                oldest_key = next(iter(self.cache), None)
                if oldest_key is not None:
                    del self.cache[oldest_key]
                    self.stats['cache_evictions'] = self.stats.get('cache_evictions', 0) + 1
            self.cache[symbol] = (value, time.time())

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _detect_plc_type(self, value: Any) -> int:
        """Auto-detect PLC-Type basierend auf Python-Type"""
        if isinstance(value, bool):
            return pyads.PLCTYPE_BOOL
        elif isinstance(value, int):
            return pyads.PLCTYPE_DINT
        elif isinstance(value, float):
            return pyads.PLCTYPE_REAL
        elif isinstance(value, str):
            return pyads.PLCTYPE_STRING
        else:
            return pyads.PLCTYPE_BYTE

    def _route_to_gateway(self, symbol: str, value: Any):
        """Routet Wert an DataGateway"""
        # Hole DataGateway
        if hasattr(self.app_context, 'module_manager'):
            data_gateway = self.app_context.module_manager.get_module('data_gateway')

            if data_gateway:
                # Route mit connection_id als source
                tag = f"{symbol}"  # z.B. "MAIN.temperature"
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
    # SYMBOL INFO
    # ========================================================================

    def get_all_symbols(self) -> list:
        """
        Liefert alle verfügbaren PLC-Symbole

        Returns:
            Liste von Symbolen
        """
        if not self.is_connected():
            return []

        try:
            symbols = self.plc.get_all_symbols()
            return symbols
        except Exception as e:
            print(f"  ⚠️  [{self.connection_id}] Fehler beim Lesen der Symbole: {e}")
            return []


# ========================================================================
# REGISTRATION
# ========================================================================

def register_plc_connection(connection_manager):
    """
    Registriert PLCConnection im Connection Manager

    Usage:
        conn_mgr = app_context.module_manager.get_module('connection_manager')
        register_plc_connection(conn_mgr)
    """
    if not PYADS_AVAILABLE:
        print("  ⚠️  PLCConnection nicht registriert: pyads fehlt")
        return

    connection_manager.register_connection_type(
        'plc',
        PLCConnection
    )

    print("  ✅ PLCConnection registriert als 'plc'")
