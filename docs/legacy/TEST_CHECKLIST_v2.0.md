# 🧪 Version 2.0.0 - Vollständige Test-Checklist

**Datum:** 2024-11-30  
**Version:** 2.0.0  
**Status:** READY FOR TESTING

---

## 📋 Test-Kategorien

### ✅ 1. Module Loading (KRITISCH)

**Ziel:** Alle Module laden fehlerfrei

- [ ] Core-Module laden (plc_communication, config_manager, symbol_manager, update_loop)
- [ ] UI-Module laden (gui_manager, status_bar, card_manager, card_renderer, search_filter, context_menu, drag_drop, tab_manager)
- [ ] Integration-Module laden (modbus, mqtt, rtsp)
- [ ] Plugin-Module laden (light, temperature, gauge, weather)
- [ ] Keine Dependency-Fehler
- [ ] Module-Status-Summary zeigt alle als "geladen"

**Kommando:**
```bash
cd /mnt/user-data/outputs
python Haussteuerung_v2.py
```

---

### ✅ 2. Status-Leiste (NEU in v2.0)

**Features zu testen:**

- [ ] Status-Leiste wird oben angezeigt
- [ ] PLC-Status Indikator (● grün/rot)
- [ ] AMS Net ID wird angezeigt
- [ ] Datum & Uhrzeit korrekt (Format: Wochentag, DD.MM.YYYY, HH:MM:SS)
- [ ] Sonnenaufgang-Zeit für Haltern am See
- [ ] Sonnenuntergang-Zeit für Haltern am See
- [ ] Mondphase-Symbol (🌑🌒🌓🌔🌕🌖🌗🌘)
- [ ] Auto-Update jede Sekunde
- [ ] Zeitzonen-Handling (MEZ/MESZ)

**Erwartetes Aussehen:**
```
● 5.1.38.60 | Samstag, 30.11.2024, 20:45:32 | ☀️ Auf: 08:12 | Unter: 16:32 | 🌘
```

---

### ✅ 3. Card-Manager (NEU in v2.0)

**3.1 Card-Liste**
- [ ] Öffne "⚙️ Card-Verwaltung" Tab
- [ ] Alle existierenden Cards werden aufgelistet
- [ ] Cards zeigen Icon, Name und Etage

**3.2 Neue Card erstellen**
- [ ] Klick "➕ Neue Card"
- [ ] Editor-Dialog öffnet sich
- [ ] Plugin-Typ auswählbar (Light, Temperature, Gauge, Weather)
- [ ] Auto-generierte Card-ID
- [ ] Name eingeben
- [ ] Icon auswählen
- [ ] Etage auswählen
- [ ] Plugin-spezifische Felder erscheinen

**3.3 Symbol-Browser**
- [ ] Klick "🔍" bei Variable
- [ ] Browser-Dialog öffnet sich
- [ ] Such-Feld funktioniert (Live-Suche)
- [ ] Typ-Filter (ALL, BOOL, REAL, INT)
- [ ] Symbol auswählen übernimmt Wert
- [ ] Close Button funktioniert

**3.4 Plugin-spezifische Felder**

**Light Plugin:**
- [ ] Input Variable Feld + Symbol-Browser
- [ ] Output Variable Feld + Symbol-Browser
- [ ] Typ (Toggle/Pulse) Radio-Buttons
- [ ] Impuls-Dauer Spinbox (50-2000ms)

**Temperature Plugin:**
- [ ] Variable Feld + Symbol-Browser
- [ ] Einheit (°C/°F) Radio-Buttons

**Gauge Plugin:**
- [ ] Variable Feld + Symbol-Browser
- [ ] Min/Max Werte
- [ ] Einheit Feld
- [ ] Variablen-Typ (REAL/INT/DINT)

**Weather Plugin:**
- [ ] Standort Feld
- [ ] Temp Variable + Browser
- [ ] Feuchte Variable + Browser
- [ ] Wind Variable + Browser
- [ ] API Key Feld (optional, password-masked)

**3.5 Card-Operationen**
- [ ] Card bearbeiten funktioniert
- [ ] Card duplizieren funktioniert
- [ ] Card löschen mit Bestätigung
- [ ] Speichern übernimmt Änderungen
- [ ] Abbrechen verwirft Änderungen

**3.6 Statistik**
- [ ] Gesamt-Anzahl Cards korrekt
- [ ] Anzahl nach Typ korrekt (Light, Temp, Gauge, Weather)
- [ ] Anzahl nach Etage korrekt

---

### ✅ 4. Drag & Drop v2.0 (ERWEITERT)

**4.1 Basis Drag & Drop**
- [ ] Card am Drag-Handle (⋮⋮⋮) greifen
- [ ] Card folgt Maus smooth
- [ ] Visuelles Feedback (Border-Änderung)
- [ ] Card zu anderer Position ziehen
- [ ] Positionen tauschen funktioniert
- [ ] Layout wird gespeichert

**4.2 Grid-Snapping (NEU)**
- [ ] Drag-Bewegung snappt zu 10px Grid
- [ ] Smooth Movement trotz Snapping
- [ ] Drop-Position exakt im Raster

**4.3 Multi-Select (BONUS)**
- [ ] Ctrl+Click auf Card selektiert
- [ ] Mehrere Cards gleichzeitig auswählbar
- [ ] Visuelles Feedback für Selektion (Border)
- [ ] Clear Selection funktioniert

**4.4 Visual Feedback**
- [ ] Gezogene Card: GROOVE Border, 3px
- [ ] Ziel-Card: SUNKEN Border, 3px
- [ ] Normal: RAISED Border, 1px
- [ ] Cursor ändert sich zu 'fleur' am Handle

---

### ✅ 5. Update-Loop (NEU in v2.0)

**5.1 Live-Updates**
- [ ] Update-Loop startet automatisch
- [ ] Intervall: 1 Sekunde
- [ ] Cards aktualisieren sich live

**5.2 Light-Cards**
- [ ] Input-Wert wird gelesen
- [ ] Status-Kreis ändert Farbe (grün=EIN, grau=AUS)
- [ ] Status-Text ändert sich (EIN/AUS)

**5.3 Temperature-Cards**
- [ ] Temperatur-Wert wird gelesen
- [ ] Anzeige aktualisiert sich
- [ ] Farbe basiert auf Temperatur (blau<15°C, grün 15-25°C, orange>25°C)
- [ ] Einheit korrekt (°C oder °F)

**5.4 Gauge-Cards**
- [ ] Wert wird gelesen
- [ ] Balken-Länge entspricht Wert
- [ ] Farbe basiert auf Prozent (grün<50%, orange 50-80%, rot>80%)
- [ ] Wert-Label aktualisiert sich

**5.5 Weather-Cards**
- [ ] Temperatur aktualisiert sich
- [ ] Luftfeuchtigkeit aktualisiert sich
- [ ] Wind aktualisiert sich

**5.6 Fehler-Handling**
- [ ] Fehlerhafte Variables crashen nicht
- [ ] Auto-Reconnect bei PLC-Disconnect
- [ ] Fehler werden geloggt, nicht angezeigt

**5.7 Smart-Update**
- [ ] Nur sichtbare Cards werden aktualisiert
- [ ] Performance bleibt gut (>30 Cards)

---

### ✅ 6. Tab-Manager (NEU in v2.0)

**6.1 Tab-Verwaltungs-Dialog**
- [ ] Dialog öffnet sich mit "📑 Tab-Manager"
- [ ] Alle Tabs werden aufgelistet mit Icons

**6.2 Neuen Tab hinzufügen**
- [ ] "➕ Neuer Tab" Button
- [ ] Name-Dialog erscheint
- [ ] Icon-Auswahl-Dialog erscheint
- [ ] Tab wird erstellt
- [ ] Tab erscheint im Notebook

**6.3 Tab umbenennen**
- [ ] Tab auswählen
- [ ] "✏️ Umbenennen" Button
- [ ] Neuer Name-Dialog
- [ ] Tab-Text ändert sich

**6.4 Tab löschen**
- [ ] Tab auswählen
- [ ] "🗑️ Löschen" Button
- [ ] Bestätigungs-Dialog
- [ ] Tab wird entfernt

**6.5 Tab-Icons**
- [ ] Icons: 📋, 🏡, 🔼, ⬆️, ☀️, 🌤️, 📊, 🎥, 🔧, ⚙️
- [ ] Icon wird im Tab angezeigt
- [ ] Icon ändert sich beim Umbenennen

---

### ✅ 7. GUI & Theme-System

**7.1 Hauptfenster**
- [ ] Window-Titel: "TwinCAT Smart Home v2.0.0"
- [ ] Fullscreen möglich
- [ ] Responsive Design
- [ ] Close-Button funktioniert

**7.2 Themes**
- [ ] Blue Theme (Standard)
- [ ] Dark Theme
- [ ] Green Theme
- [ ] Theme wechseln in Einstellungen
- [ ] Farben ändern sich sofort

**7.3 Notebook/Tabs**
- [ ] Tabs sind wählbar
- [ ] Content wird gewechselt
- [ ] Scroll funktioniert bei vielen Cards

**7.4 Control Panel**
- [ ] "🔄 Reconnect" Button - Reconnect PLC
- [ ] "🔄 Reload" Button - GUI neu laden
- [ ] "📦 Module" Button - Module-Info
- [ ] "⚙️ Einstellungen" Button - Settings-Dialog

---

### ✅ 8. Einstellungen-Dialog

**8.1 Theme-Tab**
- [ ] Theme-Buttons vorhanden (Blue, Dark, Green)
- [ ] Theme-Wechsel funktioniert
- [ ] Farben ändern sich live

**8.2 PLC-Tab**
- [ ] Status angezeigt (Verbunden/Getrennt)
- [ ] AMS Net ID angezeigt
- [ ] Fehler-Count angezeigt
- [ ] Cache-Info angezeigt

**8.3 Info-Tab**
- [ ] Version korrekt (2.0.0)
- [ ] Build-Datum korrekt (2024-11-30)
- [ ] Modul-Anzahl korrekt
- [ ] Card-Anzahl korrekt

---

### ✅ 9. PLC-Kommunikation

**9.1 Verbindung**
- [ ] Auto-Connect beim Start
- [ ] Status wird angezeigt (grün/rot)
- [ ] Reconnect funktioniert
- [ ] Fehler-Handling

**9.2 Read/Write**
- [ ] read_by_name funktioniert
- [ ] write_by_name funktioniert
- [ ] Datentypen korrekt (BOOL, REAL, INT, DINT)
- [ ] Cache wird genutzt

**9.3 Symbol-Manager**
- [ ] TPY-File wird geladen
- [ ] Symbole werden gecacht
- [ ] Suche funktioniert
- [ ] Filter funktionieren

---

### ✅ 10. Config-Manager

**10.1 Konfiguration laden**
- [ ] config.json wird geladen
- [ ] Custom Lights werden geladen
- [ ] Layout wird geladen
- [ ] Themes werden geladen

**10.2 Konfiguration speichern**
- [ ] Neue Card wird gespeichert
- [ ] Geänderte Card wird gespeichert
- [ ] Gelöschte Card wird entfernt
- [ ] Layout-Änderungen werden gespeichert

**10.3 Versions-Migration**
- [ ] Alte Config wird erkannt
- [ ] Migration wird durchgeführt
- [ ] Daten bleiben erhalten

---

### ✅ 11. Plugins

**11.1 Light Plugin**
- [ ] Toggle funktioniert
- [ ] Pulse funktioniert
- [ ] Status-Update korrekt
- [ ] Visuelles Feedback

**11.2 Temperature Plugin**
- [ ] Wert wird angezeigt
- [ ] Einheit korrekt
- [ ] Farbe basiert auf Temperatur

**11.3 Gauge Plugin**
- [ ] Balken zeigt Prozent korrekt
- [ ] Min/Max funktioniert
- [ ] Farbe basiert auf Wert

**11.4 Weather Plugin**
- [ ] Alle Werte werden angezeigt
- [ ] Icons korrekt

---

### ✅ 12. Performance

**12.1 Startup**
- [ ] App startet in <5 Sekunden
- [ ] Alle Module laden ohne Fehler
- [ ] GUI erscheint smooth

**12.2 Runtime**
- [ ] Keine Lags beim Drag & Drop
- [ ] Update-Loop stabil (1s Intervall)
- [ ] Memory-Usage stabil
- [ ] CPU-Usage akzeptabel

**12.3 Stress-Test**
- [ ] 30+ Cards funktionieren smooth
- [ ] Drag & Drop mit vielen Cards
- [ ] Update-Loop bei vielen Cards

---

### ✅ 13. Fehler-Handling

**13.1 PLC-Fehler**
- [ ] Disconnect wird erkannt
- [ ] Auto-Reconnect versucht
- [ ] Status-Update korrekt
- [ ] Keine Crashes

**13.2 Config-Fehler**
- [ ] Ungültige JSON wird abgefangen
- [ ] Fehlende Felder werden ergänzt
- [ ] Backup wird erstellt

**13.3 Module-Fehler**
- [ ] Fehlende Dependencies werden gemeldet
- [ ] Module-Load-Fehler werden geloggt
- [ ] App läuft trotzdem weiter

---

## 🎯 Critical Path (Minimal-Test)

Wenn Zeit knapp ist, diese Tests MÜSSEN funktionieren:

1. ✅ **Startup:** App startet, alle Module laden
2. ✅ **Status-Leiste:** Wird angezeigt mit Uhrzeit
3. ✅ **Card-Manager:** Neue Card erstellen funktioniert
4. ✅ **Symbol-Browser:** Öffnet und findet Variablen
5. ✅ **Drag & Drop:** Card verschieben funktioniert
6. ✅ **Update-Loop:** Live-Werte aktualisieren sich
7. ✅ **Save:** Änderungen werden gespeichert

---

## 📊 Test-Ergebnisse

**Datum:** _____________  
**Tester:** _____________  
**Umgebung:** _____________

### Zusammenfassung:

- **Module Loading:** ☐ PASS ☐ FAIL
- **Status-Leiste:** ☐ PASS ☐ FAIL
- **Card-Manager:** ☐ PASS ☐ FAIL
- **Drag & Drop:** ☐ PASS ☐ FAIL
- **Update-Loop:** ☐ PASS ☐ FAIL
- **Tab-Manager:** ☐ PASS ☐ FAIL
- **Performance:** ☐ PASS ☐ FAIL

### Gefundene Bugs:

1. _________________________________
2. _________________________________
3. _________________________________

### Notizen:

_______________________________________
_______________________________________
_______________________________________

---

## 🚀 Release-Kriterien

Version 2.0.0 ist ready für Release wenn:

- [x] Alle Critical Path Tests PASS
- [ ] Mindestens 80% aller Tests PASS
- [ ] Keine Critical Bugs
- [ ] Performance akzeptabel
- [ ] Dokumentation vollständig

**Status:** ⏳ IN PROGRESS

---

**VIEL ERFOLG BEIM TESTEN! 🎉**
