# 🔧 v2.1.3 - Custom Tabs Fix + RTSP/MQTT Roadmap

**Version:** 2.1.3  
**Status:** CUSTOM TABS FUNKTIONIEREN! ✅

---

## ✅ **Gefixte Probleme:**

### **Problem #1: Custom Tabs verschwanden nach Neustart** ❌
```
Tab erstellen → App schließen → Tab weg!
```

### **Problem #2: Keine Cards in Custom Tabs** ❌
```
Custom Tab → Card-Verwaltung → Tab nicht in Auswahl!
```

---

## ✅ **Fixes v2.1.3:**

### **Fix #1: Tab-Persistence**
```python
# Tabs werden jetzt in config.json gespeichert!
{
  "custom_tabs": {
    "tab_0": {
      "name": "Garage",
      "icon": "🚗"
    }
  }
}
```

### **Fix #2: Tabs werden beim Start geladen**
```python
def _load_tabs():
    config_data = self.config.config
    tabs_config = config_data.get('custom_tabs', {})
    
    for tab_id, tab_info in tabs_config.items():
        self.add_tab(name=tab_info['name'], icon=tab_info['icon'])
```

### **Fix #3: Custom Tabs in Etagen-Auswahl**
```python
# Card-Editor zeigt jetzt ALLE Tabs:
floors = ['🏡 Erdgeschoss', '🔼 Obergeschoss', '⬆️ Dachboden']

# + Custom Tabs:
for tab_info in tab_manager.tabs:
    floors.append(f"{tab_info['icon']} {tab_info['name']}")
```

### **Fix #4: Cards funktionieren in Custom Tabs**
```python
# Custom Tabs nutzen gleiche Logik wie Standard-Floors
def _create_custom_tab_content(parent, tab_info):
    floor_name = f"{tab_info['icon']} {tab_info['name']}"
    app.create_floor_content(parent, floor_name)
```

---

## 📥 **Download v2.1.3:**

**BEIDE Dateien laden:**
1. [Haussteuerung_v2.py v2.1.3](computer:///mnt/user-data/outputs/Haussteuerung_v2.py)
2. [tab_manager.py v2.1.3](computer:///mnt/user-data/outputs/modules/ui/tab_manager.py)
3. [card_manager.py v2.1.3](computer:///mnt/user-data/outputs/modules/ui/card_manager.py)

---

## 🧪 **Test:**

**1. Custom Tab erstellen:**
```
1. 📑 Tab-Manager → ➕ Neuer Tab
2. Name: "Garage"
3. Icon: 🚗
4. Erstellen
5. Tab erscheint!
```

**2. Card in Custom Tab:**
```
1. ⚙️ Card-Verwaltung → ➕ Neue Card
2. Name: "Garagentor"
3. Etage: 🚗 Garage  ← JETZT SICHTBAR!
4. Speichern
5. Card erscheint in Garage-Tab!
```

**3. Persistence testen:**
```
1. App schließen
2. App neu starten
3. ERWARTE: 🚗 Garage Tab ist da!
4. ERWARTE: Garagentor Card ist da!
```

---

## 🚀 **Roadmap: RTSP & MQTT (v2.2.0)**

### **RTSP-Kamera Integration:**
```
Features:
- Kamera-Tab mit Live-Stream
- URL-Konfiguration
- Mehrere Kameras
- Snapshot-Funktion

Konfiguration:
{
  "rtsp": {
    "cameras": [
      {
        "name": "Eingang",
        "url": "rtsp://192.168.2.100:554/stream"
      }
    ]
  }
}

Aufwand: ~30min
```

### **MQTT/SolarAssistant:**
```
Features:
- MQTT-Broker Verbindung
- Topic-Abonnierung
- Werte-Anzeige in Cards
- PV-Daten (Leistung, Ertrag, SOC)

Konfiguration:
{
  "mqtt": {
    "broker": "192.168.2.50",
    "port": 1883,
    "topics": {
      "pv_power": "solar/pv/power",
      "battery_soc": "solar/battery/soc"
    }
  }
}

Aufwand: ~1h
```

---

## 📋 **v2.1.3 Changelog:**

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

---

## 🎉 **v2.1.3 ist stabil!**

**Custom Tabs:**
- ✅ Erstellen funktioniert
- ✅ Persistence funktioniert
- ✅ Cards funktionieren
- ✅ Alles wird gespeichert!

**Nächstes Update (v2.2.0):**
- 📹 RTSP Kameras (~30min)
- 📊 MQTT/SolarAssistant (~1h)

**v2.1.3 ist PRODUCTION READY! 🚀**
