# BMS Monitor Example

Demonstriert **BMS-Integration über Bluetooth** (Battery Management System).

## Was macht dieses Beispiel?

Zeigt wie man BMS-Daten über Bluetooth Low Energy ausliest:
- Automatische BMS-Verbindung (JBD/Xiaoxiang Protokoll)
- Periodisches Polling von BMS-Daten
- Alarm-Überwachung (Spannung, Temperatur)
- DataGateway Integration
- Multi-BMS Support (mehrere Batterien parallel)

## Use Cases

- **Wohnmobil/Camper**: Lithium-Batterieüberwachung
- **Solar-Speicher**: Heimspeicher-Monitoring
- **E-Mobility**: E-Bike/E-Scooter Batterie-Tracking
- **Energiespeicher**: Stationäre Batteriesysteme
- **Off-Grid Systeme**: Insel-Anlagen Überwachung

---

## Voraussetzungen

### 1. Hardware

**Unterstützte BMS:**
- JBD/Xiaoxiang BMS (Jiabaida)
- Overkill Solar BMS
- Daly BMS (geplant)
- JK BMS (geplant)

**Bluetooth:**
- BLE-fähiger Adapter (USB-Dongle oder integriert)
- Windows: Bluetooth 4.0+
- Linux: BlueZ 5.x

### 2. Connection Manager Konfiguration

In `config/connections.json`:

```json
{
  "connections": {
    "bms_main": {
      "type": "bluetooth",
      "name": "Hauptbatterie BMS",
      "enabled": true,
      "config": {
        "address": "AA:BB:CC:DD:EE:FF",
        "name": "xiaoxiang",
        "timeout": 10.0,
        "scan_timeout": 5.0,
        "auto_reconnect": true,
        "notify_characteristics": []
      }
    },
    "bms_backup": {
      "type": "bluetooth",
      "name": "Backup-Batterie BMS",
      "enabled": false,
      "config": {
        "address": "11:22:33:44:55:66",
        "timeout": 10.0,
        "auto_reconnect": true
      }
    }
  }
}
```

**BLE-Adresse finden:**

```bash
# Linux
sudo hcitool lescan

# Windows (PowerShell)
Get-PnpDevice -Class Bluetooth

# Python (mit bleak)
python -m bleak.discover
```

### 3. Python Packages

```bash
pip install bleak
```

---

## Basis-Verwendung

### 1. BMS-Verbindung

```python
# Hole Connection Manager
conn_mgr = self.app.module_manager.get_module('connection_manager')

# Finde BMS-Verbindungen
all_connections = conn_mgr.get_all_connections()

for conn_id, connection in all_connections.items():
    if connection.__class__.__name__ == 'BluetoothConnection':
        if 'bms' in conn_id.lower():
            self.bms_connections[conn_id] = connection
```

### 2. BMS-Parser initialisieren

```python
from modules.bluetooth.bms_parser import bms_parser_registry

# Hole Parser (JBD/Xiaoxiang)
parser = bms_parser_registry.get_parser("JBD", connection_id)

# Request Basic Info
cmd = parser.get_request_basic_info_command()

# Schreibe Command
bt_conn.write_characteristic(parser.get_write_characteristic_uuid(), cmd)

# Lese Response
response = bt_conn.read_characteristic(parser.get_read_characteristic_uuid())

# Parse
bms_data = parser.parse(response, "basic")
```

### 3. BMS-Daten auslesen

```python
def poll_bms(self, connection_id: str):
    bt_conn = self.bms_connections[connection_id]
    parser = self.bms_parsers[connection_id]

    # 1. Request Basic Info
    cmd_basic = parser.get_request_basic_info_command()
    bt_conn.write_characteristic(parser.get_write_characteristic_uuid(), cmd_basic)

    time.sleep(0.5)

    response = bt_conn.read_characteristic(parser.get_read_characteristic_uuid())
    bms_data = parser.parse(response, "basic")

    # 2. Request Cell Voltages
    cmd_cells = parser.get_request_cell_voltages_command()
    bt_conn.write_characteristic(parser.get_write_characteristic_uuid(), cmd_cells)

    time.sleep(0.5)

    response_cells = bt_conn.read_characteristic(parser.get_read_characteristic_uuid())
    bms_data = parser.parse(response_cells, "cells")

    return bms_data
```

### 4. BMS-Daten verarbeiten

```python
print(f"Voltage: {bms_data.total_voltage:.2f}V")
print(f"Current: {bms_data.current:.2f}A")
print(f"Power: {bms_data.power:.0f}W")
print(f"SoC: {bms_data.soc}%")
print(f"Temp: {bms_data.temp_avg:.1f}°C")

# Cell Voltages
for i, voltage in enumerate(bms_data.cell_voltages):
    print(f"Cell {i+1}: {voltage:.3f}V")

# Protection Flags
for flag, active in bms_data.protection_flags.items():
    if active:
        print(f"⚠️  Protection: {flag}")
```

---

## Erweiterte Funktionen

### 1. Alarm-Überwachung

```python
def check_alarms(self, bms_data):
    alarms = []

    # Cell-Voltage Alarms
    for i, voltage in enumerate(bms_data.cell_voltages):
        if voltage < 3.0:  # Undervoltage
            alarms.append({
                'type': 'cell_undervoltage',
                'cell': i,
                'voltage': voltage
            })
        elif voltage > 3.65:  # Overvoltage
            alarms.append({
                'type': 'cell_overvoltage',
                'cell': i,
                'voltage': voltage
            })

    # Temperature Alarms
    if bms_data.temp_max > 45.0:
        alarms.append({
            'type': 'over_temperature',
            'temperature': bms_data.temp_max
        })

    return alarms
```

### 2. DataGateway Integration

```python
# Route BMS-Daten zu DataGateway
data_dict = bms_data.to_dict()

for key, value in data_dict.items():
    tag = f"bms.{key}"
    self.data_gateway.route_data(
        source_id=self.__class__.__name__,
        tag=tag,
        value=value
    )
```

### 3. Multi-BMS Aggregation

```python
def get_total_capacity(self):
    """Berechnet Gesamt-Kapazität aller BMS"""
    total_capacity = 0.0
    total_soc_weighted = 0.0

    for conn_id, parser in self.bms_parsers.items():
        if parser.last_data:
            capacity = parser.last_data.capacity_full
            soc = parser.last_data.soc

            total_capacity += capacity
            total_soc_weighted += capacity * soc

    avg_soc = total_soc_weighted / total_capacity if total_capacity > 0 else 0

    return {
        'total_capacity_ah': total_capacity,
        'average_soc': avg_soc
    }
```

---

## BMS-Daten Struktur

### BMSData Objekt

```python
@dataclass
class BMSData:
    # Basic
    total_voltage: float      # Gesamt-Spannung (V)
    current: float            # Strom (A, positiv=Laden, negativ=Entladen)
    power: float              # Leistung (W)

    # State of Charge
    soc: int                  # State of Charge (%)
    soh: int                  # State of Health (%)

    # Capacity
    capacity_remaining: float # Verbleibend (Ah)
    capacity_full: float      # Voll-Kapazität (Ah)

    # Temperatures
    temperatures: List[float] # Temperaturen (°C)
    temp_avg: float           # Durchschnitt (°C)
    temp_min: float           # Minimum (°C)
    temp_max: float           # Maximum (°C)

    # Cell Voltages
    cell_voltages: List[float] # Zellspannungen (V)
    cell_min: float            # Niedrigste Zelle (V)
    cell_max: float            # Höchste Zelle (V)
    cell_delta: float          # Differenz (V)

    # Protection
    protection_flags: Dict[str, bool]

    # Charge/Discharge
    charge_enabled: bool
    discharge_enabled: bool

    # Balancing
    balancing_active: bool
    balancing_cells: List[int]  # Indices

    # Cycles
    cycles: int
```

---

## JBD/Xiaoxiang Protokoll

### Command Structure

```
[START] [CMD] [LEN] [DATA] [CHECKSUM_H] [CHECKSUM_L] [END]
 0xDD   0xA5  0x00   ...     XX          XX         0x77
```

### Commands

| Command | Code | Description |
|---------|------|-------------|
| Basic Info | 0x03 | Voltage, Current, SoC, Temp |
| Cell Voltages | 0x04 | Alle Zellspannungen |
| Device Name | 0x05 | Gerätename |

### Beispiel: Basic Info Request

```python
# Command: DD A5 03 00 FF FD 77
cmd = bytes([
    0xDD,        # Start
    0xA5,        # Read Command
    0x03,        # Basic Info
    0x00,        # Data Length
    0xFF, 0xFD,  # Checksum
    0x77         # End
])
```

---

## Debugging

### BLE-Verbindung testen

```python
import asyncio
from bleak import BleakClient

async def test_connection(address):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")

        # Liste Services
        for service in client.services:
            print(f"Service: {service.uuid}")

            for char in service.characteristics:
                print(f"  Char: {char.uuid} (Props: {char.properties})")

asyncio.run(test_connection("AA:BB:CC:DD:EE:FF"))
```

### Parser testen

```python
from modules.bluetooth.parsers.jbd_parser import JBDParser

parser = JBDParser("test")

# Test mit Beispiel-Response
response = bytes([...])  # Von echtem BMS
bms_data = parser.parse(response, "basic")

if bms_data:
    print(f"Parse OK: {bms_data.to_dict()}")
else:
    print(f"Parse Fehler! Errors: {parser.parse_errors}")
```

### Checksum Debugging

```python
# JBD Checksum prüfen
data = response[1:-3]  # Ohne Start/Checksum/End
checksum_expected = struct.unpack('>H', response[-3:-1])[0]
checksum_calculated = (0x10000 - sum(data)) & 0xFFFF

print(f"Expected: {checksum_expected:04X}")
print(f"Calculated: {checksum_calculated:04X}")
```

---

## Real-World Beispiel: Wohnmobil

### Szenario

**3 Batterien:**
- `bms_main` - Hauptbatterie (200Ah LiFePO4)
- `bms_starter` - Starterbatterie (100Ah AGM)
- `bms_solar` - Solar-Speicher (150Ah LiFePO4)

### Implementierung

```python
def monitor_camper_batteries(self):
    """Überwacht alle Camper-Batterien"""

    # Hole Daten von allen BMS
    bms_main = self.poll_bms("bms_main")
    bms_starter = self.poll_bms("bms_starter")
    bms_solar = self.poll_bms("bms_solar")

    # Berechne Gesamt-Kapazität
    total_ah = (
        bms_main.capacity_remaining +
        bms_starter.capacity_remaining +
        bms_solar.capacity_remaining
    )

    # Prüfe Ladezustand
    if bms_main.soc < 20:
        print("⚠️  Hauptbatterie kritisch!")
        # Schalte nicht-essentielle Verbraucher ab
        self.disable_non_essential_loads()

    # Solar-Optimierung
    if bms_solar.soc > 90 and bms_main.soc < 80:
        print("☀️ Solar voll → Lade Hauptbatterie")
        self.route_solar_to_main()

    # Publiziere Gesamt-Status
    self.publish("camper/battery_status", {
        'total_capacity_ah': total_ah,
        'main_soc': bms_main.soc,
        'solar_soc': bms_solar.soc,
        'starter_voltage': bms_starter.total_voltage
    })
```

---

## Testing

### Unit-Test

```bash
cd smarthome-sdk-v5/bms_example
python main.py
```

**Voraussetzung**: Mindestens ein BMS muss in `config/connections.json` konfiguriert sein.

### Integration-Test

1. Starte SmartHome Edge OS
2. Aktiviere BMS Plugin
3. Öffne Admin-UI → Connections
4. Prüfe ob BMS verbunden ist
5. Öffne Logs → Prüfe auf BMS-Daten
6. Teste Alarme (z.B. Zelle überladen)

---

## Best Practices

### ✅ DO:

- Nutze **Auto-Reconnect** für BLE-Verbindungen
- Implementiere **Timeout-Handling** (BLE kann langsam sein)
- **Validiere** BMS-Responses (Checksum!)
- **Logge** wichtige Events (Alarme, Verbindungsabbrüche)
- Nutze **Polling-Interval** > 5s (nicht zu häufig)

### ❌ DON'T:

- Blockiere **nicht** mit synchronen BLE-Calls ohne Timeout
- Schreibe **nicht** ohne Pause zwischen Commands (min 0.5s)
- Ignoriere **nicht** Protection-Flags
- Vergiss **nicht** Balancing-Status zu prüfen

---

## Troubleshooting

### BLE-Verbindung schlägt fehl

**Symptom**: `Connection timeout`

**Lösung**:
1. Prüfe ob BMS in Reichweite (< 10m)
2. Prüfe ob BMS nicht bereits mit anderer App verbunden
3. Erhöhe Timeout auf 15s
4. Scanne nach BLE-Geräten: `python -m bleak.discover`

### Parser-Fehler

**Symptom**: `Parse-Fehler` oder `Ungültige Response`

**Lösung**:
1. Prüfe Checksum-Berechnung
2. Logge Roh-Response: `print(response.hex())`
3. Vergleiche mit BMS-Protokoll-Dokumentation
4. Teste mit anderem BMS-Tool (z.B. Xiaoxiang App)

### Keine Daten empfangen

**Symptom**: `read_characteristic()` liefert None

**Lösung**:
1. Prüfe Write-Characteristic UUID
2. Prüfe ob Command korrekt
3. Erhöhe Wartezeit zwischen Write/Read auf 1s
4. Prüfe ob BMS Notifications unterstützt (statt Polling)

---

## Support

- **Bluetooth Manager**: `modules/bluetooth/bluetooth_manager.py`
- **BMS Parser**: `modules/bluetooth/bms_parser.py`
- **JBD Parser**: `modules/bluetooth/parsers/jbd_parser.py`
- **Connection Manager**: `modules/core/connection_manager.py`

---

**Version**: 1.0.0
**Autor**: TwinCAT Team
**Lizenz**: MIT
**Min. OS Version**: 5.0.0
