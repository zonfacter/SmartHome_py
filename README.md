# 🏠 TwinCAT Smart Home v2.2.6 - Vollständige Projekt-Dokumentation

**Projekt:** TwinCAT Smart Home Visualisierung  
**Version:** 2.2.6  
**Datum:** 2025-11-30  
**Status:** ✅ PRODUCTION READY  

---

## 📋 **INHALTSVERZEICHNIS**

1. [Projekt-Übersicht](#projekt-übersicht)
2. [Architektur](#architektur)
3. [Features](#features)
4. [Module & Plugins](#module--plugins)
5. [Vollständiger Changelog](#vollständiger-changelog)
6. [Kritische Bugfixes](#kritische-bugfixes)
7. [Installation & Setup](#installation--setup)
8. [Konfiguration](#konfiguration)
9. [Bekannte Einschränkungen](#bekannte-einschränkungen)
10. [Migration von älteren Versionen](#migration-von-älteren-versionen)

---

## 📌 **Aktuelle Betriebsdoku (Web-HMI)**

Für den aktuellen produktiven Ablauf sind diese Dokumente die verbindliche Quelle:

- `docs/01_quickstart.md`
- `docs/02_twincat_setup.md`
- `docs/03_camera_setup.md`
- `docs/04_gateway_integration.md`
- `docs/05_api_reference.md`
- `docs/06_api_lifecycle_policy.md`
- `docs/07_operations_playbook.md`
- `docs/openapi.json`
- `docs/08_socket_events.md`
- `docs/WEB_SETUP_ROUTING_ADS_GUIDE.md`
- `docs/STAGING_GATE.md` (Release-Gates, Canary, Go/No-Go)
- `docs/SECURITY_INCIDENT_SENTRY_DSN.md` (Incident-Runbook & Secret-Policy)
- `docs/DOCKER_DEPLOYMENT.md` (verbindlicher Docker-Betriebspfad)

Inhalt:
- PLC Runtime (TC2/TC3) korrekt konfigurieren
- ADS TwinCAT Routen im Web-Setup verwalten (Status/Anlegen/Test)
- Routing-Regeln über Setup-UI bearbeiten (`config/routing.json`)
- Docker-Hardening/Least-Privilege: `docs/DOCKER_LEAST_PRIVILEGE.md`
- Release-Verifikation (Checksums + Attestation): `docs/RELEASE_VERIFICATION.md`
- Dokumentations-Index + Historisch-Markierung: `docs/README.md`

---

## 📖 **PROJEKT-ÜBERSICHT**

### **Zweck**
Vollständig modulare Smart Home Visualisierung für TwinCAT PLC-Steuerungen mit Unterstützung für:
- TwinCAT 2 & 3 (ADS-Kommunikation)
- MQTT-Integration (SolarAssistant, IoT)
- Modbus (Wechselrichter, Sensoren)
- RTSP-Kameras
- Dynamisches Card-System
- Custom Tabs
- Theme-System

### **Technologie-Stack**
- **Backend:** Python 3.x
- **GUI:** Tkinter
- **PLC-Kommunikation:** pyads (TwinCAT ADS)
- **MQTT:** paho-mqtt
- **Modbus:** pymodbus
- **Architektur:** Plugin-basiertes Modulsystem

### **Entwicklungszeitraum**
- Start: v1.0 (Basic Light Control)
- Aktuell: v2.2.6 (Vollständig modular, 20 Module)
- Entwicklungszeit: ~24 Stunden mit Claude Sonnet 4.5

---

## 🏗️ **ARCHITEKTUR**

### **Modulares System**

```
TwinCAT_SmartHome/
├── Haussteuerung.py          # Hauptanwendung
├── module_manager.py             # Zentrales Modulsystem
│
├── modules/
│   ├── core/                     # Kern-Module
│   │   ├── plc_communication.py  # TwinCAT ADS
│   │   ├── config_manager.py     # Konfiguration & Backups
│   │   ├── symbol_manager.py     # PLC Symbol-Cache (14.264 Symbole)
│   │   └── update_loop.py        # Live-Update System
│   │
│   ├── ui/                       # UI-Module
│   │   ├── gui_manager.py        # GUI Framework & Themes
│   │   ├── card_manager.py       # Card-Editor & Symbol-Browser
│   │   ├── card_renderer.py      # Card-Rendering
│   │   ├── tab_manager.py        # Dynamisches Tab-Management
│   │   ├── drag_drop.py          # Drag & Drop mit Grid-Snapping
│   │   ├── status_bar.py         # Statusleiste
│   │   ├── search_filter.py      # Suche & Filter
│   │   └── context_menu.py       # Rechtsklick-Menü
│   │
│   ├── integrations/             # Integration-Module
│   │   ├── mqtt_integration.py   # MQTT für SolarAssistant/IoT
│   │   ├── modbus_integration.py # Modbus TCP/RTU
│   │   └── rtsp_integration.py   # RTSP Kamera-Streams
│   │
│   └── plugins/                  # Plugin-Module (Cards)
│       ├── light_plugin.py       # Licht-Steuerung (Toggle/Pulse)
│       ├── temperature_plugin.py # Temperatur-Anzeige
│       ├── gauge_plugin.py       # Messwertsanzeige
│       ├── weather_plugin.py     # Wetter-Daten
│       └── solarassistant_plugin.py # PV-Daten via MQTT
│
└── Documents/TwinCAT_SmartHome/  # User-Daten
    ├── twincat_config.json       # Hauptkonfiguration
    ├── twincat_layout.json       # Card-Positionen
    ├── symbol_cache.json         # PLC-Symbole (14.264)
    └── backups/                  # Auto-Backups
```

### **Modul-System**

**BaseModule:**
```python
class BaseModule:
    NAME = "module_name"
    VERSION = "1.0.0"
    DESCRIPTION = "..."
    DEPENDENCIES = ['other_module']
    
    def initialize(self, app_context):
        # Wird beim Start aufgerufen
        pass
    
    def shutdown(self):
        # Wird beim Beenden aufgerufen
        pass
```

**Module registrieren sich selbst:**
```python
def register(module_manager):
    module_manager.register_module(
        MyModule.NAME,
        MyModule.VERSION,
        MyModule.DESCRIPTION,
        MyModule  # Klasse
    )
```

**Auto-Discovery:**
- Durchsucht `modules/core/`, `modules/ui/`, `modules/integrations/`, `modules/plugins/`
- Lädt alle `.py` Dateien (außer `__init__.py`)
- Ruft `register()` Funktion auf
- Erstellt Modul-Instanzen
- Prüft Abhängigkeiten

---

## ✨ **FEATURES**

### **1. PLC-Kommunikation (TwinCAT 2/3)**
- ADS-Protokoll via pyads
- Auto-Reconnect
- Cache-System (reduziert PLC-Last)
- Symbol-Download von PLC (14.264+ Symbole)
- Live-Updates (0.2s - 5.0s konfigurierbar)

**Unterstützte Typen:**
- BOOL, BYTE, WORD, DWORD
- INT, DINT, REAL, LREAL
- STRING, TIME, DATE

**Ports:**
- TwinCAT 2: Port 801 (TC2PLC1)
- TwinCAT 3: Port 851 (TC3PLC1)

### **2. Card-System**

**Card-Typen:**
- **Light:** Toggle/Pulse-Steuerung mit Input/Output
- **Temperature:** Celsius/Fahrenheit
- **Gauge:** Messwertsanzeige mit Min/Max
- **Weather:** Temperatur, Feuchte, Wind
- **SolarAssistant:** PV-Leistung, Batterie-SOC, Netz, Ertrag

**Card-Features:**
- Drag & Drop mit Grid-Snapping
- Live-Updates
- Kontext-Menü (Rechtsklick)
- Position-Speicherung
- Etagen-Zuordnung

### **3. Symbol-Browser**
- Live-Suche in 14.264+ Symbolen
- 3-Spalten Tabelle (Name, Typ, Live-Wert)
- Live-Updates (max 100 Symbole gleichzeitig)
- Symbol-Download von PLC
- Cache-System

### **4. Tab-Management**
- Standard-Tabs (Erdgeschoss, Obergeschoss, Dachboden)
- Custom Tabs mit Icons
- Dynamisches Hinzufügen/Löschen
- Persistence (wird gespeichert)
- Drag & Drop zwischen Tabs

### **5. MQTT-Integration**
- Broker-Verbindung (mit Auth)
- Topic-Subscription mit Wildcards
- Auto-Reconnect
- JSON-Payload Parsing
- SolarAssistant Cards

**Unterstützte Systeme:**
- SolarAssistant
- HomeAssistant
- Deye Wechselrichter
- Generische MQTT-Broker

### **6. Performance-System**
- Konfigurierbares Update-Intervall (0.2s - 5.0s)
- Symbol-Browser Limit (10-500 Symbole)
- Smart-Update (nur sichtbare Cards)
- Cache-System

### **7. Theme-System**
- 3 Themes: Blue, Dark, Green
- Vollständige UI-Anpassung
- Wird gespeichert

### **8. Konfiguration**
- JSON-basiert
- Auto-Backup vor Änderungen
- Versionierung
- User-freundlich

---

## 📦 **MODULE & PLUGINS**

### **Core-Module (4)**

**1. plc_communication v1.0.0**
- TwinCAT ADS Kommunikation
- Read/Write/Toggle Funktionen
- Cache-System
- Connection-Management

**2. config_manager v1.0.0**
- JSON-basierte Konfiguration
- Auto-Backups
- Custom Lights Management
- Theme-Verwaltung

**3. symbol_manager v2.0.5**
- PLC Symbol-Cache (14.264+ Symbole)
- Symbol-Download von PLC
- Suche & Filter
- Format-Konvertierung (v1.2 → v2.0)

**4. update_loop v2.0.6**
- Live-Update System
- Thread-basiert
- Konfigurierbares Intervall
- Smart-Updates (nur sichtbare Cards)

### **UI-Module (8)**

**1. gui_manager v1.0.0**
- Tkinter Framework
- Theme-System
- Widget-Factory
- Farb-Management

**2. card_manager v2.0.7**
- Card-Editor Dialog
- Symbol-Browser (Live)
- Card CRUD-Operationen
- Etagen-Auswahl

**3. card_renderer v2.0.0**
- Plugin-basiertes Rendering
- Drag & Drop Integration
- Card-Lifecycle

**4. tab_manager v2.0.4**
- Dynamisches Tab-Management
- Custom Tabs
- Persistence
- Icon-Auswahl

**5. drag_drop v2.0.5**
- Grid-Snapping
- Visual Feedback
- Position-Speicherung
- Offset-Korrektur

**6. status_bar v2.0.0**
- PLC-Status
- Verbindungsinfo
- Fehler-Anzeige

**7. search_filter v1.0.0**
- Echtzeit-Suche
- Fuzzy-Matching
- Performance-optimiert

**8. context_menu v1.0.0**
- Rechtsklick-Menü
- Card-Operationen
- Kontext-sensitiv

### **Integration-Module (3)**

**1. mqtt_integration v1.0.0**
- MQTT Broker-Verbindung
- Topic-Subscription
- JSON-Parsing
- Auto-Reconnect
- **WICHTIG:** Lädt IMMER (auch ohne paho-mqtt)

**2. modbus_integration v1.0.0**
- Modbus TCP/RTU
- Wechselrichter-Support
- Register-Mapping

**3. rtsp_integration v1.0.0**
- RTSP Kamera-Streams
- Multi-Kamera Support
- Snapshot-Funktion

### **Plugins (5)**

**1. light v1.0.0**
- Toggle/Pulse Modi
- Input/Output Mapping
- Konfigurierbare Pulse-Dauer (50-2000ms)
- Live-Status via INPUT-Variable

**2. temperature v1.0.0**
- Celsius/Fahrenheit
- PLC-Variable Anbindung
- Live-Updates

**3. gauge v1.0.0**
- Messwertsanzeige
- Min/Max Range
- Einheiten-Anzeige
- REAL/DINT Support

**4. weather v1.0.0**
- Temperatur, Feuchte, Wind
- PLC-Variable Anbindung
- Optional: API-Integration

**5. solarassistant v1.0.0**
- PV-Leistung (W)
- Batterie-SOC (%) mit Farb-Codierung
- Netz-Leistung (W) mit Ein/Einspeisung
- Tages-Ertrag (kWh)
- MQTT-basiert

---

## 📝 **VOLLSTÄNDIGER CHANGELOG**

### **v2.2.6 (2025-11-30) - MQTT Import-Fix** ✅ AKTUELL

**Fixed:**
- ✅ mqtt_integration lädt jetzt IMMER (auch ohne paho-mqtt)
- ✅ paho-mqtt Import in `__init__()` verschoben (war Datei-Level)
- ✅ Graceful Degradation bei fehlendem paho-mqtt
- ✅ Modul erscheint in Module-Liste auch ohne paho-mqtt

**Technical:**
- Import von `paho.mqtt.client` in `__init__()` statt global
- `self.mqtt_available` Flag
- `self.mqtt_module` als Referenz
- Bessere Fehler-Meldungen

**Files Changed:**
- `modules/integrations/mqtt_integration.py`
- `Haussteuerung_v2.py`

---

### **v2.2.5 (2025-11-30) - MQTT Debug Verbessert**

**Improved:**
- ✅ Detaillierte MQTT-Fehler-Meldungen
- ✅ paho-mqtt Verfügbarkeits-Check
- ✅ Console-Debug-Output
- ✅ Exception-Details werden geloggt
- ✅ Hilfreiche Lösungsvorschläge

**Technical:**
- Try-catch in test_mqtt_connection()
- Import-Check für paho-mqtt
- Traceback-Logging

**Files Changed:**
- `Haussteuerung_v2.py`

---

### **v2.2.4 (2025-11-30) - Hardcodierte Tabs Fix**

**Fixed:**
- ✅ Standard-Tabs (Erdgeschoss, Obergeschoss, Dachboden) werden NICHT mehr gespeichert
- ✅ Tab-Duplikation ENDGÜLTIG gefixt
- ✅ MQTT-Test-Button holt Modul dynamisch
- ✅ Doppelter `_load_tabs()` Aufruf entfernt

**Technical:**
- Standard-Tabs mit `skip_save=True`
- MQTT-Modul wird aus `module_manager` geladen wenn `self.mqtt` leer

**Files Changed:**
- `Haussteuerung_v2.py`

---

### **v2.2.3 (2025-11-30) - Alte Module & Timestamp-IDs**

**Fixed:**
- ✅ Alte Module gelöscht (mqtt_module.py, modbus_module.py, rtsp_module.py)
- ✅ Tab-IDs jetzt Timestamp-basiert (eindeutig)
- ✅ AttributeError 'MQTTIntegration' behoben

**Technical:**
- Tab-ID: `tab_{int(time.time() * 1000)}` statt `tab_{len(self.tabs)}`
- Alte *_module.py aus `/modules/` entfernt
- Nur noch neue aus `/integrations/`

**Files Changed:**
- `modules/ui/tab_manager.py`
- `Haussteuerung_v2.py`
- GELÖSCHT: `modules/mqtt_module.py`, `modules/modbus_module.py`, `modules/rtsp_module.py`

---

### **v2.2.2 (2025-11-30) - Module-Loader & Skip-Save**

**Fixed:**
- ✅ module_manager lädt jetzt Unterordner (integrations/, plugins/)
- ✅ Tab-Duplikation behoben (skip_save Flag)

**Technical:**
- `load_all_modules()`: Durchsucht core/, ui/, integrations/, plugins/
- `add_tab()`: Neuer Parameter `skip_save=False`
- `_load_tabs()`: Nutzt `skip_save=True`

**Files Changed:**
- `module_manager.py`
- `modules/ui/tab_manager.py`
- `Haussteuerung_v2.py`

---

### **v2.2.1 (2025-11-30) - MQTT Hauptapp-Integration**

**Added:**
- ✅ MQTT Auto-Load beim Start
- ✅ MQTT-Config aus config.json
- ✅ Auto-Subscribe zu Topics
- ✅ **Settings UI:**
  - Broker-Konfiguration
  - Live-Status
  - Verbindung testen
  - Speichern & Laden
- ✅ Sauberes Shutdown

**Files Changed:**
- `Haussteuerung_v2.py`

---

### **v2.2.0 (2025-11-30) - MQTT & SolarAssistant** 🎉

**Added:**
- ✅ **MQTT-Integration Modul:**
  - Broker-Verbindung (mit Auth)
  - Topic-Subscription
  - Auto-Reconnect
  - JSON-Payload Parsing
  - Werte-Caching
  
- ✅ **SolarAssistant Plugin:**
  - PV-Leistung (W)
  - Batterie-SOC (%) mit Farb-Codierung
  - Netz-Leistung (W) mit Ein/Einspeisung-Anzeige
  - Tages-Ertrag (kWh)
  - Live-Updates via MQTT

- ✅ **update_loop Integration:**
  - `_update_solarassistant_card()`
  - MQTT-Werte Caching

- ✅ **card_manager Integration:**
  - SolarAssistant Felder
  - Topic-Konfiguration
  - Icon (☀️)

**Files Added:**
- `modules/integrations/mqtt_integration.py`
- `modules/plugins/solarassistant_plugin.py`

**Files Changed:**
- `modules/ui/card_manager.py`
- `modules/core/update_loop.py`
- `Haussteuerung_v2.py`

---

### **v2.1.3 (2025-11-30) - Custom Tabs Fix**

**Fixed:**
- ✅ Custom Tabs werden gespeichert
- ✅ Custom Tabs werden beim Start geladen
- ✅ Custom Tabs in Etagen-Auswahl sichtbar
- ✅ Cards funktionieren in Custom Tabs

**Technical:**
- `_save_tabs()` nach add/remove
- `_load_tabs()` nach set_notebook
- Dynamische Floor-Auswahl in card_manager
- Custom Tab Content via create_floor_content

**Files Changed:**
- `Haussteuerung_v2.py`
- `modules/ui/tab_manager.py`
- `modules/ui/card_manager.py`

---

### **v2.1.2 (2025-11-30) - Config Save/Load Fix**

**Fixed:**
- ✅ save_config() speichert ALLE Daten (nicht nur theme/lights)
- ✅ Performance-Settings werden in Config geschrieben
- ✅ Start lädt Performance-Settings aus Config
- ✅ Dialog zeigt gespeicherte Werte

**Technical:**
- `save_config()`: `dict(self.config)` kopiert alles
- Performance-Settings in `config['performance']`
- Theme mit `self.config.current_theme` und `self.config.config['theme']`

**Files Changed:**
- `modules/core/config_manager.py`
- `Haussteuerung_v2.py`

---

### **v2.1.1 (2025-11-30) - INPUT/OUTPUT Fix**

**Fixed:**
- ✅ update_loop liest INPUT statt OUTPUT für Status-Anzeige
- ✅ Toggle nutzt OUTPUT zum Schreiben
- ✅ Echte Hardware-Rückmeldung sichtbar

**Technical:**
- `_update_light_card()`: Nutzt INPUT für Status, fallback OUTPUT
- Pulse-Mode: OUTPUT = Impuls, INPUT = Rückmeldung

**Files Changed:**
- `modules/core/update_loop.py`

---

### **v2.1.0 (2025-11-30) - MAJOR RELEASE** 🎉

**Added:**
- ✅ **Performance-Settings UI:**
  - Update-Intervall: 0.2s - 5.0s
  - Symbol-Browser Limit: 10-500 Symbole
  - Live-Anwendung ohne Neustart

- ✅ **Symbol-Download von PLC:**
  - Button in Settings → PLC Tab
  - Lädt ALLE Symbole
  - Speichert automatisch in Cache
  - Progress-Dialog

**Fixed:**
- ✅ Debug-Ausgaben entfernt (Performance <200ms)
- ✅ Cache-Optimierung für Toggle

**Files Changed:**
- `Haussteuerung_v2.py`
- `modules/core/plc_communication.py`
- `modules/core/symbol_manager.py`
- `light_plugin.py`

---

### **v2.0.8 (2025-11-30) - Plugin-System Integration**

**Fixed:**
- ✅ Cards nutzen jetzt Plugins statt generische Renderer
- ✅ light_plugin wird für Light-Cards aufgerufen
- ✅ Schalten funktioniert (<200ms)
- ✅ Drag-Handle hinzugefügt

**Technical:**
- `card_renderer.py`: Nutzt `plugin.create_card()`
- `light_plugin.py`: Gibt Dict mit Widgets zurück inkl. drag_handle

**Files Changed:**
- `modules/ui/card_renderer.py`
- `light_plugin.py`
- `Haussteuerung_v2.py`

---

### **v2.0.7 (2025-11-30) - Performance & Port Fix**

**Fixed:**
- ✅ Symbol-Browser Performance (Live-Updates standardmäßig AUS)
- ✅ Max 100 Symbole live
- ✅ PLC-Port TC2 (801) statt TC3 (851)
- ✅ AttributeError `get_value` → `get_config_value`
- ✅ NameError `e is not defined` entfernt

**Technical:**
- Symbol-Browser: `live_update_active = False`, `max_live_symbols = 100`
- Port: `pyads.PORT_TC2PLC1` (801)
- Config: `get_config_value()` statt `get_value()`

**Files Changed:**
- `modules/ui/card_manager.py`
- `Haussteuerung_v2.py`
- `modules/core/config_manager.py`

---

### **v2.0.6 (2025-11-30) - Live Symbol-Browser**

**Added:**
- ✅ Live Symbol-Browser (3-Spalten Tabelle)
- ✅ Echtzeit-Werte
- ✅ OUTPUT-Read Fix für Live-Updates
- ✅ Thread-Safe GUI-Updates

**Files Changed:**
- `modules/ui/card_manager.py`
- `modules/core/update_loop.py`

---

### **v1.2 → v2.0 Migration**

**Major Changes:**
- ✅ Vollständig modular (20 Module)
- ✅ Plugin-System für Cards
- ✅ Tab-Manager
- ✅ Drag & Drop
- ✅ Symbol-Cache Format v2.0 (Dict statt List)
- ✅ Kompatibilität mit v1.2 Configs

---

## 🐛 **KRITISCHE BUGFIXES**

### **Bug #1: MQTT-Modul lädt nicht** ⭐ WICHTIGSTER FIX

**Problem:**
```python
# mqtt_integration.py
import paho.mqtt.client as mqtt  # ImportError!
# → Ganze Datei lädt nicht
# → Modul nicht registriert
```

**Lösung (v2.2.6):**
```python
class MqttIntegration:
    def __init__(self):
        try:
            import paho.mqtt.client as mqtt
            self.mqtt_available = True
            self.mqtt_module = mqtt
        except ImportError:
            self.mqtt_available = False
            self.mqtt_error = "paho-mqtt nicht installiert"
```

**Impact:** KRITISCH - MQTT war komplett unbrauchbar

---

### **Bug #2: Tab-Duplikation (Hardcodierte Tabs)**

**Problem:**
```python
# Jeder Start:
add_tab("Erdgeschoss")  # → SPEICHERT!
add_tab("Obergeschoss") # → SPEICHERT!
_load_tabs()            # → LÄDT!

# Start 1: 3 Tabs
# Start 2: 6 Tabs
# Start 3: 9 Tabs (exponentiell!)
```

**Lösung (v2.2.4):**
```python
add_tab("Erdgeschoss", ..., skip_save=True)  # NICHT speichern!
```

**Impact:** HOCH - System wurde mit Tabs überflutet

---

### **Bug #3: Tab-ID Kollisionen**

**Problem:**
```python
tab_id = f"tab_{len(self.tabs)}"  # tab_0, tab_1, tab_2
# Beim Laden: Kollisionen!
```

**Lösung (v2.2.3):**
```python
import time
tab_id = f"tab_{int(time.time() * 1000)}"  # Eindeutig!
```

**Impact:** HOCH - Tabs duplizierten sich

---

### **Bug #4: Module-Loader fand Unterordner nicht**

**Problem:**
```python
# Nur: modules/*_module.py
# NICHT: modules/integrations/*.py
```

**Lösung (v2.2.2):**
```python
for subdir in ['core', 'ui', 'integrations', 'plugins']:
    # Lädt ALLE .py
```

**Impact:** KRITISCH - Integration-Module unsichtbar

---

### **Bug #5: INPUT/OUTPUT vertauscht**

**Problem:**
```python
# Status las OUTPUT (Impuls)
# Nicht INPUT (echte Hardware-Rückmeldung)
```

**Lösung (v2.1.1):**
```python
# Status liest INPUT für echte Rückmeldung
# OUTPUT nur zum Schreiben
```

**Impact:** MITTEL - 2x Klicken nötig

---

### **Bug #6: Config-Daten gingen verloren**

**Problem:**
```python
config_data = {
    'theme': ...,
    'custom_lights': ...
    # PLC, Performance fehlen!
}
```

**Lösung (v2.1.2):**
```python
config_data = dict(self.config)  # ALLES kopieren!
```

**Impact:** HOCH - Settings gingen verloren

---

### **Bug #7: Symbol-Browser zu langsam**

**Problem:**
```
Versuch ALLE 14.264 Symbole live zu lesen!
```

**Lösung (v2.0.7):**
```python
live_update_active = False  # Standardmäßig AUS
max_live_symbols = 100      # Limit
```

**Impact:** MITTEL - UI unbrauchbar bei großen Systemen

---

### **Bug #8: Falscher PLC-Port**

**Problem:**
```python
port = pyads.PORT_TC3PLC1  # 851 (TC3)
# Aber User nutzt TC2!
```

**Lösung (v2.0.7):**
```python
port = pyads.PORT_TC2PLC1  # 801 (TC2)
```

**Impact:** KRITISCH - PLC verbindet nicht

---

### **Bug #9: Cards nutzen nicht Plugins**

**Problem:**
```python
# card_renderer erstellt generische Cards
# Plugin wird ignoriert!
```

**Lösung (v2.0.8):**
```python
plugin.create_card(...)  # Nutze Plugin!
```

**Impact:** KRITISCH - Schalten funktionierte nicht

---

### **Bug #10: Alte Module überschreiben neue**

**Problem:**
```
/modules/mqtt_module.py (ALT, MQTTIntegration)
/modules/integrations/mqtt_integration.py (NEU, MqttIntegration)
# Beide geladen → Konflikt!
```

**Lösung (v2.2.3):**
```
Alte Module löschen!
```

**Impact:** KRITISCH - AttributeError

---

## 🚀 **INSTALLATION & SETUP**

### **1. Voraussetzungen**

**Python:**
```bash
Python 3.8+
```

**Abhängigkeiten (Windows):**
```bash
pip install pyads --break-system-packages
pip install paho-mqtt --break-system-packages  # Für MQTT
pip install pymodbus --break-system-packages   # Für Modbus (optional)
```

**Abhängigkeiten (Linux / Debian):**
```bash
# Virtual Environment erstellen (empfohlen)
python3 -m venv venv
source venv/bin/activate

# Pakete installieren
pip install -r requirements.txt
# Für reproduzierbare Builds (CI/Release):
pip install --require-hashes -r requirements.lock.txt
```

Details zu Lockfiles, CI-Checks und Update-Prozess: `docs/REPRODUCIBLE_BUILDS.md`

### **1b. Linux-Setup (ADS-Route zu Beckhoff PLC)**

Auf Linux-Systemen gibt es keinen TwinCAT ADS Router. pyads nutzt eine eingebaute
Standalone-Bibliothek, die direkte TCP-Verbindungen zur PLC aufbaut.

**ADS-Route automatisch einrichten:**
```bash
source venv/bin/activate
python3 scripts/setup_ads_route.py
```

**ADS-Route manuell einrichten (Python):**
```python
import pyads

# 1. Lokale AMS Net ID setzen
pyads.open_port()
pyads.set_local_address('192.168.2.123.1.1')  # AMS dieses Rechners

# 2. Route zur PLC anlegen (lokal)
pyads.add_route('192.168.2.162.1.1', '192.168.2.162')

# 3. Route auf der PLC anlegen (bidirektional)
pyads.add_route_to_plc(
    sending_net_id='192.168.2.123.1.1',
    adding_host_name='192.168.2.123',   # IP dieses Rechners
    ip_address='192.168.2.162',          # IP der PLC
    username='Administrator',
    password='1',
    route_name='SmartHomeVM'
)
pyads.close_port()

# 4. Verbindung mit expliziter IP (Pflicht auf Linux!)
plc = pyads.Connection('192.168.2.162.1.1', pyads.PORT_TC2PLC1, '192.168.2.162')
plc.open()
```

> **Wichtig:** Auf Linux muss `pyads.Connection()` immer mit dem **3. Parameter (IP-Adresse)**
> aufgerufen werden, da kein lokaler ADS Router Daemon läuft.

**Route auf der PLC-Seite (falls add_route_to_plc fehlschlägt):**

Auf der PLC muss eine statische Route existieren:
- **Name:** SmartHomeVM (o.ä.)
- **AMS Net Id:** 192.168.2.123.1.1 (AMS des Linux-Rechners)
- **Address:** 192.168.2.123 (IP des Linux-Rechners)
- **Transport:** TCP/IP

Bei TwinCAT 2 (CX-Serie): Route über TwinCAT System Manager oder CERHost anlegen.
Bei TwinCAT 3: Route über TwinCAT XAE unter SYSTEM → Routes anlegen.

> **Hinweis:** ADS-Routen werden sofort wirksam — ein TwinCAT-Neustart ist NICHT nötig.

### **1c. Beckhoff CX8090 Besonderheiten**

Die CX8090 (TwinCAT 2, Windows CE) hat spezifische Eigenschaften bei der
ADS-Kommunikation über TCP:

| Eigenschaft | Wert |
|---|---|
| ADS Port (PLC Runtime 1) | 801 (`pyads.PORT_TC2PLC1`) |
| TCP Connection Cooldown | ~5 Sekunden nach Disconnect |
| Erstkontakt nach open() | `read_device_info()` statt `read_state()` verwenden |
| InvokeId Mismatch | Erster `read_state()` nach `open()` kann fehlschlagen |
| Symbole | 14.264 (vollständiges Lesen via `get_all_symbols()`) |

**Connection Cooldown:**
Die CX8090 benötigt ca. 5 Sekunden nach dem Schließen einer TCP-Verbindung,
bevor sie auf einer neuen Verbindung wieder ADS-Requests beantwortet.
Dies muss beim Auto-Reconnect berücksichtigt werden:

```python
plc.close()
time.sleep(5)  # CX8090 Connection Cooldown
plc.open()
```

**Zuverlässiger Verbindungstest:**
```python
# read_state() hat InvokeId-Probleme auf CX8090 direkt nach open()
# Stattdessen read_device_info() verwenden:
plc.open()
time.sleep(2)
name, version = plc.read_device_info()  # Zuverlässiger als read_state()
print(f"PLC: {name} v{version.version}.{version.revision}.{version.build}")
```

### **2. Datei-Struktur erstellen**

```
D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu\
├── Haussteuerung_v2.py
├── module_manager.py
└── modules\
    ├── __init__.py
    ├── core\
    │   ├── __init__.py
    │   ├── plc_communication.py
    │   ├── config_manager.py
    │   ├── symbol_manager.py
    │   └── update_loop.py
    ├── ui\
    │   ├── __init__.py
    │   ├── gui_manager.py
    │   ├── card_manager.py
    │   ├── card_renderer.py
    │   ├── tab_manager.py
    │   ├── drag_drop.py
    │   ├── status_bar.py
    │   ├── search_filter.py
    │   └── context_menu.py
    ├── integrations\
    │   ├── __init__.py
    │   ├── mqtt_integration.py
    │   ├── modbus_integration.py
    │   └── rtsp_integration.py
    └── plugins\
        ├── __init__.py
        ├── light_plugin.py
        ├── temperature_plugin.py
        ├── gauge_plugin.py
        ├── weather_plugin.py
        └── solarassistant_plugin.py
```

### **3. Erste Schritte**

**Start:**
```bash
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu
python Haussteuerung_v2.py
```

**Erwarteter Output:**
```
======================================================================
  TwinCAT Smart Home v2.2.6
  Build: 2025-11-30
======================================================================

📦 Lade Core-Module...
  ✓ Modul geladen: plc_communication v1.0.0
  ✓ Modul geladen: config_manager v1.0.0
  ...

🔌 Lade Integration-Module...
  ✓ Modul geladen: mqtt_integration v1.0.0
  ...

⚙️  Initialisiere Module...
  ⚡ mqtt_integration v1.0.0 initialisiert
  ⚠️  mqtt_integration: paho-mqtt nicht verfügbar!  ← Wenn nicht installiert
  
✓ PLC verbunden: 192.168.2.162.1.1

🚀 Starte GUI...
```

---

## ⚙️ **KONFIGURATION**

### **Config-Dateien**

**Speicherort:**
```
Windows: C:\Users\[USER]\Documents\TwinCAT_SmartHome\
Linux:   ~/.config/twincat_smarthome/
```

**Dateien:**
```
twincat_config.json      # Hauptkonfiguration
twincat_layout.json      # Card-Positionen
symbol_cache.json        # PLC-Symbole (14.264+)
backups/                 # Auto-Backups
  config_backup_*.json
```

### **twincat_config.json**

```json
{
  "version": "1.0",
  "theme": "blue",
  
  "plc": {
    "ams_net_id": "192.168.2.162.1.1",
    "port": 801
  },
  
  "performance": {
    "update_interval": 0.2,
    "symbol_browser_limit": 100
  },
  
  "mqtt": {
    "broker": "192.168.2.50",
    "port": 1883,
    "username": null,
    "password": null
  },
  
  "custom_tabs": {
    "tab_1732997123456": {
      "name": "Garage",
      "icon": "🚗"
    }
  },
  
  "custom_lights": {
    "Card_ABC123": {
      "name": "Wohnzimmer Licht",
      "plugin_type": "light",
      "type": "pulse",
      "pulse_duration": 200,
      "input": "MAIN.VBEINGANG1",
      "output": "MAIN.VBAUSGANG1",
      "floor": "🏡 Erdgeschoss",
      "position": {"x": 0, "y": 0},
      "icon": "💡"
    },
    
    "Card_XYZ789": {
      "name": "PV-Anlage",
      "plugin_type": "solarassistant",
      "topics": {
        "pv_power": "solar/pv/power",
        "battery_soc": "solar/battery/soc",
        "grid_power": "solar/grid/power",
        "daily_yield": "solar/daily/yield"
      },
      "floor": "🏡 Erdgeschoss",
      "icon": "☀️"
    }
  }
}
```

### **PLC-Konfiguration**

**TwinCAT 2:**
```json
{
  "plc": {
    "ams_net_id": "192.168.2.162.1.1",
    "port": 801
  }
}
```

**TwinCAT 3:**
```json
{
  "plc": {
    "ams_net_id": "192.168.2.162.1.1",
    "port": 851
  }
}
```

**Port-Tabelle:**
```
TC2 PLC1: 801
TC2 PLC2: 811
TC2 PLC3: 821
TC2 PLC4: 831

TC3 PLC1: 851
TC3 PLC2: 852
TC3 PLC3: 853
TC3 PLC4: 854
```

### **MQTT-Konfiguration**

**SolarAssistant:**
```json
{
  "mqtt": {
    "broker": "192.168.2.50",
    "port": 1883,
    "username": null,
    "password": null
  }
}
```

**Mit Auth:**
```json
{
  "mqtt": {
    "broker": "192.168.2.50",
    "port": 1883,
    "username": "smarthome",
    "password": "geheim123"
  }
}
```

**Topics (SolarAssistant):**
```
solar_assistant/total/pv_power/state
solar_assistant/total/battery_soc/state
solar_assistant/total/grid_power/state
solar_assistant/total/daily_yield/state
```

### **Performance-Settings**

```json
{
  "performance": {
    "update_interval": 0.2,        // 0.2s - 5.0s
    "symbol_browser_limit": 100    // 10 - 500
  }
}
```

**Empfohlene Werte:**
- **Schnell:** 0.2s Intervall, 100 Symbole
- **Standard:** 1.0s Intervall, 100 Symbole
- **Langsam:** 2.0s+ Intervall, 50 Symbole

---

## ⚠️ **BEKANNTE EINSCHRÄNKUNGEN**

### **1. MQTT**
- **Erfordert:** paho-mqtt Installation
- **Workaround:** Modul lädt trotzdem, zeigt Warnung
- **Installation:** `pip install paho-mqtt --break-system-packages`

### **2. Symbol-Browser**
- **Limit:** Max 100 Symbole live gleichzeitig
- **Grund:** Performance (14.264+ Symbole verfügbar)
- **Workaround:** Suche nutzen, Live-Updates gezielt aktivieren

### **3. PLC-Verbindung**
- **TC2 vs TC3:** Port 801 vs 851
- **Default:** TC2 (Port 801)
- **Ändern:** Settings → PLC oder config.json

### **4. Custom Tabs**
- **Standard-Tabs:** Erdgeschoss, Obergeschoss, Dachboden (nicht löschbar)
- **Custom Tabs:** Unbegrenzt
- **Grund:** Standard-Tabs haben `skip_save=True`

### **5. Theme-System**
- **Änderung:** Erfordert App-Neustart
- **Grund:** Tkinter-Limitierung
- **3 Themes:** Blue, Dark, Green

### **6. Drag & Drop**
- **Grid-Snapping:** Fest 10px
- **Keine Überlappung:** Cards können sich überlappen
- **Speicherung:** Beim Beenden der App

---

## 🔄 **MIGRATION VON ÄLTEREN VERSIONEN**

### **v1.2 → v2.2.6**

**1. Backup erstellen:**
```
C:\Users\[USER]\Documents\TwinCAT_SmartHome\
→ Gesamten Ordner kopieren!
```

**2. Symbol-Cache konvertieren:**
```
App startet automatisch Konvertierung:
v1.2 Format (List) → v2.0 Format (Dict)
```

**3. Config migrieren:**
```
Alte config.json wird automatisch gelesen.
Custom Lights werden übernommen.
```

**4. Neue Features:**
- Tab-Manager
- Performance-Settings
- MQTT (neu konfigurieren)
- Symbol-Download

**5. Breaking Changes:**
```
KEINE! v2.2.6 ist kompatibel mit v1.2 Configs.
```

### **v2.0.x → v2.2.6**

**1. Alte Module löschen:**
```
Lösche (falls vorhanden):
modules/mqtt_module.py
modules/modbus_module.py
modules/rtsp_module.py
```

**2. Tab-Duplikate bereinigen:**
```
Option A:
- 📑 Tab-Manager → Alle Custom Tabs löschen
- App neu starten
- Tabs neu erstellen

Option B:
- config.json editieren: "custom_tabs": {}
```

**3. MQTT neu konfigurieren:**
```
⚙️ Einstellungen → 📡 MQTT
pip install paho-mqtt --break-system-packages
```

### **v2.2.5 → v2.2.6**

**Nur aktualisieren:**
```
modules/integrations/mqtt_integration.py
Haussteuerung_v2.py
```

**Keine Migration nötig!**

---

## 📚 **DATEI-LISTE (Vollständig)**

### **Hauptdateien (2)**
1. `Haussteuerung_v2.py` - Hauptanwendung
2. `module_manager.py` - Modulsystem

### **Core-Module (4)**
1. `modules/core/plc_communication.py`
2. `modules/core/config_manager.py`
3. `modules/core/symbol_manager.py`
4. `modules/core/update_loop.py`

### **UI-Module (8)**
1. `modules/ui/gui_manager.py`
2. `modules/ui/card_manager.py`
3. `modules/ui/card_renderer.py`
4. `modules/ui/tab_manager.py`
5. `modules/ui/drag_drop.py`
6. `modules/ui/status_bar.py`
7. `modules/ui/search_filter.py`
8. `modules/ui/context_menu.py`

### **Integration-Module (3)**
1. `modules/integrations/mqtt_integration.py` ⭐
2. `modules/integrations/modbus_integration.py`
3. `modules/integrations/rtsp_integration.py`

### **Plugins (5)**
1. `modules/plugins/light_plugin.py`
2. `modules/plugins/temperature_plugin.py`
3. `modules/plugins/gauge_plugin.py`
4. `modules/plugins/weather_plugin.py`
5. `modules/plugins/solarassistant_plugin.py` ⭐

### **__init__.py Dateien (5)**
1. `modules/__init__.py`
2. `modules/core/__init__.py`
3. `modules/ui/__init__.py`
4. `modules/integrations/__init__.py`
5. `modules/plugins/__init__.py`

**Gesamt: 27 Dateien**

---

## 🎯 **QUICK START CHECKLISTE**

- [ ] Python 3.8+ installiert
- [ ] pyads installiert (`pip install pyads --break-system-packages`)
- [ ] paho-mqtt installiert (`pip install paho-mqtt --break-system-packages`)
- [ ] Alle 27 Dateien vorhanden
- [ ] Ordner-Struktur korrekt
- [ ] TwinCAT 2/3 läuft
- [ ] AMS Net ID konfiguriert
- [ ] Port korrekt (801=TC2, 851=TC3)
- [ ] App startet ohne Fehler
- [ ] Module: 20/20 LOADED
- [ ] PLC verbunden
- [ ] MQTT-Modul geladen (auch wenn paho-mqtt fehlt)

---

## 📞 **SUPPORT & DEBUG**

### **Häufige Probleme:**

**1. "Module nicht geladen"**
```
Lösung: Alte *_module.py löschen
```

**2. "PLC verbindet nicht"**
```
Prüfe: Port 801 (TC2) oder 851 (TC3)?
```

**5. "ADSError: timeout elapsed (1861)" auf Linux**
```
Mögliche Ursachen:
- Route auf PLC-Seite fehlt → Statische Route auf PLC anlegen
- Keine IP beim Connection()-Aufruf → 3. Parameter (IP) angeben!
- CX8090 Connection Cooldown → 5s warten nach Disconnect
- Netzwerk-Problem → ping zur PLC prüfen
- Firewall → TCP Port 48898 muss offen sein
```

**6. "InvokeId mismatch" bei CX8090**
```
Normal bei CX8090 nach open(). read_device_info() statt read_state()
als ersten Befehl verwenden. Siehe Abschnitt "CX8090 Besonderheiten".
```

**7. "ADSError: Ads operation failed with error code 6" (adstool)**
```
Error 6 = Lokaler ADS-Router kann Route nicht finden.
Bei adstool den --gw Parameter verwenden:
  adstool 192.168.2.162:801 --gw=192.168.2.162 --localams=192.168.2.123.1.1 state
```

**3. "MQTT nicht verfügbar"**
```
pip install paho-mqtt --break-system-packages
```

**4. "Tabs duplizieren sich"**
```
Lösung: v2.2.4+ verwenden
```

### **Debug-Modus:**
```
Console zeigt:
- Module-Status
- Fehler-Meldungen
- Verbindungs-Info
- Performance-Daten
```

---

## 📊 **STATISTIK**

- **Versionen:** v1.0 → v2.2.6 (12 Major Updates)
- **Module:** 20 (Core: 4, UI: 8, Integrations: 3, Plugins: 5)
- **Dateien:** 27
- **Code-Zeilen:** ~15.000+
- **Bugfixes:** 10+ kritische Bugs
- **Features:** 40+
- **Entwicklungszeit:** ~4 Monate
- **Status:** ✅ PRODUCTION READY

---

## ✅ **FINAL CHECKLIST FÜR KI-ÜBERGABE**

- [x] Vollständiger Changelog
- [x] Alle Bugfixes dokumentiert
- [x] Architektur erklärt
- [x] Installation beschrieben
- [x] Konfiguration erklärt
- [x] Migration beschrieben
- [x] Datei-Liste vollständig
- [x] Bekannte Limitierungen
- [x] Support-Hinweise
- [x] Quick Start Guide

---

**Dokument erstellt:** 2025-11-30  
**Version:** 2.2.6  
**Status:** PRODUCTION READY ✅  
**Bereit für KI-Übergabe:** ✅
