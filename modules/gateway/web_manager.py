"""
Web Manager Module v5.1.0
FINAL FIX: Beseitigt NoneType-Pfadfehler durch synchrone Initialisierung.

📁 SPEICHERORT: modules/gateway/web_manager.py
"""

from module_manager import BaseModule
from typing import Any, Dict, List
import threading
import time
import os
import sys
import json
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
    from modules.gateway.camera_trigger_store import CameraTriggerStore
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

        # ONVIF PTZ Controllers (lazy, gecacht)
        self._onvif_controllers = {}
        self._ring_event_thread = None
        self._ring_event_active = False
        self._ring_last_event_ids = {}
        self._ring_doorbell_until = {}
        self._ring_doorbell_pulse_seconds = 10.0
        self._camera_trigger_rules = []
        self._camera_trigger_state = {}
        self._camera_trigger_last_fired = {}
        self._trigger_store = None

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
                self._trigger_store = CameraTriggerStore(os.path.join(conf_dir, 'automation_rules.db'))

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
                self._load_camera_trigger_rules()

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

        @self.app.after_request
        def _disable_hls_cache(response):
            # HLS manifests/segments must not be cached, otherwise stale playlists
            # can reference already deleted TS fragments and trigger endless 404 loops.
            if request.path.startswith('/static/hls/'):
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            elif request.path.startswith('/static/js/') or request.path.startswith('/static/css/'):
                # Avoid stale frontend bundles after backend hotfixes.
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            return response

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
            conn_id = request.args.get('connection_id', 'plc_001')
            force = request.args.get('refresh', 'false').lower() == 'true'

            try:
                symbols = []
                if self.symbol_browser:
                    symbols = self.symbol_browser.get_symbols(conn_id, force_refresh=force) or []
                else:
                    logger.warning("Symbol-Browser nicht verfuegbar - liefere nur Gateway-Variablen")

                # Gateway-Variablen (z. B. Ring-Klingel) in die Auswahlliste aufnehmen
                symbols.extend(self._get_gateway_virtual_symbols())

                logger.info(f"Symbol-Abruf: {len(symbols)} Symbole geladen")

                return jsonify({
                    'symbols': symbols,
                    'count': len(symbols),
                    'connection_id': conn_id
                })
            except Exception as e:
                logger.error(f"Symbol-Abruf Fehler: {e}", exc_info=True)
                return jsonify({'symbols': [], 'count': 0, 'error': str(e)})

        @self.app.route('/api/variables/search', methods=['GET'])
        def search_variables():
            """Serverseitige Variablensuche (skalierbar für große Symbolmengen)."""
            try:
                conn_id = request.args.get('connection_id', 'plc_001')
                query = (request.args.get('q') or request.args.get('query') or '').strip().lower()
                type_filter = (request.args.get('type') or '').strip().upper()
                limit = max(1, min(int(request.args.get('limit', 200)), 1000))

                symbols = []
                if self.symbol_browser:
                    symbols = self.symbol_browser.get_symbols(conn_id, force_refresh=False) or []

                # Gateway virtuelle Variablen ergänzen
                symbols.extend(self._get_gateway_virtual_symbols())

                results = []
                for sym in symbols:
                    if not isinstance(sym, dict):
                        continue
                    name = str(sym.get('name', ''))
                    sym_type = str(sym.get('type', ''))
                    if query and query not in name.lower():
                        continue
                    if type_filter and type_filter not in sym_type.upper():
                        continue
                    results.append({
                        'name': name,
                        'type': sym_type,
                        'comment': sym.get('comment', '')
                    })
                    if len(results) >= limit:
                        break

                return jsonify({
                    'success': True,
                    'query': query,
                    'count': len(results),
                    'limit': limit,
                    'variables': results
                })
            except Exception as e:
                logger.error(f"Variable-Suche Fehler: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e), 'variables': []}), 500

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
        # RING API ENDPOINTS
        # ==========================================

        @self.app.route('/api/ring/status', methods=['GET'])
        def ring_status():
            try:
                from modules.integrations.ring_module import get_ring_status
                return jsonify(get_ring_status())
            except Exception as e:
                logger.error(f"Fehler bei GET /api/ring/status: {e}", exc_info=True)
                return jsonify({'available': False, 'configured': False, 'error': str(e)}), 500

        @self.app.route('/api/ring/auth', methods=['POST'])
        def ring_auth():
            try:
                data = request.json or {}
                username = (data.get('username') or '').strip()
                password = data.get('password') or ''
                otp_raw = (data.get('otp') or '').strip()
                otp = ''.join(ch for ch in otp_raw if ch.isdigit()) or None
                user_agent = (data.get('user_agent') or '').strip() or None

                if not username or not password:
                    return jsonify({'success': False, 'error': 'username und password erforderlich'}), 400

                from modules.integrations.ring_module import authenticate_ring
                result = authenticate_ring(username, password, otp=otp, user_agent=user_agent)

                status = 200 if result.get('success') else 401
                return jsonify(result), status
            except Exception as e:
                logger.error(f"Fehler bei POST /api/ring/auth: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/ring/cameras', methods=['GET'])
        def ring_list_cameras():
            try:
                from modules.integrations.ring_module import list_ring_cameras
                result = list_ring_cameras()
                if result.get('success'):
                    return jsonify(result)
                return jsonify(result), 401
            except Exception as e:
                logger.error(f"Fehler bei GET /api/ring/cameras: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/ring/cameras/import', methods=['POST'])
        def ring_import_camera():
            """Importiert eine Ring-Kamera in cameras.json."""
            try:
                data = request.json or {}
                ring_device_id = str(data.get('ring_device_id', '')).strip()
                if not ring_device_id:
                    return jsonify({'success': False, 'error': 'ring_device_id erforderlich'}), 400

                cam_id = str(data.get('id', '')).strip() or f"ring_{ring_device_id}"
                cam_name = data.get('name') or f"Ring {ring_device_id}"

                config = _load_cameras_config()
                config.setdefault('cameras', {})

                config['cameras'][cam_id] = {
                    'name': cam_name,
                    'url': f"/api/cameras/{cam_id}/snapshot",
                    'type': 'ring',
                    'autostart': False,
                    'ring': {
                        'device_id': ring_device_id
                    }
                }
                _save_cameras_config(config)

                return jsonify({'success': True, 'camera_id': cam_id})
            except Exception as e:
                logger.error(f"Fehler bei POST /api/ring/cameras/import: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        # ==========================================
        # CAMERA / STREAM API ENDPOINTS
        # ==========================================

        def _cameras_config_path():
            return os.path.join(os.path.abspath(os.getcwd()), 'config', 'cameras.json')

        def _load_cameras_config():
            path = _cameras_config_path()
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
            return {"cameras": {}}

        def _save_cameras_config(config):
            path = _cameras_config_path()
            with open(path, 'w') as f:
                json.dump(config, f, indent=2)

        @self.app.route('/api/camera-triggers', methods=['GET', 'POST'])
        def camera_triggers():
            """Liest/aktualisiert Kamera-Trigger-Regeln."""
            try:
                if request.method == 'GET':
                    self._load_camera_trigger_rules()
                    return jsonify({'success': True, 'rules': self._camera_trigger_rules})

                data = request.get_json(silent=True) or {}
                rules = data.get('rules')
                if not isinstance(rules, list):
                    return jsonify({'success': False, 'error': 'rules muss eine Liste sein'}), 400

                if self._trigger_store:
                    stored = self._trigger_store.replace_rules(rules)
                    self._camera_trigger_rules = stored
                    self._camera_trigger_state = {}
                    self._camera_trigger_last_fired = {}
                else:
                    path = os.path.join(os.path.abspath(os.getcwd()), 'config', 'camera_triggers.json')
                    payload = {'version': '1.0', 'rules': rules}
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)
                    self._load_camera_trigger_rules()

                return jsonify({'success': True, 'rules': self._camera_trigger_rules})
            except Exception as e:
                logger.error(f"Fehler bei /api/camera-triggers: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/cameras', methods=['GET'])
        def list_cameras():
            """Liste aller Kameras + Stream-Status"""
            try:
                config = _load_cameras_config()
                cameras = config.get('cameras', {})
                stream_mgr = self.app_context.module_manager.get_module('stream_manager')

                result = {}
                for cam_id, cam_cfg in cameras.items():
                    running = False
                    hls_url = None
                    if stream_mgr:
                        running = stream_mgr.is_stream_running(cam_id)
                        if running:
                            hls_url = f"/static/hls/{cam_id}.m3u8"
                    result[cam_id] = {
                        'name': cam_cfg.get('name', cam_id),
                        'url': cam_cfg.get('url', ''),
                        'substream_url': cam_cfg.get('substream_url', ''),
                        'type': cam_cfg.get('type', 'rtsp'),
                        'autostart': cam_cfg.get('autostart', False),
                        'onvif': cam_cfg.get('onvif', None),
                        'ring': cam_cfg.get('ring', None),
                        'stream_running': running,
                        'hls_url': hls_url,
                        'preview_url': f"/api/cameras/{cam_id}/snapshot" if cam_cfg.get('type') == 'ring' else None
                    }

                return jsonify({'cameras': result})
            except Exception as e:
                logger.error(f"Fehler bei GET /api/cameras: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/alert', methods=['POST'])
        def trigger_camera_alert():
            """Broadcastet ein Kamera-Alarm-Event ans Frontend (Vorbereitung Gateway-Trigger)."""
            try:
                data = request.get_json(silent=True) or {}
                cam_id = str(data.get('cam_id') or data.get('camera_id') or '').strip()
                if not cam_id:
                    return jsonify({'success': False, 'error': 'cam_id fehlt'}), 400

                config = _load_cameras_config()
                cam_cfg = config.get('cameras', {}).get(cam_id, {})
                payload = {
                    'cam_id': cam_id,
                    'name': data.get('name') or cam_cfg.get('name') or cam_id,
                    'type': data.get('type') or cam_cfg.get('type') or 'ring',
                    'source': data.get('source', 'gateway'),
                    'timestamp': int(time.time())
                }
                self.broadcast_event('camera_alert', payload)
                return jsonify({'success': True, 'event': payload})
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras/alert: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/snapshot', methods=['GET'])
        def camera_snapshot(cam_id):
            """Liefert Snapshot fuer Ring- und RTSP-Kameras."""
            try:
                config = _load_cameras_config()
                cam_cfg = config.get('cameras', {}).get(cam_id)
                if not cam_cfg:
                    return jsonify({'error': 'Kamera nicht gefunden'}), 404

                cam_type = (cam_cfg.get('type') or 'rtsp').lower()
                image_data = None

                if cam_type == 'ring':
                    ring_cfg = cam_cfg.get('ring') or {}
                    ring_device_id = ring_cfg.get('device_id')
                    if not ring_device_id:
                        return jsonify({'error': 'Ring device_id fehlt in Kamera-Konfiguration'}), 400

                    from modules.integrations.ring_module import get_ring_snapshot
                    retries = request.args.get('retries', default=8, type=int)
                    delay = request.args.get('delay', default=2, type=int)
                    retries = max(1, min(retries, 20))
                    delay = max(1, min(delay, 10))

                    result = get_ring_snapshot(str(ring_device_id), retries=retries, delay=delay)
                    if not result.get('success'):
                        return jsonify({'error': result.get('error', 'Snapshot fehlgeschlagen')}), 500
                    image_data = result.get('content')
                elif cam_type == 'rtsp':
                    stream_url = cam_cfg.get('substream_url') or cam_cfg.get('url')
                    if not stream_url:
                        return jsonify({'error': 'RTSP URL fehlt in Kamera-Konfiguration'}), 400

                    stream_mgr = self.app_context.module_manager.get_module('stream_manager')
                    if not stream_mgr:
                        return jsonify({'error': 'Stream Manager nicht verfuegbar'}), 503

                    timeout = request.args.get('timeout', default=6, type=int)
                    image_data = stream_mgr.capture_snapshot(stream_url, timeout=timeout)
                else:
                    return jsonify({'error': f'Snapshot fuer Typ {cam_type} nicht unterstuetzt'}), 400

                if not image_data:
                    return jsonify({'error': 'Leerer Snapshot erhalten'}), 500

                response = send_file(
                    io.BytesIO(image_data),
                    mimetype='image/jpeg',
                    download_name=f'{cam_id}.jpg'
                )
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                return response
            except Exception as e:
                logger.error(f"Fehler bei GET /api/cameras/{cam_id}/snapshot: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ring/webrtc/start', methods=['POST'])
        def start_ring_webrtc_stream(cam_id):
            """Startet Ring WebRTC-Session anhand Browser SDP offer."""
            try:
                config = _load_cameras_config()
                cam_cfg = config.get('cameras', {}).get(cam_id)
                if not cam_cfg:
                    return jsonify({'success': False, 'error': 'Kamera nicht gefunden'}), 404
                if cam_cfg.get('type') != 'ring':
                    return jsonify({'success': False, 'error': 'Nur fuer Ring-Kameras'}), 400

                data = request.json or {}
                sdp_offer = data.get('offer')
                keep_alive_timeout = int(data.get('keep_alive_timeout', 45))
                if not sdp_offer:
                    return jsonify({'success': False, 'error': 'offer erforderlich'}), 400

                ring_cfg = cam_cfg.get('ring') or {}
                device_id = ring_cfg.get('device_id')
                if not device_id:
                    return jsonify({'success': False, 'error': 'Ring device_id fehlt'}), 400

                from modules.integrations.ring_module import start_ring_webrtc
                result = start_ring_webrtc(str(device_id), sdp_offer, keep_alive_timeout=keep_alive_timeout)
                if result.get('success'):
                    status = 200
                else:
                    err = (result.get('error') or '').lower()
                    status = 503 if ('deaktiviert' in err or '406' in err) else 500
                return jsonify(result), status
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras/{cam_id}/ring/webrtc/start: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ring/webrtc/candidate', methods=['POST'])
        def send_ring_webrtc_candidate_endpoint(cam_id):
            """Leitet lokale ICE-Candidates vom Browser an Ring weiter."""
            try:
                data = request.json or {}
                session_id = data.get('session_id')
                candidate = data.get('candidate')
                mline_index = data.get('sdpMLineIndex')
                if session_id is None or candidate is None or mline_index is None:
                    return jsonify({'success': False, 'error': 'session_id, candidate, sdpMLineIndex erforderlich'}), 400

                from modules.integrations.ring_module import send_ring_webrtc_candidate
                result = send_ring_webrtc_candidate(str(session_id), str(candidate), int(mline_index))
                status = 200 if result.get('success') else 500
                return jsonify(result), status
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras/{cam_id}/ring/webrtc/candidate: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ring/webrtc/keepalive', methods=['POST'])
        def keepalive_ring_webrtc_endpoint(cam_id):
            """Hält bestehende Ring WebRTC Session aktiv."""
            try:
                data = request.json or {}
                session_id = data.get('session_id')
                if not session_id:
                    return jsonify({'success': False, 'error': 'session_id erforderlich'}), 400

                from modules.integrations.ring_module import keepalive_ring_webrtc
                result = keepalive_ring_webrtc(str(session_id))
                status = 200 if result.get('success') else 500
                return jsonify(result), status
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras/{cam_id}/ring/webrtc/keepalive: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ring/webrtc/stop', methods=['POST'])
        def stop_ring_webrtc_endpoint(cam_id):
            """Stoppt Ring WebRTC Session."""
            try:
                data = request.json or {}
                session_id = data.get('session_id')
                if not session_id:
                    return jsonify({'success': False, 'error': 'session_id erforderlich'}), 400

                from modules.integrations.ring_module import stop_ring_webrtc
                result = stop_ring_webrtc(str(session_id))
                status = 200 if result.get('success') else 500
                return jsonify(result), status
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras/{cam_id}/ring/webrtc/stop: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/cameras', methods=['POST'])
        def add_camera():
            """Kamera hinzufügen (speichert Config, startet Stream bei RTSP)"""
            try:
                data = request.json
                cam_id = data.get('id')
                cam_name = data.get('name', '')
                cam_url = data.get('url', '')
                cam_type = data.get('type', 'rtsp')
                autostart = data.get('autostart', True)

                if not cam_id or not cam_url:
                    return jsonify({'error': 'id und url erforderlich'}), 400

                # Config speichern
                config = _load_cameras_config()
                config['cameras'][cam_id] = {
                    'name': cam_name,
                    'url': cam_url,
                    'type': cam_type,
                    'autostart': autostart
                }
                _save_cameras_config(config)

                # Stream starten bei RTSP
                hls_url = None
                stream_running = False
                if cam_type == 'rtsp' and autostart:
                    stream_mgr = self.app_context.module_manager.get_module('stream_manager')
                    if stream_mgr and stream_mgr.has_ffmpeg:
                        stream_mgr.start_stream(cam_id, cam_url)
                        stream_running = stream_mgr.is_stream_running(cam_id)
                        if stream_running:
                            hls_url = f"/static/hls/{cam_id}.m3u8"

                logger.info(f"Kamera hinzugefuegt: {cam_id} ({cam_url})")
                return jsonify({
                    'success': True,
                    'camera_id': cam_id,
                    'stream_running': stream_running,
                    'hls_url': hls_url
                })
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>', methods=['DELETE'])
        def delete_camera(cam_id):
            """Kamera entfernen (stoppt Stream, loescht Config)"""
            try:
                # Stream stoppen
                stream_mgr = self.app_context.module_manager.get_module('stream_manager')
                if stream_mgr:
                    stream_mgr.stop_stream(cam_id)

                # Aus Config entfernen
                config = _load_cameras_config()
                if cam_id in config.get('cameras', {}):
                    del config['cameras'][cam_id]
                    _save_cameras_config(config)

                logger.info(f"Kamera entfernt: {cam_id}")
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Fehler bei DELETE /api/cameras/{cam_id}: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>', methods=['PUT'])
        def update_camera(cam_id):
            """Kamera-Konfiguration aktualisieren"""
            try:
                config = _load_cameras_config()
                if cam_id not in config.get('cameras', {}):
                    return jsonify({'error': 'Kamera nicht gefunden'}), 404

                data = request.json or {}
                cam_cfg = config['cameras'][cam_id]
                restart_stream = False

                # Aktualisierbare Felder
                if 'name' in data:
                    cam_cfg['name'] = data['name']
                if 'url' in data:
                    if cam_cfg.get('url') != data['url']:
                        restart_stream = True
                    cam_cfg['url'] = data['url']
                if 'substream_url' in data:
                    if cam_cfg.get('substream_url') != data['substream_url']:
                        restart_stream = True
                    cam_cfg['substream_url'] = data['substream_url']
                if 'type' in data:
                    if cam_cfg.get('type') != data['type']:
                        restart_stream = True
                    cam_cfg['type'] = data['type']
                if 'autostart' in data:
                    cam_cfg['autostart'] = data['autostart']

                # ONVIF-Config (komplett ersetzen wenn angegeben)
                if 'onvif' in data:
                    if data['onvif']:
                        cam_cfg['onvif'] = data['onvif']
                    else:
                        cam_cfg.pop('onvif', None)

                _save_cameras_config(config)

                # Bei geänderter Stream-Quelle laufenden FFmpeg-Prozess beenden.
                if restart_stream:
                    stream_mgr = self.app_context.module_manager.get_module('stream_manager')
                    if stream_mgr:
                        stream_mgr.stop_stream(cam_id, cleanup=True)

                logger.info(f"Kamera aktualisiert: {cam_id}")
                return jsonify({'success': True, 'camera': cam_cfg})
            except Exception as e:
                logger.error(f"Fehler bei PUT /api/cameras/{cam_id}: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/start', methods=['POST'])
        def start_camera_stream(cam_id):
            """Startet HLS-Transkodierung fuer eine Kamera"""
            try:
                config = _load_cameras_config()
                cam_cfg = config.get('cameras', {}).get(cam_id)
                if not cam_cfg:
                    return jsonify({'error': 'Kamera nicht gefunden'}), 404

                stream_mgr = self.app_context.module_manager.get_module('stream_manager')
                if not stream_mgr:
                    return jsonify({'error': 'Stream Manager nicht verfuegbar'}), 503

                cam_type = (cam_cfg.get('type') or 'rtsp').lower()
                if cam_type == 'ring':
                    ring_cfg = cam_cfg.get('ring') or {}
                    ring_device_id = ring_cfg.get('device_id')
                    if not ring_device_id:
                        return jsonify({'error': 'Ring device_id fehlt'}), 400

                    from modules.integrations.ring_module import get_ring_refresh_token
                    refresh_token = get_ring_refresh_token()
                    if not refresh_token:
                        return jsonify({'error': 'Kein Ring refresh_token vorhanden. Bitte neu anmelden.'}), 401

                    success = stream_mgr.start_ring_stream(cam_id, str(ring_device_id), refresh_token)
                    if success:
                        return jsonify({
                            'success': True,
                            'hls_url': f"/static/hls/{cam_id}.m3u8",
                            'mode': 'ring_bridge'
                        })
                    return jsonify({'error': 'Ring-Bridge konnte nicht gestartet werden'}), 500

                if not stream_mgr.has_ffmpeg:
                    return jsonify({'error': 'Stream Manager oder FFmpeg nicht verfuegbar'}), 503

                # Stream-URL und Resolution bestimmen
                stream_url = cam_cfg['url']
                resolution = None

                data = request.get_json(silent=True) or {}
                if data:
                    use_substream = data.get('use_substream', False)
                    if use_substream:
                        # SubStream: copy passthrough wenn substream_url vorhanden
                        substream_url = cam_cfg.get('substream_url')
                        if substream_url:
                            stream_url = substream_url
                            resolution = None  # copy passthrough
                        else:
                            # Fallback: MainStream mit Skalierung
                            resolution = '640x360'
                    else:
                        resolution = data.get('resolution')

                success = stream_mgr.start_stream(cam_id, stream_url, resolution=resolution)
                if success:
                    return jsonify({
                        'success': True,
                        'hls_url': f"/static/hls/{cam_id}.m3u8"
                    })
                else:
                    return jsonify({'error': 'Stream konnte nicht gestartet werden'}), 500
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras/{cam_id}/start: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/stop', methods=['POST'])
        def stop_camera_stream(cam_id):
            """Stoppt HLS-Transkodierung fuer eine Kamera"""
            try:
                stream_mgr = self.app_context.module_manager.get_module('stream_manager')
                if not stream_mgr:
                    return jsonify({'error': 'Stream Manager nicht verfuegbar'}), 503

                config = _load_cameras_config()
                cam_cfg = config.get('cameras', {}).get(cam_id) or {}
                cam_type = (cam_cfg.get('type') or 'rtsp').lower()
                data = request.get_json(silent=True) or {}
                immediate = bool(data.get('immediate', False))
                if cam_type == 'ring' and not immediate:
                    success = stream_mgr.schedule_stop_stream(cam_id, delay_seconds=45.0, cleanup=True)
                else:
                    success = stream_mgr.stop_stream(cam_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Fehler bei POST /api/cameras/{cam_id}/stop: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        # ==========================================
        # CAMERA DIAGNOSTICS ENDPOINT
        # ==========================================

        @self.app.route('/api/cameras/diagnose', methods=['POST'])
        def diagnose_camera_endpoint():
            """Kamera-Diagnose: Port-Scan, RTSP-Probe, ONVIF, Snapshot"""
            try:
                data = request.json or {}
                host = data.get('host', '').strip()
                if not host:
                    return jsonify({'error': 'host erforderlich'}), 400

                user = data.get('user', 'admin')
                password = data.get('password', 'admin')

                from modules.integrations.camera_diagnostics import diagnose_camera
                result = diagnose_camera(host, user=user, password=password)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Kamera-Diagnose Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/scan', methods=['POST'])
        def scan_network_endpoint():
            """Netzwerk nach Kameras scannen (WS-Discovery + Port-Scan)"""
            try:
                data = request.json or {}
                subnet = data.get('subnet')
                ports = data.get('ports')
                user = data.get('user', 'admin')
                password = data.get('password', 'admin')

                # Ports validieren
                if ports:
                    ports = [int(p) for p in ports if 0 < int(p) <= 65535]

                from modules.integrations.camera_diagnostics import scan_network
                result = scan_network(subnet=subnet, ports=ports or None,
                                      user=user, password=password)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Netzwerk-Scan Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        # ==========================================
        # ONVIF PTZ API ENDPOINTS
        # ==========================================

        def _get_onvif_controller(cam_id):
            """Lazy-Init eines ONVIF PTZ Controllers fuer eine Kamera."""
            if cam_id in self._onvif_controllers:
                ctrl = self._onvif_controllers[cam_id]
                if ctrl.connected:
                    return ctrl

            config = _load_cameras_config()
            cam_cfg = config.get('cameras', {}).get(cam_id)
            if not cam_cfg or 'onvif' not in cam_cfg:
                return None

            try:
                from modules.integrations.onvif_ptz import OnvifPTZController
                onvif_cfg = cam_cfg['onvif']
                ctrl = OnvifPTZController(
                    host=onvif_cfg['host'],
                    port=onvif_cfg.get('port', 80),
                    user=onvif_cfg.get('user', 'admin'),
                    password=onvif_cfg.get('password', 'admin')
                )
                ctrl.connect()
                self._onvif_controllers[cam_id] = ctrl
                return ctrl
            except Exception as e:
                logger.error(f"ONVIF Controller Fehler fuer {cam_id}: {e}")
                return None

        @self.app.route('/api/cameras/<cam_id>/ptz/status', methods=['GET'])
        def ptz_status(cam_id):
            """PTZ-Status und Faehigkeiten"""
            try:
                ctrl = _get_onvif_controller(cam_id)
                if not ctrl:
                    return jsonify({'has_ptz': False, 'connected': False})

                status = ctrl.get_ptz_status()
                return jsonify({
                    'has_ptz': ctrl.has_ptz,
                    'connected': ctrl.connected,
                    'position': status
                })
            except Exception as e:
                logger.error(f"PTZ status Fehler: {e}", exc_info=True)
                return jsonify({'has_ptz': False, 'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ptz/move', methods=['POST'])
        def ptz_move(cam_id):
            """Kontinuierliche PTZ-Bewegung starten"""
            try:
                ctrl = _get_onvif_controller(cam_id)
                if not ctrl or not ctrl.has_ptz:
                    return jsonify({'error': 'PTZ nicht verfuegbar'}), 404

                data = request.json or {}
                pan = float(data.get('pan', 0.0))
                tilt = float(data.get('tilt', 0.0))
                zoom = float(data.get('zoom', 0.0))
                timeout_ms = int(data.get('timeout_ms', 250))

                success = ctrl.continuous_move(pan, tilt, zoom, timeout_ms=timeout_ms)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"PTZ move Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ptz/stop', methods=['POST'])
        def ptz_stop(cam_id):
            """PTZ-Bewegung stoppen"""
            try:
                ctrl = _get_onvif_controller(cam_id)
                if not ctrl or not ctrl.has_ptz:
                    return jsonify({'error': 'PTZ nicht verfuegbar'}), 404

                success = ctrl.stop()
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"PTZ stop Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ptz/presets', methods=['GET'])
        def ptz_presets(cam_id):
            """Preset-Liste abrufen"""
            try:
                ctrl = _get_onvif_controller(cam_id)
                if not ctrl or not ctrl.has_ptz:
                    return jsonify({'presets': []})

                presets = ctrl.get_presets()
                return jsonify({'presets': presets})
            except Exception as e:
                logger.error(f"PTZ presets Fehler: {e}", exc_info=True)
                return jsonify({'presets': [], 'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ptz/preset', methods=['POST'])
        def ptz_goto_preset(cam_id):
            """Zu einem Preset fahren"""
            try:
                ctrl = _get_onvif_controller(cam_id)
                if not ctrl or not ctrl.has_ptz:
                    return jsonify({'error': 'PTZ nicht verfuegbar'}), 404

                data = request.json or {}
                token = data.get('token')
                if not token:
                    return jsonify({'error': 'token erforderlich'}), 400

                success = ctrl.go_to_preset(token)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"PTZ goto preset Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ptz/preset/save', methods=['POST'])
        def ptz_save_preset(cam_id):
            """Aktuellen Standort als Preset speichern"""
            try:
                ctrl = _get_onvif_controller(cam_id)
                if not ctrl or not ctrl.has_ptz:
                    return jsonify({'error': 'PTZ nicht verfuegbar'}), 404

                data = request.json or {}
                name = data.get('name', 'Preset')

                token = ctrl.set_preset(name)
                if token:
                    return jsonify({'success': True, 'token': token, 'name': name})
                else:
                    return jsonify({'error': 'Preset konnte nicht gespeichert werden'}), 500
            except Exception as e:
                logger.error(f"PTZ save preset Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/cameras/<cam_id>/ptz/home', methods=['POST'])
        def ptz_home(cam_id):
            """Home-Position anfahren"""
            try:
                ctrl = _get_onvif_controller(cam_id)
                if not ctrl or not ctrl.has_ptz:
                    return jsonify({'error': 'PTZ nicht verfuegbar'}), 404

                success = ctrl.go_home()
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"PTZ home Fehler: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

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

                # Gateway-interne Variablen (nicht-PLC) direkt in Telemetrie schreiben
                if variable.startswith('GATEWAY.') and self.data_gateway:
                    self.data_gateway.update_telemetry(variable, value)
                    logger.info(f"✍️  Gateway-Variable geschrieben: {variable} = {value}")
                    return jsonify({
                        'status': 'success',
                        'message': 'Gateway-Variable geschrieben',
                        'variable': variable,
                        'value': value,
                        'plc_id': plc_id
                    })

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

                # Gateway-interne Variablen (nicht-PLC) direkt aus Telemetrie lesen
                if variable.startswith('GATEWAY.') and self.data_gateway:
                    value = self.data_gateway.get_telemetry(variable)
                    if value is None:
                        return jsonify({'status': 'error', 'message': 'Gateway-Variable nicht gefunden'}), 404
                    timestamp = time.time()
                    self.variable_manager.update_value(variable, value, plc_id)
                    return jsonify({
                        'status': 'success',
                        'variable': variable,
                        'value': value,
                        'timestamp': timestamp,
                        'plc_id': plc_id,
                        'source': 'gateway'
                    })

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

    def _load_cameras_config_for_monitor(self) -> Dict[str, Any]:
        path = os.path.join(os.path.abspath(os.getcwd()), 'config', 'cameras.json')
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {"cameras": {}}
        return {"cameras": {}}

    def _get_ring_camera_configs(self) -> List[Dict[str, str]]:
        config = self._load_cameras_config_for_monitor()
        cameras = config.get('cameras', {}) or {}
        ring_cams = []
        for cam_id, cam_cfg in cameras.items():
            if (cam_cfg.get('type') or '').lower() != 'ring':
                continue
            device_id = str((cam_cfg.get('ring') or {}).get('device_id') or '').strip()
            if not device_id:
                continue
            ring_cams.append({
                'cam_id': str(cam_id),
                'device_id': device_id,
                'name': cam_cfg.get('name') or str(cam_id)
            })
        return ring_cams

    def _get_gateway_virtual_symbols(self) -> List[Dict[str, Any]]:
        """Gateway-eigene Variablen für die Symbolauswahl (z. B. Ring)."""
        symbols = []
        for cam in self._get_ring_camera_configs():
            base = f"GATEWAY.RING.{cam['cam_id']}"
            symbols.extend([
                {
                    'name': f"{base}.doorbell",
                    'type': 'BOOL',
                    'index_group': 0,
                    'index_offset': 0,
                    'size': 1,
                    'comment': f"Ring Klingel-Trigger ({cam['name']})"
                },
                {
                    'name': f"{base}.last_ding_ts",
                    'type': 'DINT',
                    'index_group': 0,
                    'index_offset': 0,
                    'size': 4,
                    'comment': f"Unix-Zeitstempel letztes Klingeln ({cam['name']})"
                },
                {
                    'name': f"{base}.last_event_id",
                    'type': 'STRING',
                    'index_group': 0,
                    'index_offset': 0,
                    'size': 80,
                    'comment': f"Letzte Ring Event-ID ({cam['name']})"
                },
            ])
        return symbols

    def _camera_trigger_config_path(self) -> str:
        return os.path.join(os.path.abspath(os.getcwd()), 'config', 'camera_triggers.json')

    def _load_camera_trigger_rules(self):
        rules = []
        path = self._camera_trigger_config_path()

        # SQLite is source of truth. Import legacy JSON once when DB is empty.
        if self._trigger_store:
            try:
                if self._trigger_store.is_empty():
                    self._trigger_store.import_legacy_json(path)
                rules = self._trigger_store.list_rules()
            except Exception as e:
                logger.warning(f"Konnte Trigger-Regeln nicht aus DB laden: {e}")
                rules = []

        # Default-Regel: Ring Doorbell Variable triggert Ring-Kamera Popup
        if not rules:
            default_rules = []
            for cam in self._get_ring_camera_configs():
                default_rules.append({
                    "id": f"ring_{cam['cam_id']}_doorbell_popup",
                    "name": f"Ring Klingel {cam['name']}",
                    "enabled": True,
                    "variable": f"GATEWAY.RING.{cam['cam_id']}.doorbell",
                    "on_value": True,
                    "operator": "eq",
                    "category": "ring",
                    "tags": ["ring", "doorbell", "popup"],
                    "camera_id": cam['cam_id'],
                    "camera_type": "ring",
                    "duration_seconds": 30,
                    "cooldown_seconds": 0
                })
            rules = default_rules
            if self._trigger_store:
                try:
                    rules = self._trigger_store.replace_rules(rules)
                except Exception as e:
                    logger.warning(f"Konnte Default-Trigger-Regeln nicht in DB schreiben: {e}")
            else:
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump({"version": "1.0", "rules": rules}, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Konnte camera_triggers.json nicht schreiben: {e}")

        self._camera_trigger_rules = rules
        self._camera_trigger_state = {}
        self._camera_trigger_last_fired = {}
        logger.info(f"Kamera-Trigger-Regeln geladen: {len(rules)}")

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in ('1', 'true', 'on', 'yes')
        return bool(value)

    @staticmethod
    def _to_float(value: Any):
        try:
            return float(value)
        except Exception:
            return None

    def _trigger_value_matches(self, actual: Any, expected: Any, operator: str = 'eq') -> bool:
        op = (operator or 'eq').strip().lower()
        if op in ('eq', '=='):
            if isinstance(expected, bool):
                return self._to_bool(actual) is expected
            return actual == expected
        if op in ('ne', '!='):
            if isinstance(expected, bool):
                return self._to_bool(actual) is not expected
            return actual != expected
        if op in ('gt', '>'):
            a = self._to_float(actual)
            b = self._to_float(expected)
            return a is not None and b is not None and a > b
        if op in ('gte', '>='):
            a = self._to_float(actual)
            b = self._to_float(expected)
            return a is not None and b is not None and a >= b
        if op in ('lt', '<'):
            a = self._to_float(actual)
            b = self._to_float(expected)
            return a is not None and b is not None and a < b
        if op in ('lte', '<='):
            a = self._to_float(actual)
            b = self._to_float(expected)
            return a is not None and b is not None and a <= b
        if op == 'contains':
            return str(expected).lower() in str(actual).lower()
        return actual == expected

    def _handle_camera_trigger_rules(self, key: str, value: Any):
        if not self._camera_trigger_rules:
            return

        for rule in self._camera_trigger_rules:
            if not rule.get('enabled', True):
                continue
            if str(rule.get('variable', '')).strip() != key:
                continue

            rule_id = str(rule.get('id') or key)
            previous = self._camera_trigger_state.get(rule_id, None)
            operator = str(rule.get('operator') or 'eq')
            current_match = self._trigger_value_matches(value, rule.get('on_value', True), operator)
            previous_match = self._trigger_value_matches(previous, rule.get('on_value', True), operator) if previous is not None else False
            self._camera_trigger_state[rule_id] = value

            # Trigger nur auf Flanke (false -> true), verhindert Dauer-Popup
            if current_match and not previous_match:
                cooldown = max(0, int(rule.get('cooldown_seconds') or 0))
                last_fired = float(self._camera_trigger_last_fired.get(rule_id, 0))
                now = time.time()
                if cooldown > 0 and (now - last_fired) < cooldown:
                    continue

                cam_id = str(rule.get('camera_id', '')).strip()
                if not cam_id:
                    continue
                duration = int(rule.get('duration_seconds') or 30)
                self._camera_trigger_last_fired[rule_id] = now
                self.broadcast_event('camera_alert', {
                    'cam_id': cam_id,
                    'type': str(rule.get('camera_type') or 'ring'),
                    'source': 'camera_trigger_rule',
                    'trigger_rule_id': rule_id,
                    'trigger_variable': key,
                    'duration_seconds': max(5, min(duration, 120)),
                    'timestamp': int(time.time())
                })

    def _set_ring_doorbell_state(self, cam_id: str, cam_name: str, event_id: str, ding_ts: Any, active: bool):
        if not self.data_gateway:
            return

        base = f"GATEWAY.RING.{cam_id}"
        self.data_gateway.update_telemetry(f"{base}.doorbell", bool(active))
        if event_id:
            self.data_gateway.update_telemetry(f"{base}.last_event_id", str(event_id))
        if ding_ts is not None:
            self.data_gateway.update_telemetry(f"{base}.last_ding_ts", ding_ts)

        if active:
            # Ring-Bridge beim Klingeln vorwärmen: reduziert Zeit bis Live-Bild sichtbar.
            try:
                stream_mgr = self.app_context.module_manager.get_module('stream_manager') if self.app_context else None
                if stream_mgr:
                    from modules.integrations.ring_module import get_ring_refresh_token
                    refresh_token = get_ring_refresh_token()
                    ring_cams = {c['cam_id']: c for c in self._get_ring_camera_configs()}
                    ring_cfg = ring_cams.get(cam_id)
                    if ring_cfg and refresh_token:
                        stream_mgr.start_ring_stream(cam_id, ring_cfg['device_id'], refresh_token)
            except Exception:
                pass

            self.broadcast_event('camera_alert', {
                'cam_id': cam_id,
                'name': cam_name,
                'type': 'ring',
                'source': 'ring_doorbell',
                'event_id': event_id,
                'timestamp': int(time.time())
            })

    def _ring_event_loop(self):
        while self._ring_event_active:
            try:
                ring_cams = self._get_ring_camera_configs()
                if not ring_cams:
                    time.sleep(3.0)
                    continue

                for cam in ring_cams:
                    cam_id = cam['cam_id']
                    device_id = cam['device_id']
                    cam_name = cam['name']

                    # Auto-reset des Doorbell-Pulses
                    until = self._ring_doorbell_until.get(cam_id)
                    if until and time.time() >= until:
                        self._ring_doorbell_until.pop(cam_id, None)
                        self._set_ring_doorbell_state(cam_id, cam_name, self._ring_last_event_ids.get(cam_id), None, False)

                    try:
                        from modules.integrations.ring_module import get_ring_latest_ding
                        result = get_ring_latest_ding(device_id)
                    except Exception:
                        continue

                    if not result.get('success'):
                        continue
                    event = result.get('event')
                    if not event:
                        continue

                    event_id = str(event.get('id') or '')
                    if not event_id:
                        continue

                    if self._ring_last_event_ids.get(cam_id) != event_id:
                        self._ring_last_event_ids[cam_id] = event_id
                        ding_ts = event.get('ding_ts')
                        self._ring_doorbell_until[cam_id] = time.time() + self._ring_doorbell_pulse_seconds
                        self._set_ring_doorbell_state(cam_id, cam_name, event_id, ding_ts, True)

                time.sleep(2.0)
            except Exception as e:
                logger.warning(f"Ring-Event-Monitor Fehler: {e}")
                time.sleep(3.0)

    def _start_ring_event_monitor(self):
        if self._ring_event_active:
            return
        # Trigger-Regeln aktualisieren (z. B. nach Ring-Import neuer Kameras)
        self._load_camera_trigger_rules()
        # Initialisiere bekannte Ring-Variablen mit Defaultwerten,
        # damit sie sofort im Gateway lesbar sind.
        if self.data_gateway:
            for cam in self._get_ring_camera_configs():
                self._set_ring_doorbell_state(cam['cam_id'], cam['name'], '', None, False)
        self._ring_event_active = True
        self._ring_event_thread = threading.Thread(target=self._ring_event_loop, daemon=True)
        self._ring_event_thread.start()
        logger.info("Ring Event Monitor gestartet")

    def _stop_ring_event_monitor(self):
        self._ring_event_active = False
        if self._ring_event_thread and self._ring_event_thread.is_alive():
            self._ring_event_thread.join(timeout=2.0)
        self._ring_event_thread = None

    def handle_telemetry_update(self, key: str, value: Any):
        """Hook für DataGateway-Telemetrieänderungen."""
        try:
            self._handle_camera_trigger_rules(key, value)
        except Exception as e:
            logger.debug(f"Trigger-Regelverarbeitung fehlgeschlagen ({key}): {e}")

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
        self._start_ring_event_monitor()

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
            self._stop_ring_event_monitor()

    def shutdown(self):
        self.running = False
        self._stop_ring_event_monitor()

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
