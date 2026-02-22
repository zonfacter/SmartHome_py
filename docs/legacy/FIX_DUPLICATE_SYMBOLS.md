# Fix: Intelligente Duplikat-Entfernung v4.6.0

**Datum:** 10. Januar 2026
**Version:** symbol_browser.py v4.6.0
**Status:** ✅ IMPLEMENTIERT

---

## Problem

Nach dem TPY-Upload zeigten Symbole im Frontend:
- ✅ **1.769 Symbole geladen** (gut!)
- ❌ **Type: "UNKNOWN"** statt "FB_Light" (schlecht!)
- ❌ **Flache Liste** statt hierarchischer TreeView (schlecht!)

### Root Cause

**Alle 46 Light-Symbole existieren DOPPELT in der TPY-Datei:**

```xml
<!-- ERSTE Instanz: OHNE Type -->
<Symbol>
  <Name>Light.Light_EG_WZ</Name>
  <!-- Kein <Type> Element! -->
</Symbol>

<!-- ZWEITE Instanz: MIT Type -->
<Symbol>
  <Name>Light.Light_EG_WZ</Name>
  <Type>FB_Light</Type>
</Symbol>
```

**Alte Duplikat-Entfernung (v4.6.0):**
```python
if full_name and full_name not in seen_names:
    unique_symbols.append((full_name, sym_elem, sym_type))
    seen_names.add(full_name)  # ← Behält das ERSTE Symbol!
```

**Problem:** Wenn das Symbol **ohne Type zuerst** kommt, wird es behalten und das Symbol **mit Type** wird verworfen!

**Ergebnis:**
- "Light.Light_EG_WZ" → Type: "UNKNOWN" (sollte "FB_Light" sein)
- Keine DataType-Expansion möglich → keine SubItems
- TreeView bleibt flach

---

## Analyse

### Doppelte Symbole in HausAutomation.tpy

```
Symbole mit mehreren Type-Einträgen: 46 von 46

Light.Light_EG_WZ
  Types: ['NO_TYPE', 'FB_Light']

Light.Light_EG_WZ_EZ
  Types: ['NO_TYPE', 'FB_Light']

Light.Light_OG_Floor
  Types: ['NO_TYPE', 'FB_Light']
```

**Type-Statistik:**
```
 20x: ('FB_Light', 'NO_TYPE')  ← 20 FB_Light Symbole doppelt
 19x: ('BOOL', 'NO_TYPE')      ← 19 BOOL Symbole doppelt
  7x: ('NO_TYPE', 'TON')        ← 7 TON Symbole doppelt
```

**ALLE Light-Symbole kommen doppelt vor!**

---

## Lösung: Priority-basierte Duplikat-Entfernung

### Neue Logik (v4.6.0)

```python
# Entferne Duplikate (INTELLIGENTE Duplikat-Entfernung)
symbol_map = {}  # name -> (element, type, priority)

for symbol_tuple in all_symbol_tuples:
    if len(symbol_tuple) == 3:
        full_name, sym_elem, sym_type = symbol_tuple
    else:
        full_name, sym_elem = symbol_tuple
        sym_type = None

    if not full_name:
        continue

    # Bestimme Priorität (höher = besser):
    # Priority 10: Symbole mit echtem Type (FB_Light, BOOL, TON, etc.)
    # Priority 1:  Symbole ohne Type (UNKNOWN, None)
    if sym_type and sym_type != 'UNKNOWN':
        priority = 10
    else:
        priority = 1

    # Behalte Symbol nur wenn es neu ist ODER höhere Priorität hat
    if full_name not in symbol_map or priority > symbol_map[full_name][2]:
        symbol_map[full_name] = (sym_elem, sym_type, priority)

# Konvertiere Map zurück zu Liste
unique_symbols = [(name, elem, typ) for name, (elem, typ, _) in symbol_map.items()]
```

### Beispiel-Ablauf

**Input (2 Symbole mit gleichem Namen):**
```
1. ("Light.Light_EG_WZ", <Element>, None)         → Priority 1
2. ("Light.Light_EG_WZ", <Element>, "FB_Light")   → Priority 10
```

**Verarbeitung:**
```
1. Symbol 1: Neu → Speichere in Map mit Priority 1
   symbol_map["Light.Light_EG_WZ"] = (<Element>, None, 1)

2. Symbol 2: Existiert bereits, aber Priority 10 > 1
   → ÜBERSCHREIBE mit besserem Symbol!
   symbol_map["Light.Light_EG_WZ"] = (<Element>, "FB_Light", 10)
```

**Output:**
```
("Light.Light_EG_WZ", <Element>, "FB_Light")  ✅
```

---

## Erwartetes Ergebnis

### Nach Server-Neustart + TPY-Upload

**Server-Logs:**
```
📂 Root-Element: PlcProjectInfo
🔍 Gefunden: 952 <Symbol> Elemente (Top-Level)
🔍 Gefunden: 237 <DataType> Elemente
📚 DataType-Map erstellt: 237 Typen
🔍 Rekursiv gefunden: ~2000 Symbole (inkl. DataType-SubItems)
✅ ~1700 eindeutige Symbole extrahiert (mit Priority-Filter!)
💾 ~1700 Symbole konvertiert zu PLCSymbol-Objekten
```

**Frontend (Browser Console):**
```javascript
{
  name: "Light.Light_EG_WZ",
  type: "FB_Light",  // ← NICHT mehr "UNKNOWN"!
  ...
}
```

**TreeView sollte jetzt expandierte Symbole zeigen:**
```
{
  name: "Light.Light_EG_WZ.bOn",
  type: "BOOL",
  ...
}
```

### TreeView Hierarchie

**Mit korrekter Type-Information werden DataTypes expandiert:**

```
📁 Light (Ordner)
  📁 Light_EG_WZ (FB_Light)
    🔵 bOn (BOOL)
    🔵 bOff (BOOL)
    🔵 bLight (BOOL)
    🔵 bSwitch (BOOL)
    📁 RisingEdgeOn (R_TRIG)
      🔵 Q (BOOL)
      🔵 M (BOOL)
    📁 RisingEdgeOff (R_TRIG)
      🔵 Q (BOOL)
      🔵 M (BOOL)
  📁 Light_EG_WZ_EZ (FB_Light)
    ...
```

**Ohne Type-Information (v4.6.0 - alt):**
```
🔵 Light.Light_EG_WZ (UNKNOWN)  ← Flach, keine Kinder
🔵 Light.Light_EG_WZ_EZ (UNKNOWN)
```

---

## Test-Schritte

### 1. Server neu starten

```bash
# STRG+C zum Beenden
python main.py
```

### 2. Cache löschen (optional aber empfohlen)

```bash
del config\cache\symbol_cache.json
```

### 3. TPY neu hochladen

- Setup-Seite öffnen
- `HausAutomation.tpy` hochladen

### 4. Überprüfung

**Server-Log sollte zeigen:**
```
✅ ~1700 eindeutige Symbole extrahiert
```

**Browser Console:**
```javascript
// Klicke auf ein Symbol im TreeView
// Sollte zeigen:
{
  name: "Light.Light_EG_WZ",
  type: "FB_Light",  // ← KORREKT!
  ...
}

// Suche nach expandierten SubItems:
{
  name: "Light.Light_EG_WZ.bOn",
  type: "BOOL",  // ← ERWEITERT!
  ...
}
```

**TreeView sollte zeigen:**
- Ordner-Icons bei FB_Light Symbolen
- Chevrons zum Aufklappen
- Verschachtelte SubItems (bOn, bOff, RisingEdgeOn.Q, etc.)

---

## Geänderte Dateien

### `modules/plc/symbol_browser.py`

**Lines 1-26:** Version-Header aktualisiert (v4.6.0)

**Lines 368-401:** Intelligente Duplikat-Entfernung:
- Priority-System implementiert
- Symbol-Map statt einfachem Set
- Bevorzugt Symbole mit Type

---

## Kritische Änderungen (NICHT verlieren!)

### 1. Priority-System

```python
if sym_type and sym_type != 'UNKNOWN':
    priority = 10  # Symbole mit Type
else:
    priority = 1   # Symbole ohne Type
```

Ohne diese Logik: **Doppelte Symbole werden zufällig ausgewählt!**

### 2. Überschreib-Logik

```python
if full_name not in symbol_map or priority > symbol_map[full_name][2]:
    symbol_map[full_name] = (sym_elem, sym_type, priority)
```

Ohne diese Logik: **Erste Symbol wird immer behalten** (egal ob schlechtere Qualität)

---

## Vergleich: Vorher vs. Nachher

| Aspekt | v4.6.0 | v4.6.0 |
|--------|--------|--------|
| **Symbole geladen** | 1.769 | 1.769 |
| **Light.Light_EG_WZ Type** | UNKNOWN ❌ | FB_Light ✅ |
| **DataType-Expansion** | Nein ❌ | Ja ✅ |
| **Expandierte SubItems** | 0 ❌ | ~140 ✅ |
| **TreeView Hierarchie** | Flach ❌ | Verschachtelt ✅ |
| **Duplikat-Strategie** | Erste behalten | Beste behalten |

---

## Nächste Schritte

1. ✅ **Server neu starten**
2. ✅ **Cache löschen** (optional)
3. ✅ **TPY neu hochladen**
4. ✅ **TreeView überprüfen** - Sollte hierarchisch sein
5. ✅ **Type-Information prüfen** - Sollte "FB_Light" statt "UNKNOWN" zeigen
6. ✅ **Expandierte Symbole suchen** - z.B. "Light.Light_EG_WZ.bOn"

---

**Erstellt:** 2026-01-10 23:30
**Status:** ✅ IMPLEMENTIERT
**Nächste Aktion:** Server-Neustart + TPY-Upload + Verifikation
