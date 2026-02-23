# 🔧 QUICK FIX - PLC-API Fehler

**Fehler:**
```
⚠️ Fehler beim Lesen von .BAUSGANG6: 'PLCCommunication' object has no attribute 'read_bool'
```

**Ursache:** Light/Temperature-Plugins nutzen falsche API!

---

## 📥 LÖSUNG (2 DATEIEN)

```bash
cd D:\Beckhoff_1\python\TwinCAT_Smarthome_Visu

# Light-Plugin FINAL
copy light_v2.1.0_FINAL.py modules\plugins\light.py

# Temperature-Plugin FINAL
copy temperature_v2.1.0_FINAL.py modules\plugins\temperature.py

# Starten
python Haussteuerung_v3.py
```

---

## ✅ WAS WURDE GEFIXT

**VORHER (Falsch):**
```python
status = self.plc.read_bool(input_var)  # ❌
```

**NACHHER (Richtig):**
```python
import pyads
status = self.plc.read_by_name(input_var, pyads.PLCTYPE_BOOL)  # ✅
```

---

## 📦 DATEIEN

1. light_v2.1.0_FINAL.py
2. temperature_v2.1.0_FINAL.py
