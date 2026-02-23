# 🎨 Theme-Anpassung - TwinCAT Smart Home

**So passt du die Farben nach deinen Wünschen an**

---

## 📍 Wo sind die Theme-Einstellungen?

Die Themes werden in der `config.json` gespeichert:

```
C:\Users\black\Documents\TwinCAT_SmartHome\config.json
```

---

## 🎨 Verfügbare Themes

### **1. Blue Theme (Standard)**
```json
"themes": {
  "blue": {
    "primary": "#2196F3",
    "secondary": "#1976D2",
    "success": "#4CAF50",
    "danger": "#F44336",
    "warning": "#FF9800",
    "bg": "#F5F5F5",
    "card_bg": "#FFFFFF",
    "text_dark": "#212121",
    "text_light": "#757575"
  }
}
```

### **2. Dark Theme**
```json
"dark": {
  "primary": "#2196F3",
  "secondary": "#1565C0",
  "success": "#66BB6A",
  "danger": "#EF5350",
  "warning": "#FFA726",
  "bg": "#212121",
  "card_bg": "#424242",
  "text_dark": "#FFFFFF",
  "text_light": "#BDBDBD"
}
```

### **3. Green Theme**
```json
"green": {
  "primary": "#4CAF50",
  "secondary": "#388E3C",
  "success": "#8BC34A",
  "danger": "#F44336",
  "warning": "#FF9800",
  "bg": "#F1F8E9",
  "card_bg": "#FFFFFF",
  "text_dark": "#212121",
  "text_light": "#757575"
}
```

---

## ✏️ Farben anpassen

### **Schritt 1: config.json öffnen**

```batch
notepad "C:\Users\black\Documents\TwinCAT_SmartHome\config.json"
```

### **Schritt 2: Finde den "themes" Abschnitt**

```json
{
  "version": "1.0",
  "theme": "blue",
  "plc": { ... },
  "themes": {
    "blue": {
      "primary": "#2196F3",    <- Hauptfarbe (Buttons, Akzente)
      "secondary": "#1976D2",  <- Sekundärfarbe
      "success": "#4CAF50",    <- Erfolgs-Farbe (grüne Buttons)
      "danger": "#F44336",     <- Gefahr-Farbe (rote Buttons)
      "warning": "#FF9800",    <- Warn-Farbe (orange Buttons)
      "bg": "#F5F5F5",         <- Hintergrund
      "card_bg": "#FFFFFF",    <- Card-Hintergrund
      "text_dark": "#212121",  <- Dunkler Text
      "text_light": "#757575"  <- Heller Text
    }
  }
}
```

### **Schritt 3: Farben ändern**

**Beispiel: Blaues Theme in Rot ändern**

```json
"blue": {
  "primary": "#E53935",      <- Rot statt Blau
  "secondary": "#C62828",    <- Dunkelrot
  "success": "#4CAF50",      <- Bleibt grün
  "danger": "#F44336",       <- Bleibt rot
  "warning": "#FF9800",      <- Bleibt orange
  "bg": "#FFEBEE",           <- Hellroter Hintergrund
  "card_bg": "#FFFFFF",      <- Weiß bleibt
  "text_dark": "#212121",    <- Schwarz bleibt
  "text_light": "#757575"    <- Grau bleibt
}
```

### **Schritt 4: Speichern & Neustarten**

1. **Speichere** die config.json
2. **Schließe** die App
3. **Starte** die App neu
4. **Fertig!** ✅

---

## 🌈 Farb-Codes (HEX)

**Beliebte Farben:**

| Farbe | HEX Code | Beispiel |
|-------|----------|----------|
| Rot | `#F44336` | 🔴 |
| Rosa | `#E91E63` | 🌸 |
| Lila | `#9C27B0` | 🟣 |
| Blau | `#2196F3` | 🔵 |
| Türkis | `#00BCD4` | 🔷 |
| Grün | `#4CAF50` | 🟢 |
| Gelb | `#FFEB3B` | 🟡 |
| Orange | `#FF9800` | 🟠 |
| Grau | `#9E9E9E` | ⚪ |
| Schwarz | `#212121` | ⚫ |

**Farb-Picker:** https://htmlcolorcodes.com/color-picker/

---

## 💡 Eigenes Theme erstellen

### **Schritt 1: Neues Theme hinzufügen**

```json
"themes": {
  "blue": { ... },
  "dark": { ... },
  "green": { ... },
  "custom": {                 <- Neues Theme!
    "primary": "#FF1744",     <- Deine Farbe
    "secondary": "#D50000",
    "success": "#76FF03",
    "danger": "#FF6E40",
    "warning": "#FFAB00",
    "bg": "#FAFAFA",
    "card_bg": "#FFFFFF",
    "text_dark": "#212121",
    "text_light": "#757575"
  }
}
```

### **Schritt 2: Theme aktivieren**

```json
{
  "version": "1.0",
  "theme": "custom",  <- Ändere auf dein Theme-Name
  ...
}
```

### **Schritt 3: App neustarten** ✅

---

## 🎨 Theme-Vorlagen

### **Dunkel-Blau (Professional)**
```json
"professional": {
  "primary": "#1565C0",
  "secondary": "#0D47A1",
  "success": "#2E7D32",
  "danger": "#C62828",
  "warning": "#F57C00",
  "bg": "#263238",
  "card_bg": "#37474F",
  "text_dark": "#ECEFF1",
  "text_light": "#90A4AE"
}
```

### **Hell & Modern**
```json
"modern": {
  "primary": "#00ACC1",
  "secondary": "#0097A7",
  "success": "#26A69A",
  "danger": "#EF5350",
  "warning": "#FFA726",
  "bg": "#FAFAFA",
  "card_bg": "#FFFFFF",
  "text_dark": "#212121",
  "text_light": "#757575"
}
```

### **Warm & Gemütlich**
```json
"warm": {
  "primary": "#F57C00",
  "secondary": "#EF6C00",
  "success": "#7CB342",
  "danger": "#E53935",
  "warning": "#FDD835",
  "bg": "#FFF8E1",
  "card_bg": "#FFFFFF",
  "text_dark": "#3E2723",
  "text_light": "#795548"
}
```

---

## 🚀 Schnell-Anpassung

**Nur Haupt-Farbe ändern (Primary):**

1. Öffne `config.json`
2. Finde `"primary": "#2196F3"`
3. Ändere auf deine Farbe: `"primary": "#E91E63"` (Rosa)
4. Speichern & Neustarten

**Nur Hintergrund-Farbe ändern:**

1. Finde `"bg": "#F5F5F5"`
2. Ändere auf: `"bg": "#E8EAF6"` (Hell-Lila)
3. Speichern & Neustarten

---

## ⚠️ Wichtige Hinweise

### **Farb-Kontrast beachten:**
- Heller Text (`text_light`) auf dunklem Hintergrund (`card_bg`)
- Dunkler Text (`text_dark`) auf hellem Hintergrund
- Guter Kontrast = bessere Lesbarkeit!

### **Nach Änderungen:**
- **IMMER** App neu starten
- Theme-Änderung in UI aktiviert nur Reload
- Manuelle config.json Änderungen brauchen Neustart

### **Backup:**
```batch
copy "C:\Users\black\Documents\TwinCAT_SmartHome\config.json" ^
     "C:\Users\black\Documents\TwinCAT_SmartHome\config.json.backup"
```

---

## 🔧 Troubleshooting

### **Problem: Theme ändert sich nicht**

**Lösung:**
1. Prüfe ob config.json gespeichert wurde
2. Prüfe JSON-Syntax (keine fehlenden Kommas!)
3. App komplett schließen (nicht minimieren)
4. App neu starten

### **Problem: App startet nicht nach Theme-Änderung**

**Lösung:**
```batch
:: Backup wiederherstellen
copy "C:\Users\black\Documents\TwinCAT_SmartHome\config.json.backup" ^
     "C:\Users\black\Documents\TwinCAT_SmartHome\config.json"
```

### **Problem: Farben sehen komisch aus**

**Ursache:** HEX-Code falsch

**Richtig:** `#2196F3` (6 Zeichen, 0-9, A-F)  
**Falsch:** `#21G6F3` (G nicht erlaubt)

---

## 📚 Weiterführende Infos

**Color Picker Tools:**
- https://htmlcolorcodes.com/color-picker/
- https://www.google.com/search?q=color+picker

**Material Design Colors:**
- https://materialui.co/colors

**Farbschema-Generator:**
- https://coolors.co/

---

**Viel Spaß beim Anpassen! 🎨**
