# Variable Manager Implementation - Progress Report

**Datum:** 11. Januar 2026 03:15 Uhr
**Status:** 🚧 IN PROGRESS (Phase 1-3 von 4 abgeschlossen)
**Version:** v4.6.0

---

## ✅ Abgeschlossene Aufgaben (Phase 1-3)

### 1. Variable Manager Module (✅ COMPLETE)

**Datei:** `modules/plc/variable_manager.py` (neu erstellt)

**Features:**
- ✅ Symbol-Registry mit SymbolInfo Dataclass
- ✅ Widget-Subscription Management (subscribe/unsubscribe)
- ✅ Value-Cache mit Timestamp
- ✅ Multi-PLC Support (plc_id als Key)
- ✅ Statistiken (get_statistics)
- ✅ Cache-Cleanup (clear_cache)

**Code-Struktur:**
```python
class VariableManager:
    - symbols: Dict[(plc_id, var_name), SymbolInfo]
    - subscriptions: Dict[(plc_id, var_name), Set(widget_ids)]
    - widget_mappings: Dict[widget_id, (plc_id, var_name)]
    - value_cache: Dict[(plc_id, var_name), (value, timestamp)]
```

**Methoden:**
- `register_symbol(symbol_info)` - Symbol registrieren
- `register_symbols_bulk(symbols, plc_id)` - Bulk-Registrierung
- `subscribe_widget(widget_id, variable, plc_id)` - Subscription
- `unsubscribe_widget(widget_id)` - Unsubscribe
- `get_subscribers(variable, plc_id)` - Hole Subscriber
- `update_value(variable, value, plc_id)` - Cache aktualisieren
- `get_cached_value(variable, plc_id)` - Cache lesen
- `get_symbol_info(variable, plc_id)` - Metadaten holen
- `get_statistics()` - Statistiken

### 2. Data Gateway Extension (✅ COMPLETE)

**Datei:** `modules/gateway/data_gateway.py` (erweitert)

**Neue Features (Lines 986-1174):**
- ✅ `start_variable_polling(var_mgr, socketio, interval)` - Start Polling
- ✅ `stop_variable_polling()` - Stop Polling
- ✅ `_variable_poll_loop()` - Background Thread Loop
- ✅ `_read_subscribed_variables(vars)` - Bulk-Read mit Grouping
- ✅ `write_variable(var, value, plc_id)` - PLC Write + Broadcast

**Polling-Logik:**
```python
while polling_active:
    # Hole abonnierte Variablen
    subscribed_vars = variable_manager.get_all_subscribed_variables()

    # Lese von PLC (gruppiert nach plc_id)
    updates = _read_subscribed_variables(subscribed_vars)

    # Broadcast via WebSocket
    socketio.emit('variable_updates', updates)

    # Sleep
    time.sleep(poll_interval)  # Standard: 0.5s
```

**Change-Detection:**
- Nur geänderte Werte werden gesendet
- Cache-Vergleich vor jedem Update
- Reduziert WebSocket-Traffic

**Multi-PLC Support:**
- Variablen werden nach plc_id gruppiert
- Jede PLC wird separat abgefragt
- Update-Format: `{plc_id: {var_name: {...}}}`

---

### 3. Web Manager Integration (✅ COMPLETE)

**Datei:** `modules/gateway/web_manager.py` (erweitert)

**Änderungen:**

#### 3.1 Initialization (Lines 30, 74, 132-155)
- ✅ Import: `from modules.plc.variable_manager import create_variable_manager`
- ✅ Instance Variable: `self.variable_manager = None`
- ✅ Variable Manager Instanz erstellt in `initialize()`
- ✅ Symbole aus Symbol-Browser registriert
- ✅ Polling Thread gestartet (2 Hz)

```python
# ⭐ v4.6.0: Initialize Variable Manager
logger.info("Initialisiere Variable Manager...")
self.variable_manager = create_variable_manager()

# Register symbols from cache
if self.symbol_browser:
    cached_symbols = self.symbol_browser.get_symbols('plc_001')
    if cached_symbols:
        self.variable_manager.register_symbols_bulk(cached_symbols, 'plc_001')
        logger.info(f"✅ Variable Manager: {len(cached_symbols)} Symbole registriert")

# Start variable polling
if self.data_gateway and self.variable_manager:
    self.data_gateway.start_variable_polling(
        self.variable_manager,
        self.socketio,
        poll_interval=0.5  # 2 Hz
    )
    logger.info("✅ Variable Polling Thread gestartet (2 Hz)")
```

#### 3.2 HTTP API Endpoints (Lines 802-926)

**✅ `/api/variables/write` (POST)**
- Schreibt Wert in PLC-Variable
- Body: `{plc_id, variable, value}`
- Broadcast über WebSocket nach Schreiben

**✅ `/api/variables/read` (POST)**
- Liest Variable (Cache oder direkt von PLC)
- Body: `{plc_id, variable, use_cache}`
- Aktualisiert Cache wenn direkt gelesen

**✅ `/api/variables/statistics` (GET)**
- Gibt Variable Manager Statistiken zurück
- Statistics: `{total_symbols, total_subscriptions, ...}`

#### 3.3 WebSocket Event Handlers (Lines 952-1044)

**✅ `subscribe_variable` Event**
- Widget abonniert Variable
- Data: `{widget_id, variable, plc_id}`
- Sendet aktuellen Cache-Wert sofort zurück
- Bestätigung: `subscribe_success` Event

**✅ `unsubscribe_variable` Event**
- Widget beendet Subscription
- Data: `{widget_id}`
- Bestätigung: `unsubscribe_success` Event

**✅ Error Handling**
- Alle Fehler werden als `error` Event gesendet
- Log-Ausgabe für Debugging

#### 3.4 Shutdown Extension (Lines 1105-1108)
- ✅ Polling Thread wird sauber gestoppt
- ✅ `data_gateway.stop_variable_polling()` aufgerufen

---

### 4. Frontend Implementation (✅ COMPLETE)

**Dateien:**
- `web/static/js/variable-manager.js` (neu erstellt)
- `web/static/js/app.js` (erweitert)
- `web/templates/index.html` (erweitert)

#### 4.1 Variable Manager (JavaScript)

**Datei:** `web/static/js/variable-manager.js` (neu)

**Klasse:** `VariableManager`

**Constructor:**
```javascript
constructor(socket) {
    this.socket = socket;
    this.subscriptions = new Map();  // widget_id → {variable, plc_id, callback}
    this.valueCache = new Map();     // `${plc_id}/${variable}` → {value, timestamp, type}
    this.eventCallbacks = new Map(); // event → Set(callbacks)
    this.stats = {...};
}
```

**Methoden:**
- ✅ `subscribe(widgetId, variable, callback, plcId)` - Widget subscribes
- ✅ `unsubscribe(widgetId)` - Widget unsubscribes
- ✅ `writeVariable(variable, value, plcId)` - Async Write (HTTP POST)
- ✅ `readVariable(variable, useCache, plcId)` - Async Read (HTTP POST)
- ✅ `getCachedValue(variable, plcId)` - Lokaler Cache-Zugriff
- ✅ `on(eventName, callback)` - Event-Handler registrieren
- ✅ `off(eventName, callback)` - Event-Handler entfernen
- ✅ `getStatistics()` - Frontend-Statistiken
- ✅ `getBackendStatistics()` - Backend-Statistiken (Async)
- ✅ `cleanup()` - Cleanup aller Subscriptions

**Event Handling:**
- ✅ `variable_updates` - Updates vom Backend verarbeiten
- ✅ `subscribe_success` - Subscription bestätigt
- ✅ `unsubscribe_success` - Unsubscribe bestätigt
- ✅ `error` - Fehler vom Backend

#### 4.2 Integration in app.js (Line 249-251)

**Änderung in `initializeSocket()`:**
```javascript
// ⭐ v4.6.0: Initialize Variable Manager
this.variableManager = new VariableManager(this.socket.socket);
console.log('✅ Variable Manager initialisiert');
```

#### 4.3 HTML Template (Line 883)

**Änderung in `web/templates/index.html`:**
```html
<script src="/static/js/socket_handler.js"></script>
<script src="/static/js/variable-manager.js"></script> <!-- ⭐ v4.6.0 -->
<script src="/static/js/app.js"></script>
```

---

## ⏳ Offene Aufgaben (Phase 4)

### Phase 4: Widget-Binding Implementation

#### 4.1 Widget-Config Format erweitern

**TODO:** Widget-Config um `variable` Feld erweitern

**Beispiel:**
```json
{
  "widget_001": {
    "id": "widget_001",
    "type": "boolean",
    "page": "dashboard",
    "position": {"x": 100, "y": 100},
    "config": {
      "title": "Wohnzimmer Licht",
      "variable": "Light.Light_EG_WZ.bLight",  // ← NEU
      "plc_id": "plc_001",  // ← NEU (optional)
      "read_only": false
    }
  }
}
```

---

### Phase 4: Widget-Binding Implementation

#### 4.1 Boolean Widget mit Variable-Binding

**TODO:** Widget-Rendering-Logik erweitern

```javascript
// In app.js renderWidget():
if (widget.config.variable) {
    // Subscribe zu Variable
    this.variableManager.subscribe(
        widget.config.variable,
        (value, data) => {
            // Update Widget UI
            this.updateWidgetValue(widget.id, value);
        },
        widget.id
    );
}

// Click-Handler:
async toggleWidget(widgetId) {
    const widget = this.widgets[widgetId];
    const currentValue = this.variableManager.getValue(widget.config.variable);
    const newValue = !currentValue;

    try {
        await this.variableManager.writeVariable(
            widget.config.variable,
            newValue
        );
    } catch (error) {
        console.error('Fehler beim Schalten:', error);
    }
}
```

#### 4.2 Widget-Cleanup bei Remove

**TODO:**
```javascript
removeWidget(widgetId) {
    const widget = this.widgets[widgetId];

    // Unsubscribe von Variable
    if (widget.config.variable) {
        this.variableManager.unsubscribe(
            widget.config.variable,
            this.widgetCallbacks[widgetId],
            widgetId
        );
    }

    // DOM cleanup
    widget.element.remove();
    delete this.widgets[widgetId];
}
```

---

## 🔄 Datenfluss (Implementiert)

### Backend Datenfluss (✅ COMPLETE)

```
┌─────────────────┐
│   TwinCAT PLC   │
└────────┬────────┘
         │ ADS (pyads)
         ▼
┌─────────────────────────┐
│  PLC Communication      │
│  read_by_name()         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Data Gateway           │
│  - Polling Thread       │  ← ✅ IMPLEMENTIERT
│  - _read_subscribed_    │
│    variables()          │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Variable Manager       │  ← ✅ IMPLEMENTIERT
│  - Value Cache          │
│  - Subscriptions        │
│  - Symbol Registry      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Socket.IO Broadcast    │  ← ⏳ TODO
│  emit('variable_updates')│
└─────────────────────────┘
```

### Frontend Datenfluss (⏳ TODO)

```
┌─────────────────────────┐
│  Socket.IO Client       │
│  on('variable_updates') │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Variable Manager (JS)  │  ← ⏳ TODO
│  - Callbacks            │
│  - Cache                │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Widget Update          │  ← ⏳ TODO
│  updateUI(value)        │
└─────────────────────────┘
```

---

## 📊 Architektur-Compliance

### ✅ Einhaltung der bestehenden Architektur

Das implementierte Design **passt perfekt** zur bestehenden Architektur (siehe `docs/ARCHITECTURE.md`):

**Bestehende Layer:**
1. Frontend (HTML/CSS/JS)
2. Web Manager (Flask + SocketIO)
3. Data Gateway (Protocol Abstraction)
4. PLC Communication (pyads)

**Neue Komponenten (erweitern, brechen nicht):**
1. **Variable Manager** - Neue Klasse für Subscription-Management
2. **Polling-Thread** - Erweitert Data Gateway
3. **WebSocket Events** - Neue Events in Web Manager
4. **Frontend Manager** - Neue JS-Klasse

**Keine Breaking Changes!**
- Bestehende API-Endpoints bleiben unverändert
- Bestehende Module funktionieren weiter
- Neue Funktionalität ist optional (nur bei Widget-Binding)

---

## 🎯 Nächste Schritte (Priorität)

### Sofort (Phase 2):

1. **web_manager.py Integration**
   - Variable Manager importieren und initialisieren
   - Polling-Thread starten
   - Socket.IO Events hinzufügen
   - HTTP Endpoints hinzufügen

2. **Test Backend:**
   - Server starten
   - Polling-Thread läuft
   - WebSocket-Verbindung funktioniert

### Danach (Phase 3):

3. **Frontend Variable Manager**
   - `variable-manager.js` erstellen
   - In index.html einbinden
   - WebSocket-Verbindung testen

4. **Widget-Binding**
   - Widget-Config erweitern
   - Rendering-Logik anpassen
   - Boolean Widget testen

---

## 📁 Dateistruktur

```
modules/
├── plc/
│   ├── variable_manager.py  ← ✅ NEU (Phase 1)
│   └── symbol_browser.py
├── gateway/
│   ├── data_gateway.py      ← ✅ ERWEITERT (Phase 1)
│   └── web_manager.py       ← ⏳ TODO (Phase 2)

web/
├── static/
│   └── js/
│       ├── variable-manager.js  ← ⏳ TODO (Phase 3)
│       └── app.js               ← ⏳ TODO (Phase 3)

config/
└── widgets.json  ← ⏳ TODO (Phase 4 - Format erweitern)
```

---

## 🐛 Bekannte Limitierungen

### 1. Polling-Interval

**Aktuell:** Festes Intervall (0.5s = 2 Hz)

**Zukunft:** Adaptive Polling-Rates (siehe VARIABLE_MANAGER_DESIGN.md)
- Fast: 0.1s für kritische Werte (Buttons)
- Normal: 0.5s für Standard (Gauges)
- Slow: 2.0s für unkritische Werte (Statistiken)

### 2. Batch-Reading

**Aktuell:** Einzelne Variablen-Reads

**Zukunft:** Batch-Reading von Strukturen
```python
# Statt:
bOn = plc.read('Light.Light_EG_WZ.bOn')
bOff = plc.read('Light.Light_EG_WZ.bOff')

# Besser:
structure = plc.read_structure('Light.Light_EG_WZ')
# → {'bOn': True, 'bOff': False, ...}
```

### 3. SubItem Index-Berechnung

**Aktuell:** SubItems haben index_group=0, index_offset=0

**Problem:** Kann nicht direkt gelesen werden

**Workaround:** Über Parent-Symbol lesen (pyads macht das automatisch)

---

## 📚 Dokumentation

**Erstellt:**
- ✅ `VARIABLE_MANAGER_DESIGN.md` - Komplettes Design-Dokument
- ✅ `VARIABLE_MANAGER_PROGRESS.md` - Dieser Progress-Report
- ✅ `modules/plc/variable_manager.py` - Inline-Dokumentation
- ✅ `modules/gateway/data_gateway.py` - Inline-Dokumentation (Lines 986-1174)

**TODO:**
- ⏳ `ARCHITECTURE.md` erweitern (Variable Manager Layer)
- ⏳ `API_DOCUMENTATION.md` erweitern (neue Endpoints)
- ⏳ `WIDGET_BINDING_GUIDE.md` erstellen (für Developer)

---

**Status:** 🟢 Phase 1 abgeschlossen - Bereit für Phase 2
**Nächste Session:** Integration in web_manager.py + API Endpoints
**Geschätzte Zeit:** 1-2 Stunden für Phase 2

**Erstellt:** 2026-01-11 02:00
**Letzte Änderung:** 2026-01-11 02:00
