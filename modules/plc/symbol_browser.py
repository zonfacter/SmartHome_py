"""
PLC Symbol Browser v5.1.1
Moderner Symbol-Browser mit DataType-basiertem TPY-Parser

📁 SPEICHERORT: modules/plc/symbol_browser.py

Features v5.1.1:
- ⭐ Direkte Symbol-Abfrage von PLC (pyads 3.5.0)
- ⭐ NEUER DataType-basierter TPY-Parser (TwinCAT 2 & 3 kompatibel)
- ⭐ Rekursive SubItem-Expansion aus DataTypes Section
- ⭐ Intelligente Duplikat-Entfernung (bevorzugt Symbole mit Type)
- ⭐ Korrekte Type-Detection (BOOL, INT, REAL, STRING, etc.)
- ⭐ Hierarchische TreeView-Struktur für das Frontend
- ⭐ Fix: Robustes JSON-Caching gegen NoneType-Pfad-Fehler
- ⭐ Multi-PLC Support via Connection Manager

Änderungen v5.1.1:
- FIX: Intelligente Duplikat-Entfernung bevorzugt Symbole mit Type
- Problem: TPY-Dateien enthalten manche Symbole doppelt (mit/ohne Type)
- Lösung: Priority-System wählt immer die beste Type-Information aus

Änderungen v5.1.0:
- TPY-Parser nutzt jetzt DataType-Map für SubItem-Expansion
- Sollte ~14.000 Symbole finden (statt nur 751 Top-Level)
- Kompatibel mit TwinCAT 2 TPY-Format (DataTypes + Symbols getrennt)
"""

import time
import json
import os
from typing import Dict, List, Any, Optional

# Versuche pyads zu importieren, um ADS-Funktionalität bereitzustellen
try:
    import pyads
    PYADS_AVAILABLE = True
except ImportError:
    PYADS_AVAILABLE = False


class PLCSymbol:
    """Repräsentiert ein einzelnes PLC-Symbol mit allen relevanten Metadaten."""
    def __init__(self, name: str, symbol_type: str = None, index_group: int = 0,
                 index_offset: int = 0, size: int = 0, comment: str = "",
                 type: str = None, **kwargs):
        """
        Args:
            name: Symbol-Name
            symbol_type: Typ des Symbols (bevorzugt)
            type: Alias für symbol_type (für JSON-Kompatibilität)
            **kwargs: Zusätzliche Parameter werden ignoriert (für Zukunftssicherheit)
        """
        self.name = name
        # Accept both 'symbol_type' and 'type' for JSON compatibility
        self.symbol_type = symbol_type or type or "UNKNOWN"
        self.index_group = index_group
        self.index_offset = index_offset
        self.size = size
        self.comment = comment

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert das Symbol-Objekt in ein Dictionary für JSON-Export/API."""
        return {
            'name': self.name,
            'type': self.symbol_type,
            'index_group': self.index_group,
            'index_offset': self.index_offset,
            'size': self.size,
            'comment': self.comment
        }


class PLCSymbolBrowser:
    """Verwaltet das Auslesen, Caching und die hierarchische Darstellung von PLC-Symbolen."""
    def __init__(self, connection_manager=None):
        """
        Initialisiert den Browser und stellt robuste Pfade sicher.
        Fix: Verwendet os.path.abspath, um NoneType-Fehler bei os.path.join zu vermeiden.
        """
        self.conn_mgr = connection_manager
        self.symbol_cache = {}
        self.cache_timestamp = {}

        # Pfad-Initialisierung (Absoluter Pfad-Fix für v5.0.5)
        base_path = os.path.abspath(os.getcwd())
        self.cache_dir = os.path.join(base_path, 'config', 'cache')

        # Sicherstellen, dass das Cache-Verzeichnis existiert
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

        self.cache_file = os.path.join(self.cache_dir, "symbol_cache.json")

    def get_symbols(self, connection_id: str, force_refresh: bool = False) -> List[Dict]:
        """
        Hauptmethode zum Abrufen der Symbole.
        Prüft erst RAM-Cache, dann Disk-Cache, dann Live-Abfrage.
        """
        if not PYADS_AVAILABLE:
            print("  ⚠️ pyads nicht verfügbar.")
            return []

        # 1. RAM-Cache Prüfung (TTL 300 Sekunden)
        if not force_refresh and connection_id in self.symbol_cache:
            if time.time() - self.cache_timestamp.get(connection_id, 0) < 300:
                return [s.to_dict() for s in self.symbol_cache[connection_id]]

        # 2. Versuche Disk-Cache zu laden (gibt gecachte Symbole zurück)
        print(f"  ℹ️ Lade Symbole aus Cache für {connection_id}...")
        self.load_cache_from_file(self.cache_file)
        cached_data = self.symbol_cache.get(connection_id, [])

        # Wenn Cache-Daten vorhanden sind, gebe sie zurück
        if cached_data:
            print(f"  ✓ {len(cached_data)} Symbole aus Cache geladen.")
            return [s.to_dict() for s in cached_data]

        # 3. Kein Cache - versuche ConnectionManager
        if self.conn_mgr:
            plc_conn = self.conn_mgr.get_connection(connection_id)
            if plc_conn and plc_conn.is_connected():
                print(f"  ℹ️ Live-Abfrage von PLC {connection_id}...")
                return self._fetch_from_plc(plc_conn, connection_id)

        # 4. Keine Verbindung und kein Cache
        print(f"  ⚠️ Keine Symbole verfügbar für {connection_id}. Bitte TPY hochladen oder PLC verbinden.")
        return []

    def _fetch_from_plc(self, plc_conn, connection_id):
        """Führt die eigentliche ADS-Abfrage durch (Optimiert für pyads 3.5.0)."""
        try:
            # Zugriff auf den internen pyads-Client der Verbindung
            client = plc_conn.client

            # Lese Device Info zur Verifizierung der Verbindung
            try:
                name, version = client.read_device_info()
                print(f"  ℹ️ Verbunden mit: {name} (v{version})")
            except Exception as e:
                print(f"  ⚠️ Device Info konnte nicht gelesen werden: {e}")

            # Alle Symbole direkt über ADS auslesen (v3.5.0 kompatibel)
            raw_symbols = client.get_all_symbols()
            symbols_list = []

            for s in raw_symbols:
                # Mapping der pyads SAdsSymbolEntry Objekte auf unsere PLCSymbol Klasse
                plc_symbol = PLCSymbol(
                    name=s.name,
                    symbol_type=str(s.symbol_type),
                    index_group=s.index_group,
                    index_offset=s.index_offset,
                    size=s.size,
                    comment=getattr(s, 'comment', '')
                )
                symbols_list.append(plc_symbol)

            # RAM-Cache aktualisieren
            self.symbol_cache[connection_id] = symbols_list
            self.cache_timestamp[connection_id] = time.time()

            # Disk-Cache für Offline-Betrieb sichern
            self.save_cache_to_file(self.cache_file, connection_id)

            print(f"  ✓ {len(symbols_list)} Symbole von {connection_id} geladen.")
            return [s.to_dict() for s in symbols_list]

        except Exception as e:
            print(f"  ✗ ADS Error (3.5.0) bei Symbol-Abfrage: {e}")
            return []

    def get_tree(self, connection_id: str) -> Dict[str, Any]:
        """Konvertiert die flache Symbolliste in eine Baumstruktur für die UI."""
        symbols = self.get_symbols(connection_id)
        tree = {'name': 'PLC_ROOT', 'children': [], 'type': 'folder'}
        for s in symbols:
            self._add_to_tree(tree, s)
        return tree

    def _add_to_tree(self, tree, symbol):
        """Hilfsmethode: Splittet Symbolnamen und ordnet sie hierarchisch in den Baum ein."""
        parts = symbol['name'].split('.')
        current = tree
        for i, part in enumerate(parts):
            if 'children' not in current:
                current['children'] = []

            # Prüfe, ob dieser Teilpfad bereits existiert
            child = next((c for c in current['children'] if c['name'] == part), None)

            if not child:
                is_leaf = (i == len(parts) - 1)
                child = {
                    'name': part,
                    'full_name': '.'.join(parts[:i + 1]),
                    'type': symbol['type'] if is_leaf else 'STRUCT',
                    'is_leaf': is_leaf
                }

                if is_leaf:
                    # Metadaten nur an Blättern (Variablen) anhängen
                    child.update({
                        'size': symbol['size'],
                        'comment': symbol['comment'],
                        'index_group': symbol['index_group'],
                        'index_offset': symbol['index_offset']
                    })
                else:
                    # Strukturelemente erhalten eine Liste für Kinder
                    child['children'] = []

                current['children'].append(child)
            current = child

    def save_cache_to_file(self, file_path, connection_id):
        """Speichert die Symbolliste einer Verbindung als JSON-Datei."""
        try:
            # Sicherstellen, dass Pfad ein String ist (v5.0.5 Fix)
            f_path = str(file_path)
            data = {
                'connection_id': connection_id,
                'timestamp': self.cache_timestamp.get(connection_id),
                'symbols': [s.to_dict() for s in self.symbol_cache[connection_id]]
            }
            with open(f_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  ⚠️ Fehler beim Speichern des Symbol-Caches: {e}")

    def load_cache_from_file(self, file_path):
        """Lädt eine gespeicherte Symbolliste von der Disk."""
        # Prüfen, ob die Datei existiert und Pfad valide ist
        if not file_path or not os.path.exists(file_path):
            return False

        try:
            with open(str(file_path), 'r', encoding='utf-8') as f:
                data = json.load(f)
                cid = data.get('connection_id')
                if cid:
                    # Dictionary-Daten zurück in PLCSymbol Objekte mappen
                    self.symbol_cache[cid] = [PLCSymbol(**s) for s in data.get('symbols', [])]
                    self.cache_timestamp[cid] = data.get('timestamp', time.time())
            return True
        except Exception as e:
            print(f"  ⚠️ Fehler beim Laden des Symbol-Caches: {e}")
            return False


    def load_symbols_from_tpy(self, tpy_filepath: str, connection_id: str = 'plc_001') -> int:
        """
        Lädt Symbole aus einer TPY-Datei und speichert sie im Cache.

        Args:
            tpy_filepath: Absoluter Pfad zur TPY-Datei
            connection_id: ID der Verbindung (Standard: 'plc_001')

        Returns:
            Anzahl der geladenen Symbole
        """
        try:
            import xml.etree.ElementTree as ET

            # Parse TPY-Datei
            tree = ET.parse(tpy_filepath)
            root = tree.getroot()

            print(f"  📂 Root-Element: {root.tag}")

            # Suche ALLE Symbol-Elemente (funktioniert für TwinCAT 2 & 3)
            all_symbols = root.findall('.//Symbol')
            print(f"  🔍 Gefunden: {len(all_symbols)} <Symbol> Elemente (Top-Level)")

            # SCHRITT 1: Baue DataType-Map (für TwinCAT 2 TPY Format)
            # DataTypes enthalten die SubItem-Definitionen für Strukturen/FBs
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

            # SCHRITT 2: Hilfsfunktion zum Text-Extrahieren
            def get_text(element, tag_name, default=''):
                """Extrahiert Text aus einem Child-Element"""
                elem = element.find(tag_name)
                if elem is not None and elem.text:
                    return elem.text.strip()
                return element.get(tag_name) or default

            # SCHRITT 3: Rekursive DataType-Expansion (wie convert_tpy_csv.py)
            def expand_datatype_subitems(datatype_name, parent_name, depth=0):
                """Expandiert SubItems aus einem DataType rekursiv

                Beispiel:
                - FB_Light (DataType mit SubItems)
                  - bOn (BOOL)
                  - bOff (BOOL)
                  - RisingEdgeOn (R_TRIG - ist auch ein DataType!)
                    - Q (BOOL)
                    - M (BOOL)
                """
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

            # SCHRITT 4: Sammle alle Symbole + ihre DataType-expandierten SubItems
            all_symbol_tuples = []

            for sym in all_symbols:
                # Top-Symbol Name
                top_name = get_text(sym, 'Name')
                if not top_name or top_name.isspace():
                    continue

                # Top-Symbol Type (kann leer sein in TwinCAT 2!)
                top_type = get_text(sym, 'Type', 'UNKNOWN')

                # Füge Top-Symbol hinzu
                all_symbol_tuples.append((top_name, sym, top_type))

                # Wenn das Symbol einen Typ hat, der in DataTypes definiert ist,
                # expandiere dessen SubItems rekursiv
                if top_type and top_type != 'UNKNOWN' and top_type in datatype_by_name:
                    sub_symbols = expand_datatype_subitems(top_type, top_name)
                    all_symbol_tuples.extend(sub_symbols)

                # FALLBACK: Falls Symbol direkte SubItems hat (TwinCAT 3 Format)
                # werden diese auch erfasst
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

            # Entferne Duplikate (INTELLIGENTE Duplikat-Entfernung)
            # Problem: Manche Symbole existieren mehrfach in TPY (mit und ohne Type)
            # Lösung: Bevorzuge Symbole mit Type gegenüber Symbolen ohne Type
            symbol_map = {}  # name -> (element, type, priority)

            for symbol_tuple in all_symbol_tuples:
                # Tuple kann 2 oder 3 Elemente haben:
                # - (name, element) für alte Symbole ohne Type
                # - (name, element, type) für neue DataType-expandierte Symbole
                if len(symbol_tuple) == 3:
                    full_name, sym_elem, sym_type = symbol_tuple
                else:
                    full_name, sym_elem = symbol_tuple
                    sym_type = None

                if not full_name:
                    continue

                # Bestimme Priorität (höher = besser):
                # 1. Symbole mit echtem Type (nicht UNKNOWN, nicht None)
                # 2. Symbole ohne Type
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

            # Konvertiere XML-Symbole zu PLCSymbol-Objekten
            symbols_list = []

            for full_name, sym_elem, extracted_type in unique_symbols:
                # Name ist bereits vollständig (z.B. "MAIN.fbController.nValue")
                name = full_name

                # Überspringe Symbole mit leerem Namen
                if not name or name.isspace():
                    continue

                # Type: Verwende extracted_type wenn vorhanden, sonst aus XML extrahieren
                if extracted_type and extracted_type != 'UNKNOWN':
                    sym_type = extracted_type
                else:
                    type_elem = sym_elem.find('Type')
                    if type_elem is not None and type_elem.text:
                        sym_type = type_elem.text.strip()
                    else:
                        sym_type = sym_elem.get('Type') or sym_elem.get('type') or 'UNKNOWN'

                # Comment extrahieren (optional)
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
                    name=name,  # Vollständiger Pfad inkl. Parent-Namen
                    symbol_type=sym_type,
                    index_group=index_group,
                    index_offset=index_offset,
                    size=size,
                    comment=comment
                )
                symbols_list.append(plc_symbol)

            print(f"  💾 {len(symbols_list)} Symbole konvertiert zu PLCSymbol-Objekten")

            # Speichere im RAM-Cache
            self.symbol_cache[connection_id] = symbols_list
            self.cache_timestamp[connection_id] = time.time()

            # Speichere im Disk-Cache für Offline-Betrieb
            self.save_cache_to_file(self.cache_file, connection_id)

            print(f"  ✅ ERFOLG: {len(symbols_list)} Symbole aus TPY geladen und im Cache gespeichert!")
            return len(symbols_list)

        except Exception as e:
            print(f"  ✗ Fehler beim Laden der TPY-Symbole: {e}")
            import traceback
            traceback.print_exc()
            return 0


# Factory-Funktion für web_manager.py
def get_symbol_browser(connection_manager=None):
    """
    Factory-Funktion zum Erstellen eines PLCSymbolBrowser-Objekts.
    Wird von web_manager.py verwendet.
    """
    return PLCSymbolBrowser(connection_manager)