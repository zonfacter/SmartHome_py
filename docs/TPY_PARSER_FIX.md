# TPY-Parser Fix - DataType-basierte SubItem-Expansion

**Datum:** 10. Januar 2026
**Version:** symbol_browser.py v4.6.0
**Status:** ✅ IMPLEMENTIERT - Bereit zum Testen

---

## Problem

Der TPY-Parser fand nur **751 Top-Level-Symbole** statt der erwarteten **~14.000 Symbole** (wie Live-Load von PLC).

### Root Cause

**TwinCAT 2 TPY-Format Struktur:**

```xml
<PlcProjectInfo>
  <DataTypes>
    <DataType>
      <Name>FB_Light</Name>
      <SubItem>
        <Name>bOn</Name>
        <Type>BOOL</Type>
      </SubItem>
      <SubItem>
        <Name>bOff</Name>
        <Type>BOOL</Type>
      </SubItem>
      <SubItem>
        <Name>RisingEdgeOn</Name>
        <Type>R_TRIG</Type>  <!-- R_TRIG ist auch ein DataType! -->
      </SubItem>
    </DataType>

    <DataType>
      <Name>R_TRIG</Name>
      <SubItem>
        <Name>Q</Name>
        <Type>BOOL</Type>
      </SubItem>
      <SubItem>
        <Name>M</Name>
        <Type>BOOL</Type>
      </SubItem>
    </DataType>
  </DataTypes>

  <Symbols>
    <Symbol>
      <Name>Light_EG_WZ</Name>
      <Type>FB_Light</Type>  <!-- Referenz auf DataType -->
    </Symbol>
  </Symbols>
</PlcProjectInfo>
```

**Wichtig:**
- `<Symbol>` Elemente haben **KEINE direkten SubItems**
- SubItems sind in separater `<DataTypes>` Section definiert
- Symbole referenzieren DataTypes über `<Type>` Element

### Alter Parser (FALSCH)

```python
# Suchte nach SubItems direkt unter Symbol - gibt LEER zurück!
for subitem in sym.findall('./SubItem'):  # ← Findet nichts in TwinCAT 2!
    sub_symbols = extract_subitems_recursive(subitem, top_name)
    all_symbol_tuples.extend(sub_symbols)

# Ergebnis: Nur 751 Top-Level-Symbole
```

---

## Lösung: DataType-Mapping

### Implementierung (wie convert_tpy_csv.py)

#### Schritt 1: DataType-Map erstellen

```python
datatype_by_name = {}
all_datatypes = root.findall('.//DataTypes/DataType')

for dt in all_datatypes:
    dt_name = get_text(dt, 'Name')
    if dt_name:
        datatype_by_name[dt_name] = dt

# Ergebnis: ~237 DataTypes in Map
```

#### Schritt 2: Rekursive SubItem-Expansion

```python
def expand_datatype_subitems(datatype_name, parent_name, depth=0):
    """Expandiert SubItems aus einem DataType rekursiv"""
    if depth > 20:  # Schutz vor Endlos-Rekursion
        return []

    dt = datatype_by_name.get(datatype_name)
    if dt is None:
        return []

    symbols = []

    for si in dt.findall('./SubItem'):
        si_name = get_text(si, 'Name')
        si_type = get_text(si, 'Type', 'UNKNOWN')
        full_name = f"{parent_name}.{si_name}"

        # Füge SubItem hinzu
        symbols.append((full_name, si, si_type))

        # Rekursiv: Wenn SubItem-Type auch ein DataType ist
        if si_type in datatype_by_name:
            sub_symbols = expand_datatype_subitems(si_type, full_name, depth + 1)
            symbols.extend(sub_symbols)

    return symbols
```

#### Schritt 3: Symbole expandieren

```python
all_symbol_tuples = []

for sym in all_symbols:
    top_name = get_text(sym, 'Name')
    top_type = get_text(sym, 'Type', 'UNKNOWN')

    # Top-Symbol hinzufügen
    all_symbol_tuples.append((top_name, sym, top_type))

    # Wenn Type in DataTypes definiert ist, expandiere SubItems
    if top_type and top_type != 'UNKNOWN' and top_type in datatype_by_name:
        sub_symbols = expand_datatype_subitems(top_type, top_name)
        all_symbol_tuples.extend(sub_symbols)

    # FALLBACK: TwinCAT 3 Format (SubItems direkt unter Symbol)
    for subitem in sym.findall('./SubItem'):
        si_name = get_text(subitem, 'Name')
        si_type = get_text(subitem, 'Type', 'UNKNOWN')
        full_name = f"{top_name}.{si_name}"
        all_symbol_tuples.append((full_name, subitem, si_type))

        if si_type in datatype_by_name:
            nested = expand_datatype_subitems(si_type, full_name)
            all_symbol_tuples.extend(nested)
```

---

## Beispiel-Expansion

### Input (TPY):

```xml
<Symbol>
  <Name>Light_EG_WZ</Name>
  <Type>FB_Light</Type>
</Symbol>

<DataType>
  <Name>FB_Light</Name>
  <SubItem><Name>bOn</Name><Type>BOOL</Type></SubItem>
  <SubItem><Name>bOff</Name><Type>BOOL</Type></SubItem>
  <SubItem><Name>bLight</Name><Type>BOOL</Type></SubItem>
  <SubItem><Name>RisingEdgeOn</Name><Type>R_TRIG</Type></SubItem>
</DataType>

<DataType>
  <Name>R_TRIG</Name>
  <SubItem><Name>Q</Name><Type>BOOL</Type></SubItem>
  <SubItem><Name>M</Name><Type>BOOL</Type></SubItem>
</DataType>
```

### Output (Expanded Symbols):

```
Light_EG_WZ (FB_Light)
Light_EG_WZ.bOn (BOOL)
Light_EG_WZ.bOff (BOOL)
Light_EG_WZ.bLight (BOOL)
Light_EG_WZ.RisingEdgeOn (R_TRIG)
Light_EG_WZ.RisingEdgeOn.Q (BOOL)  ← Verschachtelt!
Light_EG_WZ.RisingEdgeOn.M (BOOL)
```

**7 Symbole** aus **1 Top-Symbol** + **2 DataTypes**!

---

## Erwartetes Ergebnis

### Vorher (v4.6.0):
```
📂 Root-Element: PlcProjectInfo
🔍 Gefunden: 952 <Symbol> Elemente (Top-Level)
🔍 Rekursiv gefunden: 952 Symbole (inkl. SubItems)  ← FALSCH
✅ 751 eindeutige Symbole extrahiert
💾 751 Symbole konvertiert zu PLCSymbol-Objekten
```

### Nachher (v4.6.0):
```
📂 Root-Element: PlcProjectInfo
🔍 Gefunden: 952 <Symbol> Elemente (Top-Level)
🔍 Gefunden: 237 <DataType> Elemente
📚 DataType-Map erstellt: 237 Typen
🔍 Rekursiv gefunden: ~14000 Symbole (inkl. DataType-SubItems)  ← KORREKT
✅ ~14000 eindeutige Symbole extrahiert
💾 ~14000 Symbole konvertiert zu PLCSymbol-Objekten
```

---

## TreeView Hierarchie

Die TreeView-Funktion in `app.js` war bereits korrekt implementiert:

```javascript
renderSymbolTree(symbols, container) {
    const tree = {};
    symbols.forEach(symbol => {
        const parts = symbol.name.split('.');  // "Light_EG_WZ.bOn" → ["Light_EG_WZ", "bOn"]
        let current = tree;

        parts.forEach((part, index) => {
            if (!current[part]) {
                current[part] = {
                    _isLeaf: index === parts.length - 1,
                    _symbol: index === parts.length - 1 ? symbol : null,
                    _children: {}
                };
            }
            if (!current[part]._isLeaf) {
                current = current[part]._children;
            }
        });
    });

    container.innerHTML = this.buildTreeHTML(tree, 0);
}
```

**Problem:** TreeView funktioniert nur mit vollständigen Symbol-Pfaden (z.B. "Light_EG_WZ.bOn")

**Vorher:** TPY-Parser lieferte nur "Light_EG_WZ" → Flache Liste
**Jetzt:** TPY-Parser liefert "Light_EG_WZ.bOn" → Hierarchischer Baum!

### Erwartete TreeView-Darstellung:

```
📁 Light_EG_WZ (FB_Light)
  ├─ 🔵 bOn (BOOL)
  ├─ 🔵 bOff (BOOL)
  ├─ 🔵 bLight (BOOL)
  └─ 📁 RisingEdgeOn (R_TRIG)
      ├─ 🔵 Q (BOOL)
      └─ 🔵 M (BOOL)
```

---

## Tests

### 1. Server neu starten

```bash
# STRG+C zum Beenden
python main.py
```

### 2. TPY-Datei neu hochladen

1. Setup-Seite öffnen
2. TPY-Datei hochladen
3. **Erwartete Server-Logs:**

```
📂 Root-Element: PlcProjectInfo
🔍 Gefunden: 952 <Symbol> Elemente (Top-Level)
🔍 Gefunden: 237 <DataType> Elemente
📚 DataType-Map erstellt: 237 Typen
🔍 Rekursiv gefunden: ~14000 Symbole (inkl. DataType-SubItems)
✅ ~14000 eindeutige Symbole extrahiert
💾 ~14000 Symbole konvertiert zu PLCSymbol-Objekten
✅ ERFOLG: ~14000 Symbole aus TPY geladen und im Cache gespeichert!
```

### 3. TreeView prüfen

- Setup-Seite sollte ~14.000 Nodes zeigen
- Hierarchische Struktur sichtbar (Ordner mit Chevrons)
- Verschachtelte FB-Member (z.B. "Light_EG_WZ.RisingEdgeOn.Q")

### 4. Vergleich: Live-Load vs TPY-Parser

| Methode | Symbole | Hierarchie | Status |
|---------|---------|------------|--------|
| **Live-Load** (pyads) | 14.264 | ✅ Vollständig | ✅ Funktioniert |
| **TPY-Parser** (alt v4.6.0) | 751 | ❌ Nur Top-Level | ❌ Unvollständig |
| **TPY-Parser** (neu v4.6.0) | ~14.000 | ✅ Vollständig | ✅ Sollte funktionieren |

---

## Geänderte Dateien

### `modules/plc/symbol_browser.py`

**Lines 1-20:** Version-Header aktualisiert (v4.6.0)
**Lines 257-359:** Komplette Neuimplementierung des TPY-Parsers:
- DataType-Map Erstellung
- `get_text()` Hilfsfunktion
- `expand_datatype_subitems()` rekursive Expansion
- Symbol-Iteration mit DataType-Expansion
- Fallback für TwinCAT 3 Format

**Lines 361-377:** Duplikat-Entfernung angepasst für 3-Tupel
**Lines 384-415:** PLCSymbol-Konvertierung angepasst für extracted_type

---

## Kritische Änderungen (NICHT verlieren!)

1. **DataType-Map ist essentiell** für TwinCAT 2 TPY-Parsing
2. **Rekursive Expansion** notwendig für verschachtelte DataTypes (z.B. R_TRIG in FB_Light)
3. **Depth-Limit (20)** schützt vor Endlos-Rekursion
4. **Fallback für TwinCAT 3** bewahrt Kompatibilität

---

## Nächste Schritte

1. ✅ **Server neu starten**
2. ✅ **TPY neu hochladen** - Sollte ~14.000 Symbole finden
3. ✅ **TreeView prüfen** - Sollte hierarchisch sein
4. ✅ **Suche testen** - Sollte in ~14.000 Symbolen suchen
5. ✅ **Live-Load vergleichen** - Beide Methoden sollten ähnliche Symbol-Anzahl liefern

---

## Credits

Implementierung basiert auf der Logik aus dem User-Script `convert_tpy_csv.py`:
- DataType-Mapping
- Rekursive SubItem-Expansion
- Verschachtelte DataType-Auflösung

**Erstellt:** 2026-01-10
**Status:** ✅ IMPLEMENTIERT
**Nächste Aktion:** Server-Neustart + TPY-Upload + Testing
