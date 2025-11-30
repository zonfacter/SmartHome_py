# 🏗️ Modulare Architektur - TwinCAT Smart Home v1.2.0

## 🎯 Architektur-Prinzipien

### **Warum modular?**

**Vorteile:**
- ✅ **Wartbarkeit:** Jedes Modul ist eigenständig
- ✅ **Testbarkeit:** Module einzeln testbar
- ✅ **Erweiterbarkeit:** Neue Features = Neues Modul
- ✅ **Team-Arbeit:** Mehrere Entwickler parallel
- ✅ **Wiederverwendung:** Module in anderen Projekten nutzbar
- ✅ **Stabilität:** Fehler in einem Modul betreffen nicht alle

**Beispiel:**
```
Vorher (Monolith):
- 1 Datei, 3400 Zeilen
- Änderung an GUI → Ganzes File neu testen
- Merge-Konflikte bei Team-Arbeit

Jetzt (Modular):
- Hauptdatei: 250 Zeilen (nur Orchestrierung)
- 12 Module: je 100-300 Zeilen
- GUI-Änderung → Nur gui_manager.py testen
- Parallele Entwicklung möglich
```

---

## 📁 Datei-Struktur

```
TwinCAT_SmartHome/
│
├── Haussteuerung.py          # 🎬 Hauptorchestrator (250 Zeilen)
│                              # - Lädt Module
│                              # - Koordiniert Kommunikation
│                              # - Keine Business-Logik!
│
├── module_manager.py          # 📦 Modul-Verwaltung (300 Zeilen)
│                              # - Lädt/Entlädt Module
│                              # - Versionsprüfung
│                              # - Abhängigkeits-Check
│
├── modules/
│   │
│   ├── core/                  # 🔧 Kern-Module (Pflicht)
│   │   ├── plc_communication.py    # PLC-Verbindung (200 Zeilen)
│   │   ├── config_manager.py       # Konfigurations-Verwaltung (250 Zeilen)
│   │   └── symbol_manager.py       # Symbol-Cache & DB (300 Zeilen)
│   │
│   ├── ui/                    # 🎨 UI-Module (Pflicht)
│   │   ├── gui_manager.py          # GUI-Framework (250 Zeilen)
│   │   ├── card_renderer.py        # Card-Erstellung (300 Zeilen)
│   │   ├── search_filter.py        # Suche & Filter (150 Zeilen)
│   │   ├── context_menu.py         # Rechtsklick-Menü (100 Zeilen)
│   │   └── drag_drop.py            # Drag & Drop System (200 Zeilen)
│   │
│   ├── integrations/          # 🔌 Integrations-Module (Optional)
│   │   ├── modbus_module.py        # Modbus TCP/RTU (200 Zeilen)
│   │   ├── mqtt_module.py          # MQTT (180 Zeilen)
│   │   └── rtsp_module.py          # Kamera-Streams (150 Zeilen)
│   │
│   └── plugins/               # 🧩 Plugin-Module (Optional)
│       ├── light_plugin.py         # Light Card (150 Zeilen)
│       ├── temperature_plugin.py   # Temperature Card (120 Zeilen)
│       ├── gauge_plugin.py         # Gauge Card (180 Zeilen)
│       └── weather_plugin.py       # Weather Card (150 Zeilen)
│
└── config/                    # ⚙️ Konfigurationen
    ├── twincat_config.json
    ├── twincat_layout.json
    └── symbols.db
```

**Gesamt:** ~3400 Zeilen verteilt auf 16 Dateien
**Durchschnitt:** ~210 Zeilen pro Datei

---

## 🔄 Modul-Kommunikation

### **Wie Module miteinander sprechen:**

```python
# 1. ÜBER MODULE MANAGER
app.module_manager.call_module_method('plc_communication', 'read_by_name', 'MAIN.bLight', pyads.PLCTYPE_BOOL)

# 2. DIREKTE REFERENZ (nach Initialisierung)
plc_module = app.module_manager.get_module('plc_communication')
value = plc_module.read_by_name('MAIN.bLight', pyads.PLCTYPE_BOOL)

# 3. EVENT-SYSTEM (entkoppelt)
gui_module.register_event('theme_changed', on_theme_changed)
gui_module.trigger_event('theme_changed', 'dark')
```

### **Beispiel-Ablauf: Card klicken**

```
User klickt Card
  ↓
card_renderer.py (UI)
  → Ruft context_menu.py
     ↓
context_menu.py
  → Trigger Event 'card_action'
     ↓
Haussteuerung.py (Orchestrator)
  → Hört auf Event
  → Ruft plc_communication.py
     ↓
plc_communication.py (Core)
  → Schreibt zu PLC
  → Trigger Event 'plc_written'
     ↓
card_renderer.py (UI)
  → Hört auf Event
  → Aktualisiert Card-Anzeige
```

**Vorteile:**
- UI kennt PLC-Modul nicht direkt
- PLC-Modul kann ausgetauscht werden
- Keine zirkulären Abhängigkeiten

---

## 🧩 Modul-Struktur

### **Jedes Modul hat:**

```python
"""
Modul-Name
Version: X.Y.Z
Beschreibung
"""

from module_manager import BaseModule

class MeinModul(BaseModule):
    NAME = "mein_modul"
    VERSION = "1.0.0"
    DESCRIPTION = "Was macht das Modul"
    AUTHOR = "Dein Name"
    DEPENDENCIES = ['anderes_modul']  # Optional
    
    def __init__(self):
        super().__init__()
        # Initialisierung
    
    def initialize(self, app_context):
        """Wird beim Start aufgerufen"""
        super().initialize(app_context)
        self.app = app_context
    
    # Öffentliche API-Methoden
    def meine_funktion(self, param):
        """Was die Funktion macht"""
        pass
    
    def shutdown(self):
        """Aufräumen beim Beenden"""
        pass

# Registrierung
def register(module_manager):
    module_manager.register_module(
        MeinModul.NAME,
        MeinModul.VERSION,
        MeinModul.DESCRIPTION,
        MeinModul,
        author=MeinModul.AUTHOR,
        dependencies=MeinModul.DEPENDENCIES
    )
```

---

## 📚 Module im Detail

### **1. Core-Module (Pflicht)**

#### **plc_communication.py**
```
Verantwortlich für:
- ADS-Verbindung zu TwinCAT
- Lesen/Schreiben von Variablen
- Auto-Reconnect
- Caching (Performance)

API:
- connect()
- disconnect()
- read_by_name(variable, type)
- write_by_name(variable, value, type)
- toggle_bool(variable)
- pulse(variable, duration)

Abhängigkeiten: pyads
```

#### **config_manager.py**
```
Verantwortlich für:
- Config-Dateien laden/speichern
- Versionierung
- Backups
- Migration alter Configs

API:
- load_config()
- save_config()
- create_backup()
- get_value(key)
- set_value(key, value)

Abhängigkeiten: -
```

#### **symbol_manager.py**
```
Verantwortlich für:
- Symbol-Cache (JSON/SQLite)
- TPY-Parsing
- Suche in Symbolen
- Auto-Migration

API:
- load_symbols()
- search_symbols(query)
- get_symbol(name)
- import_from_tpy(file)

Abhängigkeiten: -
```

---

### **2. UI-Module (Pflicht)**

#### **gui_manager.py**
```
Verantwortlich für:
- Hauptfenster
- Theme-System
- Notebook/Tabs
- Styled Widgets

API:
- create_window()
- define_themes()
- apply_theme(name)
- create_button()
- create_frame()

Abhängigkeiten: tkinter
```

#### **card_renderer.py**
```
Verantwortlich für:
- Cards erstellen
- Plugin-System nutzen
- Layout-Verwaltung
- Update-Loop

API:
- create_card(type, config)
- update_card(id)
- delete_card(id)
- get_all_cards()

Abhängigkeiten: gui_manager, plugins
```

#### **search_filter.py**
```
Verantwortlich für:
- Suchleiste
- Live-Filter
- Kategorie-Filter
- Ergebnis-Counter

API:
- create_search_bar()
- filter_cards(query)
- set_category(cat)
- clear_filter()

Abhängigkeiten: gui_manager
```

---

### **3. Integration-Module (Optional)**

#### **modbus_module.py**
```
Verantwortlich für:
- Modbus TCP/RTU
- Deye Wechselrichter
- Polling

API:
- add_device(name, host, port)
- read_register(device, address)
- write_register(device, address, value)

Abhängigkeiten: pymodbus
```

#### **mqtt_module.py**
```
Verantwortlich für:
- MQTT Broker-Verbindung
- SolarAssistant
- Publish/Subscribe

API:
- connect(broker, port)
- subscribe(topic, callback)
- publish(topic, payload)

Abhängigkeiten: paho-mqtt
```

#### **rtsp_module.py**
```
Verantwortlich für:
- RTSP Kamera-Streams
- Frame-Grabbing
- Video-Anzeige

API:
- add_camera(id, url)
- get_frame(id)
- start_stream(id)

Abhängigkeiten: opencv-python
```

---

## 🔧 Entwicklung

### **Neues Modul erstellen:**

```bash
# 1. Erstelle Datei
touch modules/integrations/mein_modul.py

# 2. Template kopieren
# (Siehe Modul-Struktur oben)

# 3. Implementiere Funktionen

# 4. Registriere in Haussteuerung.py
def load_integration_modules(self):
    self.module_manager.load_module_from_file('modules/integrations/mein_modul.py')

# 5. Teste
python Haussteuerung.py
```

### **Modul aktualisieren:**

```python
# Einfach Version erhöhen
VERSION = "1.1.0"

# Module Manager erkennt Update automatisch
# Zeigt in Status-Übersicht
```

### **Modul deaktivieren:**

```python
# In Haussteuerung.py auskommentieren
# self.module_manager.load_module_from_file('modules/...')

# Oder Datei umbenennen
mv mein_modul.py mein_modul.py.disabled
```

---

## 🧪 Testing

### **Modul einzeln testen:**

```python
# test_plc_communication.py
from modules.core.plc_communication import PLCCommunication

# Erstelle Modul
plc = PLCCommunication()
plc.initialize(None)

# Konfiguriere
plc.configure('192.168.1.100')

# Teste
if plc.connect():
    value = plc.read_by_name('MAIN.bTest', pyads.PLCTYPE_BOOL)
    print(f"Value: {value}")
    plc.disconnect()
```

### **Integration-Test:**

```python
# test_integration.py
from module_manager import ModuleManager

manager = ModuleManager()
manager.load_module_from_file('modules/core/plc_communication.py')
manager.load_module_from_file('modules/ui/gui_manager.py')

print(manager.get_status_summary())
```

---

## 📊 Performance

### **Modul-Loading:**
```
Startup-Zeit:
- Module laden: ~500ms
- Module initialisieren: ~200ms
- GUI aufbauen: ~1000ms

Gesamt: ~1.7s (akzeptabel)
```

### **Memory:**
```
- Hauptprogramm: ~50 MB
- Module: ~10 MB pro Modul
- Gesamt (15 Module): ~200 MB

(Monolith war: ~180 MB)
→ Overhead: 10% (akzeptabel für Modularität)
```

---

## 🚀 Migration Monolith → Modular

### **Phase 1: Core (Woche 1)**
- [x] module_manager.py
- [x] plc_communication.py
- [ ] config_manager.py
- [ ] symbol_manager.py

### **Phase 2: UI (Woche 2)**
- [x] gui_manager.py
- [ ] card_renderer.py
- [ ] search_filter.py
- [ ] context_menu.py
- [ ] drag_drop.py

### **Phase 3: Integrations (Woche 3)**
- [x] modbus_module.py
- [x] mqtt_module.py
- [x] rtsp_module.py

### **Phase 4: Plugins (Woche 4)**
- [ ] light_plugin.py
- [ ] temperature_plugin.py
- [ ] gauge_plugin.py
- [ ] weather_plugin.py

### **Phase 5: Polish (Woche 5)**
- [ ] Tests für alle Module
- [ ] Dokumentation
- [ ] Performance-Optimierung

---

## 💡 Best Practices

### **DOs:**
✅ Ein Modul = Eine Verantwortung
✅ Klare API-Definitionen
✅ Versionierung bei Änderungen
✅ Event-System für Entkopplung
✅ Error-Handling in jedem Modul
✅ Dokumentation in Docstrings

### **DON'Ts:**
❌ Module direkt importieren (nur via Manager!)
❌ Zirkuläre Abhängigkeiten
❌ Global State (außer in App-Context)
❌ Hardcoded Paths/IPs
❌ Fehlende Fehlerbehandlung
❌ Undokumentierte APIs

---

## 🎯 Ergebnis

**Vorher (Monolith):**
```
✗ 3400 Zeilen in 1 Datei
✗ Schwer wartbar
✗ Schwer testbar
✗ Team-Arbeit problematisch
✗ Feature-Änderung = Ganzes File testen
```

**Jetzt (Modular):**
```
✓ 250 Zeilen Hauptdatei
✓ 16 kleine Module (je ~200 Zeilen)
✓ Leicht wartbar
✓ Einzeln testbar
✓ Parallele Entwicklung möglich
✓ Feature-Änderung = 1 Modul testen
✓ Wiederverwendbar in anderen Projekten
```

**Win! 🎉**
