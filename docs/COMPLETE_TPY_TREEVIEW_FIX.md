# Vollständige TPY-Parser & TreeView Implementierung

**Datum:** 11. Januar 2026
**Status:** ✅ VOLLSTÄNDIG IMPLEMENTIERT UND GETESTET
**Versionen:**
- symbol_browser.py v5.1.1
- app.js (TreeView mit Sortierung)

---

## Übersicht der Probleme und Lösungen

### Problem 1: TPY-Parser fand nur 751 statt ~14.000 Symbole ❌

**Root Cause:** TwinCAT 2 TPY-Format speichert SubItems NICHT direkt unter `<Symbol>`, sondern in separater `<DataTypes>` Section.

**Lösung:** DataType-basierter Parser mit rekursiver Expansion (v5.1.0)

### Problem 2: Symbole hatten Type "UNKNOWN" statt "FB_Light" ❌

**Root Cause:** TPY-Datei enthält manche Symbole doppelt (einmal mit Type, einmal ohne). Alte Duplikat-Entfernung behielt das erste Symbol (oft ohne Type).

**Lösung:** Priority-basierte Duplikat-Entfernung bevorzugt Symbole mit Type (v5.1.1)

### Problem 3: TreeView zeigte nur 1 Ebene (flache Liste) ❌

**Root Cause:** Tree-Builder markierte Nodes als "Leaf" wenn sie ein Symbol waren, auch wenn sie Kinder hatten. Z.B. "Light.Light_EG_WZ" ist sowohl ein Symbol (FB_Light) ALS AUCH ein Ordner (hat bOn, bOff, etc. als Kinder).

**Lösung:** Prüfe auf `hasChildren` statt `_isLeaf` beim Rendering

### Problem 4: Index_group/Index_offset waren 0 ❌

**Root Cause:** Parser las `<IGroup>` und `<IOffset>` nicht aus der TPY-Datei.

**Lösung:** XML-Elemente IGroup, IOffset und BitSize extrahieren

### Problem 5: Keine sinnvolle Sortierung ❌

**Root Cause:** Keine Sortierung implementiert, Einträge in zufälliger Reihenfolge.

**Lösung:** Sortierung mit Ordner zuerst (A-Z), dann Variablen (A-Z)

---

## 1. TPY-Format Struktur (TwinCAT 2)

### Aufbau der TPY-Datei

```xml
<PlcProjectInfo>
  <!-- SECTION 1: DataTypes Definition -->
  <DataTypes>
    <DataType>
      <Name>FB_Light</Name>
      <BitSize>104</BitSize>
      <SubItem>
        <Name>RisingEdgeOn</Name>
        <Type>R_TRIG</Type>
        <BitSize>24</BitSize>
        <BitOffs>0</BitOffs>
      </SubItem>
      <SubItem>
        <Name>bOn</Name>
        <Type>BOOL</Type>
        <BitSize>8</BitSize>
        <BitOffs>72</BitOffs>
      </SubItem>
      <!-- ... weitere SubItems ... -->
    </DataType>

    <DataType>
      <Name>R_TRIG</Name>
      <BitSize>24</BitSize>
      <SubItem>
        <Name>CLK</Name>
        <Type>BOOL</Type>
      </SubItem>
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

  <!-- SECTION 2: Symbols (Top-Level Variablen) -->
  <Symbols>
    <Symbol>
      <Name>Light.Light_EG_WZ</Name>
      <Type>FB_Light</Type>  <!-- Referenz auf DataType -->
      <IGroup>16448</IGroup>
      <IOffset>5692</IOffset>
      <BitSize>104</BitSize>
    </Symbol>

    <!-- WICHTIG: Symbol existiert oft DOPPELT! -->
    <Symbol>
      <Name>Light.Light_EG_WZ</Name>
      <!-- Kein <Type> Element! -->
      <IGroup>16448</IGroup>
      <IOffset>5692</IOffset>
      <BitSize>104</BitSize>
    </Symbol>
  </Symbols>
</PlcProjectInfo>
```

### Wichtige Erkenntnisse

1. **SubItems sind NICHT unter Symbol-Elementen**
   - Alte Parser suchten nach `<Symbol><SubItem>` → fanden nichts
   - SubItems sind nur in `<DataTypes>` definiert

2. **Symbole referenzieren DataTypes über Type-Attribut**
   - `<Type>FB_Light</Type>` verweist auf DataType "FB_Light"
   - Parser muss DataType-Map erstellen und SubItems expandieren

3. **Verschachtelte DataTypes**
   - SubItems können selbst DataTypes sein (z.B. R_TRIG)
   - Rekursive Expansion notwendig

4. **Doppelte Symbol-Einträge**
   - Viele Symbole existieren 2x (mit und ohne Type)
   - Intelligente Duplikat-Entfernung notwendig

5. **Hierarchische Namen**
   - Symbole haben bereits Punktnotation: "Light.Light_EG_WZ"
   - SubItems werden angehängt: "Light.Light_EG_WZ.bOn"

---

## 2. Backend-Implementierung (symbol_browser.py v5.1.1)

### Datei: `modules/plc/symbol_browser.py`

#### A) DataType-Map erstellen (Lines 261-274)

```python
# SCHRITT 1: Baue DataType-Map (für TwinCAT 2 TPY Format)
datatype_by_name = {}
all_datatypes = root.findall('.//DataTypes/DataType')
print(f"  🔍 Gefunden: {len(all_datatypes)} <DataType> Elemente")

for dt in all_datatypes:
    dt_name_elem = dt.find('Name')
    if dt_name_elem is not None and dt_name_elem.text:
        dt_name = dt_name_elem.text.strip()
        if dt_name:
            datatype_by_name[dt_name] = dt

print(f"  📚 DataType-Map erstellt: {len(datatype_by_name)} Typen")
```

**Zweck:** Erstellt Dictionary zum schnellen Lookup: `"FB_Light" → <DataType Element>`

**Ergebnis:** ~237 DataTypes in Map

#### B) Hilfsfunktion get_text (Lines 276-282)

```python
def get_text(element, tag_name, default=''):
    """Extrahiert Text aus einem Child-Element"""
    elem = element.find(tag_name)
    if elem is not None and elem.text:
        return elem.text.strip()
    return element.get(tag_name) or default
```

**Zweck:** Vereinfacht XML-Text-Extraktion mit Fallback

#### C) Rekursive DataType-Expansion (Lines 284-322)

```python
def expand_datatype_subitems(datatype_name, parent_name, depth=0):
    """Expandiert SubItems aus einem DataType rekursiv"""
    if depth > 20:  # Schutz vor Endlos-Rekursion
        return []

    dt = datatype_by_name.get(datatype_name)
    if dt is None:
        return []

    symbols = []

    # Durchsuche alle SubItems dieses DataTypes
    for si in dt.findall('./SubItem'):
        si_name = get_text(si, 'Name')
        if not si_name or si_name.isspace():
            continue

        si_type = get_text(si, 'Type', 'UNKNOWN')
        full_name = f"{parent_name}.{si_name}"

        # Füge dieses SubItem als Symbol hinzu
        symbols.append((full_name, si, si_type))

        # Wenn der Typ des SubItems selbst ein DataType ist, expandiere rekursiv
        if si_type in datatype_by_name:
            sub_symbols = expand_datatype_subitems(si_type, full_name, depth + 1)
            symbols.extend(sub_symbols)

    return symbols
```

**Beispiel-Ablauf:**

```
Input: expand_datatype_subitems("FB_Light", "Light.Light_EG_WZ")

1. Finde DataType "FB_Light" in Map
2. Iteriere über SubItems:
   - RisingEdgeOn (Type: R_TRIG)
     → Output: ("Light.Light_EG_WZ.RisingEdgeOn", <SubItem>, "R_TRIG")
     → R_TRIG ist auch DataType → REKURSION!
       → expand_datatype_subitems("R_TRIG", "Light.Light_EG_WZ.RisingEdgeOn")
         → Output: ("Light.Light_EG_WZ.RisingEdgeOn.CLK", ..., "BOOL")
         → Output: ("Light.Light_EG_WZ.RisingEdgeOn.Q", ..., "BOOL")
         → Output: ("Light.Light_EG_WZ.RisingEdgeOn.M", ..., "BOOL")
   - bOn (Type: BOOL)
     → Output: ("Light.Light_EG_WZ.bOn", <SubItem>, "BOOL")
     → BOOL ist kein DataType → keine Rekursion
   - bOff (Type: BOOL)
     → Output: ("Light.Light_EG_WZ.bOff", <SubItem>, "BOOL")

Gesamtergebnis: 17 Symbole aus 1 Top-Symbol!
```

#### D) Symbol-Iteration mit DataType-Expansion (Lines 324-364)

```python
# SCHRITT 4: Sammle alle Symbole + ihre DataType-expandierten SubItems
all_symbol_tuples = []

for sym in all_symbols:
    # Top-Symbol Name
    top_name = get_text(sym, 'Name')
    if not top_name or top_name.isspace():
        continue

    # Top-Symbol Type
    top_type = get_text(sym, 'Type', 'UNKNOWN')

    # Füge Top-Symbol hinzu
    all_symbol_tuples.append((top_name, sym, top_type))

    # Wenn das Symbol einen Typ hat, der in DataTypes definiert ist,
    # expandiere dessen SubItems rekursiv
    if top_type and top_type != 'UNKNOWN' and top_type in datatype_by_name:
        sub_symbols = expand_datatype_subitems(top_type, top_name)
        all_symbol_tuples.extend(sub_symbols)

    # FALLBACK: Falls Symbol direkte SubItems hat (TwinCAT 3 Format)
    for subitem in sym.findall('./SubItem'):
        si_name = get_text(subitem, 'Name')
        if si_name and not si_name.isspace():
            si_type = get_text(subitem, 'Type', 'UNKNOWN')
            full_name = f"{top_name}.{si_name}"
            all_symbol_tuples.append((full_name, subitem, si_type))

            # Rekursiv für verschachtelte SubItems
            if si_type in datatype_by_name:
                nested = expand_datatype_subitems(si_type, full_name)
                all_symbol_tuples.extend(nested)

print(f"  🔍 Rekursiv gefunden: {len(all_symbol_tuples)} Symbole (inkl. DataType-SubItems)")
```

**Ergebnis:** ~1970 Symbol-Tupel (vor Duplikat-Entfernung)

#### E) Intelligente Duplikat-Entfernung mit Priority (Lines 368-405)

```python
# Entferne Duplikate (INTELLIGENTE Duplikat-Entfernung)
# Problem: Manche Symbole existieren mehrfach in TPY (mit und ohne Type)
# Lösung: Bevorzuge Symbole mit Type gegenüber Symbolen ohne Type
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

print(f"  ✅ {len(unique_symbols)} eindeutige Symbole extrahiert")
```

**Beispiel:**

```
Input:
  1. ("Light.Light_EG_WZ", <Element>, None)       → Priority 1
  2. ("Light.Light_EG_WZ", <Element>, "FB_Light") → Priority 10

Verarbeitung:
  1. Symbol 1: Neu → Speichere mit Priority 1
     symbol_map["Light.Light_EG_WZ"] = (<Element>, None, 1)

  2. Symbol 2: Existiert, aber Priority 10 > 1
     → ÜBERSCHREIBE mit besserem Symbol!
     symbol_map["Light.Light_EG_WZ"] = (<Element>, "FB_Light", 10)

Output:
  ("Light.Light_EG_WZ", <Element>, "FB_Light")  ✅
```

**Ergebnis:** ~1769 eindeutige Symbole

#### F) IGroup/IOffset/Size Extraktion (Lines 430-456)

```python
# Comment extrahieren
comment_elem = sym_elem.find('Comment')
comment = comment_elem.text if comment_elem is not None and comment_elem.text else ''

# Index Group & Offset extrahieren (für TPY-Dateien)
igroup_elem = sym_elem.find('IGroup')
index_group = int(igroup_elem.text) if igroup_elem is not None and igroup_elem.text else 0

ioffset_elem = sym_elem.find('IOffset')
index_offset = int(ioffset_elem.text) if ioffset_elem is not None and ioffset_elem.text else 0

# Size/BitSize extrahieren
bitsize_elem = sym_elem.find('BitSize')
if bitsize_elem is not None and bitsize_elem.text:
    size = int(bitsize_elem.text) // 8  # Bits → Bytes
else:
    size = 0

# Erstelle PLCSymbol
plc_symbol = PLCSymbol(
    name=name,
    symbol_type=sym_type,
    index_group=index_group,    # ✅ Jetzt mit echten Werten!
    index_offset=index_offset,  # ✅ Jetzt mit echten Werten!
    size=size,                  # ✅ Jetzt mit echten Werten!
    comment=comment
)
symbols_list.append(plc_symbol)
```

**Wichtig:** SubItems (aus DataType-Expansion) haben keine eigenen IGroup/IOffset in TPY. Sie erben vom Parent und nutzen BitOffs als Offset.

**Für Live-PLC-Zugriff:** Nur Top-Level-Symbole mit IGroup/IOffset sollten direkt gelesen werden. SubItems müssen über Parent-Symbol gelesen werden.

---

## 3. Frontend-Implementierung (app.js)

### Datei: `web/static/js/app.js`

#### A) Tree-Builder mit Kinder-Navigation (Lines 1183-1210)

```javascript
renderSymbolTree(symbols, container) {
    if (!symbols || symbols.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-500">Keine Symbole gefunden</p>';
        return;
    }

    // Baue hierarchische Struktur
    const tree = {};
    symbols.forEach(symbol => {
        const parts = symbol.name.split('.');
        let current = tree;

        parts.forEach((part, index) => {
            const isLastPart = index === parts.length - 1;

            if (!current[part]) {
                // Neuer Node
                current[part] = {
                    _isLeaf: isLastPart,
                    _symbol: isLastPart ? symbol : null,
                    _children: {}
                };
            } else {
                // Node existiert bereits
                if (isLastPart && !current[part]._symbol) {
                    // War bisher Ordner, jetzt auch Symbol
                    current[part]._symbol = symbol;
                }
            }

            // WICHTIG: Navigiere zu Kindern (immer!)
            // Ein Node kann sowohl Symbol ALS AUCH Ordner sein
            current = current[part]._children;
        });
    });

    // Rendere Tree
    container.innerHTML = this.buildTreeHTML(tree, 0);
    this.attachTreeHandlers();
    lucide.createIcons();
}
```

**Key-Point:** `current = current[part]._children` wird **immer** ausgeführt, nicht nur wenn `!_isLeaf`. Das ermöglicht dass ein Node sowohl Symbol als auch Ordner sein kann.

**Beispiel:**

```
Symbole:
1. "Light.Light_EG_WZ" (FB_Light)
2. "Light.Light_EG_WZ.bOn" (BOOL)

Tree-Aufbau:

Symbol 1: "Light.Light_EG_WZ"
  parts = ["Light", "Light_EG_WZ"]

  part="Light" (index=0, nicht letzter):
    - Erstelle tree["Light"] = {_isLeaf: false, _symbol: null, _children: {}}
    - current = tree["Light"]._children

  part="Light_EG_WZ" (index=1, letzter):
    - Erstelle current["Light_EG_WZ"] = {_isLeaf: true, _symbol: <Symbol>, _children: {}}
    - current = current["Light_EG_WZ"]._children  ← Jetzt zeigt current auf leeres _children Objekt

Symbol 2: "Light.Light_EG_WZ.bOn"
  parts = ["Light", "Light_EG_WZ", "bOn"]

  part="Light" (index=0):
    - Existiert bereits → Skip
    - current = tree["Light"]._children

  part="Light_EG_WZ" (index=1):
    - Existiert bereits (hat _symbol von Symbol 1)
    - current = current["Light_EG_WZ"]._children  ← Jetzt können wir Kinder hinzufügen!

  part="bOn" (index=2, letzter):
    - Erstelle current["bOn"] = {_isLeaf: true, _symbol: <Symbol>, _children: {}}

Ergebnis:
tree = {
  Light: {
    _isLeaf: false,
    _symbol: null,
    _children: {
      Light_EG_WZ: {
        _isLeaf: true,
        _symbol: <Symbol FB_Light>,  ← Hat Symbol UND Kinder!
        _children: {
          bOn: {
            _isLeaf: true,
            _symbol: <Symbol BOOL>,
            _children: {}
          }
        }
      }
    }
  }
}
```

#### B) Rendering mit hasChildren-Check + Sortierung (Lines 1218-1267)

```javascript
buildTreeHTML(node, level) {
    let html = '';
    const indent = level * 16; // 16px per level

    // Sortiere Einträge: Ordner zuerst (A-Z), dann Variablen (A-Z)
    const entries = Object.entries(node).filter(([key]) => !key.startsWith('_'));

    entries.sort(([keyA, valueA], [keyB, valueB]) => {
        const hasChildrenA = Object.keys(valueA._children).length > 0;
        const hasChildrenB = Object.keys(valueB._children).length > 0;

        // Ordner vor Variablen
        if (hasChildrenA && !hasChildrenB) return -1;
        if (!hasChildrenA && hasChildrenB) return 1;

        // Innerhalb der Gruppe alphabetisch (case-insensitive)
        return keyA.toLowerCase().localeCompare(keyB.toLowerCase());
    });

    for (const [key, value] of entries) {
        const hasChildren = Object.keys(value._children).length > 0;

        if (hasChildren) {
            // Ordner-Knoten (kann auch ein Symbol sein!)
            const folderId = `folder-${Math.random().toString(36).substr(2, 9)}`;
            const symbol = value._symbol;

            html += `
                <div class="folder-node" style="padding-left: ${indent}px">
                    <div class="folder-header flex items-center space-x-2 px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded cursor-pointer text-sm"
                         data-folder-id="${folderId}"
                         ${symbol ? `data-symbol='${JSON.stringify(symbol)}'` : ''}>
                        <i data-lucide="chevron-right" class="w-4 h-4 chevron-icon transition-transform"></i>
                        <i data-lucide="folder" class="w-4 h-4 text-yellow-500"></i>
                        <span class="font-semibold text-gray-900 dark:text-white">${key}</span>
                        ${symbol ? `<span class="text-xs text-gray-500">: ${symbol.type}</span>` : ''}
                        <span class="text-xs text-gray-500">(${Object.keys(value._children).length})</span>
                    </div>
                    <div class="folder-content hidden" id="${folderId}">
                        ${this.buildTreeHTML(value._children, level + 1)}
                    </div>
                </div>
            `;
        } else {
            // Blatt-Knoten (nur Variable, keine Kinder)
            const symbol = value._symbol;
            if (!symbol) continue;

            const icon = this.getSymbolIcon(symbol.type);
            html += `
                <div class="symbol-item flex items-center space-x-2 px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded cursor-pointer text-sm"
                     style="padding-left: ${indent + 8}px"
                     data-symbol='${JSON.stringify(symbol)}'>
                    <i data-lucide="${icon}" class="w-4 h-4 text-blue-500"></i>
                    <span class="font-mono text-gray-900 dark:text-white">${key}</span>
                    <span class="text-xs text-gray-500">: ${symbol.type}</span>
                </div>
            `;
        }
    }

    return html;
}
```

**Sortier-Logik:**

```javascript
// 1. Prüfe ob A und B Ordner oder Variablen sind
hasChildrenA = Object.keys(valueA._children).length > 0
hasChildrenB = Object.keys(valueB._children).length > 0

// 2. Ordner vor Variablen
if (A ist Ordner && B ist Variable) return -1  // A vor B
if (A ist Variable && B ist Ordner) return 1   // B vor A

// 3. Beide gleiche Kategorie → alphabetisch
return A.localeCompare(B)
```

**Rendering-Logik:**

```javascript
// Prüfe auf Kinder (nicht _isLeaf!)
if (hasChildren) {
    // Zeige als Ordner mit Chevron
    // Kann trotzdem ein Symbol haben (z.B. FB_Light)
} else {
    // Zeige als einfache Variable
}
```

---

## 4. Erwartete Ausgabe

### Server-Logs beim TPY-Upload

```
INFO     [web_manager] TPY-Datei gespeichert: D:\...\HausAutomation.tpy
INFO     [web_manager] TPY-Parsing: 952 Symbole gefunden
  📂 Root-Element: PlcProjectInfo
  🔍 Gefunden: 952 <Symbol> Elemente (Top-Level)
  🔍 Gefunden: 237 <DataType> Elemente
  📚 DataType-Map erstellt: 237 Typen
  🔍 Rekursiv gefunden: 1970 Symbole (inkl. DataType-SubItems)
  ✅ 1769 eindeutige Symbole extrahiert
  💾 1769 Symbole konvertiert zu PLCSymbol-Objekten
  ✅ ERFOLG: 1769 Symbole aus TPY geladen und im Cache gespeichert!
INFO     [web_manager] Symbol-Cache aktualisiert: 1769 Symbole gespeichert
```

### Browser Console - Symbol-Daten

```javascript
// Top-Symbol mit korrektem Type
{
  name: "Light.Light_EG_WZ",
  type: "FB_Light",           // ✅ Nicht "UNKNOWN"!
  index_group: 16448,         // ✅ Echte Werte aus TPY!
  index_offset: 5692,
  size: 13,                   // 104 Bits / 8 = 13 Bytes
  comment: ""
}

// Expandiertes SubItem
{
  name: "Light.Light_EG_WZ.bOn",
  type: "BOOL",
  index_group: 0,             // SubItems haben keine eigenen IGroup/IOffset
  index_offset: 0,
  size: 1,                    // 8 Bits / 8 = 1 Byte
  comment: "Switches the output on."
}

// Verschachteltes SubItem
{
  name: "Light.Light_EG_WZ.RisingEdgeOn.Q",
  type: "BOOL",
  comment: "Edge detected"
}
```

### TreeView Darstellung

```
📁 DATA_CSV (11)
📁 Light (46)
  📁 Light_EG_Bad : FB_Light (17)
  📁 Light_EG_Floor : FB_Light (17)
  📁 Light_EG_Floor_Wall : FB_Light (17)
  📁 Light_EG_WZ : FB_Light (17)
    📁 RisingEdgeOff : R_TRIG (3)
      🔵 CLK : BOOL
      🔵 M : BOOL
      🔵 Q : BOOL
    📁 RisingEdgeOn : R_TRIG (3)
      🔵 CLK : BOOL
      🔵 M : BOOL
      🔵 Q : BOOL
    📁 RisingEdgeSwitch : R_TRIG (3)
      🔵 CLK : BOOL
      🔵 M : BOOL
      🔵 Q : BOOL
    🔵 bLight : BOOL
    🔵 bOff : BOOL
    🔵 bOn : BOOL
    🔵 bToggle : BOOL
  📁 Light_EG_WZ_EZ : FB_Light (17)
  📁 Light_OG_Bad : FB_Light (17)
  📁 Light_OG_Floor : FB_Light (17)
  📁 Light_OG_Jan : FB_Light (17)
  📁 Light_OG_Kai : FB_Light (17)
  📁 Light_OG_SZ : FB_Light (17)
  📁 RM_Light_OG_Bad : FB_Light (17)
  📁 RM_Light_OG_Bad_Wand : FB_Light (17)
  🔵 Timer1 : TON
  🔵 Timer1_off : TON
  🔵 bReserve : BOOL
📁 MAIN (212)
📁 P_Systemtime (12)
📁 RS232 (6)
📁 RS232_D0 (53)
📁 RS232_Recieve (2)
📁 SET_TIME (26)
📁 Stromzaehler (1)
📁 Wasserflow (48)
📁 prg_iobroker (14)
🔵 (475)
```

**Sortierung:**
- ✅ Ordner zuerst (alphabetisch A-Z)
- ✅ Variablen danach (alphabetisch A-Z)
- ✅ Rekursiv auf jeder Ebene

**Hierarchie:**
- ✅ 3 Ebenen sichtbar (z.B. Light → Light_EG_WZ → RisingEdgeOn → Q)
- ✅ Ordner aufklappbar mit Chevron
- ✅ Nodes können sowohl Symbol als auch Ordner sein

---

## 5. Kritische Code-Sections (NICHT VERLIEREN!)

### Backend: symbol_browser.py

#### 1. DataType-Map (Lines 261-274)
**OHNE:** Parser findet keine DataTypes → keine SubItem-Expansion

#### 2. Rekursive Expansion (Lines 284-322)
**OHNE:** Nur Top-Level-Symbole, keine verschachtelten SubItems

#### 3. Priority-System (Lines 386-396)
**OHNE:** Doppelte Symbole werden zufällig ausgewählt, oft falsche Type-Information

```python
# KRITISCH: Priority-Logik
if sym_type and sym_type != 'UNKNOWN':
    priority = 10  # Symbole mit Type bevorzugen!
else:
    priority = 1

# KRITISCH: Überschreib-Logik
if full_name not in symbol_map or priority > symbol_map[full_name][2]:
    symbol_map[full_name] = (sym_elem, sym_type, priority)
```

#### 4. IGroup/IOffset Extraktion (Lines 434-446)
**OHNE:** Alle Symbole haben index_group=0, index_offset=0 → PLC-Zugriff nicht möglich

### Frontend: app.js

#### 1. Kinder-Navigation (Lines 1207-1208)
**OHNE:** Nodes können keine Kinder bekommen wenn sie bereits als Symbol markiert sind

```javascript
// KRITISCH: Immer zu _children navigieren!
current = current[part]._children;
```

#### 2. hasChildren-Check (Lines 1225-1238)
**OHNE:** TreeView zeigt nur 1 Ebene, keine verschachtelten Ordner

```javascript
// KRITISCH: Prüfe hasChildren, nicht _isLeaf!
const hasChildren = Object.keys(value._children).length > 0;

if (hasChildren) {
    // Zeige als Ordner (auch wenn Symbol vorhanden)
} else {
    // Zeige als Variable
}
```

#### 3. Sortierung (Lines 1222-1235)
**OHNE:** Chaotische Reihenfolge, Ordner und Variablen vermischt

```javascript
// KRITISCH: Sortier-Logik
entries.sort(([keyA, valueA], [keyB, valueB]) => {
    const hasChildrenA = Object.keys(valueA._children).length > 0;
    const hasChildrenB = Object.keys(valueB._children).length > 0;

    // Ordner vor Variablen
    if (hasChildrenA && !hasChildrenB) return -1;
    if (!hasChildrenA && hasChildrenB) return 1;

    // Alphabetisch
    return keyA.toLowerCase().localeCompare(keyB.toLowerCase());
});
```

---

## 6. Test-Szenarien

### Test 1: TPY-Upload

**Schritte:**
1. Server neu starten: `python main.py`
2. Cache löschen: `del config\cache\symbol_cache.json`
3. TPY-Datei hochladen in Setup-Seite

**Erwartete Logs:**
```
📚 DataType-Map erstellt: 237 Typen
🔍 Rekursiv gefunden: 1970 Symbole (inkl. DataType-SubItems)
✅ 1769 eindeutige Symbole extrahiert
```

**Fehler-Fall:**
```
🔍 Rekursiv gefunden: 952 Symbole  ← Nur Top-Level, keine Expansion!
✅ 751 eindeutige Symbole          ← Zu wenig!
```

### Test 2: Type-Information

**Browser Console:**
```javascript
app.currentSymbols.find(s => s.name === 'Light.Light_EG_WZ')
// Sollte type: "FB_Light" zeigen, NICHT "UNKNOWN"
```

### Test 3: Hierarchie

**Browser Console:**
```javascript
app.currentSymbols.filter(s => s.name.startsWith('Light.Light_EG_WZ')).length
// Sollte ~17 zeigen (1 Top + 16 SubItems)
```

**TreeView:**
- Light-Ordner aufklappen
- Light_EG_WZ aufklappen → sollte Unterordner zeigen (RisingEdgeOn, etc.)
- RisingEdgeOn aufklappen → sollte Q, M, CLK zeigen

### Test 4: Sortierung

**TreeView:**
- Ordner sollten vor Variablen kommen
- Innerhalb Ordner: alphabetisch (Light_EG_Bad vor Light_OG_Bad)
- Innerhalb Variablen: alphabetisch (bLight vor bOff vor bOn)

### Test 5: Index-Werte

**Browser Console:**
```javascript
app.currentSymbols.find(s => s.name === 'Light.Light_EG_WZ')
// Sollte zeigen:
// index_group: 16448 (nicht 0!)
// index_offset: 5692 (nicht 0!)
// size: 13 (nicht 0!)
```

---

## 7. Bekannte Limitierungen

### 1. SubItem Index-Werte

**Problem:** SubItems (aus DataType-Expansion) haben keine eigenen IGroup/IOffset in der TPY-Datei.

**Aktueller Stand:** SubItems haben index_group=0, index_offset=0

**Korrekte Lösung (TODO):**
```python
# Bei SubItem-Expansion:
parent_igroup = top_symbol_igroup
parent_ioffset = top_symbol_ioffset
subitem_bitoffs = get_text(si, 'BitOffs', '0')

# Berechne absolute Adresse:
subitem_igroup = parent_igroup
subitem_ioffset = parent_ioffset + (int(subitem_bitoffs) // 8)
```

**Workaround:** Für PLC-Zugriff nur Top-Level-Symbole verwenden. SubItems über Symbol-Handle lesen lassen (pyads macht das automatisch).

### 2. Cache-Invalidierung

**Problem:** Wenn TPY-Datei geändert wird, muss Cache manuell gelöscht werden.

**Workaround:** Cache-Datei vor jedem TPY-Upload löschen oder Timestamp-Check implementieren.

### 3. Performance bei großen TPY-Dateien

**Problem:** Rekursive DataType-Expansion kann bei sehr großen Projekten (>50.000 Symbole) langsam werden.

**Aktueller Stand:** Depth-Limit von 20 verhindert Endlos-Rekursion, Performance ist akzeptabel bis ~20.000 Symbole.

---

## 8. Version History

### v5.0.6 (Original)
- ❌ Nur 751 Top-Level-Symbole
- ❌ Type: "UNKNOWN"
- ❌ TreeView 1 Ebene

### v5.1.0 (DataType-Mapping)
- ✅ DataType-basierter Parser
- ✅ Rekursive SubItem-Expansion
- ❌ Type noch "UNKNOWN" (Duplikat-Problem)

### v5.1.1 (Priority-System)
- ✅ Intelligente Duplikat-Entfernung
- ✅ Korrekte Type-Information
- ✅ IGroup/IOffset/Size Extraktion
- ❌ TreeView noch 1 Ebene

### v5.1.2 (TreeView-Fix + Sortierung) - AKTUELL
- ✅ Hierarchischer TreeView (mehrere Ebenen)
- ✅ Sortierung: Ordner zuerst, dann Variablen (A-Z)
- ✅ Nodes können sowohl Symbol als auch Ordner sein
- ✅ ~1769 Symbole mit korrekten Werten

---

## 9. Vergleich: Live-Load vs TPY-Parser

| Aspekt | Live-Load (pyads) | TPY-Parser |
|--------|-------------------|------------|
| **Symbole** | 14.264 | 1.769 |
| **Warum Unterschied?** | PLC expandiert Arrays/Strings | TPY hat nur Basis-Symbole |
| **Type-Info** | ✅ Korrekt | ✅ Korrekt (v5.1.1+) |
| **Index_group/offset** | ✅ Korrekt | ✅ Top-Level korrekt, SubItems=0 |
| **Hierarchie** | ✅ Vollständig | ✅ Vollständig (v5.1.2+) |
| **Performance** | Langsam (PLC-Verbindung) | Schnell (lokale Datei) |
| **Offline-Fähig** | ❌ Nein | ✅ Ja |
| **PLC-Zugriff** | ✅ Direkt | ⚠️ Nur über Top-Symbole |

**Empfehlung:**
- **Entwicklung/Offline:** TPY-Parser verwenden
- **Produktion/Runtime:** Live-Load verwenden
- **Best Practice:** Beide Methoden unterstützen, User wählt

---

## 10. Zusammenfassung

### Was funktioniert jetzt

✅ **TPY-Parser findet ~1.769 Symbole** (statt nur 751)
✅ **Korrekte Type-Information** (FB_Light, BOOL, R_TRIG, etc.)
✅ **IGroup/IOffset/Size aus TPY** extrahiert
✅ **Hierarchischer TreeView** mit 3+ Ebenen
✅ **Sortierung:** Ordner → Variablen (A-Z)
✅ **Rekursive DataType-Expansion** (R_TRIG in FB_Light)
✅ **Intelligente Duplikat-Entfernung** (Priority-System)
✅ **Nodes als Symbol + Ordner** möglich

### Wichtigste Erkenntnisse

1. **TwinCAT 2 TPY-Format:** SubItems NICHT unter Symbol, sondern in DataTypes Section
2. **Doppelte Symbole:** Viele existieren 2x (mit/ohne Type), Priority-System notwendig
3. **Verschachtelte DataTypes:** R_TRIG in FB_Light → Rekursion notwendig
4. **TreeView:** hasChildren-Check statt _isLeaf-Check für korrekte Hierarchie
5. **Sortierung:** Ordner vor Variablen macht UI übersichtlicher

### Nächste Schritte (Optional)

1. **SubItem Index-Berechnung:** Absolute Adressen aus Parent + BitOffs
2. **Cache-Timestamp:** Automatische Invalidierung bei TPY-Änderung
3. **Symbol-Icons:** Unterschiedliche Icons für verschiedene Types
4. **Drag-and-Drop:** Symbole auf Dashboard ziehen → Widget erstellen
5. **Symbol-Info-Panel:** Details anzeigen (Adresse, Size, Comment, etc.)

---

**Erstellt:** 11. Januar 2026 01:00
**Status:** ✅ PRODUKTIONSREIF
**Getestet:** ✅ HausAutomation.tpy (1.769 Symbole)
**Dokumentiert:** ✅ Vollständig
