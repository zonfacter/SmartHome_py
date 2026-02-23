# 🎨 STATUS-FEEDBACK v2.1.0
## Live-Updates & farbige Buttons

**Was ist neu:**
- ✅ **Buttons ändern Farbe** basierend auf Status
- ✅ **Live-Updates** vom PLC
- ✅ **Visuelles Feedback** (Grün=Ein, Grau=Aus, Rot=Fehler)

---

## 📦 INSTALLATION

### **Schritt 1: Light-Plugin v2.1 installieren**

```bash
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu

# Ersetze Light-Plugin
copy light_v2.1.0.py modules\plugins\light.py

# Optional: Temperature-Plugin
copy temperature_v2.1.0.py modules\plugins\temperature.py
```

### **Schritt 2: Update-Loop Integration**

Der Update-Loop muss die `update_card()` Methode der Plugins aufrufen.

**Datei:** `modules/core/update_loop.py`

**Füge hinzu in der Update-Methode:**

```python
def update_cards(self):
    """Aktualisiert alle Cards"""
    if not self.cards:
        return
    
    # Hole alle Cards
    all_cards = self.cards.get_all_cards()
    
    for card_id, widgets in all_cards.items():
        card_data = widgets.get('data', {})
        plugin_type = card_data.get('plugin_type')
        
        if not plugin_type:
            continue
        
        # Hole Plugin
        plugin = self.app.module_manager.get_module(plugin_type)
        
        if plugin and hasattr(plugin, 'update_card'):
            try:
                # ⭐ Rufe update_card() vom Plugin auf
                plugin.update_card(card_id, card_data)
            except Exception as e:
                pass  # Ignoriere Fehler
```

**In der Haupt-Update-Schleife:**

```python
def update_loop(self):
    """Haupt-Update-Loop"""
    while self.running:
        try:
            # ... andere Updates ...
            
            # ⭐ Card-Updates
            self.update_cards()
            
        except Exception as e:
            print(f"⚠️ Update-Fehler: {e}")
        
        time.sleep(self.interval)
```

### **Schritt 3: Card-ID übergeben**

**WICHTIG:** Cards brauchen ihre ID für Updates!

**In:** `modules/core/card_renderer.py`

**Methode:** `create_card()`

```python
def create_card(self, parent, card_id: str, card_data: dict):
    """Erstellt Card"""
    
    # ⭐ WICHTIG: Card-ID in Daten speichern!
    card_data['_card_id'] = card_id
    
    # Hole Plugin
    plugin_type = card_data.get('plugin_type', 'light')
    plugin = self.app.module_manager.get_module(plugin_type)
    
    if not plugin:
        return None
    
    # Erstelle Frame
    card_frame = tk.Frame(parent, bg=self.gui.colors['card_bg'],
                         relief=tk.RAISED, borderwidth=2)
    
    # ⭐ Plugin erstellt Inhalt (bekommt card_id via card_data)
    if hasattr(plugin, 'create_card_content'):
        plugin.create_card_content(card_frame, card_data)
    
    # Speichere Widget
    self.cards[card_id] = {
        'frame': card_frame,
        'data': card_data
    }
    
    return card_frame
```

---

## 🎯 WIE ES FUNKTIONIERT

### **Light-Plugin:**

**1. create_card_content():**
```python
def create_card_content(self, parent, card_data):
    card_id = card_data.get('_card_id')  # ← Hole ID
    
    # Erstelle Button
    button = tk.Button(...)
    
    # Speichere für Updates
    self.card_widgets[card_id] = {
        'button': button,
        'input_var': card_data.get('input'),
        ...
    }
```

**2. update_card():**
```python
def update_card(self, card_id, card_data):
    widgets = self.card_widgets[card_id]
    input_var = widgets['input_var']
    button = widgets['button']
    
    # Lese Status vom PLC
    status = self.plc.read_bool(input_var)
    
    if status:
        button.config(bg='#4CAF50')  # Grün = EIN
    else:
        button.config(bg='#757575')  # Grau = AUS
```

**3. Update-Loop ruft auf:**
```python
# Jede Sekunde:
plugin.update_card(card_id, card_data)
# → Button ändert Farbe automatisch!
```

---

## 🎨 FARB-SCHEMA

### **Light-Button:**

| Status | Farbe | Bedeutung |
|--------|-------|-----------|
| **EIN** | 🟢 Grün (#4CAF50) | Licht ist eingeschaltet |
| **AUS** | ⚫ Grau (#757575) | Licht ist ausgeschaltet |
| **Unbekannt** | ⚫ Grau (#757575) | Kein Input oder PLC nicht verbunden |
| **Fehler** | 🔴 Rot (#FF5722) | Fehler beim Lesen |

### **Temperature-Label:**

| Temperatur | Farbe | Bedeutung |
|------------|-------|-----------|
| **< 15°C** | 🔵 Blau (#2196F3) | Kalt |
| **15-25°C** | 🟢 Grün (#4CAF50) | Angenehm |
| **> 25°C** | 🔴 Rot (#FF5722) | Warm |

---

## 🧪 TESTEN

### **1. Neue Light-Card mit Input erstellen:**

```
⚙️ Card-Verwaltung → ➕ Neue Card

Name: [Licht Test]
Plugin-Typ: ● Light

⚙️ Plugin-Konfiguration:

Input Variable (Status-Feedback):  ← ⭐ WICHTIG!
[MAIN.bLichtStatus          ] [🔍]
💡 PLC-Variable für Status-Rückmeldung

Output Variable*:
[MAIN.bLichtAusgang         ] [🔍]

Schalt-Typ: ● Toggle

[💾 Speichern]
```

### **2. App starten & beobachten:**

```bash
python Haussteuerung_v3.py
```

**Erwarte:**
```
✓ Modul geladen: light v2.1.0
✓ Modul geladen: temperature v2.1.0

▶️ Starte Update-Loop...
```

### **3. Status-Änderung testen:**

**GUI zeigt:**
```
💡 Licht Test
┌─────────────────┐
│     Toggle      │  ← ⚫ Grau (AUS)
└─────────────────┘
Status: AUS
```

**Klick auf Button:**
```
💡 Licht Test
┌─────────────────┐
│     Toggle      │  ← 🟢 Grün (EIN)
└─────────────────┘
Status: EIN
```

**Button ändert Farbe LIVE!** ✅

---

## ⚠️ WICHTIG

### **Input-Variable MUSS gesetzt sein!**

Ohne `input` Variable:
```json
{
  "output": "MAIN.bLichtAusgang",
  "input": ""  ← ❌ Leer!
}
```
→ Button bleibt **grau** (kein Feedback)

Mit `input` Variable:
```json
{
  "output": "MAIN.bLichtAusgang",
  "input": "MAIN.bLichtStatus"  ← ✅ Gesetzt!
}
```
→ Button ändert **Farbe** basierend auf Status! 🎉

---

## 📊 VORHER vs. NACHHER

### **VORHER (v2.0):**
```
💡 Licht
┌─────────────────┐
│     Toggle      │  ← Immer grau
└─────────────────┘
```
❌ Keine Rückmeldung  
❌ Weiß nicht ob Licht an/aus  
❌ Muss PLC-Status separat prüfen  

### **NACHHER (v2.1):**
```
💡 Licht
┌─────────────────┐
│     Toggle      │  ← 🟢 Grün = EIN!
└─────────────────┘
Status: EIN
```
✅ Live-Feedback  
✅ Farbe zeigt Status  
✅ Status-Text optional  
✅ Update jede Sekunde  

---

## 🔧 ERWEITERT: EIGENE FARBEN

**Du kannst Farben anpassen in:**

`modules/plugins/light_v2.1.0.py`

```python
if status:
    button.config(
        bg='#4CAF50',  # ← Ändere Farbe hier!
        activebackground='#45a049'
    )
```

**Farbvorschläge:**
- 🟢 Grün: `#4CAF50` (Standard)
- 🔵 Blau: `#2196F3`
- 🟡 Gelb: `#FFC107`
- 🟠 Orange: `#FF9800`
- 🟣 Lila: `#9C27B0`

---

## 🎉 FERTIG!

**Nach Installation:**
- ✅ Buttons ändern Farbe basierend auf PLC-Status
- ✅ Live-Updates jede Sekunde
- ✅ Visuelles Feedback ohne TwinCAT HMI öffnen zu müssen
- ✅ Professional Look!

**Status-Feedback wie in kommerziellen SCADA-Systemen!** 🚀

---

## 📦 ALLE DATEIEN

1. **[light_v2.1.0.py](computer:///mnt/user-data/outputs/modules/plugins/light_v2.1.0.py)** ⭐  
   Grün/Grau/Rot Button-Farben

2. **[temperature_v2.1.0.py](computer:///mnt/user-data/outputs/modules/plugins/temperature_v2.1.0.py)** 🌡️  
   Blau/Grün/Rot Temperatur-Farben

**Teste es jetzt!** 💪
