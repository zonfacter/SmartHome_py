# Multi-PLC Example

Demonstriert wie man **mehrere PLCs gleichzeitig** über den Connection Manager nutzt.

## Was macht dieses Beispiel?

Zeigt den parallelen Zugriff auf mehrere TwinCAT/ADS PLCs:
- Mehrere PLC-Instanzen verbinden
- Daten von allen PLCs gleichzeitig lesen
- Cross-PLC Logik implementieren
- Aggregierte Statistik über alle PLCs
- Zentrale Alarmsammlung

## Use Cases

- **Multi-Standort Steuerung** (Haus + Garage + Keller)
- **Verteilte Systeme** (mehrere SPS-Steuerungen)
- **Redundante Architekturen** (Haupt-PLC + Backup-PLC)
- **Aggregierte Überwachung** (Zentrale Alarmliste)
- **Cross-PLC Kommunikation** (PLC A steuert PLC B)

---

## Voraussetzungen

### 1. Connection Manager konfigurieren

In `config/connections.json`:

```json
{
  "connections": {
    "plc_main": {
      "type": "plc",
      "name": "Haupt-PLC (Gebäude)",
      "enabled": true,
      "config": {
        "ams_net_id": "192.168.2.162.1.1",
        "ams_port": 851,
        "ip_address": "192.168.2.162",
        "timeout": 5000,
        "auto_reconnect": true,
        "health_check_variable": "MAIN.bSystemReady"
      }
    },
    "plc_garage": {
      "type": "plc",
      "name": "Garagen-PLC",
      "enabled": true,
      "config": {
        "ams_net_id": "192.168.2.163.1.1",
        "ams_port": 851,
        "ip_address": "192.168.2.163",
        "timeout": 5000,
        "auto_reconnect": true
      }
    },
    "plc_energy": {
      "type": "plc",
      "name": "Energiemanagement-PLC",
      "enabled": false,
      "config": {
        "ams_net_id": "192.168.2.164.1.1",
        "ams_port": 851,
        "ip_address": "192.168.2.164",
        "timeout": 5000,
        "auto_reconnect": true
      }
    }
  },
  "settings": {
    "health_check_interval": 30,
    "reconnect_max_attempts": 10
  }
}
```

### 2. PLC-Variablen strukturieren

Jede PLC sollte ähnliche Basisvariablen haben:

```iecst
PROGRAM MAIN
VAR
    // Status
    bSystemReady    : BOOL := FALSE;
    nOperationMode  : INT := 0;  // 0=Off, 1=Run, 2=Standby

    // Alarme
    bAlarm          : BOOL := FALSE;
    nAlarmCode      : INT := 0;
    sAlarmText      : STRING(255) := '';

    // Energie
    bEnergyAlarm    : BOOL := FALSE;

    // Notfall
    bEmergencyStop  : BOOL := FALSE;

    // Messwerte
    nTemperature    : INT := 200;  // 20.0°C
    nHumidity       : INT := 450;  // 45.0%
END_VAR
```

---

## Basis-Verwendung

### 1. PLC-Verbindungen finden

```python
# Hole Connection Manager
conn_mgr = self.app.module_manager.get_module('connection_manager')

# Finde alle PLC-Verbindungen
all_connections = conn_mgr.get_all_connections()

for conn_id, connection in all_connections.items():
    if connection.__class__.__name__ == 'PLCConnection':
        print(f"PLC gefunden: {conn_id}")
        self.active_plcs[conn_id] = connection
```

### 2. Von spezifischer PLC lesen

```python
# Hole bestimmte PLC
plc_main = conn_mgr.get_connection("plc_main")

if plc_main and plc_main.is_connected():
    # Lese Variable
    temperature = plc_main.read_by_name("MAIN.nTemperature")

    # Mit Type-Hint
    alarm = plc_main.read_by_name("MAIN.bAlarm", pyads.PLCTYPE_BOOL)

    # Ohne Cache (immer fresh)
    fresh_value = plc_main.read_by_name("MAIN.nTemperature", use_cache=False)
```

### 3. In spezifische PLC schreiben

```python
plc_garage = conn_mgr.get_connection("plc_garage")

if plc_garage and plc_garage.is_connected():
    # Setze Operation-Mode
    plc_garage.write_by_name("MAIN.nOperationMode", 2)  # Standby

    # Acknowledge Alarm
    plc_garage.write_by_name("MAIN.bAlarm", False)
```

### 4. Alle PLCs überwachen

```python
def monitor_all_plcs(self):
    for conn_id, plc_conn in self.active_plcs.items():
        if not plc_conn.is_connected():
            print(f"{conn_id} - OFFLINE")
            continue

        # Lese Standard-Variablen
        ready = plc_conn.read_by_name("MAIN.bSystemReady")
        mode = plc_conn.read_by_name("MAIN.nOperationMode")
        temp = plc_conn.read_by_name("MAIN.nTemperature")

        print(f"{conn_id} - Ready: {ready}, Mode: {mode}, Temp: {temp/10.0}°C")
```

---

## Erweiterte Funktionen

### 1. Cross-PLC Logik

```python
def cross_plc_logic(self):
    """
    Szenario: Wenn Haupt-PLC Energie-Alarm hat,
    dann schalte Garagen-PLC in Standby
    """
    plc_main = self.active_plcs.get('plc_main')
    plc_garage = self.active_plcs.get('plc_garage')

    if not plc_main or not plc_garage:
        return

    # Lese Energy-Alarm
    energy_alarm = plc_main.read_by_name("MAIN.bEnergyAlarm")

    if energy_alarm:
        # Setze Garage in Standby
        current_mode = plc_garage.read_by_name("MAIN.nOperationMode")

        if current_mode != 2:  # 2 = Standby
            print("Energy-Alarm! Setze Garage in Standby...")
            plc_garage.write_by_name("MAIN.nOperationMode", 2)

            # Publiziere Event
            self.publish("system/cross_plc_action", {
                'action': 'standby_garage',
                'reason': 'energy_alarm'
            })
```

### 2. Zentrale Alarmsammlung

```python
def collect_alarms(self):
    """Sammelt Alarme von allen PLCs"""
    alarm_list = []

    for conn_id, plc_conn in self.active_plcs.items():
        if not plc_conn.is_connected():
            continue

        # Lese Alarm-Status
        alarm_active = plc_conn.read_by_name("MAIN.bAlarm")

        if alarm_active:
            # Hole Details
            alarm_code = plc_conn.read_by_name("MAIN.nAlarmCode")
            alarm_text = plc_conn.read_by_name("MAIN.sAlarmText")

            alarm_list.append({
                'plc': conn_id,
                'code': alarm_code,
                'text': alarm_text,
                'timestamp': time.time()
            })

    # Publiziere Alarm-Liste
    self.publish("alarms/list", alarm_list)

    return alarm_list
```

### 3. Aggregierte Statistik

```python
def get_aggregate_stats(self):
    """Liefert aggregierte Statistik über alle PLCs"""
    stats = {
        'total_plcs': len(self.active_plcs),
        'connected': 0,
        'disconnected': 0,
        'total_packets_sent': 0,
        'total_packets_received': 0,
        'total_errors': 0
    }

    for conn_id, plc_conn in self.active_plcs.items():
        plc_status = plc_conn.get_status()

        if plc_status['status'] == 'connected':
            stats['connected'] += 1
        else:
            stats['disconnected'] += 1

        # Aggregiere Statistik
        stats['total_packets_sent'] += plc_status['stats']['packets_sent']
        stats['total_packets_received'] += plc_status['stats']['packets_received']
        stats['total_errors'] += plc_status['stats']['errors']

    return stats
```

### 4. PLC-Status Matrix

```python
def print_plc_matrix(self):
    """Zeigt Status-Matrix aller PLCs"""
    print("\n" + "="*80)
    print("  PLC-STATUS MATRIX")
    print("="*80)
    print(f"  {'PLC':<20} {'Status':<15} {'Temp':<10} {'Alarme':<10} {'Packets':<10}")
    print("-"*80)

    for conn_id, plc_conn in self.active_plcs.items():
        status = plc_conn.get_status()

        # Lese Messwerte
        temp = "-"
        alarms = "-"

        if status['status'] == 'connected':
            try:
                temp_raw = plc_conn.read_by_name("MAIN.nTemperature")
                temp = f"{temp_raw/10.0:.1f}°C"

                alarm_active = plc_conn.read_by_name("MAIN.bAlarm")
                alarms = "🚨 AKTIV" if alarm_active else "✅ OK"
            except:
                pass

        packets = status['stats']['packets_received']

        print(f"  {conn_id:<20} {status['status']:<15} {temp:<10} {alarms:<10} {packets:<10}")

    print("="*80 + "\n")
```

---

## DataGateway Integration

### 1. Auto-Routing

Jede PLC routet automatisch Daten zum DataGateway:

```python
# In PLCConnection.read_by_name():
value = self.plc.read_by_name(symbol)

# Auto-Route zu DataGateway
self._route_to_gateway(symbol, value)
```

### 2. Subscribe auf PLC-Daten

```python
def initialize(self):
    # Subscribe auf alle PLC-Daten
    self.data_gateway.subscribe("plc_*", self.on_plc_data_received)

    # Oder spezifisch
    self.data_gateway.subscribe("plc_main.MAIN.bAlarm", self.on_main_alarm)
    self.data_gateway.subscribe("plc_garage.*", self.on_garage_data)

def on_plc_data_received(self, datapoint: Dict):
    """Callback für PLC-Daten"""
    source = datapoint['source_id']  # z.B. "plc_main"
    tag = datapoint['tag']            # z.B. "MAIN.temperature"
    value = datapoint['value']

    print(f"PLC-Daten: {source}.{tag} = {value}")
```

### 3. Routing zwischen PLCs

Via `config/routing.json`:

```json
{
  "routes": [
    {
      "id": "plc_main_to_garage",
      "description": "Route Haupt-Status zu Garage",
      "source": "plc_main",
      "source_pattern": "MAIN.bSystemReady",
      "targets": [
        {
          "type": "plc",
          "connection_id": "plc_garage",
          "mapping": {
            "MAIN.bSystemReady": "MAIN.bMainSystemReady"
          }
        }
      ],
      "enabled": true
    }
  ]
}
```

---

## Error-Handling

### 1. Connection Loss Detection

```python
def monitor_plc_health(self):
    """Überwacht PLC-Verbindungen"""
    for conn_id, plc_conn in self.active_plcs.items():
        if not plc_conn.is_connected():
            print(f"⚠️  {conn_id} - Verbindung verloren!")

            # Prüfe Reconnect-Attempts
            status = plc_conn.get_status()
            attempts = status['reconnect_attempts']

            if attempts > 5:
                print(f"⚠️  {conn_id} - Viele Reconnect-Versuche: {attempts}")
                # Optional: Benachrichtigung senden
```

### 2. Graceful Degradation

```python
def read_with_fallback(self, primary_plc: str, backup_plc: str, symbol: str):
    """Liest von Primary, fallback zu Backup bei Fehler"""
    # Versuche Primary
    plc = self.active_plcs.get(primary_plc)
    if plc and plc.is_connected():
        try:
            return plc.read_by_name(symbol)
        except:
            pass

    # Fallback zu Backup
    plc = self.active_plcs.get(backup_plc)
    if plc and plc.is_connected():
        try:
            return plc.read_by_name(symbol)
        except:
            pass

    return None
```

### 3. Timeout-Handling

```python
def read_with_timeout(self, conn_id: str, symbol: str, timeout: float = 2.0):
    """Liest mit Custom-Timeout"""
    import threading

    result = [None]
    error = [None]

    def read_thread():
        try:
            plc = self.active_plcs.get(conn_id)
            if plc and plc.is_connected():
                result[0] = plc.read_by_name(symbol, use_cache=False)
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=read_thread)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        print(f"⚠️  Timeout beim Lesen von {conn_id}.{symbol}")
        return None

    if error[0]:
        print(f"⚠️  Fehler: {error[0]}")
        return None

    return result[0]
```

---

## Performance-Tipps

### 1. Batch-Reads

```python
def read_multiple(self, conn_id: str, symbols: List[str]):
    """Liest mehrere Variablen auf einmal"""
    plc = self.active_plcs.get(conn_id)
    if not plc or not plc.is_connected():
        return {}

    results = {}
    for symbol in symbols:
        try:
            results[symbol] = plc.read_by_name(symbol, use_cache=True)
        except Exception as e:
            results[symbol] = None

    return results
```

### 2. Cache-Strategie

```python
# Schnelle Werte mit Cache
temperature = plc.read_by_name("MAIN.nTemperature", use_cache=True)

# Kritische Werte ohne Cache
alarm = plc.read_by_name("MAIN.bAlarm", use_cache=False)

# Cache-Timeout anpassen (in plc_connection.py)
plc.cache_timeout = 0.5  # 500ms statt 100ms
```

### 3. Paralleles Monitoring

```python
import threading

def monitor_plc_async(self, conn_id: str):
    """Monitort PLC asynchron"""
    thread = threading.Thread(
        target=self._monitor_single_plc,
        args=(conn_id,)
    )
    thread.daemon = True
    thread.start()

def monitor_all_async(self):
    """Monitort alle PLCs parallel"""
    for conn_id in self.active_plcs.keys():
        self.monitor_plc_async(conn_id)
```

---

## Testing

### Unit-Test

```bash
cd smarthome-sdk-v5/multi_plc_example
python main.py
```

**Voraussetzung**: Mindestens eine PLC muss in `config/connections.json` konfiguriert sein.

### Integration-Test

1. Starte SmartHome Edge OS
2. Aktiviere Multi-PLC Plugin
3. Öffne Admin-UI → Connections
4. Prüfe ob alle PLCs verbunden sind
5. Öffne Logs → Prüfe auf Fehler
6. Teste Cross-PLC Logik (z.B. Energie-Alarm auslösen)

---

## Debugging

### Connection-Status prüfen

```python
status = plc_conn.get_status()
print(f"Status: {status}")

# Returns:
{
    'connection_id': 'plc_main',
    'type': 'PLCConnection',
    'status': 'connected',
    'connected_at': 1735926000.123,
    'last_error': None,
    'reconnect_attempts': 0,
    'stats': {
        'packets_sent': 42,
        'packets_received': 127,
        'bytes_sent': 336,
        'bytes_received': 1016,
        'errors': 0,
        'last_activity': 1735926100.456
    }
}
```

### PLC-Symbole auflisten

```python
plc = conn_mgr.get_connection("plc_main")
if plc and plc.is_connected():
    symbols = plc.get_all_symbols()

    for symbol in symbols:
        print(f"  {symbol.name} ({symbol.symbol_type})")
```

### Device-Info

```python
device_info = plc.read_device_info()
if device_info:
    print(f"Device: {device_info.name}")
    print(f"Version: {device_info.version}")
```

---

## Best Practices

### ✅ DO:

- Prüfe **immer** `is_connected()` vor Read/Write
- Nutze **Cache** für häufig gelesene Werte
- Implementiere **Fallback-Logik** bei Connection-Loss
- **Aggregiere** Daten von mehreren PLCs
- Nutze **DataGateway Routing** für PLC-zu-PLC Kommunikation
- **Logge** wichtige Cross-PLC Events

### ❌ DON'T:

- Blockiere **nicht** mit synchronen Reads in Loops
- Lese **nicht** ohne Cache in High-Frequency Loops
- Ignoriere **nicht** Connection-Errors
- Schreibe **nicht** ohne Fehlerbehandlung
- Vergiss **nicht** Timeout-Handling

---

## Real-World Beispiel: Smart Home

### Szenario

**3 PLCs:**
- `plc_main` - Gebäudesteuerung (Heizung, Licht, Jalousien)
- `plc_garage` - Garagen-Steuerung (Tor, Licht, Wallbox)
- `plc_energy` - Energiemanagement (Solar, Batterie, Netz)

### Implementierung

```python
def smart_home_logic(self):
    """Intelligente Energie-Verteilung"""

    # 1. Hole PV-Leistung
    plc_energy = self.active_plcs['plc_energy']
    pv_power = plc_energy.read_by_name("MAIN.rPV_Power")  # kW

    # 2. Hole Wallbox-Status
    plc_garage = self.active_plcs['plc_garage']
    wallbox_charging = plc_garage.read_by_name("MAIN.bWallbox_Charging")
    wallbox_power = plc_garage.read_by_name("MAIN.rWallbox_Power")  # kW

    # 3. Hole Heizungs-Status
    plc_main = self.active_plcs['plc_main']
    heating_power = plc_main.read_by_name("MAIN.rHeating_Power")  # kW

    # 4. Berechne verfügbare PV-Leistung
    available_pv = pv_power - wallbox_power - heating_power

    # 5. Intelligente Steuerung
    if available_pv < 0:
        # Zu wenig PV → Reduziere Wallbox
        if wallbox_charging:
            print("⚡ PV zu gering → Reduziere Wallbox auf Minimum")
            plc_garage.write_by_name("MAIN.rWallbox_PowerLimit", 1.4)  # 1.4kW (6A)

    elif available_pv > 5.0:
        # Viel PV → Maximiere Wallbox
        if wallbox_charging:
            print("☀️ Viel PV → Maximiere Wallbox")
            plc_garage.write_by_name("MAIN.rWallbox_PowerLimit", 11.0)  # 11kW (16A 3-phase)
```

---

## Support

- **Connection Manager**: `modules/core/connection_manager.py`
- **PLC Connection**: `modules/core/plc_connection.py`
- **DataGateway**: `modules/gateway/data_gateway.py`
- **Weitere Beispiele**: `smarthome-sdk-v5/*/`

---

**Version**: 1.0.0
**Autor**: TwinCAT Team
**Lizenz**: MIT
**Min. OS Version**: 4.6.0
