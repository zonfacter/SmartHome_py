"""
JBD/Xiaoxiang BMS Parser v1.0
Parser für JBD/Xiaoxiang BMS Protokoll

📁 SPEICHERORT: modules/bluetooth/parsers/jbd_parser.py

Unterstützt:
- JBD BMS (Jiabaida)
- Xiaoxiang BMS
- Overkill Solar BMS

Protocol:
- Start: 0xDD
- Read: 0xA5
- Write: 0x5A
- End: 0x77
- Checksum: 16-bit checksum (2's complement)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bms_parser import BaseBMSParser, BMSData, register_bms_parser
from typing import Optional
import struct


@register_bms_parser
class JBDParser(BaseBMSParser):
    """
    JBD/Xiaoxiang BMS Parser

    Command Structure:
    [START] [CMD] [LEN] [DATA...] [CHECKSUM_H] [CHECKSUM_L] [END]
     0xDD   0xA5  0x00    ...      XX          XX         0x77

    Response Structure:
    [START] [STATUS] [LEN] [DATA...] [CHECKSUM_H] [CHECKSUM_L] [END]
     0xDD     0x00    XX      ...       XX          XX         0x77
    """

    # Characteristic UUIDs (JBD Standard)
    READ_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
    WRITE_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"

    # Commands
    CMD_BASIC_INFO = 0x03        # Basic Info (Voltage, Current, SoC, etc.)
    CMD_CELL_VOLTAGES = 0x04     # Cell Voltages
    CMD_DEVICE_NAME = 0x05       # Device Name

    def __init__(self, connection_id: str):
        super().__init__(connection_id)

    def get_protocol_name(self) -> str:
        return "JBD"

    def get_read_characteristic_uuid(self) -> str:
        return self.READ_UUID

    def get_write_characteristic_uuid(self) -> str:
        return self.WRITE_UUID

    def get_request_basic_info_command(self) -> bytes:
        """
        Command: DD A5 03 00 FF FD 77
        - 0xDD: Start
        - 0xA5: Read Command
        - 0x03: Basic Info
        - 0x00: Data Length
        - 0xFFFD: Checksum
        - 0x77: End
        """
        cmd = bytes([0xDD, 0xA5, self.CMD_BASIC_INFO, 0x00])
        checksum = self._calculate_checksum_jbd(cmd[2:])  # Ab CMD
        cmd += struct.pack('>H', checksum)  # Big-Endian 16-bit
        cmd += bytes([0x77])
        return cmd

    def get_request_cell_voltages_command(self) -> bytes:
        """
        Command: DD A5 04 00 FF FC 77
        """
        cmd = bytes([0xDD, 0xA5, self.CMD_CELL_VOLTAGES, 0x00])
        checksum = self._calculate_checksum_jbd(cmd[2:])
        cmd += struct.pack('>H', checksum)
        cmd += bytes([0x77])
        return cmd

    def parse_basic_info(self, data: bytes) -> Optional[BMSData]:
        """
        Parsed Basic Info Response

        Response Format (27 bytes data):
        [0-1]:   Total Voltage (0.01V)
        [2-3]:   Current (0.01A, signed)
        [4-5]:   Remaining Capacity (0.01Ah)
        [6-7]:   Full Capacity (0.01Ah)
        [8-9]:   Cycles
        [10-11]: Production Date
        [12-15]: Balance Status (4 bytes)
        [16-17]: Protection Status
        [18]:    Software Version
        [19]:    SoC (%)
        [20]:    FET Status (Charge/Discharge)
        [21]:    Cell Count
        [22]:    Temp Count
        [23-24]: Temp 1 (0.1K - 273.15)
        [25-26]: Temp 2 (0.1K - 273.15)
        """
        if len(data) < 34:  # Min: Start + Status + Len + 27 Data + Checksum + End
            return None

        # Validiere Start/End
        if data[0] != 0xDD or data[-1] != 0x77:
            return None

        # Extrahiere Data-Payload
        data_len = data[2]
        payload = data[3:3+data_len]

        if len(payload) < 27:
            return None

        bms = BMSData()

        # Total Voltage (0.01V)
        bms.total_voltage = struct.unpack('>H', payload[0:2])[0] * 0.01

        # Current (0.01A, signed)
        current_raw = struct.unpack('>h', payload[2:4])[0]  # signed
        bms.current = current_raw * 0.01

        # Remaining Capacity (0.01Ah)
        bms.capacity_remaining = struct.unpack('>H', payload[4:6])[0] * 0.01

        # Full Capacity (0.01Ah)
        bms.capacity_full = struct.unpack('>H', payload[6:8])[0] * 0.01
        bms.capacity_design = bms.capacity_full  # Annahme

        # Cycles
        bms.cycles = struct.unpack('>H', payload[8:10])[0]

        # Protection Status (2 bytes = 16 bits)
        protection_raw = struct.unpack('>H', payload[16:18])[0]
        bms.protection_flags = self._parse_protection_flags(protection_raw)

        # SoC (%)
        bms.soc = payload[19]

        # FET Status (Bit 0: Charge, Bit 1: Discharge)
        fet_status = payload[20]
        bms.charge_enabled = bool(fet_status & 0x01)
        bms.discharge_enabled = bool(fet_status & 0x02)

        # Temperatures (0.1K - 273.15 = °C)
        if len(payload) >= 27:
            temp1_raw = struct.unpack('>H', payload[23:25])[0]
            temp1 = (temp1_raw * 0.1) - 273.15

            temp2_raw = struct.unpack('>H', payload[25:27])[0]
            temp2 = (temp2_raw * 0.1) - 273.15

            bms.temperatures = [temp1, temp2]

        # Balancing
        balance_status = struct.unpack('>I', payload[12:16])[0]  # 4 bytes
        bms.balancing_cells = self._parse_balance_status(balance_status)
        bms.balancing_active = len(bms.balancing_cells) > 0

        return bms

    def parse_cell_voltages(self, data: bytes, bms_data: BMSData) -> BMSData:
        """
        Parsed Cell Voltages Response

        Response Format:
        [0]: Cell Count
        [1-2]: Cell 1 Voltage (0.001V)
        [3-4]: Cell 2 Voltage (0.001V)
        ...
        """
        if len(data) < 7:  # Min: Start + Status + Len + 1 Cell + Checksum + End
            return bms_data

        # Validiere Start/End
        if data[0] != 0xDD or data[-1] != 0x77:
            return bms_data

        # Extrahiere Data-Payload
        data_len = data[2]
        payload = data[3:3+data_len]

        if len(payload) < 1:
            return bms_data

        # Cell Count
        cell_count = payload[0]

        # Cell Voltages (0.001V)
        cell_voltages = []
        for i in range(cell_count):
            offset = 1 + (i * 2)
            if offset + 2 <= len(payload):
                voltage_raw = struct.unpack('>H', payload[offset:offset+2])[0]
                voltage = voltage_raw * 0.001  # mV to V
                cell_voltages.append(voltage)

        bms_data.cell_voltages = cell_voltages

        return bms_data

    # ========================================================================
    # PROTOCOL-SPECIFIC HELPERS
    # ========================================================================

    def _calculate_checksum_jbd(self, data: bytes) -> int:
        """
        JBD Checksum: 16-bit 2's Complement

        Args:
            data: Data bytes (ab Command, ohne Start/End)

        Returns:
            16-bit Checksum
        """
        checksum = sum(data)
        checksum = 0x10000 - checksum  # 2's complement
        return checksum & 0xFFFF

    def validate_response(self, data: bytes) -> bool:
        """Validiert JBD Response"""
        if len(data) < 7:
            return False

        # Start-Byte
        if data[0] != 0xDD:
            return False

        # End-Byte
        if data[-1] != 0x77:
            return False

        # Checksum
        data_len = data[2]
        payload = data[3:3+data_len]
        checksum_expected = struct.unpack('>H', data[3+data_len:3+data_len+2])[0]
        checksum_calculated = self._calculate_checksum_jbd(data[1:3+data_len])

        if checksum_calculated != checksum_expected:
            print(f"  ⚠️  Checksum-Fehler! Expected: {checksum_expected:04X}, Got: {checksum_calculated:04X}")
            return False

        return True

    def detect_protocol(self, data: bytes) -> bool:
        """Auto-Detection für JBD-Protokoll"""
        if len(data) < 7:
            return False

        # Prüfe Start/End Bytes
        if data[0] == 0xDD and data[-1] == 0x77:
            return True

        return False

    def _parse_protection_flags(self, flags: int) -> dict:
        """
        Parsed Protection-Flags (16 bits)

        Bit 0: Cell Overvoltage
        Bit 1: Cell Undervoltage
        Bit 2: Pack Overvoltage
        Bit 3: Pack Undervoltage
        Bit 4: Charge Over-Temperature
        Bit 5: Charge Under-Temperature
        Bit 6: Discharge Over-Temperature
        Bit 7: Discharge Under-Temperature
        Bit 8: Charge Overcurrent
        Bit 9: Discharge Overcurrent
        Bit 10: Short Circuit
        Bit 11: Front-end IC Error
        Bit 12: Software Lock MOS
        Bit 13-15: Reserved
        """
        return {
            'cell_overvoltage': bool(flags & (1 << 0)),
            'cell_undervoltage': bool(flags & (1 << 1)),
            'pack_overvoltage': bool(flags & (1 << 2)),
            'pack_undervoltage': bool(flags & (1 << 3)),
            'charge_over_temp': bool(flags & (1 << 4)),
            'charge_under_temp': bool(flags & (1 << 5)),
            'discharge_over_temp': bool(flags & (1 << 6)),
            'discharge_under_temp': bool(flags & (1 << 7)),
            'charge_overcurrent': bool(flags & (1 << 8)),
            'discharge_overcurrent': bool(flags & (1 << 9)),
            'short_circuit': bool(flags & (1 << 10)),
            'frontend_ic_error': bool(flags & (1 << 11)),
            'software_lock_mos': bool(flags & (1 << 12))
        }

    def _parse_balance_status(self, balance: int) -> list:
        """
        Parsed Balance-Status (32 bits)

        Jedes Bit repräsentiert eine Zelle (max 32 Zellen)

        Args:
            balance: 32-bit Balance-Status

        Returns:
            Liste von Cell-Indices die balancieren
        """
        balancing_cells = []
        for i in range(32):
            if balance & (1 << i):
                balancing_cells.append(i)
        return balancing_cells


# ========================================================================
# STANDALONE TEST
# ========================================================================

def test_jbd_parser():
    """Test JBD Parser mit Beispiel-Daten"""
    print("="*60)
    print("  JBD Parser Test")
    print("="*60)

    parser = JBDParser("test_bms")

    # Beispiel: Basic Info Response (simuliert)
    # DD 00 1B [27 bytes data] [checksum] 77
    # Minimal-Response mit Dummy-Daten
    basic_info_response = bytes([
        0xDD, 0x00, 0x1B,  # Start, Status, Length
        # Total Voltage: 51.20V (0x1400 = 5120 * 0.01)
        0x14, 0x00,
        # Current: -10.00A (0xFC18 = -1000 * 0.01)
        0xFC, 0x18,
        # Remaining: 100.00Ah (0x2710 = 10000 * 0.01)
        0x27, 0x10,
        # Full: 105.00Ah (0x2904 = 10500 * 0.01)
        0x29, 0x04,
        # Cycles: 10 (0x000A)
        0x00, 0x0A,
        # Production Date
        0x00, 0x00,
        # Balance Status (4 bytes)
        0x00, 0x00, 0x00, 0x03,  # Cells 0 und 1 balancieren
        # Protection Status (keine Alarme)
        0x00, 0x00,
        # Software Version
        0x01,
        # SoC: 95%
        0x5F,
        # FET Status: Both enabled (0x03)
        0x03,
        # Cell Count: 16
        0x10,
        # Temp Count: 2
        0x02,
        # Temp 1: 25°C = 298.15K = 2981.5 * 0.1 = 0x0BA7
        0x0B, 0xA7,
        # Temp 2: 26°C = 299.15K = 2991.5 * 0.1 = 0x0BAF
        0x0B, 0xAF,
        # Checksum (berechnet)
        0xFD, 0x8F,
        # End
        0x77
    ])

    print("\n1. Parse Basic Info...")
    bms_data = parser.parse(basic_info_response, "basic")

    if bms_data:
        print(f"   ✅ Parse erfolgreich!")
        print(f"   Voltage: {bms_data.total_voltage:.2f}V")
        print(f"   Current: {bms_data.current:.2f}A")
        print(f"   Power: {bms_data.power:.2f}W")
        print(f"   SoC: {bms_data.soc}%")
        print(f"   Capacity: {bms_data.capacity_remaining:.2f}/{bms_data.capacity_full:.2f}Ah")
        print(f"   Cycles: {bms_data.cycles}")
        print(f"   Temp Avg: {bms_data.temp_avg:.1f}°C")
        print(f"   Balancing: {bms_data.balancing_active} (Cells: {bms_data.balancing_cells})")
        print(f"   Charge/Discharge: {bms_data.charge_enabled}/{bms_data.discharge_enabled}")
    else:
        print("   ✗ Parse fehlgeschlagen!")

    print("\n2. Test Commands...")
    basic_cmd = parser.get_request_basic_info_command()
    print(f"   Basic Info CMD: {basic_cmd.hex()}")

    cells_cmd = parser.get_request_cell_voltages_command()
    print(f"   Cell Voltages CMD: {cells_cmd.hex()}")

    print("\n" + "="*60)


if __name__ == "__main__":
    test_jbd_parser()
