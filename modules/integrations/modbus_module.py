"""
Modbus Integration Module
Version: 1.0.0
Ermöglicht Modbus TCP/RTU Kommunikation für Deye Wechselrichter & andere Geräte
"""

from module_manager import BaseModule
from typing import Dict, Any, Optional
import threading
import time


class ModbusIntegration(BaseModule):
    """
    Modbus TCP/RTU Integration
    
    Unterstützt:
    - Modbus TCP (Ethernet)
    - Modbus RTU (Serial)
    - Auto-Reconnect
    - Polling mehrerer Geräte
    """
    
    NAME = "modbus_integration"
    VERSION = "1.0.0"
    DESCRIPTION = "Modbus TCP/RTU für Wechselrichter & Sensoren"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = []
    
    def __init__(self):
        super().__init__()
        self.clients = {}  # Device-Name -> Client
        self.registers = {}  # Device-Name -> {address: value}
        self.polling_thread = None
        self.running = False
    
    def initialize(self, app_context: Any):
        """Initialisiert Modbus-Kommunikation"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def add_device(self, name: str, host: str, port: int = 502, 
                   unit_id: int = 1, protocol: str = 'tcp'):
        """
        Fügt Modbus-Gerät hinzu
        
        Args:
            name: Geräte-Name (z.B. 'deye_inverter')
            host: IP-Adresse oder COM-Port
            port: TCP-Port (Standard: 502)
            unit_id: Modbus Unit-ID
            protocol: 'tcp' oder 'rtu'
        """
        try:
            # Lazy import - nur wenn benötigt
            from pymodbus.client import ModbusTcpClient, ModbusSerialClient
            
            if protocol == 'tcp':
                client = ModbusTcpClient(host, port=port)
            else:  # rtu
                client = ModbusSerialClient(port=host, baudrate=9600)
            
            self.clients[name] = {
                'client': client,
                'unit_id': unit_id,
                'connected': False
            }
            
            # Verbinde
            if client.connect():
                self.clients[name]['connected'] = True
                print(f"  ✓ Modbus-Gerät '{name}' verbunden ({host}:{port})")
                return True
            else:
                print(f"  ✗ Verbindung zu '{name}' fehlgeschlagen")
                return False
                
        except ImportError:
            print(f"  ⚠️  pymodbus nicht installiert! pip install pymodbus")
            return False
        except Exception as e:
            print(f"  ✗ Fehler bei '{name}': {e}")
            return False
    
    def read_holding_register(self, device: str, address: int, 
                              count: int = 1) -> Optional[list]:
        """Liest Holding Register"""
        if device not in self.clients:
            return None
        
        try:
            client_info = self.clients[device]
            client = client_info['client']
            unit_id = client_info['unit_id']
            
            result = client.read_holding_registers(address, count, slave=unit_id)
            
            if result.isError():
                return None
            
            return result.registers
            
        except Exception as e:
            print(f"  ✗ Fehler beim Lesen von {device} @ {address}: {e}")
            return None
    
    def write_holding_register(self, device: str, address: int, value: int) -> bool:
        """Schreibt Holding Register"""
        if device not in self.clients:
            return False
        
        try:
            client_info = self.clients[device]
            client = client_info['client']
            unit_id = client_info['unit_id']
            
            result = client.write_register(address, value, slave=unit_id)
            return not result.isError()
            
        except Exception as e:
            print(f"  ✗ Fehler beim Schreiben zu {device} @ {address}: {e}")
            return False
    
    def get_deye_pv_power(self, device: str = 'deye_inverter') -> Optional[float]:
        """Liest PV-Leistung vom Deye Wechselrichter (Beispiel)"""
        # Deye Register: 672 = AC Output Power (W)
        result = self.read_holding_register(device, 672, 1)
        if result:
            return float(result[0])
        return None
    
    def start_polling(self, interval: float = 5.0):
        """Startet automatisches Polling aller Geräte"""
        if self.running:
            return
        
        self.running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, args=(interval,))
        self.polling_thread.daemon = True
        self.polling_thread.start()
        print(f"  ⚡ Modbus Polling gestartet (Interval: {interval}s)")
    
    def _polling_loop(self, interval: float):
        """Polling-Loop (Background-Thread)"""
        while self.running:
            for device_name in self.clients.keys():
                # Beispiel: Lese häufig verwendete Register
                # TODO: Konfigurierbar machen
                pass
            
            time.sleep(interval)
    
    def stop_polling(self):
        """Stoppt Polling"""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2)
    
    def shutdown(self):
        """Beendet alle Verbindungen"""
        self.stop_polling()
        
        for name, client_info in self.clients.items():
            try:
                client_info['client'].close()
                print(f"  ✓ Modbus-Gerät '{name}' getrennt")
            except:
                pass


# Registrierungs-Funktion
def register(module_manager):
    """Registriert dieses Modul beim ModuleManager"""
    module_manager.register_module(
        ModbusIntegration.NAME,
        ModbusIntegration.VERSION,
        ModbusIntegration.DESCRIPTION,
        ModbusIntegration,
        author=ModbusIntegration.AUTHOR,
        dependencies=ModbusIntegration.DEPENDENCIES
    )
