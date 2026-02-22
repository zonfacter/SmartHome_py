# 🚀 Quick Start Integration Guide
## TwinCAT SmartHome v4.7.0 - Manuelle Integration

**⏱️ Geschätzte Zeit: 10 Minuten**

---

## ✅ **Was bereits implementiert ist (Backend):**

1. ✅ TreeView Component (`web/static/js/components/tree_view.js`)
2. ✅ Variable Explorer (`web/static/js/components/variable_explorer.js`)
3. ✅ Widget CRUD APIs (`/api/widgets/*`)
4. ✅ Config Manager Widget-Methods (`get_widgets()`, `add_widget()`, etc.)
5. ✅ Monitor Hardware Data (`psutil` Integration)
6. ✅ PLC Symbol-Tree API (`/api/plc/symbols/tree`)

---

## 📋 **Was Sie jetzt tun müssen:**

### **Schritt 1: JavaScript-Dateien einbinden** (2 Minuten)

Öffnen Sie `web/templates/index.html` und fügen Sie **VOR `</body>`** hinzu:

```html
<!-- Variable Explorer Components -->
<script src="/static/js/components/tree_view.js"></script>
<script src="/static/js/components/variable_explorer.js"></script>

<!-- Existing closing body tag -->
</body>
```

**Position:** Nach allen anderen `<script>`-Tags, aber vor `</body>`.

---

### **Schritt 2: Variable Explorer HTML hinzufügen** (5 Minuten)

Finden Sie in `web/templates/index.html` die Admin-Seite (`<div id="page-admin"`).

Fügen Sie **am Ende der Admin-Seite** (vor dem schließenden `</div>`) ein:

```html
<!-- Variable Explorer Section -->
<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
    <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-bold flex items-center">
            <i data-lucide="folder-tree" class="w-6 h-6 mr-2"></i>
            Variable Explorer
        </h2>
        <button onclick="variableExplorer?.refresh()"
                class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center">
            <i data-lucide="refresh-cw" class="w-4 h-4 mr-2"></i>
            Refresh
        </button>
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200 dark:border-gray-700 mb-4">
        <nav class="flex space-x-4">
            <button id="explorer-tab-plc"
                    class="px-4 py-2 border-b-2 border-blue-500 text-blue-600 dark:text-blue-400 font-semibold">
                <i data-lucide="cpu" class="w-4 h-4 inline mr-1"></i>
                PLC-Symbole
            </button>
            <button id="explorer-tab-mqtt"
                    class="px-4 py-2 border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                <i data-lucide="wifi" class="w-4 h-4 inline mr-1"></i>
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
                <p class="text-gray-500 dark:text-gray-400 text-center text-sm">
                    <i data-lucide="info" class="w-8 h-8 mx-auto mb-2"></i>
                    Wählen Sie eine Variable aus
                </p>
            </div>
        </div>
    </div>
</div>
```

---

### **Schritt 3: Variable Explorer initialisieren** (2 Minuten)

Öffnen Sie `web/static/js/app.js` und finden Sie die `loadAdminPage()` Methode.

Fügen Sie **am Anfang der Methode** hinzu:

```javascript
async loadAdminPage() {
    console.log('👑 Lade Admin...');

    // NEU: Variable Explorer initialisieren
    if (typeof VariableExplorer !== 'undefined' && !window.variableExplorer) {
        window.variableExplorer = new VariableExplorer(this);
        await variableExplorer.init();
    }

    // Existing code continues...
    await this.loadPLCConfigs();
    await this.loadLogs();
    await this.loadServiceInfo();
    // ... rest of the method
}
```

---

### **Schritt 4: Hardware-Monitor im Frontend anzeigen** (1 Minute)

Optional: Erweitern Sie die Monitor-Seite um Hardware-Daten.

In `app.js` → `updateMonitorStats()` hinzufügen:

```javascript
updateMonitorStats(data) {
    // ... existing code ...

    // NEU: Hardware-Daten
    if (data.hardware && !data.hardware.error) {
        const cpuElem = document.getElementById('monitor-cpu');
        const memElem = document.getElementById('monitor-memory');

        if (cpuElem) cpuElem.textContent = `${data.hardware.cpu_percent.toFixed(1)}%`;
        if (memElem) memElem.textContent = `${data.hardware.memory_percent.toFixed(1)}%`;
    }
}
```

Fügen Sie entsprechende HTML-Elemente zur Monitor-Seite hinzu:

```html
<div class="stat-card">
    <div class="stat-label">CPU</div>
    <div id="monitor-cpu" class="stat-value">-</div>
</div>
<div class="stat-card">
    <div class="stat-label">RAM</div>
    <div id="monitor-memory" class="stat-value">-</div>
</div>
```

---

## 🧪 **Testen:**

### **1. Server neu starten:**
```bash
python -X utf8 start_web_hmi.py --port 5001
```

### **2. Admin-Seite öffnen:**
```
http://localhost:5001
→ Admin
```

### **3. Variable Explorer prüfen:**
- ✅ Sollte PLC-Symbole als Baum anzeigen
- ✅ Klick auf Variable → Pfad wird kopiert
- ✅ Button "Widget erstellen" funktioniert

### **4. Monitor-Seite prüfen:**
```
http://localhost:5001
→ Monitor
```

- ✅ Gateway zeigt: "Windows (Intel GPU)"
- ✅ CPU/RAM Werte (wenn psutil installiert)
- ✅ Latenz-Messung funktioniert

---

## 🔧 **Troubleshooting:**

### **"TreeView is not defined"**
**Problem:** Scripts nicht geladen

**Lösung:**
1. Prüfen Sie `index.html` → Scripts vor `</body>`
2. Browser-Cache leeren (Ctrl+F5)
3. Konsole öffnen (F12) → Fehler prüfen

---

### **"PLC-Symbole können nicht geladen werden"**
**Problem:** Keine .tpy Datei

**Lösung:**
1. Admin → PLC-Konfiguration
2. "Upload .tpy" Button
3. `TwinCAT_Project.tpy` auswählen

---

### **"psutil not found" Fehler**
**Problem:** psutil nicht installiert

**Lösung:**
```bash
pip install psutil --break-system-packages
```

Oder in `requirements.txt` hinzufügen:
```
psutil>=5.9.0
```

---

### **Widget wird nicht persistent gespeichert**
**Problem:** Config-Datei fehlt

**Lösung:**
- System erstellt automatisch `Documents/TwinCAT_SmartHome/twincat_config.json`
- Prüfen Sie Schreibrechte auf dem Ordner

---

## 📊 **Nächste Features (v4.8):**

Nach erfolgreicher Integration können Sie implementieren:

1. **Widget-Editor Dialog** - WYSIWYG-Editor für Widgets
2. **Drag & Drop** - Variablen direkt auf Seiten ziehen
3. **MQTT Topic-Browser** - Hierarchische Topic-Ansicht
4. **Multi-Connection** - Mehrere PLCs/MQTT-Broker

Siehe `FEATURE_ROADMAP.md` für Details.

---

## 💡 **Quick Tips:**

### **Variable zu Widget binden:**
```javascript
// In Browser-Konsole (F12):
await variableExplorer.createWidget('MAIN.temperature', 'REAL');
```

### **Widget programmatisch erstellen:**
```javascript
await fetch('/api/widgets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        type: 'gauge',
        title: 'Temperatur',
        page: 'dashboard',
        bindings: {
            value: {
                variable: 'MAIN.fTemperature',
                plc_type: 'REAL'
            }
        }
    })
});
```

### **Widget löschen:**
```javascript
await fetch('/api/widgets/widget_id', { method: 'DELETE' });
```

---

**Fertig! 🎉 Ihr System ist jetzt v4.7.0-kompatibel.**

Bei Problemen: Prüfen Sie Browser-Konsole (F12) und Server-Logs.
