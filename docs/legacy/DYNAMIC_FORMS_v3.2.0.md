# 🎯 v3.2.0 - DYNAMISCHE EINGABEMASKEN

**Version:** 3.2.0  
**Feature:** Schema-basierte Card-Editor mit Symbol-Browser

---

## ✨ WAS IST NEU?

### **Dynamische Eingabemasken!**

**VORHER (v3.1):**
```
Plugin-Felder: [Text-Box mit JSON]
```
❌ JSON manuell schreiben  
❌ Keine Validierung  
❌ Fehleranfällig  
❌ Kein Symbol-Browser  

**NACHHER (v3.2):**
```
⚙️ Plugin-Konfiguration

Input Variable (optional):
[                        ] [🔍]  ← Symbol-Browser!

Output Variable*:
[MAIN.VBAUSGANG43       ] [🔍]  ← Symbol-Browser!

Schalt-Typ:
○ Toggle (Umschalten)  ○ Pulse (Impuls)

Impulsdauer (ms):
[200 ▼]  ← Spinbox 50-5000
```
✅ Automatische Felder aus Plugin-Schema  
✅ Symbol-Browser für PLC-Variablen  
✅ Validierung (Required, Min/Max, Typ)  
✅ Conditional Fields (nur zeigen wenn nötig)  
✅ Professionell & benutzerfreundlich  

---

## 📦 INSTALLATION

### **Dateien:**

1. **Card-Manager v3.2.0**
   ```bash
   copy card_manager_v3.2.0.py modules\ui\card_manager.py
   ```

2. **Plugin-Schemas (alle 5!)**
   ```bash
   copy light_v2.py modules\plugins\light.py
   copy temperature_v2.py modules\plugins\temperature.py
   copy gauge_v2.py modules\plugins\gauge.py
   copy weather_v2.py modules\plugins\weather.py
   copy solarassistant_v2.py modules\plugins\solarassistant.py
   ```

3. **App neu starten**
   ```bash
   python Haussteuerung_v3.py
   ```

---

## 🎨 EINGABEMASKEN - ÜBERSICHT

### **1. LIGHT PLUGIN**

```
⚙️ Plugin-Konfiguration

Input Variable (optional):
[.BAUSGANG62                    ] [🔍]
💡 PLC-Variable für Status-Rückmeldung

Output Variable*:
[MAIN.VBAUSGANG43               ] [🔍]
💡 PLC-Variable zum Schalten

Schalt-Typ*:
○ Toggle (Umschalten)  ● Pulse (Impuls)

Impulsdauer (ms):        ← Nur bei Pulse!
[200 ▼]
💡 Dauer des Impulses in Millisekunden
```

**Feldtypen:**
- ✅ `plc_variable` mit Symbol-Browser 🔍
- ✅ `choice` mit Radio-Buttons
- ✅ `integer` mit Spinbox & Min/Max
- ✅ `show_if` für Conditional Fields

---

### **2. TEMPERATURE PLUGIN**

```
⚙️ Plugin-Konfiguration

Temperatur-Variable*:
[MAIN.fTemperatur               ] [🔍]
💡 PLC-Variable mit Temperaturwert

Einheit*:
● Celsius (°C)  ○ Fahrenheit (°F)  ○ Kelvin (K)

Nachkommastellen*:
[1 ▼]  (0-3)
💡 Anzahl Nachkommastellen
```

**Feldtypen:**
- ✅ `plc_variable` (REAL-Typ)
- ✅ `choice` mit mehreren Optionen
- ✅ `integer` mit Limits

---

### **3. GAUGE PLUGIN**

```
⚙️ Plugin-Konfiguration

Messwert-Variable*:
[MAIN.fDruck                    ] [🔍]
💡 PLC-Variable mit Messwert

Minimum*:
[0.0    ]

Maximum*:
[100.0  ]

Einheit*:
[bar    ]
💡 Anzeigeeinheit (z.B. bar, l/min, kW)

Nachkommastellen*:
[1 ▼]  (0-3)

Warngrenze (optional):
[80.0   ]
💡 Wert ab dem Warnung angezeigt wird

Kritische Grenze (optional):
[95.0   ]
💡 Wert ab dem kritischer Zustand angezeigt wird
```

**Feldtypen:**
- ✅ `plc_variable`
- ✅ `float` für Dezimalzahlen
- ✅ `string` für Einheit
- ✅ `integer` für Nachkommastellen
- ✅ `required: False` für optionale Felder

---

### **4. WEATHER PLUGIN**

```
⚙️ Plugin-Konfiguration

Standort*:
[Haltern am See                 ]
💡 Standort für Wetterdaten

Temperatur-Variable (optional):
[MAIN.fAussenTemp               ] [🔍]
💡 PLC-Variable für Temperatur

Luftfeuchte-Variable (optional):
[MAIN.fAussenFeuchte            ] [🔍]
💡 PLC-Variable für Luftfeuchtigkeit

Wind-Variable (optional):
[MAIN.fWindSpeed                ] [🔍]
💡 PLC-Variable für Windgeschwindigkeit

API-Key (optional):
[••••••••••••••••••••••         ]
💡 OpenWeatherMap API-Key für Live-Daten

Update-Intervall (Minuten)*:
[15 ▼]  (5-60)
💡 Wie oft Live-Daten aktualisiert werden
```

**Feldtypen:**
- ✅ `string` für Standort
- ✅ `plc_variable` (optional)
- ✅ `password` für API-Key (maskiert!)
- ✅ `integer` für Intervall

---

### **5. SOLARASSISTANT PLUGIN**

```
⚙️ Plugin-Konfiguration

MQTT Topic-Prefix*:
[solar_assistant                ]
💡 Basis-Topic für SolarAssistant MQTT-Daten

PV-Leistung Topic*:
[solar/pv/power                 ]
💡 MQTT-Topic für PV-Leistung

Batterie-SOC Topic (optional):
[solar/battery/soc              ]
💡 MQTT-Topic für Batterie-Ladestand

Netz-Leistung Topic (optional):
[solar/grid/power               ]
💡 MQTT-Topic für Netz-Leistung

Hausverbrauch Topic (optional):
[solar/home/power               ]
💡 MQTT-Topic für Hausverbrauch

Batterie anzeigen*:
☑ 
💡 Batterie-Informationen auf Card anzeigen

Netz anzeigen*:
☑
💡 Netz-Informationen auf Card anzeigen
```

**Feldtypen:**
- ✅ `string` für Topics
- ✅ `boolean` für Checkboxen

---

## 🔍 SYMBOL-BROWSER

**So funktioniert's:**

1. **PLC-Variable-Feld:**
   ```
   Output Variable*:
   [                               ] [🔍]
   ```

2. **Klick auf 🔍 Button**

3. **Symbol-Browser öffnet sich:**
   ```
   ┌─────────────────────────────────────────┐
   │ 🔍 Symbol-Browser           Filter: BOOL │
   ├─────────────────────────────────────────┤
   │ Suche: [ausgang___________]              │
   ├─────────────────────────────────────────┤
   │ MAIN.VBAUSGANG1              BOOL        │
   │ MAIN.VBAUSGANG2              BOOL        │
   │ MAIN.VBAUSGANG43             BOOL   ← ✓  │
   │ MAIN.VBAUSGANG62             BOOL        │
   │ GVL.bAusgangGarage           BOOL        │
   │ ...                                      │
   ├─────────────────────────────────────────┤
   │ [✓ Auswählen]  [✕ Abbrechen]            │
   └─────────────────────────────────────────┘
   ```

4. **Live-Suche:**
   - Tippe "ausgang" → Zeigt alle Ausgänge
   - Tippe "main.v" → Zeigt MAIN.V*
   - Doppelklick = Auswählen

5. **Typ-Filter:**
   - Schema definiert `plc_type: "BOOL"`
   - Browser zeigt NUR BOOL-Variablen!
   - Keine irrelevanten Variablen!

6. **Ergebnis:**
   ```
   Output Variable*:
   [MAIN.VBAUSGANG43              ] [🔍]
   ```

---

## 🎯 SCHEMA-SYSTEM

### **Wie Plugin-Schemas funktionieren:**

**1. Plugin definiert Schema:**
```python
class Light:
    SCHEMA = {
        "output": {
            "type": "plc_variable",      # Feldtyp
            "label": "Output Variable",  # Anzeige-Name
            "description": "...",         # Hilfetext
            "required": True,             # Pflichtfeld
            "plc_type": "BOOL",          # Filter für Browser
            "placeholder": "z.B. ..."    # Platzhalter
        }
    }
```

**2. Card-Manager liest Schema:**
```python
plugin = app.module_manager.get_module('light')
schema = plugin.get_schema()
```

**3. Dynamische UI-Generierung:**
```python
for field_name, field_spec in schema.items():
    if field_spec['type'] == 'plc_variable':
        # Erstelle Entry + Symbol-Browser Button
    elif field_spec['type'] == 'choice':
        # Erstelle Radio-Buttons
    elif field_spec['type'] == 'integer':
        # Erstelle Spinbox
    # ...
```

---

## 📋 VERFÜGBARE FELDTYPEN

| Typ | Widget | Optionen | Beispiel |
|-----|--------|----------|----------|
| `plc_variable` | Entry + 🔍 Button | `plc_type`, `placeholder` | PLC-Variablen |
| `string` | Entry | `placeholder`, `default` | Text-Eingabe |
| `integer` | Spinbox | `min`, `max`, `step`, `default` | Zahlen |
| `float` | Entry | `default` | Dezimalzahlen |
| `boolean` | Checkbox | `default` | Ja/Nein |
| `choice` | Radio-Buttons | `choices`, `default` | Auswahl |
| `password` | Entry (maskiert) | - | Passwörter |

---

## ✅ VORTEILE

**Für Entwickler:**
- ✅ Plugin-Schema in 1 Datei definieren
- ✅ UI generiert sich automatisch
- ✅ Keine UI-Code in Plugins!
- ✅ Einfach erweiterbar

**Für Benutzer:**
- ✅ Professionelle Eingabemasken
- ✅ Symbol-Browser für PLC-Variablen
- ✅ Validierung verhindert Fehler
- ✅ Hilfe-Texte bei jedem Feld
- ✅ Kein JSON mehr!

---

## 🧪 TESTEN

### **1. Neue Light-Card erstellen:**

```
⚙️ Card-Verwaltung → ➕ Neue Card

Name: [Licht Wohnzimmer]
Icon: ● 💡
Tab: [🏡 Erdgeschoss ▼]
Plugin-Typ: ● Light

⚙️ Plugin-Konfiguration:

Output Variable*: [           ] [🔍]
  → Klick 🔍
  → Suche "wohnzimmer"
  → Auswählen "MAIN.bLichtWohnzimmer"

Schalt-Typ: ● Toggle

[💾 Speichern]
```

### **2. Gauge-Card erstellen:**

```
Name: [Heizungsdruck]
Icon: ● 📊
Plugin-Typ: ● Gauge

⚙️ Plugin-Konfiguration:

Messwert-Variable*: [           ] [🔍]
  → Suche "druck"
  → Auswählen "MAIN.fHeizungsDruck"

Minimum: [0.0  ]
Maximum: [3.0  ]
Einheit: [bar  ]
Nachkommastellen: [1 ▼]

Warngrenze: [2.5  ]
Kritische Grenze: [2.8  ]

[💾 Speichern]
```

---

## 🎉 ERGEBNIS

**JSON-Output (automatisch generiert):**

```json
{
  "Card_ABC123": {
    "name": "Licht Wohnzimmer",
    "icon": "💡",
    "tab_id": "TabID_a1b2c3",
    "plugin_type": "light",
    "input": "",
    "output": "MAIN.bLichtWohnzimmer",
    "type": "toggle"
  },
  "Card_XYZ789": {
    "name": "Heizungsdruck",
    "icon": "📊",
    "tab_id": "TabID_a1b2c3",
    "plugin_type": "gauge",
    "variable": "MAIN.fHeizungsDruck",
    "min_value": 0.0,
    "max_value": 3.0,
    "unit": "bar",
    "decimals": 1,
    "warn_threshold": 2.5,
    "critical_threshold": 2.8
  }
}
```

**Perfekt formatiert & validiert!** ✅

---

## 🚀 UPGRADE VON v3.1 → v3.2

**Alte Cards bleiben kompatibel!**

```json
// ALT (v3.1):
{
  "output": "MAIN.VBAUSGANG43",
  "type": "pulse"
}

// Funktioniert weiterhin! ✅
```

**Neue Cards haben mehr Validierung:**
- Required-Felder müssen ausgefüllt sein
- Min/Max werden geprüft
- PLC-Typ wird validiert

---

## 📊 FEATURE-VERGLEICH

| Feature | v3.1 | v3.2 |
|---------|------|------|
| Tab-Dropdown | ✅ | ✅ |
| JSON-Edit | ✅ | ❌ |
| **Dynamische Felder** | ❌ | ✅ |
| **Symbol-Browser** | ❌ | ✅ |
| **Validierung** | ❌ | ✅ |
| **Hilfe-Texte** | ❌ | ✅ |
| **Conditional Fields** | ❌ | ✅ |
| Plugin-erweiterbar | ❌ | ✅ |

---

## 🎯 ZUSAMMENFASSUNG

**v3.2.0 bringt:**
1. ✅ **Dynamische Eingabemasken** aus Plugin-Schemas
2. ✅ **Symbol-Browser** für PLC-Variablen (mit 🔍)
3. ✅ **7 Feldtypen** (plc_variable, string, integer, float, boolean, choice, password)
4. ✅ **Typ-Filter** im Symbol-Browser (nur BOOL, nur REAL, ...)
5. ✅ **Validierung** (Required, Min/Max, Typ-Prüfung)
6. ✅ **Hilfe-Texte** bei jedem Feld
7. ✅ **Conditional Fields** (show_if)
8. ✅ **Professionelles UI** wie in kommerziellen Tools!

**Von manuell JSON zu visueller Konfiguration!** 🚀

---

**JETZT INSTALLIEREN UND TESTEN!** 💪
