# 🔧 Kritische Fixes für v1.2

## Fehler 1: AttributeError: 'filter_category'

**Problem:**
```python
File "Haussteuerung.py", line 1945, in filter_cards
    category = self.filter_category.get()
AttributeError: 'TwinCATVisu' object has no attribute 'filter_category'
```

**Ursache:**
`filter_category` wird in `create_search_bar()` initialisiert, aber `filter_cards()` wird schon vorher aufgerufen (durch trace).

**Fix:**
In `__init__()` VOR `self.create_gui()` hinzufügen:
```python
# Zeile ~72 (nach self.drag_data)
self.filter_category = tk.StringVar(value='all')
self.filter_buttons = {}
self.search_var = None  # Wird später initialisiert
```

---

## Fehler 2: UnboundLocalError: 'header_frame'

**Problem:**
```python
File "Haussteuerung.py", line 2031, in create_light_card
    header_frame.bind("<Button-3>", lambda e: self.show_card_context_menu(e, light_id))
UnboundLocalError: cannot access local variable 'header_frame' where it is not associated with a value
```

**Ursache:**
Rechtsklick-Bindings wurden BEFORE `header_frame` erstellt wurde.

**Fix:**
In `create_light_card()` die Rechtsklick-Bindings NACH der Erstellung von `header_frame` einfügen (Zeile ~2040).

---

## Fehler 3: Keine Version in Console

**Problem:**
Console zeigt nicht welche Version läuft.

**Fix:**
Füge `print_startup_banner()` Funktion hinzu:

```python
def print_startup_banner(self):
    """Zeigt Startup-Banner mit Versionsinformationen"""
    print("=" * 60)
    print(f"{self.APP_NAME} v{self.APP_VERSION}")
    print(f"Build: {self.BUILD_DATE}")
    print(f"Config Version: {self.CONFIG_VERSION}")
    print("=" * 60)
```

Rufe in `__init__()` GANZ AM ANFANG auf:
```python
def __init__(self):
    self.print_startup_banner()  # <- NEU
    self.root = tk.Tk()
    ...
```

---

## Kompletter Fix-Patch

Füge in `twincat_visu_improved.py` ein:

### 1. Nach Klassen-Definition (Zeile ~20):
```python
class TwinCATVisu:
    # === VERSIONS-INFORMATIONEN ===
    APP_VERSION = "1.2.0"
    APP_NAME = "TwinCAT Smart Home"
    CONFIG_VERSION = "1.0"
    LEGACY_VERSIONS = []
    BUILD_DATE = "2024-11-29"
```

### 2. In __init__() GANZ AM ANFANG:
```python
def __init__(self):
    self.print_startup_banner()  # <- NEU
    ...
```

### 3. Nach self.drag_data (Zeile ~73):
```python
# Filter-Variablen initialisieren (VOR create_gui!)
self.filter_category = tk.StringVar(value='all')
self.filter_buttons = {}
self.search_var = None
```

### 4. Füge Funktion hinzu (nach __init__):
```python
def print_startup_banner(self):
    """Zeigt Startup-Banner"""
    print("=" * 60)
    print(f"{self.APP_NAME} v{self.APP_VERSION}")
    print(f"Build: {self.BUILD_DATE}")
    print(f"Config Version: v{self.CONFIG_VERSION}")
    print("=" * 60)
```

### 5. In create_light_card() - VERSCHIEBE Rechtsklick-Bindings:

**VORHER:**
```python
drag_label.bind("<ButtonRelease-1>", lambda e: self.stop_drag(e, light_id))

# Rechtsklick-Menü (Quick Actions)  <- FALSCHE POSITION
card.bind("<Button-3>", ...)
content_frame.bind("<Button-3>", ...)
header_frame.bind("<Button-3>", ...)  # <- header_frame existiert noch nicht!

# Header mit Icon und Name
header_frame = tk.Frame(...)  # <- HIER wird es erst erstellt!
```

**NACHHER:**
```python
drag_label.bind("<ButtonRelease-1>", lambda e: self.stop_drag(e, light_id))

# Header mit Icon und Name
header_frame = tk.Frame(...)
header_frame.pack(fill=tk.X)

icon_label = tk.Label(...)
icon_label.pack(side=tk.LEFT)

name_label = tk.Label(...)
name_label.pack(side=tk.LEFT, padx=15)

# Rechtsklick-Menü (HIER ist die richtige Position!)
card.bind("<Button-3>", lambda e: self.show_card_context_menu(e, light_id))
content_frame.bind("<Button-3>", lambda e: self.show_card_context_menu(e, light_id))
header_frame.bind("<Button-3>", lambda e: self.show_card_context_menu(e, light_id))
icon_label.bind("<Button-3>", lambda e: self.show_card_context_menu(e, light_id))
name_label.bind("<Button-3>", lambda e: self.show_card_context_menu(e, light_id))
```

---

## Test nach Fix:

```bash
python Haussteuerung.py
```

**Erwartete Ausgabe:**
```
============================================================
TwinCAT Smart Home v1.2.0
Build: 2024-11-29
Config Version: v1.0
============================================================
📦 Module Manager v1.0.0 gestartet
  ✓ Modul geladen: modbus_integration v1.0.0
  ✓ Modul geladen: mqtt_integration v1.0.0
  ✓ Modul geladen: rtsp_integration v1.0.0
==================================================
MODULE STATUS
==================================================
Gesamt: 3 | Geladen: 3 | Fehler: 0
==================================================
✓ modbus_integration     v1.0.0     - Modbus TCP/RTU für Wechselrichter
✓ mqtt_integration       v1.0.0     - MQTT für SolarAssistant & IoT
✓ rtsp_integration       v1.0.0     - RTSP Kamera-Streams
==================================================
✓ Konfiguration geladen: v1.0, Theme=blue, Custom Lights=1
✓ Symbol-Cache geladen: 14264 Symbole
Parsed 14264 Symbols.
```

**Keine Fehler mehr!**

---

## Wichtig für Modularität:

Module-Verzeichnis erstellen:
```bash
mkdir modules
```

Module kopieren:
```bash
cp modbus_module.py modules/
cp mqtt_module.py modules/
cp rtsp_module.py modules/
cp module_manager.py .
```

