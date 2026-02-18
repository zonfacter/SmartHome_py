"""
PLC Communication Module
Version: 1.1.0
Verwaltet ADS-Verbindung zum TwinCAT PLC

🆕 v1.1.0:
- max_errors erhöht (5 → 20)
- Reconnect-Cooldown (30s)
- Besseres Error-Handling
- Verhindert Reconnect-Spam!
"""

from module_manager import BaseModule
from typing import Optional, Any
import pyads
import threading
import time


class PLCCommunication(BaseModule):
    """
    PLC-Kommunikations-Modul v1.1.0
    
    ⭐ NEU: Anti-Reconnect-Spam!
    - max_errors: 5 → 20
    - Reconnect-Cooldown: 30s
    - Besseres Logging
    
    Funktionen:
    - Verbindungsaufbau/-verwaltung
    - Lesen/Schreiben von Variablen
    - Smart Auto-Reconnect
    - Caching
    """
    
    NAME = "plc_communication"
    VERSION = "1.1.0"
    DESCRIPTION = "TwinCAT ADS Kommunikation"
    AUTHOR = "TwinCAT Team"
    
    def __init__(self):
        super().__init__()
        self.plc = None
        self.connected = False
        self.config = {
            'ams_net_id': None,  # KEIN DEFAULT! Muss explizit konfiguriert werden
            'port': pyads.PORT_TC2PLC1,
            'timeout': 5000,
            'auto_reconnect': True
        }
        self.cache = {}
        self.cache_timeout = 0.1  # 100ms Cache
        
        # ⭐ v1.1.0: Verbessertes Error-Handling
        self.consecutive_errors = 0
        self.max_errors = 20  # ERHÖHT von 5!
        self.last_reconnect = 0  # Letzter Reconnect-Timestamp
        self.reconnect_cooldown = 30  # 30s zwischen Reconnects
        
        # Statistik
        self.total_reads = 0
        self.total_writes = 0
        self.total_errors = 0
        
    def initialize(self, app_context: Any):
        """Initialisiert PLC-Verbindung"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
        print(f"     Max Errors: {self.max_errors}, Reconnect-Cooldown: {self.reconnect_cooldown}s")

        # AUTO-CONNECT: Verbinde automatisch wenn AMS NetID konfiguriert ist
        config_mgr = app_context.module_manager.get_module('config_manager')
        if config_mgr:
            saved_ams_id = config_mgr.get_config_value('plc_ams_net_id')
            saved_port = config_mgr.get_config_value('plc_ams_port', pyads.PORT_TC2PLC1)
            saved_ip = config_mgr.get_config_value('plc_ip_address')

            if saved_ams_id:
                print(f"  🔄 Auto-Connect: Konfigurierte PLC gefunden")
                print(f"     AMS NetID: {saved_ams_id}")
                self.configure(saved_ams_id, port=saved_port)
                if self.connect():
                    print(f"  ✅ Auto-Connect erfolgreich!")
                else:
                    print(f"  ⚠️  Auto-Connect fehlgeschlagen (wird später retry)")
    
    def configure(self, ams_net_id: str, port: int = None, timeout: int = 5000):
        """Konfiguriert PLC-Verbindung"""
        self.config['ams_net_id'] = ams_net_id
        if port:
            self.config['port'] = port
        self.config['timeout'] = timeout
    
    def connect(self) -> bool:
        """Stellt Verbindung zum PLC her"""
        # ⭐ Validate AMS NetID ist konfiguriert
        if not self.config['ams_net_id']:
            print(f"  ✗ PLC-Verbindung fehlgeschlagen: Keine AMS NetID konfiguriert!")
            print(f"     Bitte zuerst configure() aufrufen oder über Web-UI konfigurieren")
            self.connected = False
            return False

        try:
            if self.plc:
                self.plc.close()

            self.plc = pyads.Connection(
                self.config['ams_net_id'],
                int(self.config['port'])
            )
            self.plc.open()
            self.connected = True
            self.consecutive_errors = 0

            print(f"  ✓ PLC verbunden: {self.config['ams_net_id']} (Port {self.config['port']})")
            return True
        except Exception as e:
            print(f"  ✗ PLC-Verbindung fehlgeschlagen: {e}")
            print(f"     AMS NetID: {self.config['ams_net_id']}, Port: {self.config['port']}")
            if "Target port not found" in str(e):
                print("     Hinweis: Bitte TwinCAT-Runtime-Port in Setup korrekt setzen (z. B. TC2=801, TC3=851).")
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
        """
        Versucht Reconnect
        
        ⭐ v1.1.0: Mit Cooldown!
        """
        now = time.time()
        
        # ⭐ Prüfe Cooldown
        if now - self.last_reconnect < self.reconnect_cooldown:
            remaining = int(self.reconnect_cooldown - (now - self.last_reconnect))
            print(f"  ⏳ Reconnect-Cooldown aktiv ({remaining}s verbleibend)")
            return False
        
        print(f"  🔄 Versuche PLC-Reconnect... (Fehler: {self.consecutive_errors}/{self.max_errors})")
        
        self.last_reconnect = now
        self.disconnect()
        time.sleep(1)
        
        success = self.connect()
        
        if success:
            print(f"  ✅ Reconnect erfolgreich! (Stats: {self.total_reads} reads, {self.total_errors} errors)")
        
        return success
    
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
            
            # ⭐ Reset Fehler-Counter bei Erfolg
            if self.consecutive_errors > 0:
                self.consecutive_errors = 0
            
            self.total_reads += 1
            return value
            
        except Exception as e:
            self.consecutive_errors += 1
            self.total_errors += 1
            
            # ⭐ DEBUG: Logge fehlerhafte Variablen (nur erste 3 mal)
            if self.consecutive_errors <= 3:
                print(f"  ⚠️  Read-Fehler [{self.consecutive_errors}/{self.max_errors}]: {variable} → {e}")
            
            # ⭐ Nur bei schweren Fehlern reconnecten
            if self.consecutive_errors >= self.max_errors:
                if self.config['auto_reconnect']:
                    # Prüfe ob Reconnect erlaubt (Cooldown)
                    now = time.time()
                    if now - self.last_reconnect >= self.reconnect_cooldown:
                        threading.Thread(target=self.reconnect, daemon=True).start()
                    else:
                        # Cooldown aktiv, reset Error-Counter um weitere Reconnects zu vermeiden
                        self.consecutive_errors = self.max_errors - 5
            
            # Stille Fehler (kein Print für jede fehlerhafte Variable)
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
            
            # ⭐ Reset Fehler-Counter bei Erfolg
            if self.consecutive_errors > 0:
                self.consecutive_errors = 0
            
            self.total_writes += 1
            return True
            
        except Exception as e:
            self.consecutive_errors += 1
            self.total_errors += 1
            print(f"  ⚠️  Write-Fehler {variable}: {e}")
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
        """
        Gibt Verbindungs-Status zurück
        
        ⭐ v1.1.0: Erweiterte Statistik
        """
        return {
            'connected': self.connected,
            'ams_net_id': self.config['ams_net_id'],
            'consecutive_errors': self.consecutive_errors,
            'max_errors': self.max_errors,
            'cached_variables': len(self.cache),
            'total_reads': self.total_reads,
            'total_writes': self.total_writes,
            'total_errors': self.total_errors,
            'error_rate': f"{(self.total_errors / max(self.total_reads, 1) * 100):.1f}%"
        }
    
    def clear_cache(self):
        """Leert Cache"""
        self.cache.clear()
    
    def reset_statistics(self):
        """⭐ v1.1.0: Reset Statistik"""
        self.total_reads = 0
        self.total_writes = 0
        self.total_errors = 0
        self.consecutive_errors = 0
    
    def shutdown(self):
        """Beendet Verbindung"""
        print(f"  📊 PLC-Statistik: {self.total_reads} reads, {self.total_writes} writes, {self.total_errors} errors")
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
