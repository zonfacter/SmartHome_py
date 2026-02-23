# Variable Manager & Data Gateway - Design Dokument

**Datum:** 11. Januar 2026
**Status:** 📋 DESIGN PHASE
**Ziel:** Zentrale Datenverwaltung für Widget ↔ PLC Kommunikation

---

## 1. Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Widget 1 │  │ Widget 2 │  │ Widget 3 │  │ Widget N │       │
│  │ (Button) │  │ (Gauge)  │  │ (Switch) │  │ (Chart)  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │              │             │              │
│       └─────────────┴──────────────┴─────────────┘              │
│                           │                                      │
│                ┌──────────▼──────────┐                          │
│                │  Variable Manager   │                          │
│                │  (JavaScript)       │                          │
│                │  - Subscriptions    │                          │
│                │  - Value Cache      │                          │
│                │  - Update Queue     │                          │
│                └──────────┬──────────┘                          │
│                           │                                      │
│                    WebSocket / HTTP                             │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        BACKEND (Flask)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Variable Manager (Python)                   │   │
│  │  - Variable Registry (Symbol → Widget Mappings)         │   │
│  │  - Subscription Management                               │   │
│  │  - Rate Limiting                                         │   │
│  │  - Value History                                         │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │              Data Gateway                                │   │
│  │  - PLC Communication (pyads)                            │   │
│  │  - WebSocket Broadcasting (Socket.IO)                   │   │
│  │  - Value Caching                                         │   │
│  │  - Background Polling Thread                            │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                    ADS Protocol (pyads)
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      TwinCAT PLC                                 │
│  - Light.Light_EG_WZ.bOn                                        │
│  - MAIN.Temperature                                              │
│  - Rolladen.Position                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Komponenten-Design

### 2.1 Variable Registry (Backend)

**Datei:** `modules/plc/variable_manager.py`

**Aufgaben:**
- Symbol-Metadaten speichern (Name, Type, IGroup, IOffset)
- Widget → Variable Zuordnungen verwalten
- Subscription-Liste pflegen (welche Widgets wollen welche Variablen?)

**Datenstruktur:**

```python
class VariableManager:
    def __init__(self):
        # Symbol-Registry: name → SymbolInfo
        self.symbols = {}

        # Widget-Subscriptions: variable_name → set(widget_ids)
        self.subscriptions = {}

        # Widget-Mappings: widget_id → variable_name
        self.widget_mappings = {}

        # Value-Cache: variable_name → (value, timestamp)
        self.value_cache = {}

    def register_symbol(self, symbol: PLCSymbol):
        """Registriert ein Symbol aus dem Symbol-Browser"""
        self.symbols[symbol.name] = symbol

    def subscribe_widget(self, widget_id: str, variable_name: str):
        """Widget abonniert eine Variable"""
        if variable_name not in self.subscriptions:
            self.subscriptions[variable_name] = set()
        self.subscriptions[variable_name].add(widget_id)
        self.widget_mappings[widget_id] = variable_name

    def unsubscribe_widget(self, widget_id: str):
        """Widget beendet Subscription"""
        if widget_id in self.widget_mappings:
            variable_name = self.widget_mappings[widget_id]
            if variable_name in self.subscriptions:
                self.subscriptions[variable_name].discard(widget_id)
            del self.widget_mappings[widget_id]

    def get_subscribers(self, variable_name: str) -> set:
        """Gibt alle Widget-IDs zurück die diese Variable abonniert haben"""
        return self.subscriptions.get(variable_name, set())

    def update_value(self, variable_name: str, value: any):
        """Aktualisiert Value-Cache"""
        self.value_cache[variable_name] = (value, time.time())
```

---

### 2.2 Data Gateway (Backend)

**Datei:** `modules/plc/data_gateway.py`

**Aufgaben:**
- PLC-Kommunikation (Read/Write via pyads)
- WebSocket Broadcasting (Socket.IO)
- Zyklisches Polling (Background Thread)
- Value-Caching

**Implementierung:**

```python
class DataGateway:
    def __init__(self, plc_communication, variable_manager, socketio):
        self.plc = plc_communication
        self.var_mgr = variable_manager
        self.socketio = socketio

        # Polling-Thread
        self.polling_thread = None
        self.polling_active = False
        self.poll_interval = 0.5  # 500ms = 2 Hz

    def start_polling(self):
        """Startet Background Polling Thread"""
        if self.polling_active:
            return

        self.polling_active = True
        self.polling_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.polling_thread.start()

    def _poll_loop(self):
        """Polling-Loop (läuft im Background)"""
        while self.polling_active:
            try:
                # Hole alle abonnierten Variablen
                subscribed_vars = list(self.var_mgr.subscriptions.keys())

                if subscribed_vars:
                    # Lese Werte von PLC
                    updates = self.read_variables(subscribed_vars)

                    # Broadcast Updates via WebSocket
                    if updates:
                        self.socketio.emit('variable_updates', updates)

                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Polling-Fehler: {e}")
                time.sleep(1)

    def read_variables(self, variable_names: list) -> dict:
        """Liest mehrere Variablen von der PLC"""
        updates = {}

        for var_name in variable_names:
            try:
                symbol = self.var_mgr.symbols.get(var_name)
                if not symbol:
                    continue

                # Lese Wert von PLC (via pyads)
                value = self.plc.read_by_name(var_name)

                # Prüfe ob Wert sich geändert hat
                cached = self.var_mgr.value_cache.get(var_name)
                if not cached or cached[0] != value:
                    # Wert hat sich geändert → Update
                    self.var_mgr.update_value(var_name, value)
                    updates[var_name] = {
                        'value': value,
                        'timestamp': time.time(),
                        'type': symbol.symbol_type
                    }

            except Exception as e:
                logger.error(f"Fehler beim Lesen von {var_name}: {e}")

        return updates

    def write_variable(self, variable_name: str, value: any):
        """Schreibt Wert zur PLC"""
        try:
            symbol = self.var_mgr.symbols.get(variable_name)
            if not symbol:
                raise ValueError(f"Symbol nicht gefunden: {variable_name}")

            # Schreibe zu PLC (via pyads)
            self.plc.write_by_name(variable_name, value)

            # Update Cache
            self.var_mgr.update_value(variable_name, value)

            # Broadcast Update
            self.socketio.emit('variable_updates', {
                variable_name: {
                    'value': value,
                    'timestamp': time.time(),
                    'type': symbol.symbol_type
                }
            })

            return True

        except Exception as e:
            logger.error(f"Fehler beim Schreiben von {variable_name}: {e}")
            raise
```

---

### 2.3 Variable Manager (Frontend)

**Datei:** `web/static/js/variable-manager.js`

**Aufgaben:**
- WebSocket-Verbindung zu Backend
- Subscription-Management
- Value-Cache im Frontend
- Widget-Updates triggern

**Implementierung:**

```javascript
class VariableManager {
    constructor() {
        // WebSocket-Verbindung
        this.socket = io();

        // Subscriptions: variable_name → Set(callback functions)
        this.subscriptions = new Map();

        // Value-Cache: variable_name → {value, timestamp, type}
        this.cache = new Map();

        // Setup Socket.IO Listeners
        this.setupSocketListeners();
    }

    setupSocketListeners() {
        // Empfange Variable-Updates vom Backend
        this.socket.on('variable_updates', (updates) => {
            for (const [varName, data] of Object.entries(updates)) {
                this.handleUpdate(varName, data);
            }
        });

        this.socket.on('connect', () => {
            console.log('✅ Variable Manager verbunden');
            // Re-subscribe nach Reconnect
            this.resubscribeAll();
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Variable Manager getrennt');
        });
    }

    subscribe(variableName, callback, widgetId = null) {
        /**
         * Widget abonniert eine Variable
         * @param variableName - Vollständiger Symbol-Name (z.B. "Light.Light_EG_WZ.bOn")
         * @param callback - Function(value, data) wird bei Updates aufgerufen
         * @param widgetId - Eindeutige Widget-ID (für Backend-Tracking)
         */

        if (!this.subscriptions.has(variableName)) {
            this.subscriptions.set(variableName, new Set());

            // Informiere Backend über Subscription
            this.socket.emit('subscribe_variable', {
                variable: variableName,
                widget_id: widgetId
            });
        }

        this.subscriptions.get(variableName).add(callback);

        // Sende aktuellen Wert sofort (falls im Cache)
        if (this.cache.has(variableName)) {
            const data = this.cache.get(variableName);
            callback(data.value, data);
        }
    }

    unsubscribe(variableName, callback, widgetId = null) {
        /**
         * Widget beendet Subscription
         */
        if (!this.subscriptions.has(variableName)) return;

        this.subscriptions.get(variableName).delete(callback);

        // Wenn keine Subscriber mehr → Backend informieren
        if (this.subscriptions.get(variableName).size === 0) {
            this.subscriptions.delete(variableName);

            this.socket.emit('unsubscribe_variable', {
                variable: variableName,
                widget_id: widgetId
            });
        }
    }

    handleUpdate(variableName, data) {
        /**
         * Verarbeitet Update vom Backend
         */
        // Update Cache
        this.cache.set(variableName, data);

        // Rufe alle Callbacks auf
        if (this.subscriptions.has(variableName)) {
            for (const callback of this.subscriptions.get(variableName)) {
                try {
                    callback(data.value, data);
                } catch (error) {
                    console.error(`Callback-Fehler für ${variableName}:`, error);
                }
            }
        }
    }

    async writeVariable(variableName, value) {
        /**
         * Schreibt Wert zur PLC
         */
        try {
            const response = await fetch('/api/plc/variables/write', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    variable: variableName,
                    value: value
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();

        } catch (error) {
            console.error(`Fehler beim Schreiben von ${variableName}:`, error);
            throw error;
        }
    }

    getValue(variableName) {
        /**
         * Holt aktuellen Wert aus Cache
         */
        const data = this.cache.get(variableName);
        return data ? data.value : null;
    }

    resubscribeAll() {
        /**
         * Re-subscribe alle Variablen nach Reconnect
         */
        for (const varName of this.subscriptions.keys()) {
            this.socket.emit('subscribe_variable', {
                variable: varName
            });
        }
    }
}

// Globale Instanz
window.variableManager = new VariableManager();
```

---

## 3. Widget → Variable Binding

### 3.1 Widget-Konfiguration erweitern

**widgets.json Format:**

```json
{
  "widget_001": {
    "id": "widget_001",
    "type": "boolean",
    "page": "dashboard",
    "position": {"x": 100, "y": 100},
    "config": {
      "title": "Wohnzimmer Licht",
      "variable": "Light.Light_EG_WZ.bLight",  // ← Variable-Binding
      "read_only": false
    }
  },
  "widget_002": {
    "type": "gauge",
    "config": {
      "title": "Temperatur",
      "variable": "MAIN.Temperature",
      "min": 0,
      "max": 50,
      "unit": "°C"
    }
  }
}
```

### 3.2 Widget-Lifecycle mit Variable Manager

**Beispiel: Boolean Widget (Button/Switch)**

```javascript
class BooleanWidget {
    constructor(widgetId, config) {
        this.widgetId = widgetId;
        this.config = config;
        this.variableName = config.variable;

        // UI erstellen
        this.element = this.createDOM();

        // Subscribe zu Variable
        this.subscribeToVariable();
    }

    subscribeToVariable() {
        if (!this.variableName) return;

        // Callback für Updates
        this.updateCallback = (value, data) => {
            this.updateUI(value);
        };

        // Subscribe
        variableManager.subscribe(
            this.variableName,
            this.updateCallback,
            this.widgetId
        );
    }

    updateUI(value) {
        // Update Button-State
        if (value) {
            this.element.classList.add('active');
            this.element.textContent = 'EIN';
        } else {
            this.element.classList.remove('active');
            this.element.textContent = 'AUS';
        }
    }

    async toggleValue() {
        // Lese aktuellen Wert
        const currentValue = variableManager.getValue(this.variableName);

        // Toggle
        const newValue = !currentValue;

        // Schreibe zu PLC
        try {
            await variableManager.writeVariable(this.variableName, newValue);
            console.log(`✅ ${this.variableName} = ${newValue}`);
        } catch (error) {
            console.error('❌ Schreib-Fehler:', error);
            alert('Fehler beim Schalten!');
        }
    }

    destroy() {
        // Cleanup: Unsubscribe
        if (this.variableName && this.updateCallback) {
            variableManager.unsubscribe(
                this.variableName,
                this.updateCallback,
                this.widgetId
            );
        }

        // Remove DOM
        this.element.remove();
    }
}
```

---

## 4. API Endpoints

### 4.1 Variable Subscription (WebSocket)

**Event:** `subscribe_variable`

```javascript
// Frontend → Backend
socket.emit('subscribe_variable', {
    variable: 'Light.Light_EG_WZ.bOn',
    widget_id: 'widget_001'
});
```

**Backend Handler:**

```python
@socketio.on('subscribe_variable')
def handle_subscribe(data):
    variable = data.get('variable')
    widget_id = data.get('widget_id')

    # Registriere Subscription
    variable_manager.subscribe_widget(widget_id, variable)

    # Sende aktuellen Wert sofort
    cached = variable_manager.value_cache.get(variable)
    if cached:
        emit('variable_updates', {
            variable: {
                'value': cached[0],
                'timestamp': cached[1]
            }
        })
```

### 4.2 Variable Write (HTTP POST)

**Endpoint:** `POST /api/plc/variables/write`

```javascript
// Frontend → Backend
fetch('/api/plc/variables/write', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        variable: 'Light.Light_EG_WZ.bOn',
        value: true
    })
});
```

**Backend Handler:**

```python
@app.route('/api/plc/variables/write', methods=['POST'])
def write_variable():
    data = request.json
    variable = data.get('variable')
    value = data.get('value')

    try:
        # Schreibe zu PLC
        data_gateway.write_variable(variable, value)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 4.3 Variable Read (HTTP GET)

**Endpoint:** `GET /api/plc/variables/read?variable=Light.Light_EG_WZ.bOn`

```python
@app.route('/api/plc/variables/read', methods=['GET'])
def read_variable():
    variable = request.args.get('variable')

    try:
        # Lese von PLC (oder Cache)
        cached = variable_manager.value_cache.get(variable)
        if cached and (time.time() - cached[1]) < 1.0:
            # Cache ist frisch (< 1 Sekunde alt)
            value = cached[0]
        else:
            # Lese frisch von PLC
            value = plc_communication.read_by_name(variable)
            variable_manager.update_value(variable, value)

        return jsonify({
            'variable': variable,
            'value': value,
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 5. Performance-Optimierungen

### 5.1 Batch Reading

Statt einzelne Variablen zu lesen:

```python
# LANGSAM (viele ADS-Requests):
value1 = plc.read_by_name('Light.Light_EG_WZ.bOn')
value2 = plc.read_by_name('Light.Light_EG_WZ.bOff')
value3 = plc.read_by_name('Light.Light_EG_WZ.bLight')

# SCHNELL (ein ADS-Request):
values = plc.read_structure_by_name('Light.Light_EG_WZ')
# → {'bOn': True, 'bOff': False, 'bLight': True, ...}
```

**Implementierung:**

```python
def read_variables_optimized(self, variable_names: list) -> dict:
    """Gruppiert Variablen nach Parent-Struktur für Batch-Reading"""

    # Gruppiere nach Parent (z.B. "Light.Light_EG_WZ")
    groups = {}
    for var in variable_names:
        parts = var.split('.')
        if len(parts) > 1:
            parent = '.'.join(parts[:-1])
            if parent not in groups:
                groups[parent] = []
            groups[parent].append(var)

    updates = {}

    # Lese jede Gruppe als Struktur
    for parent, vars in groups.items():
        try:
            structure = self.plc.read_structure_by_name(parent)

            for var in vars:
                field = var.split('.')[-1]
                if field in structure:
                    updates[var] = structure[field]

        except:
            # Fallback: Einzelne Reads
            for var in vars:
                try:
                    updates[var] = self.plc.read_by_name(var)
                except:
                    pass

    return updates
```

### 5.2 Adaptive Polling-Rate

```python
class DataGateway:
    def __init__(self):
        self.poll_intervals = {
            'fast': 0.1,    # 100ms für kritische Werte (Buttons)
            'normal': 0.5,  # 500ms für Standard (Gauges)
            'slow': 2.0     # 2s für unkritische Werte (Statistiken)
        }

        # Variable → Polling-Rate Mapping
        self.variable_rates = {}

    def set_polling_rate(self, variable_name: str, rate: str):
        """Setzt Polling-Rate für Variable"""
        self.variable_rates[variable_name] = rate

    def _poll_loop(self):
        """Polling mit verschiedenen Raten"""
        last_fast = 0
        last_normal = 0
        last_slow = 0

        while self.polling_active:
            now = time.time()

            # Fast-Poll (100ms)
            if now - last_fast >= self.poll_intervals['fast']:
                fast_vars = [v for v, r in self.variable_rates.items() if r == 'fast']
                if fast_vars:
                    self._poll_variables(fast_vars)
                last_fast = now

            # Normal-Poll (500ms)
            if now - last_normal >= self.poll_intervals['normal']:
                normal_vars = [v for v, r in self.variable_rates.items() if r == 'normal']
                if normal_vars:
                    self._poll_variables(normal_vars)
                last_normal = now

            # Slow-Poll (2s)
            if now - last_slow >= self.poll_intervals['slow']:
                slow_vars = [v for v, r in self.variable_rates.items() if r == 'slow']
                if slow_vars:
                    self._poll_variables(slow_vars)
                last_slow = now

            time.sleep(0.01)  # 10ms Sleep
```

---

## 6. Implementierungs-Reihenfolge

### Phase 1: Backend Foundation ✅
1. ✅ `modules/plc/variable_manager.py` erstellen
2. ✅ `modules/plc/data_gateway.py` erstellen
3. ✅ Integration in `modules/gateway/web_manager.py`
4. ✅ WebSocket Endpoints (Socket.IO)
5. ✅ HTTP API Endpoints

### Phase 2: Frontend Foundation
1. ⏳ `web/static/js/variable-manager.js` erstellen
2. ⏳ Integration in `app.js`
3. ⏳ WebSocket-Verbindung testen

### Phase 3: Widget-Integration
1. ⏳ Widget-Config um `variable` Feld erweitern
2. ⏳ Widget-Klassen refactoren (subscribe/unsubscribe)
3. ⏳ Boolean Widget mit Variable-Binding
4. ⏳ Gauge Widget mit Variable-Binding
5. ⏳ Number Widget mit Variable-Binding

### Phase 4: UI für Variable-Assignment
1. ⏳ Symbol-Browser → Drag & Drop zu Widget
2. ⏳ Widget-Edit-Dialog mit Variable-Picker
3. ⏳ Variable-Suche/Filter im Picker

### Phase 5: Optimierungen
1. ⏳ Batch-Reading implementieren
2. ⏳ Adaptive Polling-Rates
3. ⏳ Value-History für Charts
4. ⏳ Offline-Mode mit Cache

---

## 7. Sicherheits-Überlegungen

### 7.1 Write-Protection

```python
# Nur bestimmte Variablen schreibbar
WRITABLE_PATTERNS = [
    r'^Light\..*\.bOn$',
    r'^Light\..*\.bOff$',
    r'^Light\..*\.bToggle$',
    r'^Rolladen\..*\.bUp$',
    r'^Rolladen\..*\.bDown$',
]

def is_writable(variable_name: str) -> bool:
    for pattern in WRITABLE_PATTERNS:
        if re.match(pattern, variable_name):
            return True
    return False
```

### 7.2 Rate Limiting

```python
# Max 10 Writes pro Sekunde pro Variable
write_history = {}  # variable → [timestamps]

def check_rate_limit(variable: str) -> bool:
    now = time.time()
    if variable not in write_history:
        write_history[variable] = []

    # Entferne alte Einträge (> 1 Sekunde)
    write_history[variable] = [
        t for t in write_history[variable]
        if now - t < 1.0
    ]

    # Prüfe Limit
    if len(write_history[variable]) >= 10:
        return False  # Rate-Limit erreicht

    write_history[variable].append(now)
    return True
```

---

## 8. Testing-Strategie

### 8.1 Unit Tests

```python
# test_variable_manager.py
def test_subscribe_widget():
    vm = VariableManager()
    vm.subscribe_widget('widget_001', 'Light.bOn')

    assert 'Light.bOn' in vm.subscriptions
    assert 'widget_001' in vm.subscriptions['Light.bOn']

def test_duplicate_subscribe():
    vm = VariableManager()
    vm.subscribe_widget('widget_001', 'Light.bOn')
    vm.subscribe_widget('widget_001', 'Light.bOn')  # Doppelt

    assert len(vm.subscriptions['Light.bOn']) == 1
```

### 8.2 Integration Tests

```python
# test_data_gateway.py
def test_read_write_cycle():
    gateway = DataGateway(plc, var_mgr, socketio)

    # Schreibe Wert
    gateway.write_variable('Light.bOn', True)

    # Lese zurück
    value = gateway.read_variable('Light.bOn')

    assert value == True
```

### 8.3 Frontend Tests

```javascript
// test_variable_manager.js
describe('VariableManager', () => {
    it('should subscribe to variable', (done) => {
        const vm = new VariableManager();

        vm.subscribe('Light.bOn', (value) => {
            expect(value).toBe(true);
            done();
        });

        // Simulate update
        vm.handleUpdate('Light.bOn', {value: true});
    });
});
```

---

**Erstellt:** 11. Januar 2026 01:30
**Status:** 📋 DESIGN COMPLETE - READY FOR IMPLEMENTATION
**Nächster Schritt:** Phase 1 - Backend Foundation implementieren
