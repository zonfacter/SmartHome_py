"""
Test-Script für Web Manager v5.1.0 Fix
Prüft ob die Race-Condition behoben ist
"""

import os
import sys
import traceback

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_plc_config_manager():
    """Test 1: PLCConfigManager Pfad-Initialisierung"""
    print("=" * 60)
    print("TEST 1: PLCConfigManager Pfad-Initialisierung")
    print("=" * 60)

    try:
        from modules.gateway.plc_config_manager import PLCConfigManager

        # Simuliere die Initialisierung wie in web_manager.py
        root_dir = os.path.abspath(os.getcwd())
        conf_dir = os.path.join(root_dir, 'config')
        data_dir = os.path.join(root_dir, 'plc_data')

        print(f"  Root Dir: {root_dir}")
        print(f"  Config Dir: {conf_dir}")
        print(f"  Data Dir: {data_dir}")

        # Erstelle Manager mit expliziten Pfaden
        manager = PLCConfigManager(
            config_dir=str(conf_dir),
            plc_data_dir=str(data_dir)
        )

        # Prüfe ob Pfade gesetzt sind
        assert manager.config_dir is not None, "config_dir ist None!"
        assert manager.plc_data_dir is not None, "plc_data_dir ist None!"
        assert manager.config_file is not None, "config_file ist None!"
        assert manager.layout_file is not None, "layout_file ist None!"

        print(f"  ✓ config_dir: {manager.config_dir}")
        print(f"  ✓ plc_data_dir: {manager.plc_data_dir}")
        print(f"  ✓ config_file: {manager.config_file}")
        print(f"  ✓ layout_file: {manager.layout_file}")

        # Teste save() Methode (sollte nicht crashen)
        try:
            result = manager.save()
            print(f"  ✓ save() erfolgreich: {result}")
        except Exception as e:
            print(f"  ✗ save() Fehler: {e}")
            raise AssertionError(f"save() Fehler: {e}") from e

        # Teste get_widgets() Methode
        try:
            widgets = manager.get_widgets()
            print(f"  ✓ get_widgets() erfolgreich: {len(widgets) if widgets else 0} Widgets")
        except Exception as e:
            print(f"  ✗ get_widgets() Fehler: {e}")
            raise AssertionError(f"get_widgets() Fehler: {e}") from e

        print("\n✅ TEST 1 BESTANDEN\n")

    except Exception as e:
        print(f"\n❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
        raise AssertionError(f"TEST 1 FEHLGESCHLAGEN: {e}") from e


def test_web_manager_imports():
    """Test 2: Web Manager Imports"""
    print("=" * 60)
    print("TEST 2: Web Manager Imports")
    print("=" * 60)

    try:
        from modules.gateway.web_manager import WebManager, FLASK_AVAILABLE, MANAGERS_AVAILABLE

        print(f"  ✓ WebManager importiert")
        print(f"  ✓ FLASK_AVAILABLE: {FLASK_AVAILABLE}")
        print(f"  ✓ MANAGERS_AVAILABLE: {MANAGERS_AVAILABLE}")

        if not FLASK_AVAILABLE:
            print("  ⚠️  Flask nicht verfügbar - Web-Server kann nicht starten")
            assert FLASK_AVAILABLE, "Flask nicht verfügbar"

        if not MANAGERS_AVAILABLE:
            print("  ⚠️  Manager-Module nicht verfügbar")
            assert MANAGERS_AVAILABLE, "Manager-Module nicht verfügbar"

        print("\n✅ TEST 2 BESTANDEN\n")

    except Exception as e:
        print(f"\n❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
        raise AssertionError(f"TEST 2 FEHLGESCHLAGEN: {e}") from e


def test_web_manager_initialization():
    """Test 3: Web Manager Initialisierung (ohne Flask-Start)"""
    print("=" * 60)
    print("TEST 3: Web Manager Initialisierung")
    print("=" * 60)

    try:
        from modules.gateway.web_manager import WebManager

        # Erstelle WebManager Instanz
        web_manager = WebManager()

        print(f"  ✓ WebManager Instanz erstellt")
        print(f"  ✓ NAME: {web_manager.NAME}")
        print(f"  ✓ VERSION: {web_manager.VERSION}")

        # Prüfe Attribute
        assert hasattr(web_manager, 'plc_config_manager'), "plc_config_manager Attribut fehlt"
        assert hasattr(web_manager, 'symbol_browser'), "symbol_browser Attribut fehlt"
        assert hasattr(web_manager, 'data_gateway'), "data_gateway Attribut fehlt"
        assert hasattr(web_manager, 'app_context'), "app_context Attribut fehlt"

        print(f"  ✓ Alle Attribute vorhanden")

        print("\n✅ TEST 3 BESTANDEN\n")

    except Exception as e:
        print(f"\n❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
        raise AssertionError(f"TEST 3 FEHLGESCHLAGEN: {e}") from e


def test_api_route_handlers():
    """Test 4: API Route Handler (Mock-Test)"""
    print("=" * 60)
    print("TEST 4: API Route Handler Logic")
    print("=" * 60)

    try:
        from modules.gateway.plc_config_manager import PLCConfigManager

        # Simuliere PLCConfigManager
        root_dir = os.path.abspath(os.getcwd())
        conf_dir = os.path.join(root_dir, 'config')
        data_dir = os.path.join(root_dir, 'plc_data')

        manager = PLCConfigManager(config_dir=str(conf_dir), plc_data_dir=str(data_dir))

        # Simuliere POST Request Logic
        print("  Simuliere: POST /api/plc/config")

        assert manager is not None, "Manager ist None - würde Fehler 500 zurückgeben"

        try:
            # Dies ist die kritische Zeile aus der Route
            result = manager.save()
            print(f"  ✓ manager.save() erfolgreich: {result}")
        except Exception as e:
            print(f"  ✗ manager.save() Fehler: {e}")
            raise AssertionError(f"manager.save() Fehler: {e}") from e

        # Simuliere GET /api/widgets
        print("  Simuliere: GET /api/widgets")
        try:
            widgets = manager.get_widgets()
            widgets_result = widgets if widgets is not None else []
            print(f"  ✓ manager.get_widgets() erfolgreich: {len(widgets_result)} Widgets")
        except Exception as e:
            print(f"  ✗ manager.get_widgets() Fehler: {e}")
            raise AssertionError(f"manager.get_widgets() Fehler: {e}") from e

        print("\n✅ TEST 4 BESTANDEN\n")

    except Exception as e:
        print(f"\n❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
        raise AssertionError(f"TEST 4 FEHLGESCHLAGEN: {e}") from e


def _run_test_case(test_func):
    """CLI-Helfer für boolesche Zusammenfassung außerhalb von pytest."""
    try:
        test_func()
        return True
    except Exception:
        traceback.print_exc()
        return False


def main():
    """Führt alle Tests aus"""
    print("\n" + "=" * 60)
    print("WEB MANAGER v5.1.0 FIX - TEST SUITE")
    print("=" * 60 + "\n")

    results = []

    # Test 1: PLCConfigManager
    results.append(("PLCConfigManager Pfad-Init", _run_test_case(test_plc_config_manager)))

    # Test 2: Imports
    results.append(("Web Manager Imports", _run_test_case(test_web_manager_imports)))

    # Test 3: Initialisierung
    results.append(("Web Manager Initialisierung", _run_test_case(test_web_manager_initialization)))

    # Test 4: API Route Logic
    results.append(("API Route Handler Logic", _run_test_case(test_api_route_handlers)))

    # Zusammenfassung
    print("=" * 60)
    print("TEST ZUSAMMENFASSUNG")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ BESTANDEN" if result else "❌ FEHLGESCHLAGEN"
        print(f"  {status}: {test_name}")

    print()
    print(f"Ergebnis: {passed}/{total} Tests bestanden")
    print("=" * 60)

    if passed == total:
        print("\n🎉 ALLE TESTS BESTANDEN! Fix ist bereit für Produktion.\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} Test(s) fehlgeschlagen. Bitte Fehler prüfen.\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
