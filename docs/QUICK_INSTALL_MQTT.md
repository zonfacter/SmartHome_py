# 🚀 QUICK INSTALL - MQTT MULTI-VARIABLE

**2 Dateien, 3 Minuten!**

---

## 📥 INSTALLATION

```bash
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu

# 1. Card-Manager v3.3.0
copy card_manager_v3.3.0_MQTT.py modules\ui\card_manager.py

# 2. MQTT Multi-Variable Plugin
copy mqtt_multivariable.py modules\plugins\mqtt_multivariable.py

# 3. Starten
python Haussteuerung_v3.py
```

---

## ✅ ERFOLGS-CHECK

**Erwarte:**
```
✓ Modul geladen: card_manager v3.3.0
✓ Modul geladen: mqtt_multivariable v1.0.0
```

---

## 🧪 SCHNELL-TEST

**1. Neue Card erstellen:**
```
⚙️ Card-Verwaltung → ➕ Neue Card
Plugin-Typ: ● MQTT Multi-Variable
```

**2. Variable hinzufügen:**
```
[➕ Variable hinzufügen]

MQTT Topic: [                    ] [📡] ← Klick!
```

**3. Topic-Browser öffnet sich!** ✅

```
┌─────────────────────────────────────┐
│ 📡 MQTT Topic-Browser               │
│ ✓ Verbunden: 192.168.2.244          │
├─────────────────────────────────────┤
│ solar/pv/power          = 1234.56   │
│ solar/battery/soc       = 85.0      │
│ solar/grid/power        = -500.0    │
│ ...                                 │
└─────────────────────────────────────┘
```

---

## 🎯 MINI-BEISPIEL

**PV-Monitor (4 Variablen):**

```
Card-Größe: ● Mittel
Layout: ● Vertikal

Variable #1:
├─ Topic: solar/pv/power [📡]
├─ Name: PV-Leistung
├─ Einheit: W
└─ Decimals: 1

Variable #2:
├─ Topic: solar/battery/soc [📡]
├─ Name: Batterie
├─ Einheit: %
└─ Decimals: 0

Variable #3:
├─ Topic: solar/grid/power [📡]
├─ Name: Netz
├─ Einheit: W
└─ Decimals: 1

Variable #4:
├─ Topic: solar/daily/yield [📡]
├─ Name: Tagesertrag
├─ Einheit: kWh
└─ Decimals: 2

[💾 Speichern]
```

**Ergebnis:**
```
┌────────────────────────────────┐
│ ☀️ PV-Monitor        4 Werte  │
├────────────────────────────────┤
│ PV-Leistung        1234.5 W   │
│ Batterie                85 %   │
│ Netz               -500.0 W   │
│ Tagesertrag         12.54 kWh │
└────────────────────────────────┘
```

**Live-Updates jede Sekunde!** ✅

---

## 📦 DATEIEN

1. **[card_manager_v3.3.0_MQTT.py](computer:///mnt/user-data/outputs/modules/ui/card_manager_v3.3.0_MQTT.py)** ⭐
2. **[mqtt_multivariable.py](computer:///mnt/user-data/outputs/modules/plugins/mqtt_multivariable.py)** 📡
3. **[MQTT_MULTIVARIABLE_v3.3.0.md](computer:///mnt/user-data/outputs/MQTT_MULTIVARIABLE_v3.3.0.md)** 📖

---

## 🎉 FERTIG!

**Du hast jetzt:**
- ✅ MQTT Topic-Browser 📡
- ✅ Dynamische Variablen (bis 12!)
- ✅ Auto-Resize & Skalierung
- ✅ Live-Updates

**Viel Spaß!** 🚀
