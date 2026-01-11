# 🚀 UPGRADE GUIDE v3.0 → v3.1.0
## ID-basierte Tab-Architektur

**Datum:** 2024-12-04  
**Breaking Change:** Ja (aber automatische Migration!)

---

## 📋 WAS IST NEU?

### **Tab-IDs statt Namen!**

**VORHER (v3.0):**
```python
tab_frames['🏡 Erdgeschoss'] = frame  # ❌ String-basiert
card['floor'] = 'Obergeschoss'        # ❌ Emoji-Probleme!
```

**NACHHER (v3.1.0):**
```python
tab_frames['TabID_a1b2c3'] = frame    # ✅ ID-basiert
card['tab_id'] = 'TabID_a1b2c3'       # ✅ Eindeutig!
```

### **Vorteile:**
- ✅ **Keine Emoji-Probleme** mehr! Namen ändern = kein Problem
- ✅ **Tab-Sortierung** möglich (Drag & Drop ready)
- ✅ **Zukunftssicher** - IDs ändern sich nie
- ✅ **Automatische Migration** - deine Cards bleiben erhalten!

---

## 📥 INSTALLATION

### **Schritt 1: Backup erstellen**
```bash
# Sichere aktuelle Version
cp Haussteuerung_v3.py Haussteuerung_v3.0_BACKUP.py
cp config/twincat_config.json config/twincat_config_BACKUP.json
```

### **Schritt 2: Neue Files installieren**

**A. TabManager v3.0**
```bash
# Ersetze tab_manager.py
cp tab_manager_v3.py modules/ui/tab_manager.py
```

**B. Haussteuerung v3.1.0**
```bash
# Ersetze Hauptdatei
cp Haussteuerung_v3.1.0.py Haussteuerung_v3.py
```

**C. MQTT Browser (falls noch nicht)**
```bash
# Optional: MQTT Browser Fix
cp mqtt_browser_v2.py modules/ui/mqtt_browser.py
```

### **Schritt 3: Erste Ausführung**
```bash
python Haussteuerung_v3.py
```

**Erwarte:**
```
TwinCAT Smart Home v3.1.0
Build: 2024-12-04

📑 Erstelle Standard-Tabs...
   ✓ System-Tab erstellt: 🏡 Erdgeschoss (ID: TabID_a1b2c3)
   ✓ System-Tab erstellt: 🏠 Obergeschoss (ID: TabID_d4e5f6)
   ✓ System-Tab erstellt: 🏚️ Dachboden (ID: TabID_g7h8i9)

📑 Erstelle Tabs...
  🔍 Lade 3 Tabs aus Config...
  ✓ Tab erstellt: 🏡 Erdgeschoss (ID: TabID_a1b2c3) [System]
  ✓ Tab erstellt: 🏠 Obergeschoss (ID: TabID_d4e5f6) [System]
  ✓ Tab erstellt: 🏚️ Dachboden (ID: TabID_g7h8i9) [System]

🃏 Lade Cards...
  🔄 Migriere alte Cards (floor → tab_id)...
  🔄 Migration: 3 Cards von floor → tab_id konvertiert
  ✓ Wohnzimmer Licht in 🏡 Erdgeschoss
  ✓ Licht Kai in 🏠 Obergeschoss  ← ✅ FUNKTIONIERT JETZT!
  ✓ Licht Esszimmer in 🏡 Erdgeschoss
  ✓ 3/3 Cards gerendert
```

---

## 🔄 MIGRATION DETAILS

### **Automatisch migriert:**

**Config VORHER:**
```json
{
  "custom_lights": {
    "Card_123": {
      "name": "Licht Kai",
      "floor": "Obergeschoss",           ← Alt
      "floor": "🔼 Obergeschoss",       ← Falsches Emoji!
      ...
    }
  }
}
```

**Config NACHHER:**
```json
{
  "tabs": {
    "TabID_a1b2c3": {
      "id": "TabID_a1b2c3",
      "name": "Erdgeschoss",
      "icon": "🏡",
      "order": 0,
      "is_system": true
    },
    "TabID_d4e5f6": {
      "id": "TabID_d4e5f6",
      "name": "Obergeschoss",
      "icon": "🏠",
      "order": 1,
      "is_system": true
    }
  },
  "custom_lights": {
    "Card_123": {
      "name": "Licht Kai",
      "tab_id": "TabID_d4e5f6",         ← NEU!
      ...
    }
  }
}
```

### **Was passiert:**
1. ✅ Erste Ausführung: TabManager erstellt Standard-Tabs mit IDs
2. ✅ Migration erkennt alte "floor" Einträge
3. ✅ Mapping: "Obergeschoss" → "TabID_d4e5f6"
4. ✅ Alle Cards bekommen `tab_id` statt `floor`
5. ✅ Config wird gespeichert
6. ✅ Beim nächsten Start: Alles läuft mit IDs!

---

## 🆕 NEUE FEATURES

### **1. Tab-Manager Dialog**
```
📑 Tab-Manager → 📑 Tabs verwalten

Tabs:
□ 🏡 Erdgeschoss [System]
□ 🏠 Obergeschoss [System]
□ 🏚️ Dachboden [System]
□ 🚗 Garage

[➕ Neuer Tab] [✏️ Umbenennen] [🗑️ Löschen]
```

**Funktionen:**
- ➕ **Neue Tabs** erstellen (eigene Namen & Emojis!)
- ✏️ **Umbenennen** ohne Cards zu verlieren
- 🗑️ **Löschen** mit Warnung wenn Cards vorhanden
- 🔢 **Sortierung** (kommt später: Drag & Drop)

### **2. Card-Verwaltung Update**
```
Etage-Dropdown zeigt jetzt:
□ 🏡 Erdgeschoss
□ 🏠 Obergeschoss
□ 🏚️ Dachboden
□ 🚗 Garage        ← Custom Tabs!
```

Cards können jetzt in **alle** Tabs verschoben werden!

---

## ⚠️ TROUBLESHOOTING

### **Problem: Cards verschwunden?**
```
🃏 Lade Cards...
  ⚠️  Tab nicht gefunden: ID: TabID_xyz123
```

**Lösung:**
```bash
# 1. Restore Backup
cp config/twincat_config_BACKUP.json config/twincat_config.json

# 2. Starte App neu
python Haussteuerung_v3.py

# Migration läuft automatisch!
```

### **Problem: "tab_id fehlt"**
```
⚠️  Card 'Licht Kai' hat keine tab_id!
```

**Ursache:** Migration nicht gelaufen

**Lösung:**
```python
# In config/twincat_config.json:
# Lösche "tabs" Sektion komplett
# Beim nächsten Start werden Standard-Tabs neu erstellt
```

### **Problem: Duplikat-Tabs**
```
🏡 Erdgeschoss
🏡 Erdgeschoss
```

**Lösung:**
```bash
# Lösche config/twincat_config.json ["tabs"] Sektion
# Starte App neu
```

---

## 📊 VERGLEICH

| Feature | v3.0 | v3.1.0 |
|---------|------|--------|
| Tab-Identifier | String (Emoji + Name) | ID (TabID_XXXXXX) |
| Emoji ändern | ❌ Bricht alles | ✅ Kein Problem |
| Tab umbenennen | ❌ Cards verloren | ✅ Cards bleiben |
| Sortierung | ❌ Nicht möglich | ✅ Möglich |
| Custom Tabs | ⚠️ Problematisch | ✅ Einwandfrei |
| Migration | - | ✅ Automatisch |

---

## 🎉 UPGRADE ERFOLGREICH!

Nach erfolgreichem Upgrade:

1. ✅ Alle Cards in richtigen Tabs
2. ✅ Keine Emoji-Fehler mehr
3. ✅ Tab-Manager funktioniert
4. ✅ Config zeigt "tabs" Sektion
5. ✅ Cards haben "tab_id" statt "floor"

**Enjoy v3.1.0!** 🚀
