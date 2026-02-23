# Bug-Fix Report - 04.01.2026

## Kritische Bugs behoben

### 1. ❌ Problem: Hartcodierte AMS NetID
**Symptom**: Verbindung war nur mit `192.168.2.162.1.1` möglich, falsche IP-Adressen wurden akzeptiert
**Root Cause**: In `modules/core/plc_communication.py` Zeile 46 war die AMS NetID hartcodiert
**Fix**:
```python
# VORHER (FALSCH):
'ams_net_id': '192.168.2.162.1.1',

# NACHHER (KORREKT):
'ams_net_id': None,  # KEIN DEFAULT! Muss explizit konfiguriert werden
```

**Zusätzliche Validierung** (`connect()` Methode):
```python
if not self.config['ams_net_id']:
    print(f"  ✗ PLC-Verbindung fehlgeschlagen: Keine AMS NetID konfiguriert!")
    print(f"     Bitte zuerst configure() aufrufen oder über Web-UI konfigurieren")
    return False
```

**Auswirkung**:
- ✅ AMS NetID muss nun explizit über Web-UI (Setup-Seite) oder `configure()` gesetzt werden
- ✅ Keine versehentliche Verbindung zu falschen PLCs mehr
- ✅ Klare Fehlermeldung bei fehlender Konfiguration

---

### 2. ❌ Problem: Keine Widget-Variable-Verknüpfung möglich
**Symptom**: Benutzer konnte Widgets nicht mit Gateway-Variablen (PLC/MQTT) verbinden
**Root Cause**: Fehlendes Widget-Configuration-System

**Lösung**: Komplettes **Widget Configuration & Variable Binding System** implementiert

#### Backend API (web_manager.py):
```
GET    /api/widgets                      - Alle Widgets abrufen
POST   /api/widgets                      - Neues Widget erstellen
PUT    /api/widgets/<id>                 - Widget aktualisieren
DELETE /api/widgets/<id>                 - Widget löschen
POST   /api/widgets/<id>/bindings        - Variable an Widget binden
GET    /api/widgets/values                - Live-Werte aller gebundenen Variablen
```

#### Frontend (index.html):
- Neue **"Widgets"** Seite mit vollständiger Verwaltung
- Widget-Editor-Modal mit:
  - Titel, Typ (Switch/Slider/Gauge/Text), Seite
  - **Variable-Binding Interface**:
    - Variable-Pfad (z.B. `MAIN.bLight1`)
    - PLC-Typ (BOOL/INT/REAL/STRING)
    - Symbol-Browser-Integration
    - Test-Funktion

#### JavaScript (app.js):
- `loadWidgetsPage()` - Lädt Widget-Liste
- `renderWidgetList()` - Zeigt Widgets mit Bindings an
- `openWidgetEditor()` - Editor-Modal öffnen
- `saveWidget()` - Widget speichern (CREATE/UPDATE)
- `testVariableBinding()` - Variable-Verbindung testen
- `browseSymbols()` - Springt zum Symbol-Browser

**Features**:
- ✅ Widgets pro Seite (Dashboard/Lighting/Climate/Energy)
- ✅ Variable-Binding mit Typ-Validierung
- ✅ Live-Test der Verbindung vor dem Speichern
- ✅ Integration mit Symbol-Browser
- ✅ Persistent storage in Config-Manager
- ✅ Dark-Theme support

---

## Dateien geändert

### Core-Modul
- **modules/core/plc_communication.py**
  - Zeile 46: Hardcoded AMS NetID entfernt
  - Zeilen 80-107: Validierung in `connect()` hinzugefügt

### Gateway/Web-Manager
- **modules/gateway/web_manager.py**
  - Zeilen 638-825: Widget Configuration & Variable Binding API hinzugefügt

### Frontend
- **web/templates/index.html**
  - Zeilen 82-85: "Widgets" Navigation hinzugefügt
  - Zeilen 527-631: Widgets-Seite & Editor-Modal hinzugefügt

- **web/static/js/app.js**
  - Zeilen 179-181: Widgets-Page-Case hinzugefügt
  - Zeilen 1716-1976: Widget-Management-Funktionen hinzugefügt

---

## Auswirkung auf Multi-Instanz-Fähigkeit

### ✅ Positiv:
1. **Keine globalen Defaults mehr**: Jede Instanz muss eigene AMS NetID konfigurieren
2. **Widget-Config persistent**: Jede Instanz hat eigene Widget-Konfiguration
3. **Config-Manager-Integration**: Nutzt bestehende Config-Infrastruktur

### ⚠️ Zu beachten:
- Widget-Konfigurationen sind **pro Config-Verzeichnis** gespeichert
- Multi-Container-Setup benötigt separate Config-Volumes
- Empfehlung: `/config` als separates Volume mounten

---

## Plattform-spezifische Hinweise

### Windows:
- ✅ Alle Änderungen getestet
- ✅ UTF-8 Encoding via `python -X utf8` erforderlich

### Linux/Docker:
- ✅ Keine plattformspezifischen Änderungen
- ⚠️ Config-Verzeichnis-Permissions beachten

---

## Nächste Schritte (wie besprochen)

### Noch offen:
1. **Monitor Dashboard** - Datenfluss-Visualisierung
   - Sankey/Stream-Graph für Gateway → Client
   - Live-Latenz-Messung
   - Export-Funktion (CSV/JSON)

2. **Serial-Link Abstraktion** - Vorbereitung für RS485
   - Abstract class `SerialLink`
   - Plugin-System für Serial-Protokolle

3. **Admin-Restart Funktion**
   - Windows: `taskkill /PID` + neustart
   - Linux: `systemctl restart` / Docker-Restart

4. **Dokumentation**
   - `CHANGELOG.md`
   - `ARCHITECTURE.md`

---

## Testing-Checkliste

- [x] AMS NetID muss über Web-UI gesetzt werden
- [x] Widget erstellen mit Variable-Binding
- [x] Widget bearbeiten
- [x] Widget löschen
- [x] Test-Verbindung-Button funktioniert
- [x] Symbol-Browser-Integration
- [x] Dark-Theme auf allen neuen Seiten
- [ ] Live-Update der Widget-Werte (TODO: Auto-Refresh via WebSocket)

---

**Autor**: Claude Sonnet 4.5
**Datum**: 04.01.2026
**Version**: SmartHome OS v4.6.0
**Platform**: Windows 11, Python 3.13
