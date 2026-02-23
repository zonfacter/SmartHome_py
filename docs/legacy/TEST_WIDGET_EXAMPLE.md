# Variable Manager - Test Widget Beispiel

**Datum:** 11. Januar 2026 04:00 Uhr
**Status:** ✅ READY FOR TESTING
**Version:** v4.6.0

---

## Quick Start - Widget mit Variable-Binding erstellen

### 1. Test-Widget im Browser Console erstellen

Öffne die Browser Console (F12) und führe folgendes aus:

```javascript
// Test-Widget-Config
const testWidget = {
    id: 'test_light_001',
    type: 'boolean',
    page: 'dashboard',
    title: 'Wohnzimmer Licht (Test)',
    variable: 'Light.Light_EG_WZ.bOn',  // ⭐ Variable-Binding
    plc_id: 'plc_001',                   // ⭐ PLC-ID (optional)
    value: false,                         // Initial-Wert
    position: { x: 50, y: 50 }
};

// Hole Dashboard-Container
const dashboard = document.getElementById('dashboard-page');

// Rendere Widget
app.renderWidget(testWidget, dashboard);

console.log('✅ Test-Widget erstellt!');
console.log('📌 Widget sollte jetzt "Light.Light_EG_WZ.bOn" abonniert haben');
```

### 2. Subscription überprüfen

```javascript
// Zeige alle aktiven Subscriptions
const subscriptions = app.variableManager.getActiveSubscriptions();
console.log('📌 Aktive Subscriptions:', subscriptions);

// Frontend-Statistiken
console.log('📊 Frontend Stats:', app.variableManager.getStatistics());

// Backend-Statistiken
app.variableManager.getBackendStatistics().then(stats => {
    console.log('📊 Backend Stats:', stats);
});
```

### 3. Widget testen

**Klicke auf das Widget:**
- Widget sollte Toggle-Animation zeigen (grün ↔ grau)
- Console sollte zeigen: `🔘 Toggle Widget test_light_001: Light.Light_EG_WZ.bOn = true`
- Nach erfolgreicher PLC-Schreiboperation: `✅ Toggle erfolgreich`

**Live-Updates beobachten:**
```javascript
// Socket.IO Updates überwachen
app.socket.socket.on('variable_updates', (data) => {
    console.log('📡 Variable Update empfangen:', data);
});
```

---

## Test-Szenarien

### Szenario 1: Widget mit echter PLC-Variable

```javascript
// Widget für echte Light-Variable
const lightWidget = {
    id: 'light_wz',
    type: 'boolean',
    title: 'Wohnzimmer',
    variable: 'Light.Light_EG_WZ.bOn',
    plc_id: 'plc_001',
    value: false,
    position: { x: 100, y: 100 }
};

app.renderWidget(lightWidget, document.getElementById('dashboard-page'));
```

**Erwartetes Verhalten:**
1. Widget wird gerendert mit Toggle-Button
2. Subscribe-Request wird an Backend gesendet
3. Aktueller Wert wird vom Backend zurückgesendet
4. Widget zeigt aktuellen PLC-Wert an
5. Klick sendet Write-Request an PLC
6. Polling Thread erkennt Änderung und broadcastet Update

### Szenario 2: Mehrere Widgets für gleiche Variable

```javascript
// Widget 1
app.renderWidget({
    id: 'widget_1',
    type: 'boolean',
    title: 'Licht (Widget 1)',
    variable: 'Light.Light_EG_WZ.bOn',
    position: { x: 50, y: 50 }
}, document.getElementById('dashboard-page'));

// Widget 2
app.renderWidget({
    id: 'widget_2',
    type: 'boolean',
    title: 'Licht (Widget 2)',
    variable: 'Light.Light_EG_WZ.bOn',
    position: { x: 50, y: 150 }
}, document.getElementById('dashboard-page'));
```

**Erwartetes Verhalten:**
- Beide Widgets abonnieren die gleiche Variable
- Backend registriert 2 Subscriber für `Light.Light_EG_WZ.bOn`
- Klick auf Widget 1 → Beide Widgets werden aktualisiert
- Klick auf Widget 2 → Beide Widgets werden aktualisiert

### Szenario 3: Widget ohne Variable (Fallback)

```javascript
// Widget OHNE Variable-Binding
app.renderWidget({
    id: 'widget_no_var',
    type: 'boolean',
    title: 'Ohne Variable',
    // variable: undefined,  // ← Keine Variable!
    position: { x: 300, y: 50 }
}, document.getElementById('dashboard-page'));
```

**Erwartetes Verhalten:**
- Widget wird gerendert
- KEIN Subscribe-Request
- Widget zeigt "Keine Variable"
- Klick zeigt Fehler: `Widget hat keine Variable zugewiesen`

### Szenario 4: Number Widget (erweitert)

```javascript
// Number Widget mit Variable
app.renderWidget({
    id: 'temp_sensor',
    type: 'number',
    title: 'Temperatur',
    variable: 'Sensors.Temperature_EG_WZ',
    position: { x: 300, y: 100 }
}, document.getElementById('dashboard-page'));
```

**Erwartetes Verhalten:**
- Widget subscribes zu `Sensors.Temperature_EG_WZ`
- Updates werden über `updateWidgetValue()` verarbeitet
- Zahl wird automatisch aktualisiert (kein Click-Handler)

---

## Debug-Befehle (Browser Console)

### Variable direkt schreiben
```javascript
await app.variableManager.writeVariable(
    'Light.Light_EG_WZ.bOn',
    true,
    'plc_001'
);
```

### Variable direkt lesen
```javascript
const data = await app.variableManager.readVariable(
    'Light.Light_EG_WZ.bOn',
    true,  // use cache
    'plc_001'
);
console.log('Value:', data.value);
console.log('Timestamp:', new Date(data.timestamp * 1000));
console.log('Type:', data.type);
console.log('Source:', data.source);
```

### Cache-Wert abrufen (sync)
```javascript
const cached = app.variableManager.getCachedValue(
    'Light.Light_EG_WZ.bOn',
    'plc_001'
);
console.log('Cached:', cached);
```

### Widget manuell updaten
```javascript
app.updateWidgetValue('test_light_001', true, 'BOOL');
```

### Widget Subscription beenden
```javascript
app.variableManager.unsubscribe('test_light_001');
```

### Alle Subscriptions anzeigen
```javascript
console.table(app.variableManager.getActiveSubscriptions());
```

### Frontend Stats
```javascript
console.log(app.variableManager.getStatistics());
```

### Backend Stats
```javascript
fetch('/api/variables/statistics')
    .then(r => r.json())
    .then(data => console.log('Backend Stats:', data.statistics));
```

---

## Server-Log Überprüfung

Nach Server-Start (`python main.py`) solltest du folgende Logs sehen:

```
✅ Variable Manager initialisiert
✅ Variable Manager: 1769 Symbole registriert
✅ Variable Polling Thread gestartet (2 Hz)
```

Bei Widget-Subscribe:
```
📌 Widget test_light_001 subscribed to plc_001/Light.Light_EG_WZ.bOn
   Insgesamt 1 Subscriber für diese Variable
```

Bei Widget-Toggle (Write):
```
✍️  Variable geschrieben: plc_001/Light.Light_EG_WZ.bOn = True
```

Bei Polling-Updates (nur wenn Wert sich ändert):
```
💾 Cache aktualisiert: plc_001/Light.Light_EG_WZ.bOn = True
```

---

## Troubleshooting

### Problem: Widget wird nicht aktualisiert

**Ursache:** Polling Thread läuft nicht

**Lösung:**
```javascript
// Prüfe ob Polling läuft (sollte alle 0.5s Updates zeigen)
app.socket.socket.on('variable_updates', (data) => {
    console.log('📡 Polling Update:', data);
});
```

### Problem: "Variable Manager nicht verfügbar"

**Ursache:** Variable Manager nicht initialisiert

**Lösung:**
```javascript
// Prüfe Initialisierung
console.log('Variable Manager:', app.variableManager);

// Manuell initialisieren (falls nötig)
if (!app.variableManager) {
    app.variableManager = new VariableManager(app.socket.socket);
}
```

### Problem: Subscribe schlägt fehl

**Ursache:** Variable existiert nicht in Symbol-Registry

**Lösung:**
```javascript
// Prüfe ob Variable registriert ist
fetch('/api/variables/statistics')
    .then(r => r.json())
    .then(data => {
        console.log('Registrierte Symbole:', data.statistics.total_symbols);
    });

// Prüfe ob Symbol im Cache ist (nach TPY-Upload)
// Sollte > 0 sein
```

### Problem: Write-Operation schlägt fehl

**Ursache 1:** PLC nicht verbunden
**Lösung:** Prüfe PLC-Verbindung in Setup-Seite

**Ursache 2:** Variable ist Read-Only
**Lösung:** Prüfe Variable-Berechtigungen in TwinCAT

**Ursache 3:** Falscher Datentyp
**Lösung:** Prüfe Variable-Type (BOOL, INT, etc.)

---

## Performance-Tests

### Polling-Frequenz messen

```javascript
let updateCount = 0;
let startTime = Date.now();

app.socket.socket.on('variable_updates', (data) => {
    updateCount++;
    const elapsed = (Date.now() - startTime) / 1000;
    const hz = updateCount / elapsed;
    console.log(`📊 Updates: ${updateCount}, Elapsed: ${elapsed.toFixed(1)}s, Freq: ${hz.toFixed(2)} Hz`);
});
```

**Erwartetes Ergebnis:** ~2 Hz (wenn Werte sich ändern)

### Subscription-Overhead messen

```javascript
// Erstelle 10 Widgets
for (let i = 0; i < 10; i++) {
    app.renderWidget({
        id: `perf_test_${i}`,
        type: 'boolean',
        title: `Test ${i}`,
        variable: `Light.Light_EG_WZ.bOn`,
        position: { x: 50 + (i % 5) * 100, y: 50 + Math.floor(i / 5) * 100 }
    }, document.getElementById('dashboard-page'));
}

// Prüfe Stats
setTimeout(() => {
    console.log(app.variableManager.getStatistics());
    // active_subscriptions sollte 10 sein
    // aber nur 1 Backend-Subscription (gruppiert!)
}, 1000);
```

---

## Nächste Schritte nach erfolgreichem Test

1. ✅ **Widget-Persistierung** - Widgets in JSON speichern
2. ✅ **Drag & Drop** - Widgets verschieben und Position speichern
3. ✅ **Widget-Konfiguration** - Variable über UI zuweisen
4. ✅ **Weitere Widget-Typen** - Slider, Gauge mit Write-Funktion
5. ✅ **Adaptive Polling** - Variable Intervalle je nach Widget-Typ
6. ✅ **Batch Reading** - FB-Strukturen in einem Read lesen

---

**Erstellt:** 11. Januar 2026 04:00 Uhr
**Status:** ✅ READY FOR TESTING
**Next:** Server neu starten und Test-Widget erstellen!
