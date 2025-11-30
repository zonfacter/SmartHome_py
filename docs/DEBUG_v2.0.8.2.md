# 🔍 v2.0.8.2 - Debug-Version für PLC-Schreibtest

**Version:** 2.0.8.2  
**Status:** DEBUG-AUSGABEN AKTIVIERT ✅

---

## 🎯 **Was funktioniert schon:**

```
✅ PLC verbunden: 192.168.2.162.1.1
✅ Plugins haben PLC-Referenz
✅ Button-Click wird erkannt
✅ toggle_bool() wird aufgerufen
✅ Gibt "True" zurück
```

## ❓ **Aber warum schaltet es nicht?**

Das finden wir jetzt heraus!

---

## 📥 **Download Debug-Version:**

[plc_communication.py v2.0.8.2](computer:///mnt/user-data/outputs/modules/core/plc_communication.py) ⭐ **DEBUG!**

---

## 🧪 **Nach Update erwarten:**

**Beim Button-Klick:**
```
🔘 Button geklickt!
  Output: LIGHT.RM_LIGHT_EG_01
  PLC vorhanden: True
  PLC verbunden: True
  Button-Typ: toggle
  
  📖 Lese aktuellen Wert: LIGHT.RM_LIGHT_EG_01     <- NEU!
  📝 Schreibe neuen Wert: LIGHT.RM_LIGHT_EG_01 = True (war: False)  <- NEU!
  🔧 PLC.write_by_name(LIGHT.RM_LIGHT_EG_01, True, 33)  <- NEU!
  ✅ Write erfolgreich!                             <- NEU!
  
  ✓ Toggle: LIGHT.RM_LIGHT_EG_01 -> True
```

**ODER bei Fehler:**
```
  ❌ Write fehlgeschlagen: Nicht verbunden!
  
ODER

  ❌ Schreibfehler LIGHT.RM_LIGHT_EG_01: [Fehler-Text]
```

---

## 🔧 **Mögliche Fehler:**

1. **Variable existiert nicht** → `ADS Error: Symbol not found`
2. **Falsche Schreibrechte** → `ADS Error: No write access`
3. **PLC im CONFIG-Mode** → `ADS Error: Invalid device state`
4. **Variable ist Read-Only** → `ADS Error: Access denied`

---

## 📋 **Was jetzt testen:**

1. **Lade Debug-Version**
2. **Starte App neu**
3. **Klicke Button**
4. **Kopiere Console-Output hierher**

Dann sehen wir GENAU wo das Problem ist!

---

**Wir sind kurz vorm Ziel! 🎯**
