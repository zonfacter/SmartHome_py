# Feature Roadmap - TwinCAT SmartHome HMI

## ✅ Completed (v4.7.0)
- [x] SQLite Logging System
- [x] Service Hot-Restart (Windows/Linux)
- [x] Admin Dashboard (Logs, Service Info)
- [x] Monitor-Seite Fix (Gateway Status)
- [x] Latenz-Messung Fix
- [x] Auto-Type-Detection für PLC-Writes
- [x] Widget-Sync Fix
- [x] TreeView Component (Hierarchische Datenvisualisierung)
- [x] Variable Explorer (PLC-Symbole & MQTT-Topics)
- [x] Widget CRUD APIs (GET/POST/PUT/DELETE)
- [x] Hardware Monitor Integration (psutil - CPU/RAM)
- [x] Widget Delete Button (temporär)
- [x] ConfigManager Widget-Persistence Methods

---

## 🚧 In Progress

### Priority 1: Widget-Management System
**Status:** Design Phase
**Ziel:** Widgets über UI editieren, löschen, verschieben

#### Komponenten:
1. **Widget-Editor Dialog** (`web/static/js/components/widget_editor.js`)
   - Modal/Dialog für Widget-Einstellungen
   - Formulare für:
     - Widget-Typ auswählen (Light, Temperature, Gauge, etc.)
     - Name/Label
     - Bindings (PLC-Variable, MQTT-Topic)
     - Position & Größe
     - Styling-Optionen

2. **Context-Menü für Widgets**
   - Rechtsklick auf Widget → Menü:
     - ✏️ Bearbeiten
     - 🗑️ Löschen
     - 📋 Duplizieren
     - 🎨 Stil anpassen

3. **Drag & Drop Enhancement**
   - Widgets zwischen Seiten verschieben
   - Grid-Snapping
   - Collision-Detection

4. **Backend-API Erweiterung**
   - `PUT /api/widgets/<id>` - Update Widget
   - `DELETE /api/widgets/<id>` - Delete Widget
   - `POST /api/widgets/<id>/duplicate` - Duplizieren

#### Implementierung:
```javascript
// web/static/js/components/widget_editor.js
class WidgetEditor {
    constructor(app) {
        this.app = app;
        this.currentWidget = null;
    }

    show(widgetId = null) {
        // Zeige Editor-Modal
        // Falls widgetId gegeben: Lade Widget-Config
        // Sonst: Neues Widget erstellen
    }

    save() {
        // Speichere Widget-Config via API
        // Update UI
    }
}
```

---

### Priority 2: PLC Variable Browser (TreeView)
**Status:** Design Phase
**Ziel:** PLC-Variablen in hierarchischer Tree-Ansicht browsen

#### Komponenten:
1. **Symbol-Tree-Parser** (`modules/gateway/plc_symbol_parser.py`) ✅ Bereits vorhanden!
   - Parst .tpy Dateien
   - Erstellt hierarchische Struktur

2. **TreeView UI Component** (`web/static/js/components/tree_view.js`)
   - Collapsible Tree
   - Suche/Filter
   - Icons je nach Datentyp (BOOL, INT, REAL, etc.)

3. **Variable Explorer Panel** (neue Seite oder Sidebar)
   - TreeView mit allen PLC-Symbolen
   - Drag & Drop zu Widgets
   - Live-Werte-Anzeige

4. **Backend-API**
   - `GET /api/plc/symbols/tree` ✅ Bereits vorhanden!
   - `GET /api/plc/symbols/search?q=<query>`
   - `GET /api/plc/symbols/<path>/children`

#### Implementierung:
```javascript
// web/static/js/components/tree_view.js
class TreeView {
    constructor(containerId, options) {
        this.container = document.getElementById(containerId);
        this.options = options;
        this.expandedNodes = new Set();
    }

    render(treeData) {
        // Rendert hierarchischen Tree
        // Mit Collapse/Expand Buttons
    }

    onNodeClick(node) {
        // Toggle expand/collapse
    }

    onNodeDrag(node) {
        // Drag & Drop Support
    }
}
```

---

### Priority 3: MQTT Topic Browser (TreeView)
**Status:** Design Phase
**Ziel:** MQTT-Topics hierarchisch browsen

#### Komponenten:
1. **MQTT Topic-Hierarchie** (`modules/integrations/mqtt_integration.py`)
   - Live-Topic-Discovery
   - Hierarchie-Parser (`home/living/temp` → Tree)

2. **Topic TreeView** (analog zu PLC Browser)
   - Collapsible Tree
   - Live-Werte-Anzeige
   - Subscription-Badges

3. **Backend-API**
   - `GET /api/mqtt/topics/tree` - Hierarchische Topic-Liste
   - `GET /api/mqtt/topics/<path>/subscribe` - Topic abonnieren
   - `POST /api/mqtt/publish` - Message publishen

#### Implementierung:
```python
# modules/integrations/mqtt_integration.py
def get_topic_tree(self):
    """
    Erstellt hierarchischen Topic-Tree

    Beispiel:
    'home/living/temperature' →
    {
        'home': {
            'living': {
                'temperature': { 'value': 22.5, 'is_leaf': True }
            }
        }
    }
    """
    tree = {}
    for topic, value in self.values.items():
        parts = topic.split('/')
        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Leaf node
                current[part] = {'value': value, 'is_leaf': True}
            else:
                # Folder node
                if part not in current:
                    current[part] = {}
                current = current[part]
    return tree
```

---

### Priority 4: Multi-Connection Support
**Status:** Design Phase
**Ziel:** Mehrere PLCs, MQTT-Broker, RS485-Devices gleichzeitig

#### Architektur:
```
ConnectionManager
├── PLC1 (192.168.2.162.1.1)
├── PLC2 (192.168.2.163.1.1)
├── MQTT1 (mqtt://broker1:1883)
├── MQTT2 (mqtt://broker2:1883)
└── RS485_1 (COM3, Modbus RTU)
```

#### Komponenten:
1. **Connection Manager** (`modules/core/connection_manager.py`)
   - Verwaltet mehrere Verbindungen
   - Connection-Pooling
   - Health-Checks

2. **Connection Config** (`config/connections.json`)
   ```json
   {
     "plcs": [
       {
         "id": "plc_main",
         "name": "Haupt-PLC",
         "ams_net_id": "192.168.2.162.1.1",
         "port": 851,
         "enabled": true
       },
       {
         "id": "plc_garage",
         "name": "Garagen-PLC",
         "ams_net_id": "192.168.2.163.1.1",
         "port": 851,
         "enabled": false
       }
     ],
     "mqtt_brokers": [
       {
         "id": "mqtt_main",
         "name": "Home Assistant",
         "host": "192.168.2.100",
         "port": 1883,
         "username": "homeassistant",
         "enabled": true
       }
     ],
     "serial_devices": [
       {
         "id": "modbus_inverter",
         "name": "Wechselrichter",
         "port": "COM3",
         "baudrate": 9600,
         "protocol": "modbus_rtu",
         "enabled": true
       }
     ]
   }
   ```

3. **Widget-Bindings erweitern**
   ```json
   {
     "widget_id": "light_wz",
     "bindings": {
       "state": {
         "connection_id": "plc_main",
         "type": "plc",
         "symbol": "MAIN.lights.livingroom"
       }
     }
   }
   ```

4. **Backend-API**
   - `GET /api/connections` - Alle Verbindungen
   - `POST /api/connections` - Neue Verbindung
   - `PUT /api/connections/<id>` - Update Verbindung
   - `DELETE /api/connections/<id>` - Löschen
   - `POST /api/connections/<id>/toggle` - Enable/Disable

---

## 📅 Implementation Timeline (Vorschlag)

### Phase 1 (2-3 Tage): Widget-Management
- Widget-Editor UI
- Context-Menü
- Drag & Drop Enhancement
- CRUD-APIs

### Phase 2 (2-3 Tage): Variable/Topic Browser
- PLC TreeView
- MQTT TreeView
- Drag & Drop zu Widgets
- Live-Werte-Anzeige

### Phase 3 (3-4 Tage): Multi-Connection
- Connection Manager Architektur
- Config-System
- UI für Connection-Management
- Widget-Binding-Updates

---

## 🎯 Quick Wins (können sofort umgesetzt werden)

1. **✅ Beispiel-Widgets aus Config laden** (statt hardcoded)
2. **Widget-Seiten konfigurierbar machen** (Dashboard, Lighting, etc.)
3. **Schnelles Löschen von Widgets** (Delete-Button hinzufügen)
4. **Symbol-Upload verbessern** (Drag & Drop für .tpy)

---

## 🚀 v4.6.0 - Central Data Router ("Single Source of Truth")
**Status:** Design & Architecture Phase
**Ziel:** Zentrales Routing-System für heterogene Datenquellen mit Pub/Sub-Architektur

### Konzept: Middleware Broker Pattern

Das aktuelle System hat folgende Struktur:
```
PLC → DataGateway → Widgets
MQTT → DataGateway → Widgets
BT → DataGateway → Widgets
```

**Problem:** Keine Cross-Interface-Logik möglich (z.B. Bluetooth-Sensor → PLC-Variable schreiben)

**Lösung:** Central Data Router als "Single Source of Truth"
```
          ┌─────────────────────────────┐
          │   Central Data Router       │
          │  (Single Source of Truth)   │
          │                             │
          │  • route_data()             │
          │  • Normalization            │
          │  • Pub/Sub Broker           │
          │  • History Manager          │
          │  • Routing Rules Engine     │
          └──────────┬──────────────────┘
                     │
       ┌─────────────┼─────────────┐
       │             │             │
   ┌───▼───┐    ┌───▼───┐    ┌───▼───┐
   │  PLC  │    │ MQTT  │    │  BT   │
   └───────┘    └───────┘    └───────┘
       │             │             │
       └─────────────┼─────────────┘
                     │
              ┌──────▼──────┐
              │   Widgets   │
              │   Plugins   │
              │   History   │
              └─────────────┘
```

---

### Komponente 1: route_data() - Zentraler Message Handler

**Datei:** `modules/gateway/data_gateway.py`

**Architektur:**
```python
def route_data(self, source: str, topic: str, value: Any, metadata: Dict = None):
    """
    Zentraler Eintrittspunkt für ALLE Daten

    Args:
        source: Quelle ('plc', 'mqtt', 'bluetooth', 'serial', 'manual')
        topic: Eindeutiger Pfad (z.B. 'MAIN.temperature' oder 'home/living/temp')
        value: Wert (beliebiger Typ)
        metadata: Zusatzinfos (timestamp, unit, quality, etc.)

    Flow:
        1. Normalisierung → Unified Data Space
        2. Routing Rules anwenden
        3. Pub/Sub Broadcasting
        4. History Manager
        5. Widget Updates
        6. Cross-Interface Routing
    """
    # 1. Normalisierung
    normalized = self.normalize_data(source, topic, value, metadata)

    # 2. Routing Rules
    routes = self.routing_engine.get_routes(normalized['unified_topic'])

    # 3. Pub/Sub
    self.publish(normalized['unified_topic'], normalized)

    # 4. History
    if self.history_manager:
        self.history_manager.store(normalized)

    # 5. Cross-Interface Routing
    for route in routes:
        self.execute_route(route, normalized)
```

**Unified Data Space:**
Alle Daten werden in ein einheitliches Format konvertiert:
```python
{
    "unified_topic": "sensors/temperature/living_room",
    "source": "mqtt",
    "original_topic": "home/living/temperature",
    "value": 22.5,
    "unit": "°C",
    "timestamp": 1704405600.123,
    "quality": "good",
    "data_type": "float"
}
```

---

### Komponente 2: Routing Configuration System

**Datei:** `config/routing.json`

**Schema:**
```json
{
  "version": "5.1.0",
  "routing_rules": [
    {
      "id": "bt_sensor_to_plc",
      "enabled": true,
      "description": "BT Temperatur → PLC Variable",
      "source": {
        "type": "bluetooth",
        "topic": "sensors/temperature/outdoor",
        "filter": {
          "min": -20,
          "max": 50
        }
      },
      "targets": [
        {
          "type": "plc",
          "symbol": "MAIN.fOutdoorTemp",
          "plc_type": "REAL",
          "transform": "value * 1.0"
        },
        {
          "type": "mqtt",
          "topic": "homeassistant/sensor/outdoor_temp/state",
          "qos": 1
        }
      ],
      "conditions": [
        {
          "type": "time_range",
          "start": "06:00",
          "end": "22:00"
        },
        {
          "type": "rate_limit",
          "max_updates_per_minute": 10
        }
      ]
    },
    {
      "id": "plc_alarm_to_mqtt",
      "enabled": true,
      "description": "PLC Alarm → MQTT Notification",
      "source": {
        "type": "plc",
        "symbol": "MAIN.bAlarmActive"
      },
      "targets": [
        {
          "type": "mqtt",
          "topic": "homeassistant/alarm/state",
          "transform": "'triggered' if value else 'disarmed'"
        },
        {
          "type": "webhook",
          "url": "https://notification-service/api/alarm",
          "method": "POST",
          "payload": {
            "alarm": "{{value}}",
            "timestamp": "{{timestamp}}"
          }
        }
      ]
    },
    {
      "id": "mqtt_energy_aggregation",
      "enabled": true,
      "description": "MQTT Energie-Daten → History & Dashboard",
      "source": {
        "type": "mqtt",
        "topic_pattern": "energy/meter/+/power"
      },
      "targets": [
        {
          "type": "history",
          "table": "energy_consumption",
          "aggregation": "sum",
          "interval": "15min"
        },
        {
          "type": "widget",
          "widget_id": "energy_total",
          "binding": "value"
        }
      ]
    }
  ],
  "data_normalization": {
    "topic_mapping": {
      "plc": {
        "prefix": "plc",
        "separator": ".",
        "example": "plc.MAIN.temperature"
      },
      "mqtt": {
        "prefix": "mqtt",
        "separator": "/",
        "example": "mqtt/home/living/temp"
      },
      "bluetooth": {
        "prefix": "bt",
        "separator": "/",
        "example": "bt/sensors/temperature/outdoor"
      }
    }
  },
  "pub_sub": {
    "enable_wildcards": true,
    "wildcard_syntax": "mqtt",
    "max_subscribers_per_topic": 100
  }
}
```

**Routing Rules Engine:**
```python
# modules/core/routing_engine.py
class RoutingEngine:
    def __init__(self, config_manager):
        self.config = config_manager.get_routing_config()
        self.rules = self._load_rules()

    def get_routes(self, unified_topic: str) -> List[Route]:
        """Findet alle passenden Routing-Regeln für ein Topic"""
        matches = []
        for rule in self.rules:
            if self._matches_pattern(unified_topic, rule['source']):
                if self._check_conditions(rule):
                    matches.append(rule)
        return matches

    def _matches_pattern(self, topic: str, pattern: str) -> bool:
        """MQTT-Style Wildcards: sensors/+/temperature, sensors/#"""
        # Implementierung mit regex

    def _check_conditions(self, rule: Dict) -> bool:
        """Prüft Zeit, Rate-Limits, Value-Ranges, etc."""
```

---

### Komponente 3: History Manager Plugin

**Datei:** `modules/plugins/history_manager.py`

**Zweck:** Langzeit-Speicherung von Zeitreihendaten

**Implementierung:**
```python
class HistoryManager(BaseModule):
    """
    Speichert historische Daten in SQLite oder InfluxDB

    Features:
    - Automatische Aggregation (1min, 15min, 1h, 1d)
    - Retention Policies
    - Query-API für Frontend
    - Export (CSV, JSON)
    """

    def __init__(self):
        super().__init__()
        self.db_type = 'sqlite'  # oder 'influxdb'
        self.db_connection = None

    def store(self, data: Dict):
        """Speichert einen Datenpunkt"""
        if self.db_type == 'sqlite':
            self._store_sqlite(data)
        elif self.db_type == 'influxdb':
            self._store_influx(data)

    def _store_sqlite(self, data: Dict):
        """
        SQLite Schema:
        CREATE TABLE history (
            id INTEGER PRIMARY KEY,
            timestamp REAL,
            topic TEXT,
            value REAL,
            unit TEXT,
            source TEXT,
            metadata TEXT
        );
        CREATE INDEX idx_topic_time ON history(topic, timestamp);
        """
        query = """
            INSERT INTO history (timestamp, topic, value, unit, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.db_connection.execute(query, (
            data['timestamp'],
            data['unified_topic'],
            data['value'],
            data.get('unit'),
            data['source'],
            json.dumps(data.get('metadata', {}))
        ))

    def query(self, topic: str, start: float, end: float, aggregation: str = None):
        """
        Abfrage historischer Daten

        Args:
            topic: Topic (kann Wildcards enthalten)
            start: Unix Timestamp Start
            end: Unix Timestamp Ende
            aggregation: 'avg', 'min', 'max', 'sum' (optional)
        """
        if aggregation:
            query = f"""
                SELECT
                    CAST(timestamp / 60 AS INTEGER) * 60 as bucket,
                    {aggregation}(value) as value
                FROM history
                WHERE topic LIKE ? AND timestamp BETWEEN ? AND ?
                GROUP BY bucket
                ORDER BY bucket
            """
        else:
            query = """
                SELECT timestamp, value, unit, metadata
                FROM history
                WHERE topic LIKE ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            """

        return self.db_connection.execute(query, (topic, start, end)).fetchall()
```

**Backend API:**
```python
# modules/gateway/web_manager.py
@self.app.route('/api/history/query')
def query_history():
    topic = request.args.get('topic')
    start = float(request.args.get('start', time.time() - 86400))
    end = float(request.args.get('end', time.time()))
    aggregation = request.args.get('agg')

    history = self.app_context.module_manager.get_module('history_manager')
    data = history.query(topic, start, end, aggregation)

    return jsonify({
        'topic': topic,
        'start': start,
        'end': end,
        'data': data
    })
```

---

### Komponente 4: Universal Plugin API

**Ziel:** Standardisierte Schnittstelle für Gateway Stream-Zugriff

**Base Plugin Interface:**
```python
# modules/core/base_plugin.py
class BasePlugin(BaseModule):
    """
    Erweitert BaseModule um Plugin-spezifische Features

    Alle Plugins können:
    - Daten aus route_data() subscriben
    - Daten in route_data() publishen
    - Auf History zugreifen
    - Config lesen/schreiben
    """

    def subscribe(self, topic_pattern: str, callback: Callable):
        """
        Subscribt auf Daten-Stream

        Beispiel:
            plugin.subscribe('sensors/+/temperature', self.on_temperature)
        """
        gateway = self._app_context.module_manager.get_module('data_gateway')
        gateway.add_subscriber(topic_pattern, callback)

    def publish(self, topic: str, value: Any, metadata: Dict = None):
        """
        Publisht Daten in den Stream

        Beispiel:
            plugin.publish('calculated/avg_temp', 23.5, {'unit': '°C'})
        """
        gateway = self._app_context.module_manager.get_module('data_gateway')
        gateway.route_data(
            source='plugin:' + self.__class__.__name__,
            topic=topic,
            value=value,
            metadata=metadata
        )
```

**Beispiel-Plugin:**
```python
# modules/plugins/temperature_aggregator.py
class TemperatureAggregator(BasePlugin):
    """
    Berechnet Durchschnittstemperatur aus mehreren Sensoren
    """

    def initialize(self, app_context):
        super().initialize(app_context)

        self.temperatures = {}

        # Subscribe auf alle Temperatur-Sensoren
        self.subscribe('sensors/+/temperature', self.on_temperature)

    def on_temperature(self, data: Dict):
        """Callback für eintreffende Temperaturen"""
        self.temperatures[data['unified_topic']] = data['value']

        # Berechne Durchschnitt
        avg = sum(self.temperatures.values()) / len(self.temperatures)

        # Publishe Ergebnis
        self.publish('calculated/average_temperature', avg, {
            'unit': '°C',
            'source_count': len(self.temperatures)
        })
```

---

### Komponente 5: Status Monitor & Routing Visualization

**Datei:** `web/static/js/components/routing_monitor.js`

**Zweck:** Visualisierung der Datenflüsse in Echtzeit

**Features:**
- Sankey-Diagram für Datenflüsse
- Live-Statistiken (Messages/sec pro Route)
- Routing-Rule-Status (Enabled/Disabled/Error)
- Latenz-Messung pro Route

**UI-Mockup:**
```
┌─────────────────────────────────────────────────────┐
│  📊 Routing Monitor                          🔄 Live │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Sources          Routes           Targets          │
│                                                      │
│  ┌─────┐                          ┌─────────┐       │
│  │ PLC │────(45 msg/s)────────────▶│ Widgets │       │
│  └─────┘        │                  └─────────┘       │
│                 │                                    │
│  ┌──────┐       │  (12 msg/s)      ┌──────────┐     │
│  │ MQTT │───────┼──────────────────▶│ History  │     │
│  └──────┘       │                   └──────────┘     │
│                 │                                    │
│  ┌──────┐       └─(3 msg/s)────────▶┌─────┐         │
│  │  BT  │────────────────────────────▶│ PLC │         │
│  └──────┘                             └─────┘         │
│                                                      │
├─────────────────────────────────────────────────────┤
│  Active Routes: 8 / 12                              │
│  Total Throughput: 60 msg/s                         │
│  Avg Latency: 12ms                                  │
└─────────────────────────────────────────────────────┘
```

**Implementation:**
```javascript
class RoutingMonitor {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.updateInterval = null;
    }

    async init() {
        await this.loadRoutingStats();
        this.startLiveUpdates();
    }

    async loadRoutingStats() {
        const response = await fetch('/api/routing/stats');
        const data = await response.json();

        this.renderSankeyDiagram(data.flows);
        this.renderRouteTable(data.routes);
    }

    renderSankeyDiagram(flows) {
        // D3.js Sankey Visualization
        // flows = [
        //   { source: 'PLC', target: 'Widgets', value: 45 },
        //   { source: 'MQTT', target: 'History', value: 12 },
        //   { source: 'BT', target: 'PLC', value: 3 }
        // ]
    }
}
```

**Backend API:**
```python
# modules/gateway/web_manager.py
@self.app.route('/api/routing/stats')
def get_routing_stats():
    gateway = self.app_context.module_manager.get_module('data_gateway')

    return jsonify({
        'flows': gateway.get_flow_statistics(),
        'routes': gateway.routing_engine.get_route_status(),
        'throughput': gateway.get_throughput(),
        'latency': gateway.get_avg_latency()
    })
```

---

### Komponente 6: Pub/Sub Architecture

**Implementierung in DataGateway:**
```python
# modules/gateway/data_gateway.py
class DataGateway(BaseModule):
    def __init__(self):
        super().__init__()
        self.subscribers = {}  # topic_pattern -> [callbacks]

    def subscribe(self, topic_pattern: str, callback: Callable):
        """
        Subscribe auf Topic-Pattern (MQTT-Style Wildcards)

        Beispiele:
            subscribe('sensors/+/temperature', callback)  # Single-Level
            subscribe('sensors/#', callback)               # Multi-Level
        """
        if topic_pattern not in self.subscribers:
            self.subscribers[topic_pattern] = []
        self.subscribers[topic_pattern].append(callback)

    def publish(self, topic: str, data: Dict):
        """Publisht Daten an alle passenden Subscriber"""
        for pattern, callbacks in self.subscribers.items():
            if self._topic_matches(topic, pattern):
                for callback in callbacks:
                    try:
                        callback(data)
                    except Exception as e:
                        logging.error(f"Subscriber error: {e}")

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """
        MQTT Wildcard Matching
        + = single level wildcard
        # = multi level wildcard
        """
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')

        if '#' in pattern_parts:
            # Multi-Level Wildcard
            idx = pattern_parts.index('#')
            return topic_parts[:idx] == pattern_parts[:idx]

        if len(topic_parts) != len(pattern_parts):
            return False

        for t, p in zip(topic_parts, pattern_parts):
            if p != '+' and p != t:
                return False

        return True
```

---

## 📅 Implementation Timeline v4.6.0

### Phase 1 (1-2 Tage): Core Architecture
- [x] route_data() Methode in DataGateway
- [ ] Unified Data Space Normalisierung
- [ ] Pub/Sub Subscriber-System
- [ ] Routing Rules Parser

### Phase 2 (2-3 Tage): Routing Configuration
- [ ] config/routing.json Schema
- [ ] RoutingEngine Implementierung
- [ ] Condition Evaluation (Time, Rate-Limit, Filters)
- [ ] Transform Engine (Value-Mapping)

### Phase 3 (2 Tage): History Manager
- [ ] SQLite History Backend
- [ ] Query API
- [ ] Aggregation Functions
- [ ] Retention Policies

### Phase 4 (1-2 Tage): Plugin API
- [ ] BasePlugin erweitern
- [ ] Example Plugins (Aggregator, Alarm-Handler)
- [ ] Plugin-Discovery & Loading

### Phase 5 (2-3 Tage): Frontend Visualization
- [ ] Routing Monitor Component
- [ ] Sankey Diagram (D3.js)
- [ ] Routing Config UI (Admin Panel)
- [ ] Live Statistics Dashboard

---

## 🎯 v4.6.0 Use Cases

### Use Case 1: BT-Sensor → PLC
**Szenario:** Bluetooth Temperatursensor soll Außentemperatur an PLC senden

**Routing Rule:**
```json
{
  "source": {"type": "bluetooth", "topic": "sensors/temperature/outdoor"},
  "targets": [
    {"type": "plc", "symbol": "MAIN.fOutdoorTemp", "plc_type": "REAL"}
  ]
}
```

**Flow:**
1. BT-Modul empfängt Temperatur: 22.5°C
2. `route_data('bluetooth', 'sensors/temperature/outdoor', 22.5)`
3. Routing Engine findet Regel
4. PLC Write: `MAIN.fOutdoorTemp = 22.5`
5. History Manager speichert Datenpunkt
6. Widgets werden aktualisiert

---

### Use Case 2: PLC Alarm → MQTT + Webhook
**Szenario:** PLC-Alarm soll MQTT publishen UND Webhook triggern

**Routing Rule:**
```json
{
  "source": {"type": "plc", "symbol": "MAIN.bAlarmActive"},
  "targets": [
    {
      "type": "mqtt",
      "topic": "homeassistant/alarm/state",
      "transform": "'triggered' if value else 'disarmed'"
    },
    {
      "type": "webhook",
      "url": "https://pushover.net/api/1/messages.json",
      "method": "POST"
    }
  ]
}
```

---

### Use Case 3: Multi-Sensor Aggregation
**Szenario:** Durchschnittstemperatur aus 5 Sensoren berechnen

**Plugin:**
```python
class AvgTempPlugin(BasePlugin):
    def initialize(self, app_context):
        super().initialize(app_context)
        self.subscribe('sensors/+/temperature', self.aggregate)

    def aggregate(self, data):
        # Berechne Durchschnitt
        avg = self.calculate_average()
        # Publishe Ergebnis
        self.publish('calculated/avg_temperature', avg)
```

---

## 🔧 Migration Guide (v4.7.0 → v4.6.0)

### Schritt 1: Bestehende Integrationen anpassen
**Vorher:**
```python
# modules/gateway/data_gateway.py (v4.7)
def update_value(self, source, variable, value):
    if source == 'plc':
        self.plc_values[variable] = value
    elif source == 'mqtt':
        self.mqtt_values[variable] = value
```

**Nachher:**
```python
# modules/gateway/data_gateway.py (v4.6.0)
def update_value(self, source, variable, value):
    # Leite alles durch route_data()
    self.route_data(source, variable, value)
```

### Schritt 2: Widget-Bindings aktualisieren
Keine Änderungen erforderlich - vollständig rückwärtskompatibel!

### Schritt 3: Routing Rules konfigurieren
Erstelle `config/routing.json` mit initialen Regeln.

---

Welche Priorität sollen wir zuerst angehen? Ich empfehle:
1. **v4.6.0 Phase 1** - route_data() + Pub/Sub Core
2. **v4.6.0 Phase 2** - Routing Configuration System
3. **v4.6.0 Phase 3** - History Manager
