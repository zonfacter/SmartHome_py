"""
Serial Link Abstract Base Class
Version: 1.0.0
Abstrakte Basisklasse für serielle Kommunikation (RS485/Modbus/KNX)

Vorbereitung für Plugin-System:
- RS485 Master/Slave
- Modbus RTU/ASCII
- KNX TP
- DMX512
"""

import threading
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List


class SerialLink(ABC):
    """
    Abstrakte Basisklasse für serielle Kommunikation.

    Plugins müssen von dieser Klasse erben und die abstrakten Methoden implementieren.

    Standard-Features:
    - Thread-safe Operationen
    - Connection Management
    - Retry-Logic
    - Error-Tracking
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        """
        Initialisiert SerialLink

        Args:
            port: Serieller Port (z.B. 'COM3' oder '/dev/ttyUSB0')
            baudrate: Baudrate (default: 9600)
            timeout: Timeout in Sekunden (default: 1.0)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.is_connected = False
        self._lock = threading.Lock()
        self.log = logging.getLogger(f"SerialLink.{port}")

        # Statistik
        self.total_reads = 0
        self.total_writes = 0
        self.total_errors = 0

    @abstractmethod
    def connect(self) -> bool:
        """
        Stellt Hardware-Verbindung her

        Returns:
            True bei Erfolg, False bei Fehler

        Muss von Plugin implementiert werden!
        """
        raise NotImplementedError("Plugin muss connect() implementieren")

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Trennt Hardware-Verbindung

        Returns:
            True bei Erfolg

        Muss von Plugin implementiert werden!
        """
        raise NotImplementedError("Plugin muss disconnect() implementieren")

    @abstractmethod
    def read(self, address: int, count: int = 1) -> Optional[Any]:
        """
        Liest Daten von der seriellen Verbindung

        Args:
            address: Register-Adresse oder Device-ID
            count: Anzahl zu lesender Register/Bytes

        Returns:
            Gelesene Daten oder None bei Fehler

        Muss von Plugin implementiert werden!
        """
        raise NotImplementedError("Plugin muss read() implementieren")

    @abstractmethod
    def write(self, address: int, value: Any) -> bool:
        """
        Schreibt Daten zur seriellen Verbindung

        Args:
            address: Register-Adresse oder Device-ID
            value: Zu schreibender Wert

        Returns:
            True bei Erfolg, False bei Fehler

        Muss von Plugin implementiert werden!
        """
        raise NotImplementedError("Plugin muss write() implementieren")

    # ========================================================================
    # Helper-Methoden (Optional überschreibbar)
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """
        Gibt Status-Informationen zurück

        Returns:
            Dictionary mit Status-Daten
        """
        return {
            'port': self.port,
            'baudrate': self.baudrate,
            'connected': self.is_connected,
            'total_reads': self.total_reads,
            'total_writes': self.total_writes,
            'total_errors': self.total_errors,
            'error_rate': f"{(self.total_errors / max(self.total_reads + self.total_writes, 1) * 100):.1f}%"
        }

    def reset_statistics(self):
        """Setzt Statistik-Counter zurück"""
        self.total_reads = 0
        self.total_writes = 0
        self.total_errors = 0

    def __enter__(self):
        """Context Manager Support"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Support"""
        self.disconnect()


class ModbusRTULink(SerialLink):
    """
    Beispiel-Implementation: Modbus RTU über RS485

    Dies ist eine Referenz-Implementierung.
    Für Production sollte eine robuste Library wie pymodbus verwendet werden.
    """

    def connect(self) -> bool:
        """Verbindung herstellen"""
        try:
            # Hier würde normalerweise pyserial.Serial() aufgerufen werden
            # Für dieses Beispiel simulieren wir die Verbindung

            self.log.info(f"Verbinde mit Modbus RTU auf {self.port} @ {self.baudrate} Baud...")

            # TODO: Echte Serial-Verbindung
            # import serial
            # self.serial = serial.Serial(
            #     port=self.port,
            #     baudrate=self.baudrate,
            #     timeout=self.timeout,
            #     bytesize=8,
            #     parity='N',
            #     stopbits=1
            # )

            self.is_connected = True
            self.log.info(f"✓ Modbus RTU verbunden: {self.port}")
            return True

        except Exception as e:
            self.log.error(f"✗ Modbus RTU Verbindung fehlgeschlagen: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> bool:
        """Verbindung trennen"""
        try:
            if self.is_connected:
                # TODO: Echte Serial-Verbindung schließen
                # if hasattr(self, 'serial'):
                #     self.serial.close()

                self.is_connected = False
                self.log.info(f"✓ Modbus RTU getrennt: {self.port}")

            return True

        except Exception as e:
            self.log.error(f"✗ Fehler beim Trennen: {e}")
            return False

    def read(self, address: int, count: int = 1) -> Optional[List[int]]:
        """
        Liest Holding Registers

        Args:
            address: Register-Adresse
            count: Anzahl Register

        Returns:
            Liste von Register-Werten oder None
        """
        if not self.is_connected:
            self.log.warning("Nicht verbunden")
            return None

        with self._lock:
            try:
                self.log.debug(f"Lese {count} Register ab Adresse {address}")

                # TODO: Echte Modbus-Read-Implementierung
                # result = self.modbus_client.read_holding_registers(address, count)

                # Simulation
                result = [0] * count

                self.total_reads += 1
                return result

            except Exception as e:
                self.log.error(f"✗ Read-Fehler: {e}")
                self.total_errors += 1
                return None

    def write(self, address: int, value: Any) -> bool:
        """
        Schreibt Holding Register

        Args:
            address: Register-Adresse
            value: Wert (int oder Liste)

        Returns:
            True bei Erfolg
        """
        if not self.is_connected:
            self.log.warning("Nicht verbunden")
            return False

        with self._lock:
            try:
                self.log.debug(f"Schreibe {value} zu Adresse {address}")

                # TODO: Echte Modbus-Write-Implementierung
                # if isinstance(value, list):
                #     result = self.modbus_client.write_registers(address, value)
                # else:
                #     result = self.modbus_client.write_register(address, value)

                self.total_writes += 1
                return True

            except Exception as e:
                self.log.error(f"✗ Write-Fehler: {e}")
                self.total_errors += 1
                return False


# Test-Code
if __name__ == '__main__':
    # Setup Logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)-8s [%(name)s] %(message)s'
    )

    # Test Modbus RTU
    print("=== Modbus RTU Test ===")
    modbus = ModbusRTULink(port='COM3', baudrate=9600)

    # Connect
    if modbus.connect():
        # Read
        values = modbus.read(address=100, count=5)
        print(f"Read Result: {values}")

        # Write
        success = modbus.write(address=200, value=42)
        print(f"Write Success: {success}")

        # Status
        status = modbus.get_status()
        print(f"Status: {status}")

        # Disconnect
        modbus.disconnect()

    # Context Manager Test
    print("\n=== Context Manager Test ===")
    with ModbusRTULink(port='COM3', baudrate=19200) as link:
        print(f"Connected: {link.is_connected}")
