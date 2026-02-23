# 📁 Datei-Organisation - TwinCAT Smart Home v2.0

**Wichtig:** Alle Dateien müssen in der richtigen Ordner-Struktur liegen!

---

## 🗂️ Komplette Ordner-Struktur

```
D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu\
│
├── Haussteuerung_v2.py              ← Haupt-Anwendung (START HIER!)
├── module_manager.py                 ← Module Manager
├── config.json                       ← Konfiguration
├── requirements.txt                  ← Python Dependencies
│
├── modules/                          ← Alle Module hier!
│   │
│   ├── core/                         ← Core-Module (4 Dateien)
│   │   ├── __init__.py
│   │   ├── plc_communication.py
│   │   ├── config_manager.py
│   │   ├── symbol_manager.py
│   │   └── update_loop.py           ← NEU in v2.0!
│   │
│   ├── ui/                           ← UI-Module (8 Dateien)
│   │   ├── __init__.py
│   │   ├── gui_manager.py
│   │   ├── status_bar.py            ← NEU in v2.0!
│   │   ├── card_manager.py          ← NEU in v2.0!
│   │   ├── card_renderer.py
│   │   ├── search_filter.py
│   │   ├── context_menu.py
│   │   ├── drag_drop.py             ← v2.0 erweitert!
│   │   └── tab_manager.py           ← NEU in v2.0!
│   │
│   ├── integrations/                 ← Integration-Module (3 Dateien)
│   │   ├── __init__.py
│   │   ├── modbus_module.py
│   │   ├── mqtt_module.py
│   │   └── rtsp_module.py
│   │
│   └── plugins/                      ← Plugin-Module (4 Dateien)
│       ├── __init__.py
│       ├── light_plugin.py
│       ├── temperature_plugin.py
│       ├── gauge_plugin.py
│       └── weather_plugin.py
│
└── docs/                             ← Dokumentation
    ├── VERSION_2.0_ROADMAP.md
    ├── PROGRESS_TRACKING_v2.0.md
    ├── FEATURE_COMPARISON_v1.2_vs_v2.0.md
    ├── TEST_CHECKLIST_v2.0.md
    ├── RELEASE_NOTES_v2.0.0.md
    ├── SESSION_SUMMARY_v2.0.md
    └── FILE_ORGANIZATION.md          ← Diese Datei
```

---

## 📝 Datei-Zuordnung (Schnell-Referenz)

### **Haupt-Ebene (Root)**

| Datei | Pfad |
|-------|------|
| Haussteuerung_v2.py | `D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu\Haussteuerung_v2.py` |
| module_manager.py | `D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu\module_manager.py` |
| config.json | `D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu\config.json` |

### **Core-Module**

| Datei | Pfad |
|-------|------|
| plc_communication.py | `modules\core\plc_communication.py` |
| config_manager.py | `modules\core\config_manager.py` |
| symbol_manager.py | `modules\core\symbol_manager.py` |
| update_loop.py | `modules\core\update_loop.py` ← **NEU!** |

### **UI-Module**

| Datei | Pfad |
|-------|------|
| gui_manager.py | `modules\ui\gui_manager.py` |
| status_bar.py | `modules\ui\status_bar.py` ← **NEU!** |
| card_manager.py | `modules\ui\card_manager.py` ← **NEU!** |
| card_renderer.py | `modules\ui\card_renderer.py` |
| search_filter.py | `modules\ui\search_filter.py` |
| context_menu.py | `modules\ui\context_menu.py` |
| drag_drop.py | `modules\ui\drag_drop.py` ← **ERWEITERT!** |
| tab_manager.py | `modules\ui\tab_manager.py` ← **NEU!** |

### **Integration-Module**

| Datei | Pfad |
|-------|------|
| modbus_module.py | `modules\integrations\modbus_module.py` |
| mqtt_module.py | `modules\integrations\mqtt_module.py` |
| rtsp_module.py | `modules\integrations\rtsp_module.py` |

### **Plugin-Module**

| Datei | Pfad |
|-------|------|
| light_plugin.py | `modules\plugins\light_plugin.py` |
| temperature_plugin.py | `modules\plugins\temperature_plugin.py` |
| gauge_plugin.py | `modules\plugins\gauge_plugin.py` |
| weather_plugin.py | `modules\plugins\weather_plugin.py` |

---

## 🚀 Schnell-Installation

### **Option 1: Manuelle Ordner-Erstellung**

```batch
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu

:: Erstelle Ordner-Struktur
mkdir modules
mkdir modules\core
mkdir modules\ui
mkdir modules\integrations
mkdir modules\plugins
mkdir docs

:: Erstelle __init__.py Dateien
echo. > modules\__init__.py
echo. > modules\core\__init__.py
echo. > modules\ui\__init__.py
echo. > modules\integrations\__init__.py
echo. > modules\plugins\__init__.py
```

### **Option 2: PowerShell Script**

```powershell
# Setup-Folders.ps1
$base = "D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu"

# Erstelle Ordner
$folders = @(
    "modules\core",
    "modules\ui",
    "modules\integrations",
    "modules\plugins",
    "docs"
)

foreach ($folder in $folders) {
    New-Item -Path "$base\$folder" -ItemType Directory -Force
    New-Item -Path "$base\$folder\__init__.py" -ItemType File -Force
}

Write-Host "✅ Ordner-Struktur erstellt!"
```

Ausführen:
```powershell
.\Setup-Folders.ps1
```

---

## 📋 Installations-Checklist

### **1. Ordner-Struktur erstellen**
- [ ] `modules/core/` erstellt
- [ ] `modules/ui/` erstellt
- [ ] `modules/integrations/` erstellt
- [ ] `modules/plugins/` erstellt
- [ ] `docs/` erstellt
- [ ] Alle `__init__.py` Dateien erstellt

### **2. Haupt-Dateien kopieren**
- [ ] `Haussteuerung_v2.py` → Root
- [ ] `module_manager.py` → Root
- [ ] `config.json` → Root (oder wird auto-generiert)

### **3. Core-Module kopieren**
- [ ] `plc_communication.py` → `modules/core/`
- [ ] `config_manager.py` → `modules/core/`
- [ ] `symbol_manager.py` → `modules/core/`
- [ ] `update_loop.py` → `modules/core/`

### **4. UI-Module kopieren**
- [ ] `gui_manager.py` → `modules/ui/`
- [ ] `status_bar.py` → `modules/ui/`
- [ ] `card_manager.py` → `modules/ui/`
- [ ] `card_renderer.py` → `modules/ui/`
- [ ] `search_filter.py` → `modules/ui/`
- [ ] `context_menu.py` → `modules/ui/`
- [ ] `drag_drop.py` → `modules/ui/`
- [ ] `tab_manager.py` → `modules/ui/`

### **5. Integration-Module kopieren**
- [ ] `modbus_module.py` → `modules/integrations/`
- [ ] `mqtt_module.py` → `modules/integrations/`
- [ ] `rtsp_module.py` → `modules/integrations/`

### **6. Plugin-Module kopieren**
- [ ] `light_plugin.py` → `modules/plugins/`
- [ ] `temperature_plugin.py` → `modules/plugins/`
- [ ] `gauge_plugin.py` → `modules/plugins/`
- [ ] `weather_plugin.py` → `modules/plugins/`

### **7. Dokumentation kopieren (optional)**
- [ ] Alle .md Dateien → `docs/`

---

## ✅ Verifikation

### **Prüfe Ordner-Struktur:**

```batch
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu
tree /F
```

**Sollte zeigen:**
```
├── Haussteuerung_v2.py
├── module_manager.py
└── modules
    ├── core
    │   ├── __init__.py
    │   ├── plc_communication.py
    │   ├── config_manager.py
    │   ├── symbol_manager.py
    │   └── update_loop.py
    ├── ui
    │   ├── __init__.py
    │   ├── gui_manager.py
    │   ├── status_bar.py
    │   ├── card_manager.py
    │   ├── card_renderer.py
    │   ├── search_filter.py
    │   ├── context_menu.py
    │   ├── drag_drop.py
    │   └── tab_manager.py
    ├── integrations
    │   ├── __init__.py
    │   ├── modbus_module.py
    │   ├── mqtt_module.py
    │   └── rtsp_module.py
    └── plugins
        ├── __init__.py
        ├── light_plugin.py
        ├── temperature_plugin.py
        ├── gauge_plugin.py
        └── weather_plugin.py
```

### **Test-Start:**

```batch
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu
python Haussteuerung_v2.py
```

**Erwartete Ausgabe:**
```
======================================================================
  TwinCAT Smart Home v2.0.0
  Build: 2024-11-30
  Vollständig Modular
======================================================================

📦 Module Manager v1.0.0 gestartet

📦 Lade Core-Module...
  ⚡ plc_communication v2.0.0 geladen
  ⚡ config_manager v2.0.0 geladen
  ⚡ symbol_manager v2.0.0 geladen
  ⚡ update_loop v2.0.0 geladen

🎨 Lade UI-Module...
  ⚡ gui_manager v2.0.0 geladen
  ⚡ status_bar v2.0.0 geladen
  ⚡ card_manager v2.0.0 geladen
  [...]

✅ Alle Module geladen!
```

---

## 🐛 Troubleshooting

### **Problem: "ModuleNotFoundError: No module named 'modules'"**

**Lösung:**
```batch
:: Prüfe ob __init__.py existiert
dir modules\__init__.py
dir modules\core\__init__.py
dir modules\ui\__init__.py
dir modules\integrations\__init__.py
dir modules\plugins\__init__.py

:: Erstelle wenn fehlend
echo. > modules\__init__.py
```

### **Problem: "Module 'xyz' not found"**

**Lösung:**
```batch
:: Prüfe ob Datei im richtigen Ordner liegt
dir modules\core\update_loop.py
dir modules\ui\status_bar.py
dir modules\ui\card_manager.py
dir modules\ui\tab_manager.py
```

### **Problem: "ImportError: cannot import name 'BaseModule'"**

**Lösung:**
```batch
:: Stelle sicher dass module_manager.py im Root liegt
dir module_manager.py

:: Sollte 1 Datei zeigen
```

---

## 📌 Wichtige Hinweise

### **Pfad-Konventionen:**

✅ **RICHTIG:**
```python
modules/core/update_loop.py
modules/ui/status_bar.py
modules/ui/card_manager.py
```

❌ **FALSCH:**
```python
modules/update_loop.py           # Nicht im core/ Ordner!
ui/status_bar.py                 # Fehlt modules/ prefix!
modules/core/ui/status_bar.py    # Falsche Verschachtelung!
```

### **__init__.py Dateien:**

Jeder Ordner unter `modules/` MUSS ein `__init__.py` enthalten:
```
modules/__init__.py              ← WICHTIG!
modules/core/__init__.py         ← WICHTIG!
modules/ui/__init__.py           ← WICHTIG!
modules/integrations/__init__.py ← WICHTIG!
modules/plugins/__init__.py      ← WICHTIG!
```

Diese können leer sein, aber müssen existieren!

---

## 🎯 Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│  DATEI                    →  PFAD               │
├─────────────────────────────────────────────────┤
│  Haussteuerung_v2.py      →  Root               │
│  module_manager.py        →  Root               │
│  config.json              →  Root               │
│                                                  │
│  plc_communication.py     →  modules/core/      │
│  config_manager.py        →  modules/core/      │
│  symbol_manager.py        →  modules/core/      │
│  update_loop.py          →  modules/core/      │
│                                                  │
│  gui_manager.py           →  modules/ui/        │
│  status_bar.py           →  modules/ui/        │
│  card_manager.py         →  modules/ui/        │
│  card_renderer.py         →  modules/ui/        │
│  search_filter.py         →  modules/ui/        │
│  context_menu.py          →  modules/ui/        │
│  drag_drop.py            →  modules/ui/        │
│  tab_manager.py          →  modules/ui/        │
│                                                  │
│  modbus_module.py         →  modules/integrations/ │
│  mqtt_module.py           →  modules/integrations/ │
│  rtsp_module.py           →  modules/integrations/ │
│                                                  │
│  light_plugin.py          →  modules/plugins/   │
│  temperature_plugin.py    →  modules/plugins/   │
│  gauge_plugin.py          →  modules/plugins/   │
│  weather_plugin.py        →  modules/plugins/   │
└─────────────────────────────────────────────────┘
```

---

**💡 Tipp:** Drucke diese Seite aus oder speichere als PDF für schnelle Referenz!

**📧 Bei Fragen:** Siehe [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Viel Erfolg! 🚀**
