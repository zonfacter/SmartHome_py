# 🔧 v2.0.7.2 - TwinCAT 2 Port Fix!

**Datum:** 2025-11-30  
**Version:** 2.0.7.2  
**Status:** TC2 PORT KORRIGIERT ✅

---

## ⚠️ **WICHTIGER PORT-FIX**

**Problem:**
```
PLC-Config: 192.168.2.162.1.1:851  <- FALSCH! (TC3 Port)
```

**Du nutzt TwinCAT 2!**
- **TC2:** Port **801** (PORT_TC2PLC1)
- **TC3:** Port **851** (PORT_TC3PLC1)

**Fix:**
```python
# ALT (FALSCH):
port = pyads.PORT_TC3PLC1  # 851

# NEU (RICHTIG):
port = pyads.PORT_TC2PLC1  # 801
```

---

## 📥 **Download v2.0.7.2:**

**BEIDE Dateien laden:**

1. [Haussteuerung_v2.py v2.0.7.2](computer:///mnt/user-data/outputs/Haussteuerung_v2.py) ⭐ **TC2 PORT!**
2. [config_manager.py v2.0.7.2](computer:///mnt/user-data/outputs/modules/core/config_manager.py) ⭐ **DEFAULT CONFIG!**

---

## ✅ **Nach Update erwarten:**

```
⚙️  Initialisiere Module...
  ℹ️  Nutze Default PLC-Config (TC2)
  ℹ️  PLC-Config: 192.168.2.162.1.1:801 (TC2)  <- RICHTIG! ✅
  ✓ PLC verbunden: 192.168.2.162.1.1           <- SOLLTE KLAPPEN!
  ✓ PLC-Referenz an light übergeben
```

---

## 🔧 **Manuelle Konfiguration (Optional):**

Falls du den Port manuell setzen willst, erstelle/editiere:

**`C:\Users\[USER]\Documents\TwinCAT_SmartHome\twincat_config.json`:**
```json
{
  "version": "1.0",
  "theme": "blue",
  "plc": {
    "ams_net_id": "192.168.2.162.1.1",
    "port": 801
  },
  "custom_lights": {}
}
```

**Port-Tabelle:**
- **801** = TwinCAT 2 PLC1 (PORT_TC2PLC1) ✅ **DU!**
- **811** = TwinCAT 2 PLC2 (PORT_TC2PLC2)
- **821** = TwinCAT 2 PLC3 (PORT_TC2PLC3)
- **831** = TwinCAT 2 PLC4 (PORT_TC2PLC4)
- **851** = TwinCAT 3 PLC1 (PORT_TC3PLC1)

---

## 🎯 **Troubleshooting:**

**Falls PLC immer noch nicht verbindet:**

1. **TwinCAT 2 läuft?**
   - System Tray Icon prüfen
   - Run-Mode?

2. **Firewall?**
   - Windows Firewall → ADS Port 48898 erlauben
   - Antivirus → Python erlauben

3. **Route angelegt?**
   - TwinCAT System Manager
   - Router → Add Route
   - 192.168.2.162.1.1

4. **Test mit TcAdsMonitor:**
   - TwinCAT → ADS Monitor
   - Connect zu 192.168.2.162.1.1:801
   - Variablen sichtbar?

---

## 🎉 **v2.0.7.2 ist bereit!**

**Jetzt mit korrektem TC2 Port 801!** ✅

**Viel Erfolg! 🚀**
