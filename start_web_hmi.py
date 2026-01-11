#!/usr/bin/env python3
"""
SmartHome OS v4.5.3 - Web-HMI Starter
Startet das Web-Interface fuer iPhone/Tablet/Desktop

Usage:
    python start_web_hmi.py [--port 5000] [--host 0.0.0.0]
"""

import sys
import argparse
import os
from module_manager import ModuleManager
from dotenv import load_dotenv

# Lade die .env Datei
load_dotenv()

def main():
    """Startet Web-HMI"""
    parser = argparse.ArgumentParser(description='SmartHome OS Web-HMI')
    parser.add_argument('--port', type=int, default=5000, help='Server-Port (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server-Host (default: 0.0.0.0)')
    args = parser.parse_args()

    # ========================================================================
    # LOGGING SETUP (v4.5.3 + Sentry)
    # ========================================================================
    from modules.core.database_logger import DatabaseLogger

    # Ermittle Projekt-Root
    project_root = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(project_root, 'config', 'system_logs.db')

    # Initialisiere SQLite-basiertes Logging
    DatabaseLogger.setup(db_path=db_path)

    # Initialisiere Sentry (optional, wenn DSN gesetzt)
    try:
        from modules.core.sentry_config import init_sentry
        sentry_dsn = os.getenv('SENTRY_DSN')
        if sentry_dsn:
            init_sentry(
                dsn=sentry_dsn,
                environment=os.getenv('ENVIRONMENT', 'production'),
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1
            )
        else:
            print("  [INFO] SENTRY_DSN nicht gesetzt - Error Tracking deaktiviert")
    except Exception as e:
        print(f"  [WARNING] Sentry-Initialisierung fehlgeschlagen: {e}")

    print("=" * 60)
    print("SmartHome OS v4.5.3 - Web-HMI")
    print("=" * 60)
    print()

    # Zeige ob dies ein Restart ist
    if '--restarted' in sys.argv:
        print("✅ Service neu gestartet (Hot-Reload)\n")

    # Erstelle App-Context (minimale Version)
    class AppContext:
        def __init__(self):
            self.module_manager = ModuleManager()

    app = AppContext()

    # Auto-Discovery: Lade Module
    app.module_manager.auto_discover_modules()

    # Initialisiere alle Module über den ModuleManager (richtige Reihenfolge)
    print()
    print("Initialisiere Module (global via ModuleManager)...")
    print("-" * 60)
    app.module_manager.initialize_all_modules(app)

    # Hole wichtige Module-Instanzen für spätere Nutzung
    data_gateway = app.module_manager.get_module('data_gateway')
    web_manager = app.module_manager.get_module('web_manager')
    stream_manager = app.module_manager.get_module('stream_manager')
    mqtt = app.module_manager.get_module('mqtt_integration')
    plc = app.module_manager.get_module('plc_communication')
    variable_manager = app.module_manager.get_module('variable_manager')

    # Start a background thread to auto-connect PLC after server has started
    import threading, time

    def _auto_connect_plc():
        if not plc:
            return
        # Wait briefly for server to start (max 10s)
        attempts = 0
        while attempts < 10:
            # web_manager.running is set when start_server begins
            wm = app.module_manager.get_module('web_manager')
            if wm and getattr(wm, 'running', False):
                break
            attempts += 1
            time.sleep(0.5)

        # Try to connect up to 3 times using stored config
        cfg = app.module_manager.get_module('config_manager')
        max_tries = 3
        for i in range(1, max_tries + 1):
            if getattr(plc, 'connected', False):
                print("  ✓ PLC bereits verbunden")
                return

            try:
                if cfg:
                    ams = cfg.get_config_value('plc_ams_net_id')
                    port = cfg.get_config_value('plc_ams_port', None)
                    if ams:
                        plc.configure(ams, port=port)

                print(f"  🔌 Versuche PLC-Verbindung (Versuch {i}/{max_tries})...")
                if plc.connect():
                    print("  ✅ PLC verbunden")
                    # After connect, trigger widget sync on data_gateway if available
                    try:
                        dg = app.module_manager.get_module('data_gateway')
                        if dg and hasattr(dg, 'sync_widget_subscriptions'):
                            dg.sync_widget_subscriptions()
                    except Exception:
                        pass
                    return
                else:
                    print("  ⚠️  PLC-Verbindung fehlgeschlagen, warte 2s...")
            except Exception as e:
                print(f"  ✗ Fehler beim PLC-Connect (Versuch {i}): {e}")
            time.sleep(2)

        print("  ⚠️  PLC konnte nach mehreren Versuchen nicht verbunden werden")

    threading.Thread(target=_auto_connect_plc, daemon=True).start()

    # Hinweis-Status zu optionalen Integrationen (keine erneute Initialisierung)
    if stream_manager:
        print("Info: StreamManager verfügbar")

    if mqtt:
        print()
        print("Info: MQTT-Integration verfügbar")
        print("      Konfiguration über Web-UI: Setup -> MQTT")

    if plc:
        print()
        print("Info: PLC-Kommunikation verfügbar (Auto-Connect wird versucht)")
        
        # Optional: Register provided RTSP camera (if module available)
        rtsp_integ = app.module_manager.get_module('rtsp_integration')
        if rtsp_integ:
            try:
                cam_id = 'cam_01'
                cam_url = 'rtsp://192.168.2.89:554/1/h264major'
                rtsp_integ.add_camera(cam_id, cam_url, name='Camera-01')
                print(f"  ✓ RTSP-Kamera registriert: {cam_url}")
            
                # Test: versuche ein einzelnes Frame zu holen
                frame = rtsp_integ.get_frame(cam_id)
                if frame is not None:
                    print("  ✓ RTSP-Frame erhalten - Stream scheint erreichbar")
                else:
                    print("  ⚠️  RTSP-Frame nicht erhalten (Prüfe URL/Netzwerk)")
            except Exception as e:
                print(f"  ⚠️  RTSP-Registrierung/Check fehlgeschlagen: {e}")

    print()
    print("=" * 60)
    print(f"Server startet auf http://{args.host}:{args.port}")
    print("=" * 60)
    print()
    print("Zugriff:")
    print(f"   Lokal:    http://localhost:{args.port}")
    print(f"   Netzwerk: http://<IP>:{args.port}")
    print()
    print("Druecke Ctrl+C zum Beenden")
    print()

    try:
        # Starte Server (blockierend)
        web_manager.start_server(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print()
        print("Beende Server...")
    finally:
        # Cleanup
        if stream_manager:
            stream_manager.shutdown()
        if mqtt:
            mqtt.shutdown()
        data_gateway.shutdown()
        web_manager.shutdown()
        print("Beendet")


if __name__ == '__main__':
    main()
