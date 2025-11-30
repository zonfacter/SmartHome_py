"""
PLC Communication Module
Version: 1.0.0
Verwaltet ADS-Verbindung zum TwinCAT PLC
"""

from module_manager import BaseModule
from typing import Optional, Any
import pyads
import threading
import time


class PLCCommunication(BaseModule):
    """
    PLC-Kommunikations-Modul
    
    Funktionen:
    - Verbindungsaufbau/-verwaltung
    - Lesen/Schreiben von Variablen
    - Auto-Reconnect
    - Caching
    """
    
    NAME = "plc_communication"
    VERSION = "1.0.0"
    DESCRIPTION = "TwinCAT ADS Kommunikation"
    AUTHOR = "TwinCAT Team"
    
    def __init__(self):
        super().__init__()
        self.plc = None
        self.connected = False
        self.config = {
            'ams_net_id': '192.168.2.162.1.1',
            'port': pyads.PORT_TC2PLC1,
            'timeout': 5000,
            'auto_reconnect': True
        }
        self.cache = {}
        self.cache_timeout = 0.1  # 100ms Cache
        self.consecutive_errors = 0
        self.max_errors = 5
        
    def initialize(self, app_context: Any):
        """Initialisiert PLC-Verbindung"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def configure(self, ams_net_id: str, port: int = None, timeout: int = 5000):
        """Konfiguriert PLC-Verbindung"""
        self.config['ams_net_id'] = ams_net_id
        if port:
            self.config['port'] = port
        self.config['timeout'] = timeout
    
    def connect(self) -> bool:
        """Stellt Verbindung zum PLC her"""
        try:
            if self.plc:
                self.plc.close()
            
            self.plc = pyads.Connection(
                self.config['ams_net_id'],
                self.config['port']
            )
            
            self.plc.open()
            self.connected = True
            self.consecutive_errors = 0
            
            print(f"  ✓ PLC verbunden: {self.config['ams_net_id']}")
            return True
            
        except Exception as e:
            print(f"  ✗ PLC-Verbindung fehlgeschlagen: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Trennt PLC-Verbindung"""
        if self.plc:
            try:
                self.plc.close()
                self.connected = False
                print("  ✓ PLC getrennt")
            except:
                pass
    
    def reconnect(self) -> bool:
        """Versucht Reconnect"""
        print("  🔄 Versuche PLC-Reconnect...")
        self.disconnect()
        time.sleep(1)
        return self.connect()
    
    def read_by_name(self, variable: str, plc_type: int, use_cache: bool = True) -> Optional[Any]:
        """
        Liest Variable vom PLC
        
        Args:
            variable: Variablen-Name (z.B. 'MAIN.bLight1')
            plc_type: pyads.PLCTYPE_*
            use_cache: Cache verwenden?
        
        Returns:
            Wert oder None bei Fehler
        """
        if not self.connected:
            return None
        
        # Cache-Check
        if use_cache and variable in self.cache:
            cached_value, cached_time = self.cache[variable]
            if time.time() - cached_time < self.cache_timeout:
                return cached_value
        
        try:
            value = self.plc.read_by_name(variable, plc_type)
            
            # Cache speichern
            self.cache[variable] = (value, time.time())
            
            # Reset Fehler-Counter
            self.consecutive_errors = 0
            
            return value
            
        except Exception as e:
            self.consecutive_errors += 1
            
            if self.consecutive_errors >= self.max_errors:
                if self.config['auto_reconnect']:
                    threading.Thread(target=self.reconnect, daemon=True).start()
            
            return None
    
    def write_by_name(self, variable: str, value: Any, plc_type: int) -> bool:
        """
        Schreibt Variable zum PLC
        
        Args:
            variable: Variablen-Name
            value: Zu schreibender Wert
            plc_type: pyads.PLCTYPE_*
        
        Returns:
            True bei Erfolg
        """
        if not self.connected:
            return False
        
        try:
            self.plc.write_by_name(variable, value, plc_type)
            
            # Cache invalidieren
            if variable in self.cache:
                del self.cache[variable]
            
            self.consecutive_errors = 0
            return True
            
        except Exception as e:
            self.consecutive_errors += 1
            return False
    
    def toggle_bool(self, variable: str) -> bool:
        """Toggle Bool-Variable (SCHNELL - ohne Cache)"""
        # WICHTIG: use_cache=False für schnelles Toggle!
        current = self.read_by_name(variable, pyads.PLCTYPE_BOOL, use_cache=False)
        
        if current is not None:
            new_value = not current
            success = self.write_by_name(variable, new_value, pyads.PLCTYPE_BOOL)
            return success
        else:
            return False
    
    def pulse(self, variable: str, duration_ms: int = 200) -> bool:
        """Sendet Impuls (kurz HIGH dann LOW)"""
        if not self.write_by_name(variable, True, pyads.PLCTYPE_BOOL):
            return False
        
        def reset_pulse():
            time.sleep(duration_ms / 1000.0)
            self.write_by_name(variable, False, pyads.PLCTYPE_BOOL)
        
        threading.Thread(target=reset_pulse, daemon=True).start()
        return True
    
    def get_connection_status(self) -> dict:
        """Gibt Verbindungs-Status zurück"""
        return {
            'connected': self.connected,
            'ams_net_id': self.config['ams_net_id'],
            'consecutive_errors': self.consecutive_errors,
            'cached_variables': len(self.cache)
        }
    
    def clear_cache(self):
        """Leert Cache"""
        self.cache.clear()
    
    def shutdown(self):
        """Beendet Verbindung"""
        self.disconnect()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        PLCCommunication.NAME,
        PLCCommunication.VERSION,
        PLCCommunication.DESCRIPTION,
        PLCCommunication,
        author=PLCCommunication.AUTHOR
    )
