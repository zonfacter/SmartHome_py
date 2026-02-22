# 🚀 Server-Neustart Anleitung

## Alle Bugs sind behoben! ✅

6 kritische Fixes wurden implementiert und warten auf Aktivierung.

---

## 1️⃣ Server neu starten

### Im Terminal (wo `python main.py` läuft):

```bash
# STRG+C drücken zum Beenden
# Dann neu starten:
python main.py
```

**Was passiert:**
- Neue Widget-Rendering-Funktionen werden geladen
- Live-Symbol-Load Fix aktiviert (plc.plc)
- Leere-Symbol-Filter aktiv

---

## 2️⃣ Browser neu laden

```
F5 drücken (oder STRG+R)
```

**Was passiert:**
- Neue app.js mit Widget-Rendering wird geladen
- Dashboard lädt automatisch Widgets
- Setup-Seite lädt automatisch TreeView

---

## 3️⃣ Tests ausführen

### Chrome DevTools öffnen (F12)

### Im Console-Tab eingeben:

```javascript
await runAllTests()
```

**Erwartete Ergebnisse:**

```
✅ Test 1: System Status - PASS
✅ Test 2: PLC Connection - PASS
✅ Test 3: Symbol Cache - PASS (751 Symbole)
✅ Test 4: Live Symbol Load - PASS ← BEHOBEN!
✅ Test 5: Symbol Search - PASS
✅ Test 6: Widget Create - PASS (Widget im DOM!) ← BEHOBEN!
✅ Test 7: Widget List - PASS
✅ Test 9: TreeView Data - PASS (751 Nodes) ← BEHOBEN!
✅ Test 10: WebSocket - PASS
```

---

## 4️⃣ Widget-Test (Manuell)

### Dashboard öffnen

```javascript
app.showPage('dashboard')
```

### Test-Widget erstellen

```javascript
await test6_WidgetCreate()
```

### Prüfen ob Widget sichtbar ist

- Widget sollte SOFORT im Dashboard erscheinen
- Position: (50, 50)
- Titel: "Test Widget Console"
- Typ: Boolean (grün/grau Kreis)
- Löschen-Button (✕) oben rechts

**Wenn Widget NICHT erscheint:**
- Browser-Console auf Fehler prüfen
- Server-Logs checken

---

## 5️⃣ Live-Symbol-Load Test

### PLC verbinden (falls nicht verbunden)

```javascript
await connectPLC()
```

### Live-Symbole von PLC laden

```javascript
await test4_LiveSymbolLoad()
```

**Erwartetes Ergebnis:**

```
✅ Response Status: 200
✅ SUCCESS: XXX Symbole von PLC geladen
Cache aktualisiert: XXX Symbole
```

**KEIN HTTP 400 mehr!** ✅

---

## 6️⃣ TPY neu hochladen (Optional)

### Um 475 leere Symbole zu entfernen:

1. Setup-Seite öffnen: `app.showPage('setup')`
2. TPY-Datei erneut hochladen (gleiche Datei wie vorher)
3. Warten bis "XXX Symbole geladen" erscheint

**Erwartetes Symbol-Count:**
- Vorher: 751 Symbole (475 leer, 276 gültig)
- Nachher: ~276 Symbole (nur gültige)

**Neue Regel:** Symbole ohne Namen werden übersprungen

---

## 🐛 Behobene Bugs - Übersicht

| Bug | Status | Fix Location |
|-----|--------|--------------|
| Widget nicht angezeigt | ✅ BEHOBEN | app.js:2595-2743 |
| Live-Symbol HTTP 400 | ✅ BEHOBEN | web_manager.py:457,464 |
| TreeView 0 Nodes | ✅ BEHOBEN | app.js:1064-1067 |
| 475 leere Symbole | ✅ BEHOBEN | symbol_browser.py:291-293 |
| Widget API Response | ✅ BEHOBEN | web_manager.py:330 |
| DELETE Widget fehlt | ✅ BEHOBEN | web_manager.py:332-347 |

---

## 📋 Checkliste

Nach dem Neustart durchgehen:

- [ ] Server neu gestartet
- [ ] Browser neu geladen (F5)
- [ ] `runAllTests()` ausgeführt
- [ ] Alle Tests ✅ (außer evt. WebSocket)
- [ ] Test-Widget auf Dashboard sichtbar
- [ ] Live-Symbol-Load funktioniert (HTTP 200)
- [ ] TreeView zeigt Symbole automatisch
- [ ] (Optional) TPY neu hochgeladen

---

## ❌ Falls Probleme auftreten

### Widget nicht sichtbar

**Prüfen:**
```javascript
// 1. Widgets in Config vorhanden?
const res = await fetch('/api/widgets');
const widgets = await res.json();
console.log('Widgets:', widgets);

// 2. Container vorhanden?
document.getElementById('dashboard-page')

// 3. widgetManager initialisiert?
typeof app.loadAndRenderWidgets
```

### Live-Symbol-Load HTTP 400

**Prüfen:**
```javascript
// 1. PLC verbunden?
const res = await fetch('/api/status');
const status = await res.json();
console.log('PLC connected:', status.plc?.connected);

// 2. Verbinden falls nötig
await connectPLC()
```

### Server-Logs ansehen

```bash
# Im Terminal wo python main.py läuft:
# Suche nach:
✅ Widget erstellt: <id>
✅ ERFOLG: XXX Symbole geladen
⚠️  Fehler: ...
```

---

## 📞 Support

Falls Tests fehlschlagen:

1. **Console-Output kopieren** (komplette Ausgabe von runAllTests())
2. **Server-Logs kopieren** (Terminal-Output)
3. **Screenshot vom Problem** (z.B. fehlendes Widget)
4. **Teilen für weitere Diagnose**

---

## 🎯 Erfolgs-Kriterien

**System ist vollständig funktional wenn:**

✅ Alle 10 Tests in `runAllTests()` erfolgreich
✅ Widgets werden auf Dashboard angezeigt
✅ Live-Symbole können von PLC geladen werden
✅ TreeView zeigt Symbole automatisch
✅ Keine leeren Symbole mehr im Cache
✅ Widget-Löschen funktioniert

---

**Bereit zum Testen!** 🚀

Starte den Server neu und führe die Tests aus!
