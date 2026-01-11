"""
Web Manager Module v5.1.0
FINAL FIX: Beseitigt NoneType-Pfadfehler durch synchrone Initialisierung.

📁 SPEICHERORT: modules/gateway/web_manager.py
"""

from module_manager import BaseModule
from typing import Any, Dict
import threading
import time
import os
import sys
import logging
import traceback

# Flask & SocketIO (lazy import)
try:
    from flask import Flask, render_template, jsonify, request, send_file
    from flask_socketio import SocketIO, emit
    import io
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# PLC Komponenten
try:
    from modules.plc.symbol_browser import get_symbol_browser
    from modules.gateway.plc_config_manager import PLCConfigManager
    from modules.plc.variable_manager import create_variable_manager
    MANAGERS_AVAILABLE = True
except ImportError:
    MANAGERS_AVAILABLE = False

# Sentry Integration
try:
    from modules.core.sentry_config import get_sentry_manager
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# Logger Setup
logger = logging.getLogger(__name__)


class WebManager(BaseModule):
    """
    Web Manager v5.1.0
    Verwaltet das Web-Interface und die Kommunikation zum Frontend.
    """

    NAME = "web_manager"
    VERSION = "1.0.0"
    DESCRIPTION = "Flask + SocketIO Web-HMI Server"
    AUTHOR = "TwinCAT Team"

    def __init__(self):
        super().__init__()
        self.app = None
        self.socketio = None
        self.server_thread = None
        self.running = False
        self.plc_config_manager = None
        self.symbol_browser = None
        self.data_gateway = None
        self.app_context = None
        self.host = '0.0.0.0'
        self.port = 5000
        self.connected_clients = set()
        self.lock = threading.Lock()
        self.sentry = None

        # ⭐ Variable Manager (v5.1.0)
        self.variable_manager = None

    def initialize(self, app_context: Any):
        """Initialisiert das Modul und erzwingt absolute Pfade für alle Manager."""
        super().initialize(app_context)
        self.app_context = app_context

        logger.info("=== Web Manager v5.1.0 Initialisierung START ===")

        # Initialize Sentry if available
        if SENTRY_AVAILABLE:
            self.sentry = get_sentry_manager()
            if self.sentry:
                self.sentry.add_breadcrumb(
                    message="Web Manager initialization started",
                    category="lifecycle",
                    level="info"
                )

        try:
            # 1. PFAD-ANKER SETZEN (Wichtigster Fix für Host-Systeme)
            # Wir ermitteln den Pfad absolut, bevor Flask startet
            root_dir = os.path.abspath(os.getcwd())
            conf_dir = os.path.join(root_dir, 'config')
            data_dir = os.path.join(root_dir, 'plc_data')

            logger.info(f"Pfade initialisiert: root={root_dir}, config={conf_dir}, data={data_dir}")

            # 2. DATA GATEWAY HOLEN
            self.data_gateway = app_context.module_manager.get_module('data_gateway')
            if self.data_gateway:
                self.data_gateway.set_web_manager(self)
                logger.info("Data Gateway verknuepft")
            else:
                logger.warning("Data Gateway nicht verfuegbar")

            # 3. MANAGER INITIALISIEREN
            if MANAGERS_AVAILABLE:
                logger.info("Initialisiere PLCConfigManager...")
                # Wir übergeben die Pfade als garantierte Strings
                self.plc_config_manager = PLCConfigManager(
                    config_dir=str(conf_dir),
                    plc_data_dir=str(data_dir)
                )

                # Verify paths are set
                if self.plc_config_manager.config_file is None:
                    error_msg = "CRITICAL: PLCConfigManager.config_file ist None!"
                    logger.error(error_msg)
                    if self.sentry:
                        self.sentry.capture_message(error_msg, level="error",
                            config_dir=conf_dir, plc_data_dir=data_dir)
                else:
                    logger.info(f"PLCConfigManager bereit: config_file={self.plc_config_manager.config_file}")

                conn_mgr = app_context.module_manager.get_module('connection_manager')
                self.symbol_browser = get_symbol_browser(conn_mgr)

                # ⭐ v5.1.0: Initialize Variable Manager
                logger.info("Initialisiere Variable Manager...")
                self.variable_manager = create_variable_manager()

                # Register symbols from cache
                if self.symbol_browser:
                    try:
                        cached_symbols = self.symbol_browser.get_symbols('plc_001')
                        if cached_symbols:
                            self.variable_manager.register_symbols_bulk(cached_symbols, 'plc_001')
                            logger.info(f"✅ Variable Manager: {len(cached_symbols)} Symbole registriert")
                        else:
                            logger.info("Variable Manager: Keine Symbole im Cache (wird nach TPY-Upload gefüllt)")
                    except Exception as e:
                        logger.warning(f"Variable Manager: Symbol-Registrierung fehlgeschlagen: {e}")

                # Variable Polling will be started after Flask/SocketIO setup
                # to ensure that `self.socketio` is available. We set a flag
                # here and actually start polling right after Flask setup.

                print(f"  [OK] Manager-Systeme fuer Web-HMI bereit (Pfade verankert).")
                logger.info("Manager-Systeme vollstaendig initialisiert")
            else:
                logger.warning("Manager-Module nicht verfuegbar")

            # 4. FLASK SETUP
            if FLASK_AVAILABLE:
                logger.info("Initialisiere Flask App...")
                self._setup_flask()
                logger.info("Flask App bereit")

                # Jetzt, da Flask + SocketIO initialisiert sind, starten
                # wir das Variable-Polling (falls Manager vorhanden).
                if self.data_gateway and self.variable_manager:
                    try:
                        self.data_gateway.start_variable_polling(
                            self.variable_manager,
                            self.socketio,
                            poll_interval=0.5  # 2 Hz
                        )
                        logger.info("✅ Variable Polling Thread gestartet (2 Hz)")
                    except Exception as e:
                        logger.error(f"Fehler beim Starten des Variable-Pollings: {e}")
            else:
                logger.error("Flask nicht verfuegbar!")
                print("  [ERROR] Flask nicht verfuegbar!")

            print(f"  [OK] {self.NAME} v{self.VERSION} initialisiert")
            logger.info("=== Web Manager v5.1.0 Initialisierung ABGESCHLOSSEN ===")

            if self.sentry:
                self.sentry.add_breadcrumb(
                    message="Web Manager initialization completed",
                    category="lifecycle",
                    level="info"
                )

        except Exception as e:
            error_msg = f"Kritischer Fehler bei Web Manager Initialisierung: {e}"
            logger.error(error_msg, exc_info=True)
            print(f"  [ERROR] {error_msg}")

            if self.sentry:
                self.sentry.capture_exception(e,
                    component="web_manager",
                    phase="initialization",
                    root_dir=root_dir if 'root_dir' in locals() else None
                )

            raise

    def _setup_flask(self):
        """Konfiguriert Flask mit absoluten Template-Pfaden."""
        base_dir = os.path.abspath(os.getcwd())
        template_dir = os.path.join(base_dir, 'web', 'templates')
        static_dir = os.path.join(base_dir, 'web', 'static')

        self.app = Flask(__name__,
                         template_folder=template_dir,
                         static_folder=static_dir)

        self.app.config['SECRET_KEY'] = 'smarthome-v5-secret'
        # async_mode='threading' ist stabiler für Windows-Hosts
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')

        self._register_routes()

    def _register_routes(self):
        """Registriert API-Routen mit Fehler-Handling für None-Objekte."""

        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/api/plc/config', methods=['GET', 'POST'])
        def handle_plc_config():
            """PLC Configuration API - Mit detailliertem Logging"""

            # Log Request
            logger.info(f"API Request: {request.method} /api/plc/config from {request.remote_addr}")

            if self.sentry:
                self.sentry.add_breadcrumb(
                    message=f"API call: {request.method} /api/plc/config",
                    category="api",
                    level="info",
                    data={"method": request.method, "remote_addr": request.remote_addr}
                )

            # Manager verfügbar?
            if not self.plc_config_manager:
                error_msg = "PLCConfigManager nicht initialisiert"
                logger.error(f"API ERROR: {error_msg}")

                if self.sentry:
                    self.sentry.capture_message(
                        error_msg,
                        level="error",
                        endpoint="/api/plc/config",
                        method=request.method
                    )

                return jsonify({"status": "error", "message": error_msg}), 500

            if request.method == 'POST':
                # POST: Konfiguration speichern (Setup-Button)
                logger.info("POST /api/plc/config: Speichere PLC-Konfiguration...")

                try:
                    # Request-Daten loggen
                    data = request.json
                    logger.debug(f"Request Data: {data}")

                    # CRITICAL PATH: Hier ist der Fix wichtig!
                    # Prüfe ob config_file gesetzt ist
                    if self.plc_config_manager.config_file is None:
                        error_msg = "CRITICAL: config_file ist None - Race Condition aufgetreten!"
                        logger.error(error_msg)
                        logger.error(f"Debug: config_dir={self.plc_config_manager.config_dir}")
                        logger.error(f"Debug: plc_data_dir={self.plc_config_manager.plc_data_dir}")

                        if self.sentry:
                            self.sentry.capture_message(
                                error_msg,
                                level="fatal",
                                config_dir=self.plc_config_manager.config_dir,
                                plc_data_dir=self.plc_config_manager.plc_data_dir,
                                config_file=self.plc_config_manager.config_file
                            )

                        return jsonify({"status": "error", "message": "Pfad-Initialisierung fehlgeschlagen"}), 500

                    # Save durchführen
                    logger.info(f"Speichere nach: {self.plc_config_manager.config_file}")
                    result = self.plc_config_manager.save()

                    if result:
                        logger.info("PLC-Konfiguration erfolgreich gespeichert")

                        if self.sentry:
                            self.sentry.add_breadcrumb(
                                message="PLC config saved successfully",
                                category="api",
                                level="info"
                            )

                        return jsonify({"status": "success", "message": "Konfiguration gespeichert"})
                    else:
                        error_msg = "save() gab False zurück"
                        logger.warning(error_msg)
                        return jsonify({"status": "error", "message": "Speichern fehlgeschlagen"}), 500

                except Exception as e:
                    error_msg = f"Exception beim Speichern: {e}"
                    logger.error(error_msg, exc_info=True)
                    logger.error(f"Traceback: {traceback.format_exc()}")

                    if self.sentry:
                        self.sentry.capture_exception(e,
                            endpoint="/api/plc/config",
                            method="POST",
                            request_data=request.json if request.json else None,
                            config_file=self.plc_config_manager.config_file if self.plc_config_manager else None
                        )

                    return jsonify({"status": "error", "message": str(e)}), 400

            # GET: Konfiguration abrufen
            logger.debug("GET /api/plc/config: Sende Konfiguration")
            return jsonify(self.plc_config_manager.configs)

        @self.app.route('/api/widgets', methods=['GET', 'POST'])
        def handle_widgets():
            """Widget-Management API"""
            if request.method == 'GET':
                # GET: Alle Widgets abrufen
                widgets = {}

                # Hole Widgets aus config_manager (gleiche Quelle wie POST)
                config_mgr = self.app_context.module_manager.get_module('config_manager')
                if config_mgr:
                    widgets = config_mgr.get_config_value('widgets', {})
                    if not isinstance(widgets, dict):
                        widgets = {}

                # Frontend erwartet: {"widgets": {...}}
                return jsonify({"widgets": widgets})

            elif request.method == 'POST':
                # POST: Neues Widget erstellen
                config_mgr = self.app_context.module_manager.get_module('config_manager')
                if not config_mgr:
                    return jsonify({'error': 'Config Manager nicht verfügbar'}), 503

                data = request.json
                required = ['type', 'title']

                for field in required:
                    if field not in data:
                        return jsonify({'error': f'Feld {field} erforderlich'}), 400

                # Generiere ID
                import uuid
                widget_id = data.get('id', str(uuid.uuid4()))

                widget = {
                    'id': widget_id,
                    'type': data['type'],
                    'title': data['title'],
                    'page': data.get('page', 'dashboard'),
                    'bindings': data.get('bindings', {}),
                    'config': data.get('config', {}),
                    'created': time.time(),
                    'modified': time.time()
                }

                # Speichere in Config
                widgets = config_mgr.get_config_value('widgets', {})
                widgets[widget_id] = widget
                config_mgr.set_config_value('widgets', widgets)
                config_mgr.save_config()

                logger.info(f"Widget erstellt: {widget_id}")
                return jsonify({'success': True, 'widget': widget, 'id': widget_id, 'widget_id': widget_id})

        @self.app.route('/api/widgets/<widget_id>', methods=['PUT'])
        def update_widget(widget_id):
            """Aktualisiert ein bestehendes Widget"""
            config_mgr = self.app_context.module_manager.get_module('config_manager')
            if not config_mgr:
                return jsonify({'error': 'Config Manager nicht verfügbar'}), 503

            widgets = config_mgr.get_config_value('widgets', {})
            if widget_id not in widgets:
                return jsonify({'error': 'Widget nicht gefunden'}), 404

            # Merge update data
            update_data = request.json
            widgets[widget_id].update(update_data)

            config_mgr.set_config_value('widgets', widgets)
            config_mgr.save_config()

            logger.info(f"Widget aktualisiert: {widget_id}")
            return jsonify({'success': True, 'widget': widgets[widget_id]})

        @self.app.route('/api/widgets/<widget_id>', methods=['DELETE'])
        def delete_widget(widget_id):
            """Löscht ein Widget"""
            config_mgr = self.app_context.module_manager.get_module('config_manager')
            if not config_mgr:
                return jsonify({'error': 'Config Manager nicht verfügbar'}), 503

            widgets = config_mgr.get_config_value('widgets', {})
            if widget_id in widgets:
                del widgets[widget_id]
                config_mgr.set_config_value('widgets', widgets)
                config_mgr.save_config()
                logger.info(f"Widget gelöscht: {widget_id}")
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Widget nicht gefunden'}), 404

        @self.app.route('/api/debug/config', methods=['GET'])
        def debug_config():
            """Debug: Zeigt komplette Config"""
            config_mgr = self.app_context.module_manager.get_module('config_manager')
            if not config_mgr:
                return jsonify({'error': 'Config Manager nicht verfügbar'}), 503

            return jsonify({
                'config': config_mgr.config,
                'widgets': config_mgr.get_config_value('widgets', {}),
                'config_file': config_mgr.config_file,
                'has_widgets': 'widgets' in config_mgr.config
            })

        @self.app.route('/api/plc/symbols', methods=['GET'])
        def get_plc_symbols():
            """Liefert Symbole für den Browser (pyads 3.5.0)."""
            if not self.symbol_browser:
                logger.warning("Symbol-Browser nicht verfuegbar")
                return jsonify({'symbols': [], 'count': 0})

            conn_id = request.args.get('connection_id', 'plc_001')
            force = request.args.get('refresh', 'false').lower() == 'true'

            try:
                symbols = self.symbol_browser.get_symbols(conn_id, force_refresh=force)
                if not symbols:
                    symbols = []

                logger.info(f"Symbol-Abruf: {len(symbols)} Symbole geladen")

                return jsonify({
                    'symbols': symbols,
                    'count': len(symbols),
                    'connection_id': conn_id
                })
            except Exception as e:
                logger.error(f"Symbol-Abruf Fehler: {e}", exc_info=True)
                return jsonify({'symbols': [], 'count': 0, 'error': str(e)})

        @self.app.route('/api/plc/symbols/upload', methods=['POST'])
        def upload_tpy():
            """TPY-Datei Upload und Parsing"""
            if 'file' not in request.files:
                return jsonify({'error': 'Keine Datei'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'Keine Datei ausgewählt'}), 400

            if not file.filename.endswith('.tpy'):
                return jsonify({'error': 'Nur .tpy Dateien erlaubt'}), 400

            try:
                # Speichere TPY-Datei
                plc_data_dir = os.path.join(os.getcwd(), 'plc_data')
                os.makedirs(plc_data_dir, exist_ok=True)

                filename = file.filename
                filepath = os.path.join(plc_data_dir, filename)

                file.save(filepath)
                logger.info(f"TPY-Datei gespeichert: {filepath}")

                # TPY-Datei parsen (einfaches XML-Parsing)
                symbol_count = 0
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(filepath)
                    root = tree.getroot()

                    # Zähle Symbole (DataType-Elemente mit name-Attribut)
                    symbols = root.findall('.//{http://www.beckhoff.com/schemas/2011/07/TcPOU}Symbol')
                    if not symbols:
                        # Fallback: suche nach anderen XML-Strukturen
                        symbols = root.findall('.//Symbol')

                    symbol_count = len(symbols)
                    logger.info(f"TPY-Parsing: {symbol_count} Symbole gefunden")

                except Exception as parse_error:
                    logger.warning(f"TPY-Parsing-Fehler: {parse_error}")
                    # Wenn Parsing fehlschlägt, zähle Zeilen als grobe Schätzung
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        symbol_count = content.count('<Symbol') or content.count('VAR')

                # ⭐ NEU: Symbole im Symbol-Browser-Cache speichern
                if self.symbol_browser and symbol_count > 0:
                    try:
                        cached_count = self.symbol_browser.load_symbols_from_tpy(filepath, 'plc_001')
                        logger.info(f"Symbol-Cache aktualisiert: {cached_count} Symbole gespeichert")
                    except Exception as cache_error:
                        logger.warning(f"Cache-Speicherung fehlgeschlagen: {cache_error}")

                return jsonify({
                    'success': True,
                    'message': 'TPY-Datei hochgeladen und geparst',
                    'filename': filename,
                    'path': filepath,
                    'symbol_count': symbol_count
                })

            except Exception as e:
                logger.error(f"TPY-Upload Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/plc/symbols/live', methods=['POST'])
        def load_live_symbols():
            """Lädt Symbole direkt von der PLC via pyads"""
            try:
                # Hole PLC-Kommunikation Modul
                plc = self.app_context.module_manager.get_module('plc_communication')
                if not plc:
                    return jsonify({'error': 'PLC-Modul nicht verfügbar'}), 503

                # Prüfe ob PLC verbunden ist
                status = plc.get_connection_status()
                if not status.get('connected', False):
                    return jsonify({'error': 'PLC nicht verbunden. Bitte zuerst verbinden.'}), 400

                # Hole pyads Client (korrekt: plc.plc, nicht plc.client!)
                if not hasattr(plc, 'plc') or plc.plc is None:
                    return jsonify({'error': 'Keine aktive PLC-Verbindung'}), 400

                logger.info("Starte Live-Symbol-Abruf von PLC...")

                # Lade Symbole direkt von PLC
                try:
                    raw_symbols = plc.plc.get_all_symbols()
                    logger.info(f"pyads: {len(raw_symbols)} Symbole von PLC empfangen")

                    # Konvertiere zu PLCSymbol-Format
                    from modules.plc.symbol_browser import PLCSymbol
                    symbols_list = []

                    for s in raw_symbols:
                        plc_symbol = PLCSymbol(
                            name=s.name,
                            symbol_type=str(s.symbol_type),
                            index_group=s.index_group,
                            index_offset=s.index_offset,
                            size=getattr(s, 'size', 0),  # size kann fehlen bei manchen AdsSymbol-Objekten
                            comment=getattr(s, 'comment', '')
                        )
                        symbols_list.append(plc_symbol)

                    # Speichere im Symbol-Browser-Cache
                    if self.symbol_browser:
                        self.symbol_browser.symbol_cache['plc_001'] = symbols_list
                        self.symbol_browser.cache_timestamp['plc_001'] = time.time()
                        self.symbol_browser.save_cache_to_file(self.symbol_browser.cache_file, 'plc_001')
                        logger.info(f"Symbol-Cache aktualisiert: {len(symbols_list)} Symbole")

                    return jsonify({
                        'success': True,
                        'symbol_count': len(symbols_list),
                        'message': f'{len(symbols_list)} Symbole von PLC geladen'
                    })

                except Exception as pyads_error:
                    logger.error(f"pyads get_all_symbols() Fehler: {pyads_error}", exc_info=True)
                    return jsonify({'error': f'Symbol-Abruf fehlgeschlagen: {str(pyads_error)}'}), 500

            except Exception as e:
                logger.error(f"Live-Symbol-Abruf Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/system/status')
        def system_status():
            """System-Status für Dashboard"""
            try:
                if not self.data_gateway:
                    return jsonify({'error': 'Gateway nicht verfügbar'}), 503

                status = self.data_gateway.get_system_status()
                return jsonify(status)
            except Exception as e:
                logger.error(f"Fehler beim System-Status: {e}", exc_info=True)
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/telemetry')
        def get_all_telemetry():
            """Alle Telemetrie-Werte"""
            if not self.data_gateway:
                return jsonify({'error': 'Gateway nicht verfügbar'}), 503

            data = self.data_gateway.get_all_telemetry()
            return jsonify(data)

        @self.app.route('/api/system/dependencies')
        def check_dependencies():
            """Prüft System-Abhängigkeiten"""
            import subprocess
            import shutil

            deps = {}

            # Python-Pakete
            python_packages = {
                'pyads': 'PLC-Kommunikation',
                'paho.mqtt': 'MQTT-Integration',
                'flask': 'Webserver',
                'flask_socketio': 'WebSocket-Support'
            }

            for package, description in python_packages.items():
                try:
                    __import__(package.replace('-', '_'))
                    deps[package] = {'available': True, 'description': description}
                except ImportError:
                    deps[package] = {'available': False, 'description': description}

            # FFmpeg prüfen (für Streams)
            ffmpeg_path = shutil.which('ffmpeg')
            deps['ffmpeg'] = {
                'available': ffmpeg_path is not None,
                'description': 'FFmpeg (Streams)',
                'path': ffmpeg_path if ffmpeg_path else 'Nicht gefunden'
            }

            return jsonify(deps)

        @self.app.route('/api/plc/connect', methods=['POST'])
        def connect_plc():
            """PLC-Verbindung herstellen"""
            data = request.get_json()
            ams_id = data.get('ams_id')
            ams_port = data.get('ams_port', 851)
            ip_address = data.get('ip_address')

            if not ams_id:
                return jsonify({'error': 'ams_id erforderlich'}), 400

            plc = self.app_context.module_manager.get_module('plc_communication')
            if not plc:
                return jsonify({'error': 'PLC-Modul nicht verfügbar'}), 503

            # Speichere Config
            config_mgr = self.app_context.module_manager.get_module('config_manager')
            if config_mgr:
                config_mgr.set_config_value('plc_ams_net_id', ams_id)
                config_mgr.set_config_value('plc_ams_port', ams_port)
                config_mgr.set_config_value('plc_ip_address', ip_address or '')
                config_mgr.save_config()
                logger.info(f"PLC-Config gespeichert: {ams_id}:{ams_port}")

            try:
                plc.configure(ams_net_id=ams_id, port=ams_port)
                success = plc.connect()

                if success:
                    if self.data_gateway:
                        self.data_gateway.sync_widget_subscriptions()
                    return jsonify({'success': True, 'message': 'PLC verbunden'})
                else:
                    return jsonify({'error': 'Verbindung fehlgeschlagen'}), 500
            except Exception as e:
                logger.error(f"PLC-Connect Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/plc/disconnect', methods=['POST'])
        def disconnect_plc():
            """PLC-Verbindung trennen"""
            plc = self.app_context.module_manager.get_module('plc_communication')
            if not plc:
                return jsonify({'error': 'PLC-Modul nicht verfügbar'}), 503

            try:
                plc.disconnect()
                return jsonify({'success': True, 'message': 'PLC getrennt'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/mqtt/status')
        def mqtt_status():
            """MQTT Status"""
            mqtt = self.app_context.module_manager.get_module('mqtt_integration')
            if not mqtt:
                return jsonify({'available': False, 'error': 'MQTT-Modul nicht geladen'})

            return jsonify({
                'available': mqtt.mqtt_available,
                'connected': mqtt.connected,
                'broker': mqtt.config.get('broker', 'nicht konfiguriert'),
                'port': mqtt.config.get('port', 1883),
                'subscriptions': len(mqtt.subscriptions)
            })

        @self.app.route('/api/admin/plcs', methods=['GET', 'POST'])
        def handle_admin_plcs():
            """Alle PLC-Konfigurationen verwalten (GET = Liste, POST = Erstellen/Update)"""
            if not self.plc_config_manager:
                logger.warning("PLC Config Manager nicht verfügbar für /api/admin/plcs")
                # Gebe leere aber valide Response zurück
                empty_response = {
                    'plcs': {},
                    'statistics': {
                        'total_plcs': 0,
                        'active_plcs': 0,
                        'active_plc_id': None,
                        'config_path': 'N/A'
                    },
                    'active_plc': None
                }
                return jsonify(empty_response)

            # POST: PLC erstellen/aktualisieren
            if request.method == 'POST':
                try:
                    data = request.get_json()
                    plc_id = data.get('plc_id')
                    plc_config = data.get('config', {})

                    if not plc_id:
                        return jsonify({'error': 'plc_id erforderlich'}), 400

                    # Füge PLC hinzu oder aktualisiere
                    if not hasattr(self.plc_config_manager, 'configs'):
                        self.plc_config_manager.configs = {}

                    if 'plc_configs' not in self.plc_config_manager.configs:
                        self.plc_config_manager.configs['plc_configs'] = {}

                    self.plc_config_manager.configs['plc_configs'][plc_id] = plc_config

                    # Speichere
                    if self.plc_config_manager.save():
                        logger.info(f"PLC-Config erstellt/aktualisiert: {plc_id}")
                        return jsonify({
                            'success': True,
                            'plc_id': plc_id,
                            'message': 'PLC-Konfiguration gespeichert'
                        })
                    else:
                        return jsonify({'error': 'Speichern fehlgeschlagen'}), 500

                except Exception as e:
                    logger.error(f"Fehler beim Erstellen der PLC-Config: {e}", exc_info=True)
                    return jsonify({'error': str(e)}), 500

            # GET: Alle PLCs abrufen
            try:
                plcs = self.plc_config_manager.get_all_plcs()
                stats = self.plc_config_manager.get_statistics()

                return jsonify({
                    'plcs': plcs,
                    'statistics': stats,
                    'active_plc': self.plc_config_manager.configs.get('active_plc')
                })
            except Exception as e:
                logger.error(f"Fehler beim Laden der PLCs: {e}", exc_info=True)
                return jsonify({
                    'plcs': {},
                    'statistics': {
                        'total_plcs': 0,
                        'active_plcs': 0,
                        'active_plc_id': None,
                        'config_path': 'N/A'
                    },
                    'active_plc': None,
                    'error': str(e)
                })

        @self.app.route('/api/admin/logs')
        def get_system_logs():
            """System-Logs aus SQLite-Datenbank"""
            try:
                from modules.core.database_logger import DatabaseLogger

                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                db_path = os.path.join(project_root, 'config', 'system_logs.db')

                limit = request.args.get('limit', 100, type=int)
                logs = DatabaseLogger.get_recent_logs(db_path, limit=limit)

                return jsonify(logs)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Logs: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/admin/service/info')
        def get_service_info():
            """Service-Informationen"""
            try:
                from modules.core.service_manager import ServiceManager
                info = ServiceManager.get_restart_info()
                return jsonify(info)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/monitor/dataflow')
        def get_dataflow_stats():
            """Echtzeit-Datenfluss-Statistiken"""
            stats = {
                'protocols': {},
                'total_throughput': 0,
                'active_connections': 0,
                'timestamp': time.time(),
                'hardware': {}
            }

            # Hardware-Daten
            import platform
            try:
                import psutil
                stats['hardware'] = {
                    'platform': platform.system(),
                    'cpu_percent': psutil.cpu_percent(interval=0.1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'memory_used_mb': round(psutil.virtual_memory().used / (1024**2), 2)
                }
            except:
                stats['hardware'] = {'platform': platform.system()}

            # PLC Statistics
            plc = self.app_context.module_manager.get_module('plc_communication')
            if plc:
                plc_stats = plc.get_connection_status()
                stats['protocols']['plc'] = {
                    'name': 'TwinCAT ADS',
                    'connected': plc_stats.get('connected', False),
                    'reads': plc_stats.get('total_reads', 0),
                    'writes': plc_stats.get('total_writes', 0)
                }

            return jsonify(stats)

        @self.app.route('/api/monitor/latency')
        def measure_latency():
            """Latenz-Messung für Monitoring"""
            return jsonify({
                'timestamp': time.time(),
                'latency_ms': 0.5  # Stub - echte Messung würde über PLC gehen
            })

        # ==========================================
        # ⭐ VARIABLE MANAGER API ENDPOINTS (v5.1.0)
        # ==========================================

        @self.app.route('/api/variables/write', methods=['POST'])
        def write_variable():
            """
            Schreibt einen Wert in eine PLC-Variable

            Request Body:
            {
                "plc_id": "plc_001",
                "variable": "Light.Light_EG_WZ.bOn",
                "value": true
            }
            """
            if not self.variable_manager or not self.data_gateway:
                return jsonify({'status': 'error', 'message': 'Variable Manager nicht verfügbar'}), 503

            try:
                data = request.json
                plc_id = data.get('plc_id', 'plc_001')
                variable = data.get('variable')
                value = data.get('value')

                if not variable:
                    return jsonify({'status': 'error', 'message': 'Variable fehlt'}), 400

                # Schreibe über Data Gateway
                success = self.data_gateway.write_variable(variable, value, plc_id)

                if success:
                    logger.info(f"✍️  Variable geschrieben: {plc_id}/{variable} = {value}")
                    return jsonify({
                        'status': 'success',
                        'message': 'Variable geschrieben',
                        'variable': variable,
                        'value': value,
                        'plc_id': plc_id
                    })
                else:
                    return jsonify({'status': 'error', 'message': 'Schreiben fehlgeschlagen'}), 500

            except Exception as e:
                logger.error(f"Fehler beim Schreiben: {e}", exc_info=True)
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/variables/read', methods=['POST'])
        def read_variable():
            """
            Liest eine PLC-Variable (direkt oder aus Cache)

            Request Body:
            {
                "plc_id": "plc_001",
                "variable": "Light.Light_EG_WZ.bOn",
                "use_cache": true
            }
            """
            if not self.variable_manager:
                return jsonify({'status': 'error', 'message': 'Variable Manager nicht verfügbar'}), 503

            try:
                data = request.json
                plc_id = data.get('plc_id', 'plc_001')
                variable = data.get('variable')
                use_cache = data.get('use_cache', True)

                if not variable:
                    return jsonify({'status': 'error', 'message': 'Variable fehlt'}), 400

                # Versuche aus Cache
                if use_cache:
                    cached = self.variable_manager.get_cached_value(variable, plc_id)
                    if cached:
                        value, timestamp = cached
                        return jsonify({
                            'status': 'success',
                            'variable': variable,
                            'value': value,
                            'timestamp': timestamp,
                            'plc_id': plc_id,
                            'source': 'cache'
                        })

                # Direkt von PLC lesen
                plc = self.app_context.module_manager.get_module('plc_communication')
                if not plc:
                    return jsonify({'status': 'error', 'message': 'PLC nicht verfügbar'}), 503

                # ⭐ v5.1.2: Hole plc_type aus Symbol-Info
                symbol_info = self.variable_manager.get_symbol_info(variable, plc_id)
                if not symbol_info:
                    return jsonify({'status': 'error', 'message': 'Symbol nicht gefunden'}), 404

                value = plc.read_by_name(variable, symbol_info.symbol_type)
                timestamp = time.time()

                # Cache aktualisieren
                self.variable_manager.update_value(variable, value, plc_id)

                return jsonify({
                    'status': 'success',
                    'variable': variable,
                    'value': value,
                    'timestamp': timestamp,
                    'plc_id': plc_id,
                    'source': 'plc'
                })

            except Exception as e:
                logger.error(f"Fehler beim Lesen: {e}", exc_info=True)
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/variables/statistics', methods=['GET'])
        def variable_statistics():
            """Gibt Variable Manager Statistiken zurück"""
            if not self.variable_manager:
                return jsonify({'status': 'error', 'message': 'Variable Manager nicht verfügbar'}), 503

            try:
                stats = self.variable_manager.get_statistics()
                return jsonify({
                    'status': 'success',
                    'statistics': stats
                })

            except Exception as e:
                logger.error(f"Fehler bei Statistik-Abfrage: {e}", exc_info=True)
                return jsonify({'status': 'error', 'message': str(e)}), 500

    def _setup_socketio(self):
        """Setup SocketIO Events für Echtzeit-Kommunikation"""

        @self.socketio.on('connect')
        def handle_connect():
            """Client verbunden"""
            client_id = request.sid
            with self.lock:
                self.connected_clients.add(client_id)
            print(f"  🔌 Client verbunden: {client_id} (Total: {len(self.connected_clients)})")

            # Sende initial alle Telemetrie-Daten
            if self.data_gateway:
                telemetry = self.data_gateway.get_all_telemetry()
                emit('initial_telemetry', telemetry)

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Client getrennt"""
            client_id = request.sid
            with self.lock:
                self.connected_clients.discard(client_id)
            print(f"  🔌 Client getrennt: {client_id} (Total: {len(self.connected_clients)})")

        # ==========================================
        # ⭐ VARIABLE MANAGER WEBSOCKET EVENTS (v5.1.0)
        # ==========================================

        @self.socketio.on('subscribe_variable')
        def handle_subscribe(data):
            """
            Widget abonniert eine Variable

            Data Format:
            {
                "widget_id": "widget_123",
                "variable": "Light.Light_EG_WZ.bOn",
                "plc_id": "plc_001"
            }
            """
            if not self.variable_manager:
                emit('error', {'message': 'Variable Manager nicht verfügbar'})
                return

            try:
                widget_id = data.get('widget_id')
                variable = data.get('variable')
                plc_id = data.get('plc_id', 'plc_001')

                if not widget_id or not variable:
                    emit('error', {'message': 'widget_id und variable erforderlich'})
                    return

                # Subscribe Widget
                self.variable_manager.subscribe_widget(widget_id, variable, plc_id)

                # Sende aktuellen Wert sofort zurück
                cached = self.variable_manager.get_cached_value(variable, plc_id)
                if cached:
                    value, timestamp = cached
                    symbol_info = self.variable_manager.get_symbol_info(variable, plc_id)
                    emit('variable_update', {
                        'widget_id': widget_id,
                        'variable': variable,
                        'value': value,
                        'timestamp': timestamp,
                        'type': symbol_info.symbol_type if symbol_info else 'UNKNOWN',
                        'plc_id': plc_id
                    })

                logger.info(f"📌 Widget {widget_id} subscribed to {plc_id}/{variable}")

                # Bestätigung senden
                emit('subscribe_success', {
                    'widget_id': widget_id,
                    'variable': variable,
                    'plc_id': plc_id
                })

            except Exception as e:
                logger.error(f"Fehler bei subscribe_variable: {e}", exc_info=True)
                emit('error', {'message': str(e)})

        @self.socketio.on('unsubscribe_variable')
        def handle_unsubscribe(data):
            """
            Widget beendet Subscription

            Data Format:
            {
                "widget_id": "widget_123"
            }
            """
            if not self.variable_manager:
                emit('error', {'message': 'Variable Manager nicht verfügbar'})
                return

            try:
                widget_id = data.get('widget_id')

                if not widget_id:
                    emit('error', {'message': 'widget_id erforderlich'})
                    return

                # Unsubscribe Widget
                self.variable_manager.unsubscribe_widget(widget_id)

                logger.info(f"📌 Widget {widget_id} unsubscribed")

                # Bestätigung senden
                emit('unsubscribe_success', {
                    'widget_id': widget_id
                })

            except Exception as e:
                logger.error(f"Fehler bei unsubscribe_variable: {e}", exc_info=True)
                emit('error', {'message': str(e)})

    def broadcast_telemetry(self, key: str, value: Any):
        """
        Sendet Telemetrie-Update an alle Clients

        Args:
            key: Telemetrie-Key
            value: Wert
        """
        if not self.running or not self.socketio:
            return

        self.socketio.emit('telemetry_update', {
            'key': key,
            'value': value,
            'timestamp': time.time()
        })

    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """
        Sendet Custom Event an alle Clients

        Args:
            event_type: Event-Name
            data: Event-Daten
        """
        if not self.running or not self.socketio:
            return

        self.socketio.emit(event_type, data)

    def start_server(self, host: str = '0.0.0.0', port: int = 5000):
        """Startet den Server (wird von start_web_hmi.py aufgerufen)."""
        self.host = host
        self.port = port
        self.running = True
        print(f"  ▶️  Web-Server startet auf http://{host}:{port}")

        # Setup SocketIO Events
        if self.socketio:
            self._setup_socketio()

        try:
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                use_reloader=False,
                debug=False,
                log_output=False,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            print(f"  ✗ Server-Fehler: {e}")
        finally:
            self.running = False

    def shutdown(self):
        self.running = False

        # ⭐ v5.1.0: Stop Variable Polling
        if self.data_gateway:
            self.data_gateway.stop_variable_polling()
            logger.info("Variable Polling gestoppt")

        print("  ✓ Web Manager abgeschaltet.")

    def get_stats(self) -> Dict[str, Any]:
        """Server-Statistik"""
        with self.lock:
            return {
                'running': self.running,
                'host': self.host,
                'port': self.port,
                'connected_clients': len(self.connected_clients)
            }


def register(module_manager):
    module_manager.register_module(
        WebManager.NAME, WebManager.VERSION, WebManager.DESCRIPTION, WebManager
    )
