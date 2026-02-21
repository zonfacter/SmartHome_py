# 🚀 SmartHome Edge OS - Plugin SDK (v4.6.0)

Willkommen beim offiziellen SDK für das SmartHome Edge Gateway. Dieses SDK ermöglicht es dir, eigene Hardware (BMS, Sensoren, Wechselrichter) sicher und modular zu integrieren.

## 🎯 Was ist neu in v4.6.0?

### ⭐ Universal Data Router
Das Herzstück von v4.6.0 - alle Daten fließen zentral durch den Router:
- **Einheitliches Routing**: BMS → PLC, MQTT → Widgets, Plugin → Node-RED
- **Deklarative Konfiguration**: routing.json definiert alle Datenflüsse
- **Pattern-Matching**: Subscribe auf `plc_001.*` oder `bt.bms_001.voltage`
- **Spam-Protection**: Automatische Limitierung auf 500 pps pro Quelle

### ⭐ Multi-Connection Manager
Verwalte beliebig viele parallele Verbindungen:
- **Multi-Instance Support**: Mehrere PLCs, MQTT-Broker, Bluetooth-Geräte parallel
- **Health-Monitoring**: Automatische Health-Checks mit Auto-Reconnect
- **Unified Interface**: BaseConnection für alle Verbindungstypen
- **Event-System**: Callbacks für connected/disconnected/error Events

---

## 🛠 Schnellstart

### 1. Grundstruktur

```python
from base_plugin import BasePlugin
import time

class MeinPlugin(BasePlugin):
    def initialize(self):
        """Setup - wird einmal beim Start aufgerufen"""
        self.log.info("Plugin startet...")

    def execute(self):
        """Hauptschleife - läuft kontinuierlich"""
        while self.is_running:
            # Daten lesen/generieren
            wert = self.read_sensor()

            # Daten publizieren
            self.publish("sensors/temperature", wert)

            # CPU schonen
            time.sleep(5.0)
```

### 2. Daten Publizieren

```python
# Einfach
self.publish("sensors/temperature", 23.5)

# Mit Metadaten
self.app.data_gateway.route_data(
    source_id="MyPlugin",
    tag="sensors/humidity",
    value=65.0,
    metadata={'quality': 'good', 'unit': '%RH'}
)
```

### 3. Daten Subscriben

```python
def initialize(self):
    # Subscribe auf spezifischen Datenpunkt
    self.app.data_gateway.subscribe(
        "plc_001.MAIN.bAlarm",
        self.on_alarm
    )

    # Subscribe mit Wildcard
    self.app.data_gateway.subscribe(
        "bt.bms_001.*",
        self.on_bms_data
    )

def on_alarm(self, datapoint):
    """Callback bei Alarm"""
    if datapoint['value']:
        self.log.warning("ALARM!")
        self.publish("alarms/acknowledged", True)
```

---

## 🛡 Sicherheits-Features

### Spam-Protection (Automatisch)
- **Limit**: Max 500 Pakete/Sekunde pro Quelle (konfigurierbar)
- **Aktion**: Automatische Suspension bei Überschreitung
- **Recovery**: Manuelle Reaktivierung durch Admin

```python
# Wird automatisch geprüft
success = self.publish("tag", value)

if not success:
    # Plugin wurde gesperrt
    self.log.warning("Spam-Protection aktiv!")
```

### CPU-Throttling
- Nutze `time.sleep()` in execute()-Loop
- Empfohlen: Min 0.1s zwischen Operationen
- System überwacht CPU-Zeit automatisch

### Sentry Error-Tracking
- Alle Exceptions werden automatisch erfasst
- Sichtbar im Admin-Dashboard
- Stacktrace wird geloggt

```python
def execute(self):
    while self.is_running:
        try:
            # Deine Logik
            pass
        except Exception as e:
            # Wird automatisch von BasePlugin behandelt
            # Keine eigene Error-Behandlung nötig
```

---

## 📊 Instanz-Management (ioBroker-Style)

Über das **Admin-Interface** kann der Administrator:

### Ressourcen überwachen
- ✅ CPU-Last pro Plugin (%)
- ✅ RAM-Verbrauch (MB)
- ✅ Netzwerk-Traffic (pps)
- ✅ Uptime

### Lifecycle-Management
- 🟢 **Start**: Plugin starten
- 🟡 **Stop**: Soft-Stop (sauber beenden)
- 🔴 **Force Kill**: Hard-Kill bei Hängern
- 🔄 **Restart**: Neustart

### Dokumentation & Updates
- 📖 README.md direkt im Browser lesen
- 🔄 Online-Update prüfen (GitHub)
- 📦 Versionen vergleichen

---

## 🔄 Routing-System

### Wie funktioniert Routing?

```
Plugin.publish("sensors/temp", 23.5)
         ↓
   route_data()
         ↓
    Spam-Check ───[OK]──→ Normalisierung
         |                      ↓
      [BLOCK]            Routing-Engine
                                ↓
                    ┌───────────┴──────────┐
                    ↓                      ↓
              Match Routes            Subscribers
                    ↓                      ↓
            ┌───────┴────────┐       [Callbacks]
            ↓                ↓
    Targets (PLC, MQTT)   Unified Data Space
            ↓                      ↓
    PLC-Variable              Telemetrie
    MQTT-Publish                  ↓
    Log-System                Widgets
```

### routing.json Beispiel

```json
{
  "routes": [
    {
      "id": "plugin_to_plc",
      "from": "MyPlugin.sensors/temperature",
      "to": "plc_001.MAIN.fTemperature",
      "enabled": true
    },
    {
      "id": "all_to_widgets",
      "from": "*",
      "to": ["unified_data_space", "widgets"],
      "enabled": true
    }
  ]
}
```

### Pattern-Matching

| Pattern | Matched |
|---------|---------|
| `*` | Alle Datenpunkte |
| `plc_001.*` | Alle Tags von plc_001 |
| `plc_001.MAIN.bAlarm` | Exakter Match |
| `bt.bms_001.*` | Alle BMS-Daten |

---

## 📁 Beispiel-Plugins

### 1. `example_plugin/` - Basis-Beispiel
- Einfaches Sensor-Plugin
- Zeigt Grundstruktur
- Simulierte Daten

### 2. `routing_example/` - Routing & Subscriptions
- ⭐ **Vollständiges Routing-Beispiel**
- Publish mit Metadaten
- Subscribe auf verschiedene Quellen
- Spam-Protection Demo
- Callbacks & Pattern-Matching

**Start**: `cd routing_example && python main.py`

### 3. `connection_example/` - Custom Connection
- ⭐ **Eigene Verbindungstypen erstellen**
- BaseConnection Interface
- TCP-Socket Beispiel
- Health-Monitoring
- Integration mit Connection Manager

**Start**: `cd connection_example && python main.py`

### 4. `multi_plc_example/` - Multi-PLC Usage
- ⭐ **Mehrere PLCs parallel nutzen**
- Multi-Instance PLC-Zugriff
- Cross-PLC Datenrouting
- Aggregierte Alarm-Sammlung
- Smart Home Energie-Verteilungs-Beispiel

**Start**: `cd multi_plc_example && python main.py`

### 5. `bms_example/` - BMS Bluetooth Integration
- ⭐ **Battery Management System über Bluetooth**
- JBD/Xiaoxiang BMS Protokoll
- Alarm-Überwachung (Spannung, Temperatur)
- Multi-BMS Support (mehrere Batterien)
- Wohnmobil/Solar-Speicher Use-Case

**Start**: `cd bms_example && python main.py`

---

## 🔧 Erweiterte Features

### Metadaten nutzen

```python
metadata = {
    'quality': 'good',           # good/bad/uncertain
    'unit': '°C',                # Einheit
    'sensor_id': 'DHT22_01',     # Hardware-ID
    'timestamp': time.time(),    # Optional
    'rssi': -45                  # z.B. für BT-Geräte
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
    self.callback_ref = self.on_data
    self.app.data_gateway.subscribe(
        "plc_001.*",
        self.callback_ref
    )

def stop(self):
    self.app.data_gateway.unsubscribe(
        "plc_001.*",
        self.callback_ref
    )
    super().stop()
```

### Datapoint-Struktur

```python
{
    'source_id': str,      # "plc_001", "MyPlugin", "bt.bms_001"
    'tag': str,            # "MAIN.bAlarm", "sensors/temp"
    'value': any,          # Beliebiger Wert (JSON-serializable)
    'timestamp': float,    # Unix-Timestamp
    'quality': str,        # 'good', 'bad', 'uncertain'
    'metadata': dict       # Zusätzliche Daten
}
```

---

## ✅ Best Practices

### DO:
- ✅ Nutze `self.publish()` für normale Fälle
- ✅ Nutze `route_data()` nur für erweiterte Kontrolle
- ✅ Implementiere `time.sleep()` in execute()-Loop
- ✅ Hierarchische Tags: `sensors/temp`, nicht `temp`
- ✅ Cleanup in `stop()`: Unsubscribe, Ressourcen freigeben

### DON'T:
- ❌ Mehr als 500 pps senden
- ❌ Blockieren in Callbacks
- ❌ Endlos-Schleifen ohne sleep()
- ❌ Subscriptions ohne Cleanup

---

## 📦 Plugin-Struktur

```
my_plugin/
├── manifest.json       # Metadaten & Konfiguration
├── README.md           # Dokumentation (im Browser sichtbar)
├── main.py             # Plugin-Implementierung
└── __init__.py         # Exports
```

### manifest.json Template

```json
{
  "id": "my_plugin",
  "name": "Mein Plugin",
  "version": "1.0.0",
  "author": "Dein Name",
  "description": "Plugin-Beschreibung",
  "category": "Sensors",
  "icon": "activity",
  "min_os_version": "4.6.0",
  "dependencies": [],
  "config_schema": {
    "poll_interval": "number",
    "enabled": "boolean"
  }
}
```

---

## 🐛 Troubleshooting

### Plugin sendet keine Daten

```python
# Check 1: Gateway verfügbar?
if not hasattr(self.app, 'data_gateway'):
    self.log.error("Gateway nicht verfügbar!")
    return

# Check 2: Spam-Protection?
stats = self.app.data_gateway.source_stats[self.__class__.__name__]
if stats['status'] == 'suspended_spam':
    self.log.error("Spam-Protection aktiv - bitte Admin kontaktieren")
```

### Callbacks werden nicht aufgerufen

```python
# Prüfe Pattern
pattern = "plc_001.MAIN.bAlarm"
full_path = "plc_001.MAIN.bAlarm"

# Exakte Übereinstimmung?
assert pattern == full_path  # Sollte True sein

# Wildcard-Test
pattern = "plc_001.*"
assert full_path.startswith("plc_001.")  # Sollte True sein
```

---

## 📚 Weitere Ressourcen

- **API-Referenz**: `modules/gateway/data_gateway.py`
- **Beispiel-Plugins**: `smarthome-sdk-v5/*/`
- **Routing-Doku**: `ROADMAP.md` Phase 1
- **System-Logs**: `config/system_logs.db`

---

## 🤝 Support & Community

- **Issues**: GitHub Issues
- **Dokumentation**: Diese README
- **Beispiele**: Siehe `routing_example/`

---

**Version**: 4.6.0
**Stand**: 2026-01-04
**Lizenz**: MIT