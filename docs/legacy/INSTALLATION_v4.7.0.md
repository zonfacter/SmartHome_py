# 🚀 Installation & Nutzung v4.7.0
## TwinCAT SmartHome Web-HMI - Connectivity & Analytics Expansion

---

## ✅ **Was ist neu in v4.7.0:**

### **1. Variable Explorer (Hierarchischer Browser)**
- 📁 **TreeView für PLC-Symbole** - Browsen Sie Ihre TwinCAT-Variablen hierarchisch
- 🌐 **TreeView für MQTT-Topics** - Visualisierung aller MQTT-Topics
- 📋 **Copy to Clipboard** - Klicken Sie auf eine Variable → Pfad wird kopiert
- ➕ **Widget aus Variable erstellen** - Direkt aus dem Browser ein Widget erstellen
- 🔍 **Live-Suche** - Filtern Sie Tausende von Variablen in Millisekunden

### **2. Widget-Management Verbesserungen**
- 🗑️ **Widgets löschen** - Delete-Button bei Hover (temporär)
- ✏️ **Widgets bearbeiten** - PUT/DELETE APIs vorhanden
- 📝 **Persistente Speicherung** - Alle Änderungen in `widgets.json`

### **3. Monitor-Dashboard Fixes**
- ✅ **Gateway-Status** - Zeigt jetzt korrekt Platform, GPU, Mode
- ✅ **Latenz-Messung** - Funktioniert mit besserer Error-Handling
- ✅ **Cache-Anzeige** - Zeigt Anzahl gecachter Variablen

### **4. System-Stabilität**
- ✅ **Service Hot-Restart** - Funktioniert unter Windows (neues Fenster)
- ✅ **SQLite Logging** - Alle Fehler persistent in DB
- ✅ **Auto-Type-Detection** - PLC-Writes ohne expliziten Typ

---

## 📦 **Installation der neuen Komponenten:**

### **1. JavaScript-Komponenten einbinden**

Fügen Sie folgende Zeilen zu `web/templates/index.html` hinzu (vor `</body>`):

```html
<!-- TreeView Component -->
<script src="/static/js/components/tree_view.js"></script>

<!-- Variable Explorer -->
<script src="/static/js/components/variable_explorer.js"></script>
```

### **2. Variable Explorer in Admin-Seite integrieren**

Fügen Sie folgenden HTML-Block zur Admin-Seite hinzu:

```html
<!-- Variable Explorer Section -->
<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
    <h2 class="text-2xl font-bold mb-4 flex items-center">
        <i data-lucide="folder-tree" class="w-6 h-6 mr-2"></i>
        Variable Explorer
    </h2>

    <!-- Tabs -->
    <div class="border-b border-gray-200 dark:border-gray-700 mb-4">
        <nav class="flex space-x-4">
            <button id="explorer-tab-plc"
                    class="px-4 py-2 border-b-2 border-blue-500 text-blue-600 font-semibold">
                PLC-Symbole
            </button>
            <button id="explorer-tab-mqtt"
                    class="px-4 py-2 border-b-2 border-transparent text-gray-500 hover:text-gray-700">
                MQTT-Topics
            </button>
        </nav>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Tree-View Container -->
        <div class="lg:col-span-2">
            <!-- PLC Tree -->
            <div id="explorer-content-plc">
                <div id="plc-variable-tree"></div>
            </div>

            <!-- MQTT Tree -->
            <div id="explorer-content-mqtt" class="hidden">
                <div id="mqtt-topic-tree"></div>
            </div>
        </div>

        <!-- Info Panel -->
        <div class="lg:col-span-1">
            <div id="variable-info-panel" class="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <p class="text-gray-500 dark:text-gray-400 text-center">
                    Wählen Sie eine Variable aus
                </p>
            </div>
        </div>
    </div>
</div>
```

### **3. Variable Explorer initialisieren**

Fügen Sie in `app.js` zur `loadAdminPage()` Methode hinzu:

```javascript
async loadAdminPage() {
    console.log('👑 Lade Admin...');
    await this.loadPLCConfigs();
    await this.loadLogs();
    await this.loadServiceInfo();

    // NEU: Variable Explorer initialisieren
    if (!variableExplorer) {
        variableExplorer = new VariableExplorer(this);
        await variableExplorer.init();
    }

    // ... rest des Codes
}
```

---

## 🎯 **Nutzung des Variable Explorers:**

### **PLC-Symbole browsen:**

1. **Admin-Seite öffnen**: http://localhost:5001 → Admin
2. **"Variable Explorer" Section** nach unten scrollen
3. **Tab "PLC-Symbole"** ist standardmäßig aktiv
4. **Hierarchie durchsuchen**:
   - Ordner-Icons (📁) sind klickbar → Expand/Collapse
   - Variable-Icons variieren nach Typ:
     - 🟢 BOOL (Grün)
     - 🔵 INT/DINT (Blau)
     - 🟣 REAL/LREAL (Lila)
     - 🟡 STRING (Gelb)

### **Variable verwenden:**

#### **Methode 1: Copy & Paste**
1. Klick auf Variable
2. Pfad wird automatisch in Zwischenablage kopiert
3. Toast-Nachricht erscheint: "📋 Kopiert: MAIN.lights.livingroom"
4. Einfügen wo benötigt

#### **Methode 2: Widget erstellen**
1. Variable anklicken
2. Im Info-Panel rechts erscheinen Details
3. Button **"➕ Widget erstellen"** klicken
4. Widget wird automatisch auf Dashboard erstellt!

#### **Methode 3: Drag & Drop** (geplant für v4.8)
1. Variable mit Maus ziehen
2. Auf Dashboard/Page droppen
3. Widget wird an Position erstellt

### **Suche verwenden:**

1. Suchfeld oben im Tree nutzen
2. Echtzeit-Filterung während Tippen
3. Zeigt nur matchende Variablen + Parents
4. Löschen → Alle Variablen wieder sichtbar

---

## 🌐 **MQTT-Topics browsen:**

### **Vorbereitung:**
1. MQTT-Broker verbinden (Setup → MQTT)
2. Warten bis Topics empfangen werden

### **Nutzung:**
1. Admin → Variable Explorer
2. Tab **"MQTT-Topics"** anklicken
3. Hierarchie wird automatisch generiert:
   ```
   homeassistant/
   ├── sensor/
   │   ├── temperature/
   │   │   └── state  (22.5°C)
   │   └── humidity/
   │       └── state  (65%)
   └── switch/
       └── light_living/
           └── state  (ON)
   ```

4. Topic anklicken → Pfad kopiert
5. Widget erstellen → Bindet an MQTT-Topic

---

## 📊 **Monitor-Dashboard:**

### **Gateway-Status prüfen:**
- http://localhost:5001 → Monitor
- **Gateway** Card zeigt:
  - Platform: `Windows (Intel GPU)` oder `Linux (VAAPI)`
  - Cache: `42 Variablen`
  - Mode: Docker/VM-Status

### **Latenz messen:**
- Button **"Latenz messen"** klicken
- Ergebnisse:
  - ✅ **PLC (ADS)**: `12.34 ms` (wenn verbunden)
  - ⚠️ **PLC**: `Nicht verbunden` (wenn offline)
  - 🟣 **WebSocket**: `5.00 ms` (geschätzt)

---

## 🛠️ **Entwickler-Tipps:**

### **TreeView in eigenen Seiten verwenden:**

```javascript
// TreeView erstellen
const myTree = new TreeView('my-container-id', {
    draggable: true,
    searchable: true,
    expandLevel: 2,
    onNodeClick: (node) => {
        console.log('Clicked:', node.full_path);
    }
});

// Daten laden und rendern
const treeData = [
    {
        name: 'MAIN',
        type: 'folder',
        children: [
            {
                name: 'bLight1',
                type: 'symbol',
                full_path: 'MAIN.bLight1',
                data_type: 'BOOL'
            }
        ]
    }
];

myTree.render(treeData);
```

### **Variable Explorer API:**

```javascript
// Variable zu Widget binden
await variableExplorer.createWidget('MAIN.temperature', 'REAL');

// Refresh Trees
await variableExplorer.refresh();

// Programmatisch zu Tab wechseln
variableExplorer.switchTab('mqtt');
```

---

## 🔧 **Troubleshooting:**

### **"PLC-Symbole können nicht geladen werden"**
**Ursache:** Keine .tpy Datei hochgeladen

**Lösung:**
1. Admin → PLC-Konfiguration
2. "Upload .tpy" Button
3. TwinCAT_Project.tpy auswählen
4. Refresh Variable Explorer

### **"MQTT nicht verbunden"**
**Ursache:** Kein MQTT-Broker konfiguriert

**Lösung:**
1. Setup → MQTT
2. Broker-Adresse eingeben
3. Verbinden
4. Variable Explorer refreshen

### **"Widget wird nicht erstellt"**
**Ursache:** Keine Page ausgewählt oder falscher Typ

**Lösung:**
- Prüfen Sie `config/widgets.json`
- Standardmäßig werden Widgets auf `dashboard` erstellt
- Manuell Page ändern via API:
  ```bash
  curl -X PUT http://localhost:5001/api/widgets/<id> \
       -H "Content-Type: application/json" \
       -d '{"page": "lighting"}'
  ```

---

## 📚 **Nächste Schritte:**

### **Geplant für v4.8:**
- ✨ **Widget-Editor Dialog** - Vollständiger WYSIWYG-Editor
- 🖱️ **Drag & Drop** - Variablen direkt auf Seiten ziehen
- 🔗 **Multi-Connection** - Mehrere PLCs/MQTT-Broker gleichzeitig
- 📈 **Hardware Monitor (HAL)** - CPU/GPU/RAM Live-Monitoring
- 🎨 **Theme-Editor** - Custom Themes erstellen

### **v4.6.0 Vision:**
- 🤖 **Auto-Widget-Generator** - KI generiert Widgets aus Variablen
- 📱 **Mobile App** - Native iOS/Android App
- 🔐 **User-Management** - Multi-User mit Permissions
- 📊 **Historische Daten** - Time-Series DB Integration

---

## 💬 **Support & Feedback:**

- 🐛 **Bugs melden**: [GitHub Issues](https://github.com/your-repo/issues)
- 💡 **Feature Requests**: Roadmap diskutieren
- 📖 **Dokumentation**: `FEATURE_ROADMAP.md`

---

**Version**: 4.7.0
**Build-Datum**: 2026-01-04
**Autor**: TwinCAT Team
**Lizenz**: MIT
