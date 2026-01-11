"""
PLC Symbol Parser v1.0.0
Parser für TwinCAT .tpy Dateien

📁 SPEICHERORT: modules/gateway/plc_symbol_parser.py

Features:
- XML-Parser für .tpy Symbol-Dateien
- TreeView-Struktur für hierarchische Symbole
- Filter nach Datentyp
- Suche mit Regex
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Any, Optional
import os


class PLCSymbolParser:
    """
    PLC Symbol Parser v1.0.0

    Parst TwinCAT .tpy Dateien und extrahiert Symbole
    """

    def __init__(self, tpy_file_path: str):
        """
        Args:
            tpy_file_path: Pfad zur .tpy Datei
        """
        self.tpy_file_path = tpy_file_path
        self.symbols = []  # Flat list of all symbols
        self.tree = {}  # Hierarchical tree

    def parse(self) -> bool:
        """
        Parst die .tpy Datei

        Returns:
            True wenn erfolgreich
        """
        if not os.path.exists(self.tpy_file_path):
            print(f"  ✗ Datei nicht gefunden: {self.tpy_file_path}")
            return False

        try:
            tree = ET.parse(self.tpy_file_path)
            root = tree.getroot()

            # ====================================================================
            # TEIL 1: Parse DataTypes (Strukturdefinitionen)
            # ====================================================================
            datatypes = root.findall('.//DataType')
            print(f"  > Gefundene DataType-Elemente: {len(datatypes)}")

            for datatype in datatypes:
                # Hole DataType Name
                name_elem = datatype.find('Name')
                if name_elem is None or name_elem.text is None:
                    continue

                datatype_name = name_elem.text.strip()

                # Parse SubItems (die eigentlichen Variablen)
                subitems = datatype.findall('.//SubItem')

                for subitem in subitems:
                    # Hole SubItem Name
                    subname_elem = subitem.find('Name')
                    if subname_elem is None or subname_elem.text is None:
                        continue

                    subname = subname_elem.text.strip()

                    # Hole Type
                    type_elem = subitem.find('Type')
                    symbol_type = type_elem.text.strip() if type_elem is not None and type_elem.text else 'UNKNOWN'

                    # Hole Comment (optional)
                    comment_elem = subitem.find('Comment')
                    comment = ''
                    if comment_elem is not None and comment_elem.text:
                        comment = comment_elem.text.strip()

                    # Baue Full Name: DataType.SubItem
                    full_name = f"{datatype_name}.{subname}" if datatype_name else subname

                    # Kategorie ermitteln
                    category = 'Variable'
                    if datatype_name.startswith('_fb') or datatype_name.startswith('fb'):
                        category = 'FunctionBlock'
                    elif 'arr' in datatype_name.lower() or 'array' in symbol_type.lower():
                        category = 'Array'

                    self.symbols.append({
                        'name': full_name,
                        'type': symbol_type,
                        'category': category,
                        'parent': datatype_name,
                        'comment': comment,
                        'path': self._get_symbol_path(full_name)
                    })

            print(f"  > DataType-Symbole: {len(self.symbols)}")

            # ====================================================================
            # TEIL 2: Parse Symbol-Tabelle (MAIN.* Programmvariablen)
            # ====================================================================
            # Suche nach <Symbol><Name> Elementen (nicht in DataTypes)
            programs = root.findall('.//Program')

            for program in programs:
                # Suche nach PrgInfo/Symbol
                prginfo = program.find('.//PrgInfo')
                if prginfo is None:
                    continue

                symbols_in_program = prginfo.findall('.//Symbol')

                for symbol_elem in symbols_in_program:
                    name_elem = symbol_elem.find('Name')
                    if name_elem is None or name_elem.text is None:
                        continue

                    symbol_name = name_elem.text.strip()

                    # Versuche Typ zu ermitteln
                    # Meist gibt es keinen Type direkt, sondern nur Name
                    # Der Typ wird zur Laufzeit von der PLC aufgelöst
                    symbol_type = 'UNKNOWN'

                    # Kategorie
                    category = 'ProgramVariable'

                    self.symbols.append({
                        'name': symbol_name,
                        'type': symbol_type,
                        'category': category,
                        'parent': 'MAIN',
                        'comment': '',
                        'path': self._get_symbol_path(symbol_name)
                    })

            print(f"  > Program-Symbole: {len(self.symbols) - len(datatypes) * 10}")  # Grobe Schätzung

            # Baue hierarchische Struktur
            self._build_tree()

            print(f"  ✓ TOTAL: {len(self.symbols)} Symbole geladen")
            return True

        except Exception as e:
            import traceback
            print(f"  ✗ Parser-Fehler: {e}")
            traceback.print_exc()
            return False

    def _get_symbol_path(self, symbol_name: str) -> List[str]:
        """
        Zerlegt Symbol-Namen in Pfad-Komponenten

        Args:
            symbol_name: Z.B. "MAIN.lights.kitchen"

        Returns:
            ['MAIN', 'lights', 'kitchen']
        """
        return symbol_name.split('.')

    def _build_tree(self):
        """Baut hierarchische TreeView-Struktur"""
        self.tree = {}

        for symbol in self.symbols:
            path = symbol['path']
            current = self.tree

            for i, part in enumerate(path):
                if part not in current:
                    # Ist es das letzte Element (Blatt)?
                    is_leaf = (i == len(path) - 1)

                    if is_leaf:
                        # Blatt-Knoten
                        current[part] = {
                            '_symbol': symbol,
                            '_is_leaf': True
                        }
                    else:
                        # Ordner-Knoten
                        current[part] = {
                            '_is_leaf': False,
                            '_children': {}
                        }

                # Navigiere tiefer
                if not current[part]['_is_leaf']:
                    if '_children' not in current[part]:
                        current[part]['_children'] = {}
                    current = current[part]['_children']

    def get_all_symbols(self) -> List[Dict[str, Any]]:
        """
        Gibt alle Symbole als flache Liste zurück

        Returns:
            Liste von Symbol-Dictionaries
        """
        return self.symbols

    def search(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Sucht Symbole mit Regex

        Args:
            query: Suchbegriff (Regex)
            case_sensitive: Case-sensitive suchen?

        Returns:
            Gefilterte Symbol-Liste
        """
        if not query:
            return self.symbols

        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(query, flags)

        results = []
        for symbol in self.symbols:
            if pattern.search(symbol['name']):
                results.append(symbol)

        return results

    def filter_by_type(self, type_filter: str) -> List[Dict[str, Any]]:
        """
        Filtert Symbole nach Datentyp

        Args:
            type_filter: Typ (z.B. 'BOOL', 'INT', 'REAL')

        Returns:
            Gefilterte Symbol-Liste
        """
        if not type_filter:
            return self.symbols

        results = []
        for symbol in self.symbols:
            if type_filter.upper() in symbol['type'].upper():
                results.append(symbol)

        return results

    def get_tree_json(self) -> Dict[str, Any]:
        """
        Gibt TreeView-Struktur als JSON-kompatibles Dictionary zurück

        Returns:
            Tree-Dictionary
        """
        return self._convert_tree_to_json(self.tree)

    def _convert_tree_to_json(self, node: Dict) -> List[Dict[str, Any]]:
        """
        Konvertiert internen Tree zu JSON-Format für Frontend

        Args:
            node: Tree-Knoten

        Returns:
            JSON-kompatible Liste von Knoten
        """
        result = []

        for key, value in node.items():
            if key.startswith('_'):
                continue

            if value['_is_leaf']:
                # Blatt-Knoten
                symbol = value['_symbol']
                result.append({
                    'name': key,
                    'type': 'symbol',
                    'full_path': symbol['name'],
                    'data_type': symbol['type'],
                    'category': symbol['category']
                })
            else:
                # Ordner-Knoten
                children = self._convert_tree_to_json(value.get('_children', {}))
                result.append({
                    'name': key,
                    'type': 'folder',
                    'children': children
                })

        return result


def test_parser():
    """Test-Funktion"""
    import os

    # Suche .tpy Datei
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tpy_file = os.path.join(project_root, 'plc_data', 'TwinCAT_Project.tpy')

    print(f"🔍 Teste PLC Symbol Parser...")
    print(f"   Datei: {tpy_file}")

    parser = PLCSymbolParser(tpy_file)

    if parser.parse():
        print(f"\n📊 Statistik:")
        print(f"   Symbole gesamt: {len(parser.symbols)}")

        # Zeige erste 10 Symbole
        print(f"\n🔢 Erste 10 Symbole:")
        for symbol in parser.symbols[:10]:
            print(f"   - {symbol['name']} ({symbol['type']})")

        # Suche "light"
        results = parser.search('light')
        print(f"\n🔍 Suche 'light': {len(results)} Treffer")
        for symbol in results[:5]:
            print(f"   - {symbol['name']}")

        # TreeView-Struktur
        tree = parser.get_tree_json()
        print(f"\n🌳 Tree-Struktur: {len(tree)} Root-Knoten")
        for node in tree[:3]:
            print(f"   - {node['name']} ({node['type']})")


if __name__ == '__main__':
    test_parser()
