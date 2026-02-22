# 🔧 v2.1.1 - INPUT/OUTPUT Fix + Pulse-Erklärung

**Version:** 2.1.1  
**Status:** PULSE-LOGIK GEFIXT ✅

---

## 🎯 **Das Problem:**

**Dein Use-Case:**
```
Button → Impuls (200ms TRUE) → Zurück zu FALSE
Hardware → Schaltet wirklich → Rückmeldung über anderen Eingang
```

**Was falsch war:**
- Status-Anzeige las OUTPUT (den Impuls)
- Nicht INPUT (die echte Hardware-Rückmeldung)
- Deshalb musstest du 2x drücken!

---

## ✅ **Die Lösung:**

### **INPUT vs OUTPUT:**

```
OUTPUT (Schreiben):
- Variable die DU schreibst
- Für Befehle an Hardware
- Impuls-Ausgang
- Beispiel: MAIN.VBAUSGANG1

INPUT (Lesen):
- Variable die DU liest  
- Von Hardware zurück
- Echte Rückmeldung
- Beispiel: MAIN.VBEINGANG1
```

### **Pulse vs Toggle:**

**PULSE (Taster):**
```
Button → TRUE → 200ms → FALSE
Wie: Taster drücken
Für: Motoren, Rollladen, Impulse
```

**TOGGLE (Schalter):**
```
Button → Liest → Invertiert → Schreibt
Wie: Schalter umlegen
Für: Dauerhafte Schalter
```

---

## 📥 **Download v2.1.1:**

[update_loop.py v2.1.1](computer:///mnt/user-data/outputs/modules/core/update_loop.py)

---

## ⚙️ **Konfiguration anpassen:**

### **Card-Editor:**
```
⚙️ Card-Verwaltung → Card bearbeiten
```

### **Richtig einstellen:**
```
Typ: PULSE (nicht Toggle!)
Impuls-Dauer: 200ms
INPUT Variable: Rückmeldung (MAIN.VBEINGANG1)
OUTPUT Variable: Schalt-Ausgang (MAIN.VBAUSGANG1)
```

---

## 🎯 **Jetzt funktioniert es:**

**Ablauf:**
1. Klick Button
2. Schreibt TRUE auf OUTPUT
3. Wartet 200ms
4. Schreibt FALSE auf OUTPUT
5. Status liest INPUT (echte Hardware!)
6. Zeigt echte Rückmeldung

---

**Jetzt sollte 1x Klick reichen! 🎯**
