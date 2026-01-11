"""
Symbol Manager Module
Version: 2.0.5
Verwaltet PLC-Symbole mit Cache und Suche (v1.2 kompatibel!)
"""

from module_manager import BaseModule
from typing import List, Dict, Any, Optional
import json
import os
import xml.etree.ElementTree as ET


class SymbolManager(BaseModule):
    """
    Symbol-Manager
    
    Funktionen:
    - Symbol-Cache (JSON/SQLite)
    - TPY-Import
    - Symbol-Suche
    - Auto-Update
    """
    
    NAME = "symbol_manager"
    VERSION = "2.0.5"
    DESCRIPTION = "PLC Symbol-Cache & Suche"
    AUTHOR = "TwinCAT Team"
    
    def __init__(self):
        super().__init__()
        self.symbols = []
        self.symbol_dict = {}  # name -> symbol
        self.cache_file = None
        self.use_database = False
    
    def initialize(self, app_context: Any):
        """Initialisiert Symbol-Manager"""
        super().initialize(app_context)
        
        # Hole Config-Dir vom Config-Manager
        config_module = app_context.module_manager.get_module('config_manager')
        if config_module:
            config_dir = config_module.config_dir
            self.cache_file = os.path.join(config_dir, "symbol_cache.json")
        else:
            self.cache_file = "symbol_cache.json"
        
        # Lade Cache
        self.load_cache()
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
        print(f"  ✓ Symbole geladen: {len(self.symbols)}")
    
    def load_cache(self) -> bool:
        """Lädt Symbol-Cache"""
        # FIX: Prüfe ob cache_file gesetzt ist
        if not self.cache_file:
            print(f"  ⚠️  Konnte symbol_cache.json nicht laden: cache_file nicht initialisiert")
            return False

        if not os.path.exists(self.cache_file):
            print(f"  ℹ️  Kein Symbol-Cache gefunden")
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Prüfe Format: v1.2 (Dict) oder v2.0 (List)
            symbols_data = data.get('symbols', {})
            
            if isinstance(symbols_data, dict):
                # v1.2 Format: Dict mit name -> data
                print(f"  ℹ️  Lade v1.2 Format (Dictionary)")
                self.symbols = []
                for name, symbol_data in symbols_data.items():
                    # Konvertiere zu List-Format
                    if isinstance(symbol_data, dict):
                        symbol_dict = symbol_data.copy()
                        symbol_dict['name'] = name  # Name hinzufügen falls nicht vorhanden
                    else:
                        # Falls symbol_data nur ein String/Type ist
                        symbol_dict = {'name': name, 'type': str(symbol_data)}
                    self.symbols.append(symbol_dict)
                
            elif isinstance(symbols_data, list):
                # v2.0 Format: List
                print(f"  ℹ️  Lade v2.0 Format (List)")
                self.symbols = []
                for symbol in symbols_data:
                    if isinstance(symbol, dict):
                        self.symbols.append(symbol)
                    # Skip Strings
            
            # Erstelle Dict für schnelle Suche
            self.symbol_dict = {s.get('name', ''): s for s in self.symbols if isinstance(s, dict) and 'name' in s}
            
            print(f"  ✓ Symbol-Cache geladen: {len(self.symbols)} Symbole")
            return True
            
        except Exception as e:
            print(f"  ✗ Fehler beim Laden: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_cache(self) -> bool:
        """Speichert Symbol-Cache"""
        try:
            data = {
                'version': '1.0',
                'symbols': self.symbols,
                'count': len(self.symbols)
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            print(f"  ✓ Symbol-Cache gespeichert: {len(self.symbols)} Symbole")
            return True
            
        except Exception as e:
            print(f"  ✗ Speichern fehlgeschlagen: {e}")
            return False
    
    def import_from_tpy(self, filepath: str) -> bool:
        """Importiert Symbole aus TPY-Datei"""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            symbols = []
            
            # Parse alle DataTypes
            for datatype in root.findall('.//DataType'):
                name = datatype.get('Name', '')
                
                # Parse SubItems
                for subitem in datatype.findall('.//SubItem'):
                    subname = subitem.get('Name', '')
                    subtype = subitem.find('Type').text if subitem.find('Type') is not None else 'UNKNOWN'
                    
                    full_name = f"{name}.{subname}" if name else subname
                    
                    symbols.append({
                        'name': full_name,
                        'type': subtype,
                        'parent': name
                    })
            
            self.symbols = symbols
            self.symbol_dict = {s['name']: s for s in symbols}
            
            # Speichere Cache
            self.save_cache()
            
            print(f"  ✓ TPY importiert: {len(symbols)} Symbole")
            return True
            
        except Exception as e:
            print(f"  ✗ TPY-Import Fehler: {e}")
            return False
    
    def search_symbols(self, query: str, limit: int = 100) -> List[Dict]:
        """
        Sucht Symbole
        
        Args:
            query: Suchbegriff
            limit: Maximale Ergebnisse
        
        Returns:
            Liste von Symbolen
        """
        query_lower = query.lower()
        results = []
        
        for symbol in self.symbols:
            # Skip wenn symbol kein Dict ist
            if not isinstance(symbol, dict):
                print(f"  ⚠️  Überspringe ungültiges Symbol: {type(symbol)}")
                continue
            
            # Prüfe ob 'name' existiert
            if 'name' not in symbol:
                continue
            
            if query_lower in symbol['name'].lower():
                results.append(symbol)
                
                if len(results) >= limit:
                    break
        
        return results
    
    def get_symbol(self, name: str) -> Optional[Dict]:
        """Holt Symbol nach Name"""
        return self.symbol_dict.get(name)
    
    def get_symbols_by_type(self, plc_type: str) -> List[Dict]:
        """Holt alle Symbole eines Typs"""
        return [s for s in self.symbols if s.get('type') == plc_type]
    
    def get_bool_symbols(self) -> List[Dict]:
        """Holt alle BOOL-Symbole"""
        return self.get_symbols_by_type('BOOL')
    
    def get_real_symbols(self) -> List[Dict]:
        """Holt alle REAL-Symbole"""
        return self.get_symbols_by_type('REAL')
    
    def get_int_symbols(self) -> List[Dict]:
        """Holt alle INT-Symbole"""
        return self.get_symbols_by_type('INT')
    
    def get_all_symbols(self) -> List[Dict]:
        """Gibt alle Symbole zurück"""
        return self.symbols
    
    def get_symbol_count(self) -> int:
        """Gibt Anzahl der Symbole zurück"""
        return len(self.symbols)
    
    def clear_cache(self):
        """Leert Cache"""
        self.symbols = []
        self.symbol_dict = {}
    
    def download_from_plc(self, plc_connection) -> bool:
        """
        Lädt alle Symbole von PLC und speichert sie
        
        Args:
            plc_connection: PLC Communication Modul mit .plc pyads.Connection
        
        Returns:
            True bei Erfolg
        """
        if not plc_connection or not plc_connection.connected:
            print("  ❌ PLC nicht verbunden!")
            return False
        
        try:
            print(f"\n📥 Lade Symbole von PLC...")
            print(f"  ℹ️  Dies kann einige Sekunden dauern...")
            
            # Hole pyads Connection
            plc = plc_connection.plc
            
            # Hole alle Symbole
            symbols_info = plc.read_list_by_name('.SymbolTable')
            
            print(f"  ✓ {len(symbols_info)} Symbole geladen")
            
            # Konvertiere zu unserem Format
            self.symbols = []
            for info in symbols_info:
                symbol = {
                    'name': info.name,
                    'type': info.type,
                    'size': info.size if hasattr(info, 'size') else 0,
                    'comment': info.comment if hasattr(info, 'comment') else ''
                }
                self.symbols.append(symbol)
            
            # Update Dict
            self.symbol_dict = {s['name']: s for s in self.symbols}
            
            # Speichere Cache
            self.save_cache()
            
            print(f"  ✓ Symbol-Cache gespeichert: {len(self.symbols)} Symbole")
            print(f"  ✓ Cache-Datei: {self.cache_file}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Fehler beim Laden: {e}")
            return False
    
    def shutdown(self):
        """Speichert beim Beenden"""
        self.save_cache()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        SymbolManager.NAME,
        SymbolManager.VERSION,
        SymbolManager.DESCRIPTION,
        SymbolManager,
        author=SymbolManager.AUTHOR
    )
