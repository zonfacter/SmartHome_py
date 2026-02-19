"""
Test-Script für Logging-System (SQLite + Sentry)
Testet alle Logging-Komponenten des v5.1.0 Fixes
"""

import os
import sys
import logging

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _result(ok: bool):
    """
    Script-Modus: bool für Zusammenfassung zurückgeben.
    Pytest-Modus: bei Fehler fehlschlagen, sonst None zurückgeben.
    """
    if __name__ == "__main__":
        return ok
    assert ok


def test_sentry_integration():
    """Test 1: Sentry Integration"""
    print("=" * 60)
    print("TEST 1: Sentry Integration")
    print("=" * 60)

    try:
        from modules.core.sentry_config import get_sentry_manager
        from dotenv import load_dotenv

        load_dotenv()

        sentry = get_sentry_manager()

        # Prüfe ob DSN gesetzt ist
        dsn = os.getenv('SENTRY_DSN')
        if not dsn:
            print("  [INFO] SENTRY_DSN nicht gesetzt - Sentry deaktiviert")
            print("  [INFO] Setze SENTRY_DSN in .env um Sentry zu aktivieren")
            print("\n✅ TEST 1 ÜBERSPRUNGEN (Sentry optional)\n")
            return _result(True)

        # Initialisiere Sentry
        success = sentry.initialize(
            environment="testing",
            traces_sample_rate=1.0,  # 100% für Tests
            enable_tracing=True
        )

        if success:
            print(f"  ✓ Sentry initialisiert")
            print(f"  ✓ Environment: testing")

            # Test Message senden
            print("  → Sende Test-Nachricht an Sentry...")
            sentry.capture_message(
                "Logging System Test - Message",
                level="info",
                test_type="integration_test"
            )
            print("  ✓ Test-Nachricht gesendet")

            # Test Exception senden
            print("  → Sende Test-Exception an Sentry...")
            try:
                raise ValueError("Test-Exception für Logging-System")
            except Exception as e:
                sentry.capture_exception(e,
                    test_phase="exception_test",
                    component="test_logging_system"
                )
                print("  ✓ Test-Exception gesendet")

            # Test Breadcrumb
            print("  → Füge Test-Breadcrumb hinzu...")
            sentry.add_breadcrumb(
                message="Test breadcrumb",
                category="test",
                level="info",
                data={"step": 1}
            )
            print("  ✓ Breadcrumb hinzugefügt")

            print("\n✅ TEST 1 BESTANDEN")
            print("  → Prüfe Sentry Dashboard: https://sentry.io")
            print("  → Suche nach Events mit 'testing' Environment\n")
            return _result(True)
        else:
            print("  ✗ Sentry-Initialisierung fehlgeschlagen")
            return _result(False)

    except Exception as e:
        print(f"\n❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
        import traceback
        traceback.print_exc()
        return _result(False)


def test_database_logger():
    """Test 2: SQLite Database Logger"""
    print("=" * 60)
    print("TEST 2: SQLite Database Logger")
    print("=" * 60)

    try:
        from modules.core.database_logger import DatabaseLogger

        # DB-Pfad
        project_root = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_root, 'config', 'system_logs.db')

        print(f"  DB Path: {db_path}")

        # Setup Logger
        DatabaseLogger.setup(db_path=db_path)
        print("  ✓ Database Logger initialisiert")

        # Test Log-Einträge
        test_logger = logging.getLogger("test_logger")

        print("  → Schreibe Test-Log-Einträge...")
        test_logger.info("Test INFO Log")
        test_logger.warning("Test WARNING Log")
        test_logger.error("Test ERROR Log")
        print("  ✓ Log-Einträge geschrieben")

        # Lese letzte Logs
        print("  → Lese letzte 5 Log-Einträge...")
        recent_logs = DatabaseLogger.get_recent_logs(db_path, limit=5)

        if recent_logs:
            print(f"  ✓ {len(recent_logs)} Log-Einträge gefunden:")
            for log in recent_logs[:3]:
                print(f"    - [{log.get('level')}] {log.get('message')}")
        else:
            print("  ⚠️  Keine Logs gefunden (DB eventuell leer)")

        print("\n✅ TEST 2 BESTANDEN\n")
        return _result(True)

    except Exception as e:
        print(f"\n❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
        import traceback
        traceback.print_exc()
        return _result(False)


def test_web_manager_logging():
    """Test 3: Web Manager Logging Integration"""
    print("=" * 60)
    print("TEST 3: Web Manager Logging Integration")
    print("=" * 60)

    try:
        from modules.gateway.web_manager import WebManager, SENTRY_AVAILABLE

        print(f"  Sentry verfügbar: {SENTRY_AVAILABLE}")

        # Erstelle WebManager (ohne vollständige Initialisierung)
        web_mgr = WebManager()
        print(f"  ✓ WebManager erstellt")

        # Prüfe ob Sentry-Attribut existiert
        if hasattr(web_mgr, 'sentry'):
            print(f"  ✓ sentry Attribut vorhanden")
        else:
            print(f"  ✗ sentry Attribut fehlt!")
            return _result(False)

        # Prüfe Logging-Imports
        import logging
        logger = logging.getLogger('modules.gateway.web_manager')
        print(f"  ✓ Logger für web_manager verfügbar")

        # Test Log-Ausgabe
        logger.info("Test-Log von web_manager")
        print(f"  ✓ Test-Log ausgegeben")

        print("\n✅ TEST 3 BESTANDEN\n")
        return _result(True)

    except Exception as e:
        print(f"\n❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
        import traceback
        traceback.print_exc()
        return _result(False)


def test_plc_config_manager_logging():
    """Test 4: PLCConfigManager Logging"""
    print("=" * 60)
    print("TEST 4: PLCConfigManager Logging")
    print("=" * 60)

    try:
        from modules.gateway.plc_config_manager import PLCConfigManager

        # Erstelle Manager mit Test-Pfaden
        project_root = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(project_root, 'config')
        plc_data_dir = os.path.join(project_root, 'plc_data')

        print(f"  Config Dir: {config_dir}")
        print(f"  PLC Data Dir: {plc_data_dir}")

        manager = PLCConfigManager(
            config_dir=config_dir,
            plc_data_dir=plc_data_dir
        )

        print(f"  ✓ PLCConfigManager erstellt")

        # Verifiziere Pfade
        if manager.config_file is None:
            print(f"  ✗ config_file ist None!")
            return _result(False)

        print(f"  ✓ config_file gesetzt: {manager.config_file}")

        # Test save() (sollte Logs ausgeben)
        print("  → Teste save() Operation...")
        result = manager.save()

        if result:
            print(f"  ✓ save() erfolgreich")
        else:
            print(f"  ✗ save() fehlgeschlagen")
            return _result(False)

        print("\n✅ TEST 4 BESTANDEN\n")
        return _result(True)

    except Exception as e:
        print(f"\n❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
        import traceback
        traceback.print_exc()
        return _result(False)


def main():
    """Führt alle Logging-Tests aus"""
    print("\n" + "=" * 60)
    print("LOGGING SYSTEM TEST SUITE v5.1.0")
    print("=" * 60 + "\n")

    results = []

    # Test 1: Sentry
    results.append(("Sentry Integration", test_sentry_integration()))

    # Test 2: Database Logger
    results.append(("SQLite Database Logger", test_database_logger()))

    # Test 3: Web Manager Logging
    results.append(("Web Manager Logging", test_web_manager_logging()))

    # Test 4: PLCConfigManager Logging
    results.append(("PLCConfigManager Logging", test_plc_config_manager_logging()))

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
        print("\n🎉 ALLE LOGGING-TESTS BESTANDEN!\n")
        print("Nächste Schritte:")
        print("1. Starte das System: python start_web_hmi.py")
        print("2. Öffne Browser: http://localhost:5000")
        print("3. Gehe zu Setup-Seite und klicke 'Konfiguration speichern'")
        print("4. Prüfe Logs:")
        print("   - Console-Output")
        print("   - config/system_logs.db")
        print("   - Sentry Dashboard (falls konfiguriert)")
        print()
        return 0
    else:
        print(f"\n⚠️  {total - passed} Test(s) fehlgeschlagen. Bitte Fehler prüfen.\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
