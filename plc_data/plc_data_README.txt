# PLC Data Verzeichnis

Dieses Verzeichnis enthält PLC-spezifische Dateien.

## 📁 Inhalt

### TwinCAT_Project.tpy
Die TPY-Datei (TwinCAT Project Export) enthält alle PLC-Symbole.

**Wo bekomme ich die TPY-Datei?**
1. Öffne TwinCAT XAE (Visual Studio)
2. Rechtsklick auf dein PLC-Projekt
3. "Export TPY..." auswählen
4. Speichere als `TwinCAT_Project.tpy`
5. Kopiere die Datei hierher

## 🔧 TPY-Import

### Automatischer Import (einfach):
```bash
python import_tpy.py
```

Das Script:
- Sucht automatisch nach TPY-Dateien
- Importiert alle Symbole
- Erstellt Symbol-Cache
- Zeigt erste 10 Symbole an

### Manueller Import (in deinem Code):
```python
from modules.core.symbol_manager import SymbolManager

symbol_mgr = SymbolManager()
symbol_mgr.initialize(app_context)
symbol_mgr.import_from_tpy("plc_data/TwinCAT_Project.tpy")
```

## 📊 Was wird importiert?

Die TPY-Datei enthält:
- Alle MAIN-Variablen
- GVL (Global Variable Lists)
- Strukturen (STRUCT)
- Datentypen mit SubItems

Beispiel:
```
MAIN.bLight1          (BOOL)
MAIN.rTemperature     (REAL)
GVL_System.bEmergency (BOOL)
ST_Weather.fTemp      (REAL)
ST_Weather.fHumidity  (REAL)
```

## 🗄️ Symbol-Cache

Nach dem Import wird ein Cache erstellt:
**Speicherort:** `Documents/TwinCAT_SmartHome/symbol_cache.json`

**Vorteile:**
- ✅ Schneller Start (kein erneuter TPY-Import)
- ✅ Symbol-Suche in GUI
- ✅ Auto-Complete bei Card-Erstellung

## 🔄 Cache aktualisieren

Wenn sich deine PLC-Symbole ändern:

1. Neue TPY-Datei exportieren
2. Alte TPY-Datei ersetzen
3. Import erneut ausführen:
   ```bash
   python import_tpy.py
   ```

## 📝 Beispiel-Struktur

```
plc_data/
├── TwinCAT_Project.tpy       ← Deine TPY-Datei
├── TwinCAT_Project_v1.tpy    ← Backup (optional)
├── TwinCAT_Project_v2.tpy    ← Backup (optional)
└── README.txt                ← Diese Datei
```

## ⚠️ Wichtig

- TPY-Datei sollte aktuell sein
- Bei PLC-Änderungen: Neu exportieren!
- Cache wird automatisch in Documents/ gespeichert
- TPY-Datei NICHT ins Git committen (zu groß, projekt-spezifisch)

## 🆘 Probleme?

**TPY-Datei wird nicht gefunden:**
- Prüfe Dateinamen: Muss auf `.tpy` enden
- Prüfe Speicherort: `plc_data/` Verzeichnis
- Prüfe Dateigröße: TPY sollte > 0 KB sein

**Import schlägt fehl:**
- Prüfe TPY-Format (muss XML sein)
- Prüfe TwinCAT-Version (v2/v3)
- Prüfe Datei-Encoding (UTF-8)

**Keine Symbole gefunden:**
- Exportiere TPY neu aus TwinCAT
- Stelle sicher, dass PLC-Projekt Variablen hat
- Prüfe Console-Ausgabe beim Import
