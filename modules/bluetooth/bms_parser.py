"""
BMS Parser v4.6.0
Plugin-System für Battery Management System Parser

📁 SPEICHERORT: modules/bluetooth/bms_parser.py

Features v4.6.0:
- ⭐ Plugin-System für verschiedene BMS-Protokolle
- ⭐ BaseBMSParser abstrakte Klasse
- ⭐ Auto-Discovery & Registration
- Normalisierte Datenstruktur
- Protocol Auto-Detection
- Parser-Registry

Unterstützte Protokolle (via Plugins):
- JBD/Xiaoxiang BMS (jbd_parser.py)
- Daly BMS (daly_parser.py) - später
- JK BMS (jk_parser.py) - später
- ANT BMS (ant_parser.py) - später
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import time
import os


@dataclass
class BMSData:
    """
    Normalisierte BMS-Daten

    Alle BMS-Parser konvertieren in dieses einheitliche Format
    """
    # Basic Info
    timestamp: float = field(default_factory=time.time)
    protocol: str = ""  # z.B. "JBD", "Daly", "JK"

    # Voltage & Current
    total_voltage: float = 0.0      # V (Gesamt-Spannung)
    current: float = 0.0             # A (positiv = Laden, negativ = Entladen)
    power: float = 0.0               # W (berechnet: V * A)

    # State of Charge
    soc: int = 0                     # % (State of Charge)
    soh: int = 100                   # % (State of Health)

    # Capacity
    capacity_remaining: float = 0.0  # Ah
    capacity_full: float = 0.0       # Ah
    capacity_design: float = 0.0     # Ah

    # Temperatures
    temperatures: List[float] = field(default_factory=list)  # °C
    temp_avg: float = 0.0            # °C (Durchschnitt)
    temp_min: float = 0.0            # °C
    temp_max: float = 0.0            # °C

    # Cell Voltages
    cell_voltages: List[float] = field(default_factory=list)  # V
    cell_count: int = 0
    cell_min: float = 0.0            # V (niedrigste Zelle)
    cell_max: float = 0.0            # V (höchste Zelle)
    cell_delta: float = 0.0          # V (Differenz max-min)

    # Protection Status
    protection_flags: Dict[str, bool] = field(default_factory=dict)

    # Charge/Discharge
    charge_enabled: bool = False
    discharge_enabled: bool = False

    # Cycles
    cycles: int = 0

    # Balancing
    balancing_active: bool = False
    balancing_cells: List[int] = field(default_factory=list)  # Indices der balancierenden Zellen

    # Metadata
    manufacturer: str = ""
    device_name: str = ""
    serial_number: str = ""
    version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für DataGateway Routing"""
        return {
            'timestamp': self.timestamp,
            'protocol': self.protocol,

            # Voltage & Current
            'total_voltage': self.total_voltage,
            'current': self.current,
            'power': self.power,

            # SoC
            'soc': self.soc,
            'soh': self.soh,

            # Capacity
            'capacity_remaining': self.capacity_remaining,
            'capacity_full': self.capacity_full,
            'capacity_design': self.capacity_design,

            # Temperatures
            'temperatures': self.temperatures,
            'temp_avg': self.temp_avg,
            'temp_min': self.temp_min,
            'temp_max': self.temp_max,

            # Cells
            'cell_voltages': self.cell_voltages,
            'cell_count': self.cell_count,
            'cell_min': self.cell_min,
            'cell_max': self.cell_max,
            'cell_delta': self.cell_delta,

            # Protection
            'protection_flags': self.protection_flags,

            # Charge/Discharge
            'charge_enabled': self.charge_enabled,
            'discharge_enabled': self.discharge_enabled,

            # Cycles
            'cycles': self.cycles,

            # Balancing
            'balancing_active': self.balancing_active,
            'balancing_cells': self.balancing_cells,

            # Metadata
            'manufacturer': self.manufacturer,
            'device_name': self.device_name,
            'serial_number': self.serial_number,
            'version': self.version
        }


class BaseBMSParser(ABC):
    """
    Abstrakte Basisklasse für BMS-Parser

    Jeder BMS-Protokoll-Parser erbt von dieser Klasse und
    implementiert die abstrakten Methoden.
    """

    def __init__(self, connection_id: str):
        """
        Args:
            connection_id: Eindeutige ID der Bluetooth-Verbindung
        """
        self.connection_id = connection_id
        self.protocol_name = self.__class__.__name__.replace("Parser", "")

        # Parser-State
        self.last_data: Optional[BMSData] = None
        self.parse_errors = 0

    @abstractmethod
    def get_protocol_name(self) -> str:
        """
        Liefert Protocol-Namen

        Returns:
            z.B. "JBD", "Daly", "JK"
        """
        pass

    @abstractmethod
    def get_read_characteristic_uuid(self) -> str:
        """
        Liefert UUID des Read-Characteristics

        Returns:
            UUID als String
        """
        pass

    @abstractmethod
    def get_write_characteristic_uuid(self) -> str:
        """
        Liefert UUID des Write-Characteristics

        Returns:
            UUID als String
        """
        pass

    @abstractmethod
    def get_request_basic_info_command(self) -> bytes:
        """
        Liefert Command um Basic-Info vom BMS anzufordern

        Returns:
            Command als bytes
        """
        pass

    @abstractmethod
    def get_request_cell_voltages_command(self) -> bytes:
        """
        Liefert Command um Zellspannungen anzufordern

        Returns:
            Command als bytes
        """
        pass

    @abstractmethod
    def parse_basic_info(self, data: bytes) -> Optional[BMSData]:
        """
        Parsed Basic-Info Response

        Args:
            data: Rohdaten vom BMS

        Returns:
            BMSData oder None bei Fehler
        """
        pass

    @abstractmethod
    def parse_cell_voltages(self, data: bytes, bms_data: BMSData) -> BMSData:
        """
        Parsed Cell-Voltages Response

        Args:
            data: Rohdaten vom BMS
            bms_data: Bestehendes BMSData-Objekt (wird erweitert)

        Returns:
            BMSData mit Cell-Voltages
        """
        pass

    # ========================================================================
    # OPTIONAL HOOKS (können überschrieben werden)
    # ========================================================================

    def detect_protocol(self, data: bytes) -> bool:
        """
        Auto-Detection: Prüft ob Daten zu diesem Parser passen

        Args:
            data: Rohdaten

        Returns:
            True wenn Protokoll erkannt wurde
        """
        # Default: Immer False (kein Auto-Detect)
        return False

    def calculate_checksum(self, data: bytes) -> int:
        """
        Berechnet Checksumme (protocol-spezifisch)

        Args:
            data: Daten

        Returns:
            Checksumme
        """
        # Default: Einfache Summe
        return sum(data) & 0xFF

    def validate_response(self, data: bytes) -> bool:
        """
        Validiert Response (Checksumme, Länge, etc.)

        Args:
            data: Rohdaten

        Returns:
            True wenn gültig
        """
        # Default: Immer True (keine Validierung)
        return True

    # ========================================================================
    # HELPERS
    # ========================================================================

    def parse(self, data: bytes, data_type: str = "basic") -> Optional[BMSData]:
        """
        High-Level Parse-Methode

        Args:
            data: Rohdaten
            data_type: "basic" oder "cells"

        Returns:
            BMSData oder None
        """
        try:
            max_frame_raw = str(os.getenv('SMARTHOME_BT_MAX_FRAME_BYTES', '2048')).strip()
            try:
                max_frame_bytes = max(64, int(max_frame_raw))
            except Exception:
                max_frame_bytes = 2048
            if not isinstance(data, (bytes, bytearray)):
                self.parse_errors += 1
                return None
            if len(data) > max_frame_bytes:
                print(f"  ⚠️  [{self.connection_id}] Response zu groß ({len(data)}>{max_frame_bytes})")
                self.parse_errors += 1
                return None

            # Validiere Response
            if not self.validate_response(data):
                print(f"  ⚠️  [{self.connection_id}] Ungültige Response!")
                self.parse_errors += 1
                return None

            # Parse basierend auf Type
            if data_type == "basic":
                bms_data = self.parse_basic_info(data)
            elif data_type == "cells":
                if self.last_data:
                    bms_data = self.parse_cell_voltages(data, self.last_data)
                else:
                    # Erstelle leeres BMSData
                    bms_data = self.parse_cell_voltages(data, BMSData())
            else:
                return None

            if bms_data:
                # Setze Protocol-Name
                bms_data.protocol = self.get_protocol_name()

                # Berechne abgeleitete Werte
                self._calculate_derived_values(bms_data)

                # Cache
                self.last_data = bms_data

            return bms_data

        except Exception as e:
            print(f"  ✗ [{self.connection_id}] Parse-Fehler: {e}")
            self.parse_errors += 1
            return None

    def _calculate_derived_values(self, bms_data: BMSData):
        """Berechnet abgeleitete Werte (Power, Temp-Avg, Cell-Delta, etc.)"""

        # Power
        bms_data.power = bms_data.total_voltage * bms_data.current

        # Temperature Average/Min/Max
        if bms_data.temperatures:
            bms_data.temp_avg = sum(bms_data.temperatures) / len(bms_data.temperatures)
            bms_data.temp_min = min(bms_data.temperatures)
            bms_data.temp_max = max(bms_data.temperatures)

        # Cell Voltages Min/Max/Delta
        if bms_data.cell_voltages:
            bms_data.cell_count = len(bms_data.cell_voltages)
            bms_data.cell_min = min(bms_data.cell_voltages)
            bms_data.cell_max = max(bms_data.cell_voltages)
            bms_data.cell_delta = bms_data.cell_max - bms_data.cell_min


# ========================================================================
# PARSER REGISTRY
# ========================================================================

class BMSParserRegistry:
    """
    Registry für BMS-Parser

    Verwaltet alle verfügbaren Parser und ermöglicht Auto-Detection
    """

    def __init__(self):
        self.parsers: Dict[str, type] = {}  # protocol_name -> Parser-Class

    def register(self, parser_class: type):
        """
        Registriert einen Parser

        Args:
            parser_class: Parser-Klasse (erbt von BaseBMSParser)
        """
        if not issubclass(parser_class, BaseBMSParser):
            raise ValueError(f"{parser_class} muss von BaseBMSParser erben!")

        # Erstelle temporäre Instanz um Protocol-Name zu holen
        temp = parser_class("temp")
        protocol_name = temp.get_protocol_name()

        self.parsers[protocol_name] = parser_class
        print(f"  ✅ BMS-Parser registriert: {protocol_name}")

    def get_parser(self, protocol_name: str, connection_id: str) -> Optional[BaseBMSParser]:
        """
        Holt Parser nach Protocol-Name

        Args:
            protocol_name: z.B. "JBD", "Daly"
            connection_id: Connection-ID

        Returns:
            Parser-Instanz oder None
        """
        parser_class = self.parsers.get(protocol_name)
        if parser_class:
            return parser_class(connection_id)
        return None

    def detect_protocol(self, data: bytes, connection_id: str) -> Optional[BaseBMSParser]:
        """
        Auto-Detection: Findet passenden Parser für Rohdaten

        Args:
            data: Rohdaten
            connection_id: Connection-ID

        Returns:
            Parser-Instanz oder None
        """
        for protocol_name, parser_class in self.parsers.items():
            parser = parser_class(connection_id)
            if parser.detect_protocol(data):
                print(f"  ✅ Protocol erkannt: {protocol_name}")
                return parser

        return None

    def get_all_protocols(self) -> List[str]:
        """Liefert Liste aller registrierten Protokolle"""
        return list(self.parsers.keys())


# ========================================================================
# GLOBAL REGISTRY
# ========================================================================

# Globale Parser-Registry
bms_parser_registry = BMSParserRegistry()


def register_bms_parser(parser_class: type):
    """
    Decorator zum Registrieren von BMS-Parsern

    Usage:
        @register_bms_parser
        class JBDParser(BaseBMSParser):
            ...
    """
    bms_parser_registry.register(parser_class)
    return parser_class
