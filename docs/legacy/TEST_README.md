# TwinCAT SmartHome HMI - Test Suite Dokumentation

## Übersicht

Diese Test-Suite wurde erstellt, um die verbleibenden Bugs im TwinCAT SmartHome HMI System systematisch zu diagnostizieren und zu beheben.

## Aktuelle bekannte Probleme

1. **HTTP 400 bei Live-Symbol-Abruf** - `/api/plc/symbols/live` gibt 400 zurück
2. **Widget wird nicht angezeigt** - Widget wird erstellt, aber nicht im DOM gerendert
3. **TreeView-Struktur fehlerhaft** - Nur 751 statt 952 Symbole, Hierarchie defekt
4. **Suche funktioniert nicht** - Symbol-Suchfunktion liefert keine Ergebnisse

## Test-Suite starten

### Voraussetzungen

1. Server muss laufen (`python main.py`)
2. Chrome Browser mit DevTools (F12)
3. HMI im Browser geöffnet

### Installation

1. Öffne Chrome DevTools (F12)
2. Navigiere zum "Console" Tab
3. Kopiere den gesamten Inhalt von `TEST_CONSOLE_SCENARIOS.js`
4. Füge ihn in die Console ein und drücke Enter

Nach dem Laden siehst du die verfügbaren Test-Funktionen.

## Verfügbare Tests

### Einzelne Tests

```javascript
// System-Status prüfen
await test1_SystemStatus()

// PLC-Verbindung testen
await test2_PLCConnection()

// Symbol-Cache abrufen
await test3_SymbolCache()

// Live-Symbol-Abruf von PLC (testet HTTP 400 Problem)
await test4_LiveSymbolLoad()

// Symbol-Suche testen (testet Suchfunktion)
await test5_SymbolSearch("MAIN")

// Widget erstellen und DOM-Rendering prüfen (testet Widget-Display-Problem)
await test6_WidgetCreate()

// Alle Widgets auflisten
await test7_WidgetList()

// TPY-Upload Anleitung anzeigen
test8_TPYUploadInfo()

// TreeView-Daten analysieren (testet 751 vs 952 Problem)
await test9_TreeViewData()

// WebSocket-Status prüfen
test10_WebSocketInfo()
```

### Hilfsfunktionen

```javascript
// Mit PLC verbinden (behebt HTTP 400 Problem)
await connectPLC()

// PLC trennen
await disconnectPLC()

// Symbol-Verlust analysieren (analysiert 751 vs 952)
await analyzeSymbolLoss()
```

### Vollständige Test-Suite

```javascript
// Alle Tests nacheinander ausführen
await runAllTests()
```

## Empfohlener Test-Workflow

### 1. Schnelltest für alle Hauptprobleme

```javascript
await runAllTests()
```

Dies führt alle 10 Tests nacheinander aus und gibt eine Zusammenfassung.

### 2. Spezifische Problem-Diagnose

#### Problem: HTTP 400 bei Live-Symbol-Abruf

```javascript
// Schritt 1: System-Status prüfen
await test1_SystemStatus()

// Schritt 2: Wenn PLC nicht verbunden -> verbinden
await connectPLC()

// Schritt 3: Live-Symbol-Abruf testen
await test4_LiveSymbolLoad()
```

**Erwartetes Ergebnis:**
- Wenn PLC verbunden: Symbole werden geladen (Anzahl wird angezeigt)
- Wenn PLC nicht verbunden: Klare Fehlermeldung mit Lösungsvorschlägen

#### Problem: Widget wird nicht angezeigt

```javascript
// Widget erstellen und DOM-Check durchführen
await test6_WidgetCreate()

// Alle Widgets auflisten
await test7_WidgetList()
```

**Erwartetes Ergebnis:**
- Widget wird im DOM gefunden: `✅ Widget im DOM gefunden!`
- Widget ist sichtbar: `Sichtbar: true`
- Widget Manager enthält Widget: `✅ Widget in widgetManager.widgets gefunden`

#### Problem: TreeView zeigt nur 751 statt 952 Symbole

```javascript
// Detaillierte TreeView-Analyse
await test9_TreeViewData()

// Symbol-Verlust analysieren
await analyzeSymbolLoss()
```

**Erwartetes Ergebnis:**
- Zeigt welche Symbole fehlen
- Analysiert ob Duplikate der Grund sind (201 Symbole = 952 - 751)
- Zeigt Hierarchie und Tiefe der Symbole
- Prüft DOM-Rendering

#### Problem: Suche funktioniert nicht

```javascript
// Suche mit bekanntem Symbol testen
await test5_SymbolSearch("MAIN")

// Alternative Suchbegriffe testen
await test5_SymbolSearch("GVL")
await test5_SymbolSearch("PRG")
```

**Erwartetes Ergebnis:**
- Backend-API findet Symbole
- Frontend-Eingabefeld wird getestet
- TreeView wird gefiltert

## Interpretieren der Testergebnisse

### ✅ Erfolgreiche Tests

```
✅ Response Status: 200
✅ SUCCESS: 751 Symbole geladen
```

### ❌ Fehlgeschlagene Tests

```
❌ FEHLER: PLC nicht verbunden
💡 Lösung: PLC-Verbindung zuerst herstellen
```

### ⚠️ Warnungen

```
⚠️ WARNUNG: Keine Symbole im Cache!
💡 Tipp: TPY hochladen oder Live-Abruf verwenden
```

## Bug-Analyse Checkliste

Nachdem du die Tests ausgeführt hast, fülle diese Checkliste aus:

### Test 1: System Status
- [ ] API antwortet: `status` Property vorhanden
- [ ] PLC-Status: `plc.connected` wird korrekt angezeigt
- [ ] Fehler: _____________________

### Test 2: PLC Verbindung
- [ ] PLC Config geladen
- [ ] Active PLCs: _____
- [ ] Fehler: _____________________

### Test 3: Symbol-Cache
- [ ] Symbol Count: _____ (erwartet: 751 oder 952)
- [ ] Symbol-Struktur korrekt (name, type, index_group, index_offset)
- [ ] Fehler: _____________________

### Test 4: Live Symbol Load
- [ ] PLC verbunden vor Test
- [ ] HTTP Status: _____ (erwartet: 200)
- [ ] Symbole geladen: _____
- [ ] Fehler: _____________________

### Test 5: Symbol-Suche
- [ ] Backend-API findet Symbole: _____ Treffer
- [ ] Frontend-Input reagiert
- [ ] TreeView wird gefiltert
- [ ] Fehler: _____________________

### Test 6: Widget-Erstellung
- [ ] Widget wird erstellt (HTTP 200)
- [ ] Widget-ID erhalten: _____
- [ ] Widget im DOM gefunden
- [ ] Widget ist sichtbar
- [ ] Widget in widgetManager
- [ ] Fehler: _____________________

### Test 7: Widget-Liste
- [ ] Anzahl Widgets: _____
- [ ] Widget-Daten vollständig
- [ ] Fehler: _____________________

### Test 9: TreeView-Daten
- [ ] Symbol Count: _____ (erwartet: 751)
- [ ] Fehlende Symbole: _____ (erwartet: 201)
- [ ] Duplikate gefunden: _____
- [ ] TreeView DOM gerendert: _____ Nodes
- [ ] Fehler: _____________________

### Test 10: WebSocket
- [ ] socketHandler gefunden
- [ ] Socket connected: _____
- [ ] Socket.IO library geladen
- [ ] Fehler: _____________________

## Bekannte Fixes

### Fix 1: HTTP 400 - PLC nicht verbunden

**Problem:** `/api/plc/symbols/live` gibt HTTP 400 zurück

**Ursache:** PLC-Verbindung ist nicht aktiv (Line 436-437 in web_manager.py)

**Lösung:**
```javascript
await connectPLC()  // Erst verbinden
await test4_LiveSymbolLoad()  // Dann testen
```

### Fix 2: 751 statt 952 Symbole

**Problem:** Nur 751 Symbole werden geladen statt 952

**Analyse:** 201 Symbole werden als Duplikate gefiltert (symbol_browser.py:261-278)

**Mögliche Ursachen:**
1. TPY-Datei enthält tatsächlich 201 Duplikate (NORMAL)
2. Duplikat-Filter ist zu aggressiv (BUG - verschiedene Typen mit gleichem Namen)
3. XML-Parsing erfasst gleiche Elemente mehrfach

**Diagnose:**
```javascript
await analyzeSymbolLoss()
```

## Server-Log-Monitoring

Während du die Tests ausführst, beobachte die Server-Logs auf:

```
✅ ERFOLG: 751 Symbole geladen und gecacht
pyads: 751 Symbole von PLC empfangen
Symbol-Cache aktualisiert: 751 Symbole gespeichert
```

## Nächste Schritte

1. **Tests ausführen:** Kopiere `TEST_CONSOLE_SCENARIOS.js` in Chrome Console
2. **runAllTests() starten:** Führe vollständige Test-Suite aus
3. **Ergebnisse analysieren:** Notiere alle ✅, ❌, ⚠️ Meldungen
4. **Checkliste ausfüllen:** Dokumentiere Befunde
5. **Logs bereitstellen:** Kopiere Console-Output und Server-Logs

## Support

Bei Fragen oder unerwarteten Ergebnissen:
1. Kopiere den gesamten Console-Output
2. Kopiere die relevanten Server-Logs
3. Teile die ausgefüllte Checkliste

## Changelog

### Version 1.1 (2026-01-10)
- Erweiterte Test 4 (Live Symbol Load) mit PLC-Verbindungsprüfung
- Erweiterte Test 5 (Symbol-Suche) mit Frontend-DOM-Checks
- Erweiterte Test 6 (Widget-Erstellung) mit DOM-Rendering-Prüfung
- Erweiterte Test 9 (TreeView) mit detaillierter Symbol-Analyse
- Hinzugefügt: `connectPLC()` Hilfsfunktion
- Hinzugefügt: `disconnectPLC()` Hilfsfunktion
- Hinzugefügt: `analyzeSymbolLoss()` Hilfsfunktion

### Version 1.0 (2026-01-10)
- Initiale Test-Suite mit 10 Test-Funktionen
- Vollständige Test-Suite `runAllTests()`
