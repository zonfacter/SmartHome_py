# 📡 MQTT MULTI-VARIABLE SYSTEM
## Dynamische MQTT-Cards mit bis zu 12 Variablen

**Version:** v3.3.0  
**Features:** Topic-Browser, Dynamische Felder, Auto-Resize, Skalierung

---

## ✨ WAS IST NEU?

### **1. MQTT Topic-Browser 📡**
```
Wie Symbol-Browser, aber für MQTT Topics!
- Live-Liste aller empfangenen Topics
- Filter-Funktion
- Aktuelle Werte sichtbar
- Auto-Refresh alle 2 Sekunden
```

### **2. Dynamische Variablen (bis zu 12!)**
```
➕ Variable hinzufügen
🗑️ Variable löschen
📡 Topic-Browser pro Variable
Jede Variable hat: Topic, Name, Einheit, Nachkommastellen
```

### **3. Auto-Resize & Skalierung**
```
Layout:
- Vertical (untereinander)
- Grid (2 Spalten)
- Compact (3 Spalten)

Scale:
- Small (kompakt)
- Medium (standard)
- Large (übersichtlich)
```

---

## 📥 INSTALLATION

```bash
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu

# Card-Manager v3.3.0 (mit MQTT Support)
copy card_manager_v3.3.0_MQTT.py modules\ui\card_manager.py

# MQTT Multi-Variable Plugin
copy mqtt_multivariable.py modules\plugins\mqtt_multivariable.py

# Starten
python Haussteuerung_v3.py
```

---

## 🧪 BEISPIEL: PV-MONITORING CARD

### **Schritt 1: Card erstellen**

```
⚙️ Card-Verwaltung → ➕ Neue Card

Name: [PV-Anlage Monitor]
Icon: ☀️
Tab: [🏡 Erdgeschoss ▼]
Plugin-Typ: ● MQTT Multi-Variable

⚙️ Plugin-Konfiguration:

Card-Größe:
○ Klein ● Mittel ○ Groß

Layout:
● Vertikal ○ Grid ○ Kompakt

📊 MQTT Variablen (max 12)                    0/12

[➕ Variable hinzufügen]
```

### **Schritt 2: Variablen hinzufügen**

**Klick:** ➕ Variable hinzufügen

```
┌────────────────────────────────────────┐
│ Variable #1                         🗑️ │
├────────────────────────────────────────┤
│ MQTT Topic:                            │
│ [                              ] [📡]  │ ← Klick!
│                                        │
│ Anzeige-Name:                          │
│ [PV-Leistung                     ]     │
│                                        │
│ Einheit:                               │
│ [W                               ]     │
│                                        │
│ Nachkommastellen:                      │
│ [1 ▼]                                  │
└────────────────────────────────────────┘
```

**Klick 📡 → Topic-Browser öffnet sich:**

```
┌─────────────────────────────────────────────┐
│ 📡 MQTT Topic-Browser                       │
│ ✓ Verbunden: 192.168.2.244             │
├─────────────────────────────────────────────┤
│ Filter: [solar___________]                  │
├─────────────────────────────────────────────┤
│ solar/pv/power              = 1234.56       │ ← ✓
│ solar/battery/soc           = 85.0          │
│ solar/grid/power            = -500.0        │
│ solar/daily/yield           = 12.5          │
│ ...                                         │
├─────────────────────────────────────────────┤
│ [✓ Auswählen] [🔄 Aktualisieren] [✕]       │
└─────────────────────────────────────────────┘
```

**Wähle:** `solar/pv/power`

**Ergebnis:**
```
MQTT Topic: [solar/pv/power              ] [📡]
Anzeige-Name: [PV-Leistung                     ]
Einheit: [W                               ]
Nachkommastellen: [1 ▼]
```

### **Schritt 3: Weitere Variablen**

**Füge hinzu:**

```
Variable #1:
├─ Topic: solar/pv/power
├─ Name: PV-Leistung
├─ Einheit: W
└─ Decimals: 1

Variable #2:
├─ Topic: solar/battery/soc
├─ Name: Batterie
├─ Einheit: %
└─ Decimals: 0

Variable #3:
├─ Topic: solar/grid/power
├─ Name: Netz
├─ Einheit: W
└─ Decimals: 1

Variable #4:
├─ Topic: solar/daily/yield
├─ Name: Tagesertrag
├─ Einheit: kWh
└─ Decimals: 2
```

**Counter zeigt:** `4/12`

### **Schritt 4: Speichern**

**Klick:** 💾 Speichern

**JSON-Ausgabe:**
```json
{
  "name": "PV-Anlage Monitor",
  "icon": "☀️",
  "tab_id": "TabID_xyz",
  "plugin_type": "mqtt_multivariable",
  "scale": "medium",
  "layout": "vertical",
  "variables": [
    {
      "topic": "solar/pv/power",
      "label": "PV-Leistung",
      "unit": "W",
      "decimals": 1
    },
    {
      "topic": "solar/battery/soc",
      "label": "Batterie",
      "unit": "%",
      "decimals": 0
    },
    {
      "topic": "solar/grid/power",
      "label": "Netz",
      "unit": "W",
      "decimals": 1
    },
    {
      "topic": "solar/daily/yield",
      "label": "Tagesertrag",
      "unit": "kWh",
      "decimals": 2
    }
  ]
}
```

---

## 🎨 CARD-DARSTELLUNG

### **Layout: Vertical (Medium)**

```
┌────────────────────────────────────┐
│ ☀️ PV-Anlage Monitor      4 Werte │
├────────────────────────────────────┤
│ ┌────────────────────────────────┐ │
│ │ PV-Leistung          1234.5 W │ │
│ └────────────────────────────────┘ │
│ ┌────────────────────────────────┐ │
│ │ Batterie                  85 % │ │
│ └────────────────────────────────┘ │
│ ┌────────────────────────────────┐ │
│ │ Netz                  -500.0 W │ │
│ └────────────────────────────────┘ │
│ ┌────────────────────────────────┐ │
│ │ Tagesertrag            12.54 kWh│ │
│ └────────────────────────────────┘ │
└────────────────────────────────────┘
```

### **Layout: Grid (2 Spalten)**

```
┌────────────────────────────────────┐
│ ☀️ PV-Anlage Monitor      4 Werte │
├────────────────────────────────────┤
│ ┌────────────┐ ┌────────────────┐ │
│ │PV-Leist.   │ │Batterie     85%│ │
│ │  1234.5 W  │ └────────────────┘ │
│ └────────────┘                     │
│ ┌────────────┐ ┌────────────────┐ │
│ │Netz        │ │Tagesertrag     │ │
│ │ -500.0 W   │ │  12.54 kWh     │ │
│ └────────────┘ └────────────────┘ │
└────────────────────────────────────┘
```

### **Layout: Compact (3 Spalten)**

```
┌────────────────────────────────────┐
│ ☀️ PV-Anlage       4 Werte        │
├────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐        │
│ │PV    │ │Batt. │ │Netz  │        │
│ │1234W │ │ 85% │ │-500W │        │
│ └──────┘ └──────┘ └──────┘        │
│ ┌──────┐                           │
│ │Ertrag│                           │
│ │12.5kW│                           │
│ └──────┘                           │
└────────────────────────────────────┘
```

---

## 📊 LIVE-UPDATES

**Update-Loop aktualisiert jede Sekunde:**

```python
# MQTT Integration liefert Werte
mqtt.get_value('solar/pv/power') → 1234.56

# Plugin updated Card
plugin.update_card(card_id, card_data)

# Widget zeigt neuen Wert
"PV-Leistung          1234.5 W"
```

**Farben:**
- 🟢 Grün = Wert empfangen
- 🟠 Orange = Fehler bei Formatierung
- ⚫ Grau = Kein Wert

---

## 🎯 ANWENDUNGSFÄLLE

### **1. PV-Monitoring (4-8 Variablen)**
```
- PV-Leistung
- Batterie SOC
- Netz-Leistung
- Tagesertrag
- Hausverbrauch
- Batterie Ladeleistung
- Grid Bezug
- Grid Einspeisung
```

### **2. Wetterstation (6 Variablen)**
```
- Temperatur
- Luftfeuchtigkeit
- Luftdruck
- Windgeschwindigkeit
- Windrichtung
- Niederschlag
```

### **3. Smart Home Status (12 Variablen)**
```
- Temperatur Wohnzimmer
- Temperatur Schlafzimmer
- Temperatur Küche
- Temperatur Bad
- Luftfeuchtigkeit Wohnzimmer
- Luftfeuchtigkeit Schlafzimmer
- CO2 Wohnzimmer
- CO2 Schlafzimmer
- Stromverbrauch
- Wasserverbrauch
- Gasverbrauch
- Heizung Status
```

---

## ⚙️ ERWEITERTE KONFIGURATION

### **Scale-Vergleich:**

| Scale | Header | Label | Value | Für |
|-------|--------|-------|-------|-----|
| Small | 10pt | 8pt | 10pt | Viele Cards |
| Medium | 14pt | 10pt | 12pt | Standard |
| Large | 18pt | 12pt | 16pt | TV-Display |

### **Layout-Vergleich:**

| Layout | Spalten | Passt für |
|--------|---------|-----------|
| Vertical | 1 | 1-6 Variablen |
| Grid | 2 | 4-8 Variablen |
| Compact | 3 | 6-12 Variablen |

---

## 🔧 TROUBLESHOOTING

### **Problem 1: Topic-Browser leer**

```
📡 MQTT Topic-Browser
ℹ️ Keine Topics empfangen
💡 Tipp: Warte bis MQTT Daten empfängt
```

**Lösung:**
1. Prüfe MQTT-Verbindung (Status-Bar)
2. Warte 5-10 Sekunden
3. Klick 🔄 Aktualisieren
4. Prüfe MQTT-Broker sendet Daten

### **Problem 2: Werte bleiben "--"**

```
PV-Leistung                --
```

**Lösung:**
1. Topic korrekt eingegeben?
2. MQTT empfängt Daten? (Topic-Browser prüfen)
3. Console für Fehler prüfen

### **Problem 3: "Maximal 12 Variablen"**

**Lösung:**
- Erstelle zweite Card für mehr Variablen
- Oder nutze Filter (nur wichtigste Werte)

---

## 📦 ALLE DATEIEN

1. **[card_manager_v3.3.0_MQTT.py](computer:///mnt/user-data/outputs/modules/ui/card_manager_v3.3.0_MQTT.py)** ⭐
   - MQTT Topic-Browser
   - Dynamische Variablen-Liste
   - Symbol-Browser

2. **[mqtt_multivariable.py](computer:///mnt/user-data/outputs/modules/plugins/mqtt_multivariable.py)** 📡
   - Multi-Variable Plugin
   - 3 Layouts
   - 3 Scales
   - Auto-Resize

---

## 🎉 ZUSAMMENFASSUNG

**Was du jetzt hast:**

1. ✅ **MQTT Topic-Browser** 📡
   - Live-Liste aller Topics
   - Mit aktuellen Werten
   - Filter & Auto-Refresh

2. ✅ **Dynamische Variablen**
   - Bis zu 12 pro Card
   - ➕ Hinzufügen
   - 🗑️ Löschen
   - 📡 Topic-Browser pro Variable

3. ✅ **Flexible Darstellung**
   - 3 Layouts (Vertical/Grid/Compact)
   - 3 Scales (Small/Medium/Large)
   - Auto-Resize

4. ✅ **Live-Updates**
   - Update jede Sekunde
   - Farb-Feedback
   - Einheiten & Nachkommastellen

**Von statisch zu dynamisch!** 🚀

---

**INSTALLIERE JETZT UND ERSTELLE DEINE ERSTE MULTI-VARIABLE CARD!** 💪
