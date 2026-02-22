# 🚀 QUICK INSTALL - v3.2.0

**Dynamische Eingabemasken + Symbol-Browser**

---

## 📥 INSTALLATION (5 MINUTEN)

### **Schritt 1: Dateien kopieren**

```bash
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu

# Card-Manager v3.2.0
copy card_manager_v3.2.0.py modules\ui\card_manager.py

# Plugins mit Schemas (alle 5!)
copy light_v2.py modules\plugins\light.py
copy temperature_v2.py modules\plugins\temperature.py
copy gauge_v2.py modules\plugins\gauge.py
copy weather_v2.py modules\plugins\weather.py
copy solarassistant_v2.py modules\plugins\solarassistant.py
```

### **Schritt 2: App starten**

```bash
python Haussteuerung_v3.py
```

---

## ✅ ERFOLGS-CHECK

**Erwarte:**
```
✓ Modul geladen: card_manager v3.2.0
✓ Modul geladen: light v2.0.0
✓ Modul geladen: temperature v2.0.0
✓ Modul geladen: gauge v2.0.0
✓ Modul geladen: weather v2.0.0
✓ Modul geladen: solarassistant v2.0.0
```

---

## 🧪 SCHNELL-TEST

1. **Öffne:** ⚙️ Card-Verwaltung
2. **Klick:** ➕ Neue Card
3. **Wähle:** Plugin-Typ: ● Light
4. **Schau:**
   ```
   ⚙️ Plugin-Konfiguration
   
   Output Variable*:
   [                        ] [🔍]  ← Symbol-Browser!
   
   Schalt-Typ:
   ○ Toggle  ○ Pulse
   ```

5. **Klick:** 🔍 Button
6. **Symbol-Browser öffnet sich!** ✅

---

## 🎯 WAS IST NEU?

```
VORHER (v3.1):
Plugin-Felder: [JSON Text-Box]
❌ Manuell JSON schreiben

NACHHER (v3.2):
⚙️ Plugin-Konfiguration:
Input Variable: [         ] [🔍]
Output Variable: [        ] [🔍]
Schalt-Typ: ○ Toggle ○ Pulse
Impulsdauer: [200 ▼]
✅ Dynamische Felder + Symbol-Browser!
```

---

## 📦 ALLE DATEIEN

**Hauptkomponenten:**
1. ✅ [card_manager_v3.2.0.py](computer:///mnt/user-data/outputs/modules/ui/card_manager_v3.2.0.py)
2. ✅ [light_v2.py](computer:///mnt/user-data/outputs/modules/plugins/light_v2.py)
3. ✅ [temperature_v2.py](computer:///mnt/user-data/outputs/modules/plugins/temperature_v2.py)
4. ✅ [gauge_v2.py](computer:///mnt/user-data/outputs/modules/plugins/gauge_v2.py)
5. ✅ [weather_v2.py](computer:///mnt/user-data/outputs/modules/plugins/weather_v2.py)
6. ✅ [solarassistant_v2.py](computer:///mnt/user-data/outputs/modules/plugins/solarassistant_v2.py)

**Dokumentation:**
- 📖 [DYNAMIC_FORMS_v3.2.0.md](computer:///mnt/user-data/outputs/DYNAMIC_FORMS_v3.2.0.md) - Vollständige Doku

---

## 💡 BEISPIEL: NEUE LIGHT-CARD

```
⚙️ Card-Verwaltung → ➕ Neue Card

Standard-Felder:
- Name: [Licht Garage]
- Icon: ● 💡
- Tab: [🏡 Erdgeschoss ▼]
- Plugin-Typ: ● Light

⚙️ Plugin-Konfiguration (automatisch generiert!):

Output Variable*:
[                               ] [🔍] ← Klick!
  → Symbol-Browser öffnet sich
  → Suche: "garage"
  → Wähle: MAIN.bLichtGarage
  → Fertig! Variable eingetragen!

Schalt-Typ*:
● Toggle  ○ Pulse

[💾 Speichern]
```

**Ergebnis:**
```json
{
  "name": "Licht Garage",
  "icon": "💡",
  "tab_id": "TabID_xyz",
  "plugin_type": "light",
  "output": "MAIN.bLichtGarage",
  "type": "toggle"
}
```

**App-Neustart → Card erscheint! ✅**

---

## 🎉 FERTIG!

**Jetzt hast du:**
- ✅ Dynamische Eingabemasken
- ✅ Symbol-Browser mit 🔍
- ✅ Validierung & Hilfe-Texte
- ✅ Professionelle Card-Verwaltung

**Viel Spaß mit v3.2.0!** 🚀
