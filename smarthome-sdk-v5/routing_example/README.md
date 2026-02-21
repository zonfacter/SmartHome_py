# Routing Example Plugin

Demonstriert die Nutzung des **Universal Data Routers** (v4.6.0)

## Was macht dieses Plugin?

Dieses Plugin ist ein vollständiges Beispiel, das alle wichtigen Features des v4.6.0 Routing-Systems zeigt:

### 1. **Daten Publizieren** (`route_data`)
```python
# Einfaches Publish
self.publish("sensors/temperature", 23.5)

# Mit Metadaten
self.app.data_gateway.route_data(
    source_id="MyPlugin",
    tag="sensors/humidity",
    value=65.0,
    metadata={'quality': 'good', 'unit': '%RH'}
)
```

### 2. **Daten Subscriben** (Pattern-Matching)
```python
# Subscribe auf spezifischen Datenpunkt
gateway.subscribe("plc_001.MAIN.bAlarm", callback_function)

# Subscribe mit Wildcard
gateway.subscribe("plc_001.*", callback_function)

# Subscribe auf Bluetooth-Daten
gateway.subscribe("bt.bms_001.voltage", callback_function)
```

### 3. **Verschiedene Datentypen**
- Boolean: `True/False`
- Integer: `42`
- Float: `23.5`
- String: `"Hello"`
- Arrays: `[20.1, 21.3, 19.8]`

### 4. **Spam-Protection**
Das Plugin zeigt wie der automatische Spam-Schutz funktioniert:
- Max 500 Pakete pro Sekunde (konfigurierbar)
- Automatische Suspension bei Überschreitung
- Manuelle Reaktivierung durch Admin

---

## Installation

1. Kopiere den `routing_example` Ordner nach `modules/plugins/`
2. Konfiguriere in `config/plugins.json`:
```json
{
  "routing_example": {
    "enabled": true,
    "publish_interval": 5.0,
    "subscribe_patterns": [
      "plc_001.MAIN.bAlarm",
      "bt.bms_001.*"
    ]
  }
}
```

---

## Nutzung

### Als eigenständiger Test
```bash
python main.py
```

Führt Test-Suite aus:
- Spam-Protection Test
- Routing-Pattern Demonstration

### Im SmartHome Edge OS
Das Plugin wird automatisch geladen und:
1. Publiziert simulierte Sensor-Daten alle 5 Sekunden
2. Reagiert auf PLC-Alarme
3. Überwacht BMS-Spannungen
4. Loggt alle empfangenen Daten

---

## Beispiel-Output

```
🚀 Routing Example Plugin startet...
  ✅ Subscriptions registriert

📤 Publiziert: Temperatur=22.3°C, Feuchtigkeit=52.1%, Counter=1
🔋 BMS Spannung: 52.3V (RSSI: -45dBm)
🌡️  PLC Temperatur empfangen: MAIN.fTemperature = 21.5

🚨 ALARM empfangen von plc_001 @ 1735926000.123
📤 Publiziert: alarms/acknowledged = True
✅ Alarm zurückgesetzt @ 1735926010.456
```

---

## Architektur

### Datenfluss

```
Plugin (publish)
       ↓
route_data("MyPlugin", "sensors/temp", 23.5)
       ↓
DataGateway (Normalisierung)
       ↓
Spam-Check → Routing-Engine → Subscribers
       ↓              ↓              ↓
  [BLOCK]      [Match Routes]   [Callbacks]
                     ↓
            ┌────────┴─────────┐
            ↓                  ↓
      Targets (PLC, MQTT)   Unified Data Space
            ↓                  ↓
      PLC-Variable       Telemetrie-Cache
      MQTT-Publish            ↓
      Log-System           Widgets (WebSocket)
```

---

## Routing-Regeln (routing.json)

Beispiel-Konfiguration um Plugin-Daten weiterzuleiten:

```json
{
  "routes": [
    {
      "id": "plugin_to_plc",
      "from": "RoutingExamplePlugin.sensors/temperature",
      "to": "plc_001.MAIN.fTemperature",
      "enabled": true
    },
    {
      "id": "plugin_to_widgets",
      "from": "RoutingExamplePlugin.*",
      "to": ["widgets", "log.system"],
      "enabled": true
    },
    {
      "id": "bms_mirror_to_plc",
      "from": "bt.bms_simulator.*",
      "to": "plc_001.MAIN.Battery.*",
      "enabled": true
    }
  ]
}
```

---

## Callbacks im Detail

### 1. Alarm-Callback
```python
def on_alarm_received(self, datapoint: dict):
    """Reagiert auf PLC-Alarme"""
    if datapoint['value']:
        # Alarm aktiv
        self.publish("alarms/acknowledged", True)
    else:
        # Alarm zurückgesetzt
        self.log.info("Alarm cleared")
```

### 2. Wildcard-Callback
```python
def on_plc_data_received(self, datapoint: dict):
    """Empfängt ALLE PLC-Daten"""
    tag = datapoint['tag']
    value = datapoint['value']

    if "temperature" in tag.lower():
        # Filtere nur Temperatur-Werte
        self.log.info(f"Temp: {value}")
```

### 3. Hardware-Callback
```python
def on_bms_voltage_received(self, datapoint: dict):
    """Reagiert auf BMS-Hardware-Events"""
    voltage = datapoint['value']

    if voltage < 48.0:
        # Kritische Spannung!
        self.publish("alarms/low_voltage", True)
```

---

## Erweiterte Features

### Metadaten nutzen
```python
# Publiziere mit zusätzlichen Informationen
metadata = {
    'quality': 'good',          # good/bad/uncertain
    'unit': '°C',                # Einheit
    'sensor_id': 'DHT22_01',     # Hardware-ID
    'timestamp': time.time(),    # Optional: eigener Timestamp
    'rssi': -45                  # z.B. für Bluetooth-Geräte
}

self.app.data_gateway.route_data(
    source_id="MyPlugin",
    tag="sensors/temperature",
    value=23.5,
    metadata=metadata
)
```

### Subscribe mit Cleanup
```python
def initialize(self):
    # Registriere Callback
    self.app.data_gateway.subscribe(
        "plc_001.MAIN.*",
        self.my_callback
    )

def stop(self):
    # Cleanup: Entferne Callback
    self.app.data_gateway.unsubscribe(
        "plc_001.MAIN.*",
        self.my_callback
    )
```

---

## Fehlerbehandlung

### Spam-Protection
```python
success = self.publish("tag", value)

if not success:
    # Plugin wurde wegen Spam gesperrt
    self.log.warning("Spam-Protection aktiv!")
    self.stop()
```

### Routing-Fehler
Das DataGateway fängt alle Routing-Fehler ab:
```python
try:
    self._execute_route(route, datapoint)
except Exception as e:
    # Wird automatisch geloggt
    # Plugin läuft weiter
```

---

## Best Practices

### ✅ DO:
- Nutze `self.publish()` für normale Fälle
- Nutze `route_data()` direkt nur für erweiterte Kontrolle (Metadaten)
- Implementiere `time.sleep()` in execute()-Loop für CPU-Schonung
- Gib sinnvolle `source_id` an (z.B. Plugin-Name, Hardware-ID)
- Nutze hierarchische Tags (`sensors/temp`, nicht `temp`)

### ❌ DON'T:
- Sende nicht mehr als 500 pps
- Blockiere nicht in Callbacks
- Nutze keine Endlos-Schleifen ohne sleep()
- Vergiss nicht Subscriptions zu cleanup

---

## Testing

### Unit-Tests
```bash
python main.py
```

Führt aus:
1. **Spam-Protection Test**: Testet automatische Limitierung
2. **Routing-Pattern Test**: Zeigt verschiedene Routing-Szenarien

### Integration-Test
1. Starte SmartHome Edge OS
2. Aktiviere Plugin in Admin-UI
3. Prüfe Logs: `tail -f logs/system.log`
4. Prüfe Admin-UI: Routing-Statistiken

---

## Troubleshooting

### Problem: Plugin sendet keine Daten
```python
# Check 1: Gateway verfügbar?
if not hasattr(self.app, 'data_gateway'):
    self.log.error("Gateway nicht verfügbar!")

# Check 2: Spam-Protection?
stats = self.app.data_gateway.source_stats[self.__class__.__name__]
if stats['status'] == 'suspended_spam':
    self.log.error("Spam-Protection aktiv!")
```

### Problem: Callbacks werden nicht aufgerufen
```python
# Prüfe Pattern-Matching
pattern = "plc_001.MAIN.bAlarm"
datapoint_path = "plc_001.MAIN.bAlarm"

# Exakte Übereinstimmung?
if pattern == datapoint_path:
    # Sollte funktionieren
```

---

## Referenz-Dokumentation

### Datapoint-Struktur
```python
{
    'source_id': str,      # Quelle (z.B. "plc_001", "MyPlugin")
    'tag': str,            # Datenpunkt-Tag
    'value': any,          # Wert (JSON-serializable)
    'timestamp': float,    # Unix-Timestamp
    'quality': str,        # 'good', 'bad', 'uncertain'
    'metadata': dict       # Zusätzliche Daten
}
```

### Pattern-Syntax
- `*` - Matched alles
- `plc_001.*` - Alle Tags von plc_001
- `plc_001.MAIN.bAlarm` - Exakter Match
- `bt.bms_001.*` - Alle BMS-Daten

---

## Support

- **Dokumentation**: `smarthome-sdk-v5/README.md`
- **API-Referenz**: `modules/gateway/data_gateway.py`
- **Weitere Beispiele**: `smarthome-sdk-v5/example_plugin/`

---

**Version**: 1.0.0
**Autor**: TwinCAT Team
**Lizenz**: MIT
**Min. OS Version**: 4.6.0
