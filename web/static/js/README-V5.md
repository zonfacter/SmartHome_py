# SmartHome Edge OS v5.0 - Frontend Components

Moderne JavaScript-Komponenten für das v5.0 Frontend.

## 📦 Komponenten

### 1. **Symbol Browser v5.0** (`symbol-browser-v5.js`)

Moderner TreeView für PLC-Symbole mit korrekter Type-Detection.

**Features:**
- ✅ Hierarchische Baum-Ansicht
- ✅ Suche nach Symbol-Name
- ✅ Filter nach Type (BOOL, INT, REAL, etc.)
- ✅ Lazy-Loading für große Symbol-Bäume
- ✅ Type-Badges mit Farben
- ✅ Expand/Collapse Animation
- ✅ Symbol-Auswahl mit Callback

**API:**
```javascript
const symbolBrowser = new SymbolBrowserV5({
    container: document.getElementById('symbol-tree'),
    connectionId: 'plc_001',
    onSelect: (symbol) => {
        console.log('Selected:', symbol);
    }
});

// Refresh symbols
await symbolBrowser.loadSymbols(true);

// Search
symbolBrowser.searchQuery = 'Alarm';
symbolBrowser.applyFilters();

// Filter by type
symbolBrowser.filterType = 'BOOL';
symbolBrowser.applyFilters();
```

**Backend-Abhängigkeit:**
- `GET /api/v5/plc/symbols/tree?connection_id=plc_001`
- `GET /api/v5/plc/symbols/search?q=...&connection_id=plc_001`
- `GET /api/v5/plc/symbols/filter/BOOL?connection_id=plc_001`

---

### 2. **Widget Manager v5.0** (`widget-manager-v5.js`)

Erweiterte CRUD-Operationen für Widgets.

**Features:**
- ✅ Widget erstellen/bearbeiten/löschen
- ✅ Symbol-Browser Integration
- ✅ Filter nach Seite/Typ
- ✅ Suche nach Titel
- ✅ Statistik-Dashboard
- ✅ Variable Bindings
- ✅ Icon-Auswahl (Lucide Icons)

**API:**
```javascript
const widgetManager = new WidgetManagerV5({
    container: document.getElementById('widget-manager'),
    onWidgetCreated: (widget) => {
        console.log('Created:', widget);
    },
    onWidgetUpdated: (id, widget) => {
        console.log('Updated:', id, widget);
    },
    onWidgetDeleted: (id) => {
        console.log('Deleted:', id);
    }
});

// Reload widgets
await widgetManager.loadWidgets();

// Open create modal
widgetManager.openCreateModal();

// Open edit modal
widgetManager.openEditModal(widgetId);

// Delete widget
widgetManager.deleteWidget(widgetId);
```

**Backend-Abhängigkeit:**
- `GET /api/widgets`
- `POST /api/widgets`
- `PUT /api/widgets/:id`
- `DELETE /api/widgets/:id`

---

### 3. **Plugin Manager v5.0** (`plugin-manager-v5.js`)

ioBroker-Style Plugin-Verwaltung.

**Features:**
- ✅ Plugin-Liste (Installiert/Verfügbar/Laufend)
- ✅ Plugin-Details mit Ressourcen-Monitoring
- ✅ Start/Stop/Konfigurieren
- ✅ Statistik-Dashboard
- ✅ Filter-Tabs
- ✅ Installation-Dialog

**API:**
```javascript
const pluginManager = new PluginManagerV5({
    container: document.getElementById('plugin-manager')
});

// Reload plugins
await pluginManager.loadPlugins();

// Show plugin detail
pluginManager.showPluginDetail(plugin);

// Filter by tab
pluginManager.filterPlugins('running');
```

**Backend-Abhängigkeit:**
- `GET /api/plugins/installed`
- `GET /api/plugins/available`
- `POST /api/plugins/install`
- `POST /api/plugins/:id/start`
- `POST /api/plugins/:id/stop`

---

### 4. **SmartHome v5.0** (`smarthome-v5.js`)

Zentrale Integration aller v5.0 Features.

**Features:**
- ✅ Auto-Initialisierung aller Komponenten
- ✅ Socket.IO Integration
- ✅ Event-Handling
- ✅ Toast-Notifications
- ✅ Zentrale API

**API:**
```javascript
// Global instance available
window.smarthome

// Get components
const symbolBrowser = smarthome.getSymbolBrowser();
const widgetManager = smarthome.getWidgetManager();
const pluginManager = smarthome.getPluginManager();

// Utilities
smarthome.showToast('Erfolg!', 'success');
await smarthome.syncWidgets();
await smarthome.refreshSymbols('plc_001');

// Debug
const debugInfo = await smarthome.getWidgetDebugInfo();
```

---

## 🚀 Integration in HTML

### Minimal Setup

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <title>SmartHome v5.0</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Socket.IO -->
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body>

    <!-- Symbol Browser -->
    <div id="symbol-tree"></div>

    <!-- Widget Manager -->
    <div id="widget-manager"></div>

    <!-- Plugin Manager -->
    <div id="plugin-manager"></div>

    <!-- Load v5.0 Scripts -->
    <script src="/static/js/symbol-browser-v5.js"></script>
    <script src="/static/js/widget-manager-v5.js"></script>
    <script src="/static/js/plugin-manager-v5.js"></script>
    <script src="/static/js/smarthome-v5.js"></script>

</body>
</html>
```

### Mit SPA (Single Page App)

```javascript
// Page Navigation
function showPage(pageName) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Show selected page
    document.getElementById(`page-${pageName}`)?.classList.add('active');

    // Initialize components on page
    if (pageName === 'symbols') {
        if (!window.smarthome.symbolBrowser) {
            const container = document.getElementById('symbol-tree');
            window.smarthome.symbolBrowser = new SymbolBrowserV5({
                container: container,
                connectionId: 'plc_001'
            });
        }
    }

    if (pageName === 'widgets') {
        if (!window.smarthome.widgetManager) {
            const container = document.getElementById('widget-manager');
            window.smarthome.widgetManager = new WidgetManagerV5({
                container: container
            });
        }
    }

    if (pageName === 'plugins') {
        if (!window.smarthome.pluginManager) {
            const container = document.getElementById('plugin-manager');
            window.smarthome.pluginManager = new PluginManagerV5({
                container: container
            });
        }
    }
}
```

---

## 🎨 Styling

Alle Komponenten nutzen **Tailwind CSS** für Styling.

### Dark Mode

```javascript
// Toggle Dark Mode
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
}

// Auto Dark Mode on Load
if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark');
}
```

### Custom Colors

```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                primary: '#3B82F6',  // Blue
                secondary: '#8B5CF6', // Purple
                success: '#10B981',   // Green
                warning: '#F59E0B',   // Orange
                danger: '#EF4444'     // Red
            }
        }
    }
};
```

---

## 🔌 Events

### Custom Events

```javascript
// Symbol Selected
window.addEventListener('symbol-selected', (e) => {
    console.log('Symbol:', e.detail);
    // Auto-fill widget variable field
    document.getElementById('widget-variable').value = e.detail.full_name;
    document.getElementById('widget-plc-type').value = e.detail.type;
});

// Widget Created
window.addEventListener('widget-created', (e) => {
    console.log('Widget Created:', e.detail);
});
```

### Socket.IO Events

```javascript
// PLC Data Update
smarthome.socket.on('plc_data_update', (data) => {
    console.log('PLC Update:', data);
    // Update widget values
});

// Widget Value Update
smarthome.socket.on('widget_value_update', (data) => {
    console.log('Widget Update:', data);
    // Update UI
});
```

---

## 📊 Debug & Diagnostics

### Widget Debug

```javascript
// Get debug info
const debugInfo = await smarthome.getWidgetDebugInfo();

console.table(debugInfo.widgets);

/*
Output:
┌───────────┬─────────┬──────────────────┬───────┬────────────────┐
│  (index)  │  type   │      title       │ value │ read_successful│
├───────────┼─────────┼──────────────────┼───────┼────────────────┤
│ widget-1  │ switch  │ WZ-EZ Licht      │ true  │ true           │
│ widget-2  │ gauge   │ Temperatur WZ    │ 22.5  │ true           │
└───────────┴─────────┴──────────────────┴───────┴────────────────┘
*/
```

### API Testing

```javascript
// Test Symbol Browser API
const symbols = await fetch('/api/v5/plc/symbols?connection_id=plc_001')
    .then(r => r.json());

console.log(`Loaded ${symbols.count} symbols`);

// Test Widget API
const widgets = await fetch('/api/widgets')
    .then(r => r.json());

console.log(`Loaded ${widgets.count} widgets`);
```

---

## 🐛 Troubleshooting

### Komponente lädt nicht

**Problem**: `Uncaught ReferenceError: SymbolBrowserV5 is not defined`

**Lösung**: Script-Reihenfolge prüfen:
```html
<!-- Richtige Reihenfolge -->
<script src="/static/js/symbol-browser-v5.js"></script>
<script src="/static/js/widget-manager-v5.js"></script>
<script src="/static/js/plugin-manager-v5.js"></script>
<script src="/static/js/smarthome-v5.js"></script> <!-- Zuletzt! -->
```

### Dark Mode funktioniert nicht

**Problem**: Klassen werden nicht angewendet

**Lösung**: Tailwind Dark Mode config:
```javascript
tailwind.config = {
    darkMode: 'class' // Wichtig!
};
```

### Icons werden nicht angezeigt

**Problem**: Lucide Icons fehlen

**Lösung**:
```javascript
// Icons nach dynamischem Content neu initialisieren
if (typeof lucide !== 'undefined') {
    lucide.createIcons();
}
```

---

## 📝 Changelog

### v5.0.0 (2026-01-05)

**Neue Features:**
- ✅ Symbol Browser v5.0
- ✅ Widget Manager v5.0
- ✅ Plugin Manager v5.0
- ✅ Zentrale SmartHome v5.0 Integration
- ✅ Dark Mode Support
- ✅ Tailwind CSS Styling
- ✅ Socket.IO Integration
- ✅ Toast Notifications

**Breaking Changes:**
- Alte Symbol-Browser API deprecated
- Widget API erweitert (neue Bindings-Struktur)

---

**Version**: 5.0.0
**Autor**: TwinCAT Team
**Lizenz**: MIT
