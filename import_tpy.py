"""
TPY Import Utility
Importiert TwinCAT TPY-Dateien in den Symbol-Cache
"""

import os
import sys


def import_tpy():
    """Interaktiver TPY-Import"""
    print("=" * 60)
    print("TwinCAT TPY-Import Tool")
    print("=" * 60)
    
    # Finde TPY-Dateien
    print("\nSuche TPY-Dateien...")
    tpy_files = []
    
    # Suche in plc_data/
    if os.path.exists('plc_data'):
        for file in os.listdir('plc_data'):
            if file.endswith('.tpy'):
                tpy_files.append(os.path.join('plc_data', file))
    
    # Suche im aktuellen Verzeichnis
    for file in os.listdir('.'):
        if file.endswith('.tpy'):
            tpy_files.append(file)
    
    if not tpy_files:
        print("\n❌ Keine TPY-Dateien gefunden!")
        print("\nBitte kopiere deine TPY-Datei nach:")
        print("  - plc_data/TwinCAT_Project.tpy  (empfohlen)")
        print("  - oder ins aktuelle Verzeichnis")
        return False
    
    # Liste gefundene Dateien
    print(f"\n✓ {len(tpy_files)} TPY-Datei(en) gefunden:\n")
    for i, file in enumerate(tpy_files, 1):
        size = os.path.getsize(file) / 1024
        print(f"  {i}. {file} ({size:.1f} KB)")
    
    # Auswahl
    if len(tpy_files) == 1:
        selected = tpy_files[0]
        print(f"\n→ Verwende: {selected}")
    else:
        choice = input(f"\nWelche Datei importieren? (1-{len(tpy_files)}): ")
        try:
            selected = tpy_files[int(choice) - 1]
        except:
            print("❌ Ungültige Auswahl!")
            return False
    
    # Import durchführen
    print(f"\n📦 Importiere {selected}...")
    
    try:
        # Module importieren
        sys.path.insert(0, '.')
        from module_manager import ModuleManager
        
        # Module-Manager
        manager = ModuleManager(modules_dir='modules')
        manager.load_module_from_file('modules/core/symbol_manager.py')
        
        # Symbol-Manager holen
        symbol_mgr = manager.get_module('symbol_manager')
        
        if not symbol_mgr:
            print("❌ Symbol-Manager konnte nicht geladen werden!")
            return False
        
        # Initialisieren (ohne App-Context)
        class DummyContext:
            class ModuleManager:
                def get_module(self, name):
                    if name == 'config_manager':
                        class ConfigManager:
                            config_dir = os.path.join(
                                os.path.expanduser("~"), 
                                "Documents", 
                                "TwinCAT_SmartHome"
                            )
                        return ConfigManager()
                    return None
            module_manager = ModuleManager()
        
        symbol_mgr.initialize(DummyContext())
        
        # Import
        success = symbol_mgr.import_from_tpy(selected)
        
        if success:
            count = symbol_mgr.get_symbol_count()
            print(f"\n✅ Import erfolgreich!")
            print(f"   {count} Symbole importiert")
            print(f"\n💾 Cache gespeichert in:")
            print(f"   {symbol_mgr.cache_file}")
            
            # Beispiel-Symbole anzeigen
            symbols = symbol_mgr.get_all_symbols()[:10]
            if symbols:
                print(f"\n📋 Erste 10 Symbole:")
                for sym in symbols:
                    print(f"   - {sym['name']} ({sym['type']})")
            
            return True
        else:
            print("\n❌ Import fehlgeschlagen!")
            return False
            
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\nHinweis: Stelle sicher, dass du im TwinCAT_SmartHome-Verzeichnis bist!\n")
    
    success = import_tpy()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ TPY-Import abgeschlossen!")
        print("=" * 60)
        print("\nDu kannst jetzt die Hauptanwendung starten:")
        print("  python Haussteuerung.py")
    else:
        print("\n" + "=" * 60)
        print("⚠ TPY-Import fehlgeschlagen")
        print("=" * 60)
    
    input("\nDrücke Enter zum Beenden...")
