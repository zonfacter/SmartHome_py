# Test-Plan: TPY-Parser v5.1.0 mit DataType-Mapping

**Datum:** 10. Januar 2026
**Version:** symbol_browser.py v5.1.0
**Ziel:** Verifizieren dass TPY-Parser ~14.000 Symbole findet (statt nur 751)

---

## Vorbereitung

### 1. Server stoppen

```bash
# STRG+C im Terminal drücken
```

### 2. Server neu starten

```bash
python main.py
```

**Erwarteter Output beim Start:**
```
🚀 SmartHome HMI Server gestartet auf http://127.0.0.1:5000
```

---

## Test 1: TPY-Upload mit DataType-Expansion

### Schritte:

1. Browser öffnen: `http://127.0.0.1:5000`
2. Zu Setup-Seite navigieren
3. TPY-Datei hochladen: `plc_data/TwinCAT_Project.tpy`

### Erwartete Server-Logs:

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

### ❌ Fehler-Fall (alte v5.0.6):
```
🔍 Gefunden: 952 <Symbol> Elemente (Top-Level)
🔍 Rekursiv gefunden: 952 Symbole (inkl. SubItems)  ← NUR Top-Level!
✅ 751 eindeutige Symbole extrahiert  ← FALSCH
```

### ✅ Erfolg-Kriterium:
- Mindestens **10.000 Symbole** im Server-Log
- "DataType-Map erstellt: 237 Typen" sichtbar
- Keine Fehlermeldungen

---

## Test 2: TreeView Hierarchie

### Schritte:

1. Setup-Seite sollte automatisch TreeView laden
2. Suche nach "Light" im Search-Input
3. Überprüfe hierarchische Struktur

### Erwartete TreeView-Struktur:

```
📁 Light_EG_WZ (FB_Light)
  ├─ 🔵 bOn (BOOL)
  ├─ 🔵 bOff (BOOL)
  ├─ 🔵 bLight (BOOL)
  └─ 📁 RisingEdgeOn (R_TRIG)
      ├─ 🔵 Q (BOOL)
      └─ 🔵 M (BOOL)

📁 Light_EG_Bad (FB_Light)
  ├─ 🔵 bOn (BOOL)
  ├─ ...
```

### ✅ Erfolg-Kriterien:
- Ordner-Icons (📁) bei strukturierten Typen
- Chevron-Icons zum Aufklappen
- Verschachtelte Member sichtbar (z.B. "RisingEdgeOn.Q")
- Mindestens **2-3 Hierarchie-Ebenen** bei FB-Strukturen

### ❌ Fehler-Fall (alte v5.0.6):
```
🔵 Light_EG_WZ (FB_Light)  ← Flach, keine Kinder
🔵 Light_EG_Bad (FB_Light)
```

---

## Test 3: Symbol-Suche

### Schritte:

1. Im Search-Input "RisingEdge" eingeben
2. Warte 300ms (Debounce)
3. TreeView sollte filtern

### Erwartetes Ergebnis:

TreeView zeigt nur Symbole mit "RisingEdge" im Namen:
```
📁 Light_EG_WZ
  └─ 📁 RisingEdgeOn
      ├─ 🔵 Q
      └─ 🔵 M

📁 Light_EG_Bad
  └─ 📁 RisingEdgeOn
      ├─ 🔵 Q
      └─ 🔵 M
```

### ✅ Erfolg-Kriterien:
- Filter funktioniert bei ~14.000 Symbolen
- Hierarchie bleibt erhalten
- Nur passende Symbole sichtbar
- Debounce funktioniert (300ms Verzögerung)

---

## Test 4: Vergleich Live-Load vs TPY-Parser

### Schritte:

1. **Live-Load testen:**
   - PLC verbinden
   - "Load Symbols from PLC" Button klicken
   - Server-Log überprüfen

2. **TPY-Parser testen:**
   - TPY-Datei hochladen
   - Server-Log überprüfen

### Erwarteter Vergleich:

| Methode | Symbole | Server-Log |
|---------|---------|------------|
| **Live-Load** (pyads) | 14.264 | `✓ 14264 Symbole von plc_001 geladen` |
| **TPY-Parser** (v5.1.0) | ~14.000 | `✅ ERFOLG: ~14000 Symbole aus TPY geladen` |
| ~~TPY-Parser~~ (v5.0.6 alt) | 751 | `✅ ERFOLG: 751 Symbole aus TPY geladen` ❌ |

### ✅ Erfolg-Kriterium:
- Beide Methoden liefern **ähnliche Symbol-Anzahl** (±10%)
- Beide zeigen **hierarchische Struktur** im TreeView

---

## Test 5: DataType-Verschachtelung

### Ziel: Verifizieren dass verschachtelte DataTypes korrekt expandiert werden

### Schritte:

1. Im TreeView nach einem Symbol mit verschachtelten FB-Members suchen
2. Beispiel: "Light_EG_WZ.RisingEdgeOn.Q"
3. Überprüfe dass alle Hierarchie-Ebenen vorhanden sind

### Erwartete Hierarchie:

```
Light_EG_WZ (Top-Symbol, Type: FB_Light)
├─ Light_EG_WZ.bOn (SubItem von FB_Light, Type: BOOL)
├─ Light_EG_WZ.RisingEdgeOn (SubItem von FB_Light, Type: R_TRIG)
│   ├─ Light_EG_WZ.RisingEdgeOn.Q (SubItem von R_TRIG, Type: BOOL)
│   └─ Light_EG_WZ.RisingEdgeOn.M (SubItem von R_TRIG, Type: BOOL)
```

**Erklärung:**
1. `FB_Light` ist ein DataType mit SubItem "RisingEdgeOn"
2. "RisingEdgeOn" hat Type `R_TRIG`
3. `R_TRIG` ist auch ein DataType mit SubItems "Q" und "M"
4. Parser muss **rekursiv** beide DataTypes expandieren

### ✅ Erfolg-Kriterium:
- Mindestens **3 Hierarchie-Ebenen** sichtbar
- Vollständige Pfade (z.B. "Light_EG_WZ.RisingEdgeOn.Q")
- Type-Information korrekt (BOOL, R_TRIG, etc.)

---

## Test 6: Cache-Persistenz

### Ziel: Verifizieren dass Symbol-Cache gespeichert wird

### Schritte:

1. TPY-Datei hochladen
2. Server-Log überprüfen: `💾 ~14000 Symbole konvertiert zu PLCSymbol-Objekten`
3. Cache-Datei überprüfen: `config/cache/symbol_cache.json`
4. Server neu starten (STRG+C, dann `python main.py`)
5. Setup-Seite öffnen

### Erwartetes Verhalten:

**Beim ersten Upload:**
```
📂 Root-Element: PlcProjectInfo
🔍 Gefunden: 952 <Symbol> Elemente
📚 DataType-Map erstellt: 237 Typen
✅ ~14000 Symbole aus TPY geladen
```

**Nach Server-Neustart (Cache-Load):**
```
ℹ️ Lade Symbole aus Cache für plc_001...
✓ ~14000 Symbole aus Cache geladen.
```

### ✅ Erfolg-Kriterien:
- Cache-Datei existiert: `config/cache/symbol_cache.json`
- Cache enthält ~14.000 Symbole
- Nach Neustart: Symbole aus Cache geladen (schneller!)
- TreeView zeigt sofort alle Symbole

---

## Test 7: Type-Filter

### Schritte:

1. Setup-Seite öffnen
2. Type-Filter auf "BOOL" setzen
3. TreeView überprüfen

### Erwartetes Ergebnis:

TreeView zeigt nur Symbole vom Typ BOOL:
```
🔵 Light_EG_WZ.bOn (BOOL)
🔵 Light_EG_WZ.bOff (BOOL)
🔵 Light_EG_WZ.bLight (BOOL)
🔵 Light_EG_WZ.RisingEdgeOn.Q (BOOL)
🔵 Light_EG_WZ.RisingEdgeOn.M (BOOL)
```

**Nicht sichtbar:**
```
❌ Light_EG_WZ (FB_Light)  <- Typ ist FB_Light, nicht BOOL
❌ Light_EG_WZ.RisingEdgeOn (R_TRIG)  <- Typ ist R_TRIG, nicht BOOL
```

### ✅ Erfolg-Kriterium:
- Nur BOOL-Symbole sichtbar
- Filter funktioniert bei ~14.000 Symbolen
- Type-Information korrekt

---

## Fehler-Diagnose

### Problem 1: Immer noch nur 751 Symbole

**Mögliche Ursachen:**
1. Server nicht neu gestartet
2. Alte TPY-Cache-Datei wird geladen
3. Code-Änderungen nicht übernommen

**Lösung:**
```bash
# 1. Server stoppen (STRG+C)
# 2. Cache löschen
del config\cache\symbol_cache.json
# 3. Server neu starten
python main.py
# 4. TPY neu hochladen
```

### Problem 2: Server-Fehler beim TPY-Upload

**Mögliche Fehler:**
```python
AttributeError: 'NoneType' object has no attribute 'text'
KeyError: 'Type'
RecursionError: maximum recursion depth exceeded
```

**Lösung:**
- Überprüfe `symbol_browser.py` Lines 261-359
- Stelle sicher dass `get_text()` Funktion existiert
- Depth-Limit sollte auf 20 gesetzt sein

### Problem 3: TreeView zeigt keine Hierarchie

**Symptom:** Alle Symbole flach dargestellt

**Ursache:** Symbol-Namen ohne "." Trenner

**Lösung:**
- Überprüfe Symbol-Namen im Server-Log
- Sollten aussehen wie: "Light_EG_WZ.bOn"
- NICHT wie: "Light_EG_WZ" oder ".bOn"

---

## Erfolgs-Checkliste

### ✅ TPY-Parser v5.1.0 funktioniert wenn:

- [ ] Server-Log zeigt: "📚 DataType-Map erstellt: 237 Typen"
- [ ] Server-Log zeigt: "~14000 Symbole (inkl. DataType-SubItems)"
- [ ] TreeView zeigt mindestens 10.000 Nodes
- [ ] Hierarchische Struktur sichtbar (Ordner mit Chevrons)
- [ ] Verschachtelte FB-Member sichtbar (z.B. "Light.RisingEdge.Q")
- [ ] Symbol-Suche funktioniert bei ~14.000 Symbolen
- [ ] Type-Filter funktioniert
- [ ] Cache wird gespeichert und geladen
- [ ] Live-Load und TPY-Parser liefern ähnliche Symbol-Anzahl

---

## Nächste Schritte nach erfolgreichem Test

1. ✅ **Test-Ergebnisse dokumentieren**
2. ✅ **FINAL_SUMMARY.md aktualisieren**
3. ✅ **System in Produktion nehmen**
4. ✅ **Widget-System weiter entwickeln**
5. ✅ **Visualisierung erweitern**

---

**Erstellt:** 2026-01-10
**Version:** v5.1.0
**Status:** Bereit zum Testen
