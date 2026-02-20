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
import hmac
import secrets
from collections import deque
from urllib.parse import urlparse
import uuid
import hashlib

# Flask & SocketIO (lazy import)
try:
    from flask import Flask, render_template, jsonify, request, send_file, has_request_context, g
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
        self._control_rate_limit = {}
        self._control_rate_limit_lock = threading.Lock()
        self._stream_viewers = {}
        self._stream_viewers_lock = threading.Lock()
        self._idempotency_results = {}
        self._idempotency_lock = threading.Lock()

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

        same_site = str(os.getenv('SMARTHOME_SESSION_COOKIE_SAMESITE', 'Lax') or 'Lax').strip().title()
        if same_site not in ('Lax', 'Strict', 'None'):
            same_site = 'Lax'
        secure_cookie = str(os.getenv('SMARTHOME_SESSION_COOKIE_SECURE', 'false')).strip().lower() in (
            '1', 'true', 'yes', 'on'
        )
        secret_key = str(os.getenv('SECRET_KEY', '') or '').strip()
        if secret_key:
            self.app.config['SECRET_KEY'] = secret_key
        else:
            # Fallback nur für Entwicklungs-/Notbetrieb: reduziert Risiko eines
            # hartkodierten Shared-Secrets in produktiven Deployments.
            self.app.config['SECRET_KEY'] = secrets.token_hex(32)
            logger.warning("SECRET_KEY nicht gesetzt: ephemerer Key wurde generiert")
        self.app.config['SESSION_COOKIE_HTTPONLY'] = True
        self.app.config['SESSION_COOKIE_SAMESITE'] = same_site
        self.app.config['SESSION_COOKIE_SECURE'] = secure_cookie

        # async_mode='threading' ist stabiler für Windows-Hosts
        cors_allowed_origins = self._get_allowed_origins()
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins=cors_allowed_origins if cors_allowed_origins else None,
            async_mode='threading'
        )

        @self.app.after_request
        def _disable_hls_cache(response):
            req_id = self._get_request_id()
            response.headers['X-Request-ID'] = req_id
            # HLS manifests/segments must not be cached, otherwise stale playlists
            # can reference already deleted TS fragments and trigger endless 404 loops.
            if request.path.startswith('/static/hls/'):
                self._update_stream_viewer_metrics(request.path, request.remote_addr)
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            elif request.path.startswith('/static/js/') or request.path.startswith('/static/css/'):
                # Avoid stale frontend bundles after backend hotfixes.
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            if self.data_gateway and hasattr(self.data_gateway, 'clear_correlation_id'):
                try:
                    self.data_gateway.clear_correlation_id()
                except Exception:
                    pass
            return response

        @self.app.before_request
        def _control_api_auth_gate():
            """Schützt kritische Steuer-Endpunkte gegen unautorisierte Aufrufe."""
            incoming_req_id = str(request.headers.get('X-Request-ID') or '').strip()
            g.request_id = incoming_req_id or uuid.uuid4().hex
            if self.data_gateway and hasattr(self.data_gateway, 'set_correlation_id'):
                try:
                    self.data_gateway.set_correlation_id(g.request_id)
                except Exception:
                    pass

            payload_ok, payload_error, payload_status = self._validate_api_payload()
            if not payload_ok:
                error_class = self._classify_payload_error(payload_status, payload_error)
                logger.warning(
                    "API payload rejected: req_id=%s method=%s path=%s remote=%s class=%s reason=%s",
                    self._get_request_id(),
                    request.method,
                    request.path,
                    request.remote_addr,
                    error_class,
                    payload_error
                )
                return jsonify({
                    'success': False,
                    'error': 'invalid_payload',
                    'error_class': error_class,
                    'message': payload_error
                }), payload_status

            if not self._is_protected_control_request():
                return None

            origin_ok, origin_reason = self._is_control_request_origin_allowed()
            if not origin_ok:
                logger.warning(
                    "Control API origin denied: req_id=%s method=%s path=%s remote=%s reason=%s",
                    self._get_request_id(),
                    request.method,
                    request.path,
                    request.remote_addr,
                    origin_reason
                )
                return jsonify({
                    'success': False,
                    'error': 'forbidden_origin',
                    'message': origin_reason
                }), 403

            allowed, retry_after = self._check_control_rate_limit()
            if not allowed:
                logger.warning(
                    "Control API rate limit exceeded: req_id=%s method=%s path=%s remote=%s retry_after=%ss",
                    self._get_request_id(),
                    request.method,
                    request.path,
                    request.remote_addr,
                    retry_after
                )
                response = jsonify({
                    'success': False,
                    'error': 'rate_limited',
                    'message': 'Zu viele Requests auf kritischen Endpunkten'
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(retry_after)
                return response

            authorized, reason = self._is_authorized_control_request()
            if authorized:
                return None

            logger.warning(
                "Control API access denied: req_id=%s method=%s path=%s remote=%s reason=%s",
                self._get_request_id(),
                request.method,
                request.path,
                request.remote_addr,
                reason
            )
            return jsonify({
                'success': False,
                'error': 'unauthorized',
                'message': reason
            }), 401

        self._register_routes()

    def _is_protected_control_request(self) -> bool:
        """Definiert, welche Endpunkte Authentifizierung erzwingen."""
        path = str(getattr(request, 'path', '') or '')
        method = str(getattr(request, 'method', 'GET') or 'GET').upper()

        if path.startswith('/api/admin'):
            return True

        protected_exact = {
            '/api/plc/connect',
            '/api/plc/disconnect',
            '/api/plc/ads/route/add',
            '/api/plc/ads/route/test',
            '/api/plc/config',
            '/api/plc/symbols/upload',
            '/api/plc/symbols/live',
            '/api/ring/auth',
            '/api/ring/cameras/import',
            '/api/routing/config',
            '/api/camera-triggers',
            '/api/camera-triggers/import',
            '/api/variables/write',
            '/api/cameras',
            '/api/cameras/alert',
            '/api/cameras/scan',
            '/api/cameras/diagnose',
        }
        if path in protected_exact and method in ('POST', 'PUT', 'DELETE'):
            return True

        if path.startswith('/api/cameras/'):
            # Kamera-/PTZ-/Stream-Endpunkte sind im Betrieb steuerkritisch.
            if method != 'GET':
                return True
            if '/ptz/' in path:
                return True

        return False

    def _is_authorized_control_request(self):
        """
        Prüft Authentifizierung für Control-Requests.

        Regeln:
        - Mit gesetztem API-Key: Header/Token muss passen.
        - Ohne gesetzten API-Key: nur Loopback-Zugriffe erlauben.
        - Optionaler Kompatibilitätsmodus: Loopback ohne Key zulassen.
        """
        expected_key = (
            os.getenv('SMARTHOME_ADMIN_API_KEY', '').strip()
            or os.getenv('ADMIN_API_KEY', '').strip()
        )
        provided_key = self._extract_admin_api_key()
        loopback = self._is_loopback_request()

        if not expected_key:
            if loopback:
                return True, ''
            return False, 'SMARTHOME_ADMIN_API_KEY ist nicht gesetzt (nur Loopback erlaubt)'

        allow_loopback_without_key = os.getenv(
            'SMARTHOME_ALLOW_LOOPBACK_WITHOUT_KEY',
            'true'
        ).strip().lower() in ('1', 'true', 'yes', 'on')

        if provided_key and hmac.compare_digest(provided_key, expected_key):
            return True, ''
        if loopback and allow_loopback_without_key:
            return True, ''
        if not provided_key:
            return False, 'API-Key fehlt (Header X-API-Key oder Authorization: Bearer ...)'
        return False, 'API-Key ungültig'

    def _extract_admin_api_key(self) -> str:
        """Extrahiert Admin-API-Key aus Header/Query."""
        key = (request.headers.get('X-API-Key') or '').strip()
        if key:
            return key

        auth_header = (request.headers.get('Authorization') or '').strip()
        if auth_header.lower().startswith('bearer '):
            return auth_header[7:].strip()

        return str(request.args.get('api_key', '') or '').strip()

    def _is_loopback_request(self) -> bool:
        """Erkennt lokale Zugriffe."""
        remote = str(request.remote_addr or '').strip().lower()
        return remote in ('127.0.0.1', '::1', 'localhost')

    def _get_request_id(self) -> str:
        """Liefert aktuelle Request-Korrelations-ID."""
        if not has_request_context():
            return "-"
        req_id = getattr(g, 'request_id', '')
        if req_id:
            return str(req_id)
        return "-"

    def _check_control_rate_limit(self):
        """
        Prüft Rate-Limit für kritische Endpunkte.

        Rückgabe:
        - (True, 0) wenn erlaubt
        - (False, retry_after_seconds) wenn limitiert
        """
        window_seconds_raw = os.getenv('SMARTHOME_CONTROL_RATE_LIMIT_WINDOW_SECONDS', '60').strip()
        max_requests_raw = os.getenv('SMARTHOME_CONTROL_RATE_LIMIT_MAX_REQUESTS', '120').strip()

        try:
            window_seconds = max(1, int(window_seconds_raw))
        except Exception:
            window_seconds = 60
        try:
            max_requests = max(1, int(max_requests_raw))
        except Exception:
            max_requests = 120

        exempt_loopback = os.getenv(
            'SMARTHOME_CONTROL_RATE_LIMIT_EXEMPT_LOOPBACK',
            'true'
        ).strip().lower() in ('1', 'true', 'yes', 'on')
        if exempt_loopback and self._is_loopback_request():
            return True, 0

        now = time.time()
        ip = str(request.remote_addr or 'unknown')
        path = str(request.path or '')
        key = f"{ip}:{path}"

        with self._control_rate_limit_lock:
            bucket = self._control_rate_limit.get(key)
            if bucket is None:
                bucket = deque()
                self._control_rate_limit[key] = bucket

            cutoff = now - window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= max_requests:
                retry_after = int(max(1, window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)

            # Opportunistisches Cleanup alter Buckets.
            if len(self._control_rate_limit) > 5000:
                stale_keys = [k for k, v in self._control_rate_limit.items() if not v or v[-1] < cutoff]
                for stale_key in stale_keys[:1000]:
                    self._control_rate_limit.pop(stale_key, None)

        return True, 0

    def _get_allowed_origins(self) -> List[str]:
        """
        Ermittelt erlaubte Browser-Origin(s) für Control Requests/Socket.
        """
        raw = str(os.getenv('SMARTHOME_ALLOWED_ORIGINS', '') or '').strip()
        if raw:
            parts = [p.strip().rstrip('/') for p in raw.split(',') if p.strip()]
            return sorted(set(parts))

        host = str(request.host_url).strip() if has_request_context() else ''
        if host:
            return [host.rstrip('/')]
        return []

    def _is_control_request_origin_allowed(self):
        """
        Browser-Origin Check (CSRF-Härtung) für kritische Endpunkte.
        """
        if str(request.method or 'GET').upper() in ('GET', 'HEAD', 'OPTIONS'):
            return True, ''

        origin = str(request.headers.get('Origin') or '').strip()
        referer = str(request.headers.get('Referer') or '').strip()
        if not origin and not referer:
            # Non-browser Clients (curl/service-to-service) haben oft keinen Origin.
            return True, ''

        allowed_origins = self._get_allowed_origins()
        if not allowed_origins:
            return True, ''

        allowed = set(allowed_origins)
        if origin:
            if origin.rstrip('/') in allowed:
                return True, ''
            return False, f'Origin nicht erlaubt: {origin}'

        # Fallback: Referer-Origin gegen erlaubte Origins prüfen.
        try:
            parsed = urlparse(referer)
            ref_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
        except Exception:
            ref_origin = ''
        if ref_origin and ref_origin in allowed:
            return True, ''
        return False, f'Referer nicht erlaubt: {referer}'

    def _camera_id_from_hls_path(self, path: str) -> str:
        filename = os.path.basename(str(path or '').strip())
        if not filename:
            return ''
        if filename.endswith('.m3u8'):
            return filename[:-5]
        if filename.endswith('.ts'):
            filename = filename[:-3]
            if '_' in filename:
                return filename.rsplit('_', 1)[0]
            return filename
        return ''

    def _update_stream_viewer_metrics(self, hls_path: str, remote_addr: str):
        cam_id = self._camera_id_from_hls_path(hls_path)
        if not cam_id:
            return
        ip = str(remote_addr or 'unknown').strip()
        now = time.time()
        with self._stream_viewers_lock:
            viewers = self._stream_viewers.setdefault(cam_id, {})
            viewers[ip] = now

            # Opportunistisches Cleanup alter Viewer-Einträge.
            cutoff = now - 30.0
            for cid, cmap in list(self._stream_viewers.items()):
                stale = [addr for addr, ts in cmap.items() if ts < cutoff]
                for addr in stale:
                    cmap.pop(addr, None)
                if not cmap:
                    self._stream_viewers.pop(cid, None)

    def _get_stream_viewer_counts(self) -> Dict[str, int]:
        now = time.time()
        counts = {}
        with self._stream_viewers_lock:
            cutoff = now - 30.0
            for cam_id, cmap in list(self._stream_viewers.items()):
                stale = [addr for addr, ts in cmap.items() if ts < cutoff]
                for addr in stale:
                    cmap.pop(addr, None)
                if cmap:
                    counts[cam_id] = len(cmap)
                else:
                    self._stream_viewers.pop(cam_id, None)
        return counts

    def _validate_api_payload(self):
        """
        Basale Payload-Validierung für mutierende API-Requests.
        """
        method = str(request.method or 'GET').upper()
        path = str(request.path or '')
        if method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return True, '', 200
        if not path.startswith('/api/'):
            return True, '', 200

        max_bytes_raw = str(os.getenv('SMARTHOME_MAX_API_BODY_BYTES', '1048576')).strip()
        max_keys_raw = str(os.getenv('SMARTHOME_MAX_API_JSON_KEYS', '200')).strip()
        try:
            max_bytes = max(1024, int(max_bytes_raw))
        except Exception:
            max_bytes = 1048576
        try:
            max_keys = max(10, int(max_keys_raw))
        except Exception:
            max_keys = 200
        max_depth_raw = str(os.getenv('SMARTHOME_MAX_API_JSON_DEPTH', '12')).strip()
        max_items_raw = str(os.getenv('SMARTHOME_MAX_API_JSON_ITEMS_PER_CONTAINER', '1000')).strip()
        max_string_len_raw = str(os.getenv('SMARTHOME_MAX_API_JSON_STRING_LENGTH', '8192')).strip()
        try:
            max_depth = max(2, int(max_depth_raw))
        except Exception:
            max_depth = 12
        try:
            max_items = max(10, int(max_items_raw))
        except Exception:
            max_items = 1000
        try:
            max_string_len = max(64, int(max_string_len_raw))
        except Exception:
            max_string_len = 8192

        content_length = request.content_length or 0
        if content_length > max_bytes:
            return False, f'Payload zu groß ({content_length}>{max_bytes} bytes)', 413

        # Upload-Endpunkte (multipart/form-data) separat behandeln.
        if path in ('/api/plc/symbols/upload', '/api/camera-triggers/import'):
            return True, '', 200

        mimetype = str(request.mimetype or '').lower()
        if mimetype.startswith('application/json'):
            data = request.get_json(silent=True)
            if data is None:
                return False, 'JSON-Body ungültig oder leer', 400
            if not isinstance(data, dict):
                return False, 'JSON-Body muss ein Objekt sein', 400
            if len(data) > max_keys:
                return False, f'Zu viele JSON-Felder ({len(data)}>{max_keys})', 400
            ok, reason = self._validate_json_structure(
                data,
                max_depth=max_depth,
                max_items=max_items,
                max_string_len=max_string_len
            )
            if not ok:
                return False, reason, 400

        return True, '', 200

    def _validate_json_structure(self, value: Any, max_depth: int, max_items: int, max_string_len: int, depth: int = 0):
        """Validiert JSON-Struktur rekursiv gegen harte Grenzen."""
        if depth > max_depth:
            return False, f'JSON-Struktur zu tief (>{max_depth})'

        if value is None or isinstance(value, (bool, int, float)):
            return True, ''

        if isinstance(value, str):
            if len(value) > max_string_len:
                return False, f'String-Feld zu lang ({len(value)}>{max_string_len})'
            return True, ''

        if isinstance(value, list):
            if len(value) > max_items:
                return False, f'Array zu groß ({len(value)}>{max_items})'
            for item in value:
                ok, reason = self._validate_json_structure(item, max_depth, max_items, max_string_len, depth + 1)
                if not ok:
                    return ok, reason
            return True, ''

        if isinstance(value, dict):
            if len(value) > max_items:
                return False, f'Objekt zu groß ({len(value)}>{max_items})'
            for key, nested_value in value.items():
                if not isinstance(key, str):
                    return False, 'JSON-Objekt enthält Nicht-String-Key'
                if len(key) > max_string_len:
                    return False, f'JSON-Key zu lang ({len(key)}>{max_string_len})'
                ok, reason = self._validate_json_structure(
                    nested_value,
                    max_depth,
                    max_items,
                    max_string_len,
                    depth + 1
                )
                if not ok:
                    return ok, reason
            return True, ''

        return False, f'Nicht unterstützter JSON-Typ: {type(value).__name__}'

    def _classify_payload_error(self, status_code: int, message: str) -> str:
        """Leitet Fehlerklasse für Payload-Rejects ab."""
        msg = str(message or '').lower()
        if int(status_code) == 413:
            return 'payload_too_large'
        if 'tief' in msg or 'array' in msg or 'objekt' in msg or 'json' in msg:
            return 'schema_validation_failed'
        return 'payload_validation_failed'

    def _get_idempotency_key(self) -> str:
        """Liest Idempotency-Key aus Request-Headern."""
        key = str(request.headers.get('Idempotency-Key') or '').strip()
        if not key:
            key = str(request.headers.get('X-Idempotency-Key') or '').strip()
        if not key:
            return ''

        max_len_raw = str(os.getenv('SMARTHOME_IDEMPOTENCY_KEY_MAX_LENGTH', '128')).strip()
        try:
            max_len = max(16, int(max_len_raw))
        except Exception:
            max_len = 128
        return key[:max_len]

    def _idempotency_request_fingerprint(self, payload: Any) -> str:
        """Erzeugt Fingerprint aus Methode+Pfad+Payload."""
        try:
            canonical = json.dumps(payload if payload is not None else {}, sort_keys=True, separators=(',', ':'))
        except Exception:
            canonical = str(payload)
        base = f"{request.method}:{request.path}:{canonical}"
        return hashlib.sha256(base.encode('utf-8')).hexdigest()

    def _prune_idempotency_cache(self, now: float):
        """Entfernt abgelaufene/alte Idempotency-Einträge."""
        max_entries_raw = str(os.getenv('SMARTHOME_IDEMPOTENCY_CACHE_MAX_ENTRIES', '5000')).strip()
        try:
            max_entries = max(100, int(max_entries_raw))
        except Exception:
            max_entries = 5000

        stale_keys = [k for k, v in self._idempotency_results.items() if float(v.get('expires_at', 0.0)) <= now]
        for key in stale_keys:
            self._idempotency_results.pop(key, None)

        if len(self._idempotency_results) > max_entries:
            by_created = sorted(
                self._idempotency_results.items(),
                key=lambda item: float(item[1].get('created_at', 0.0))
            )
            overflow = len(self._idempotency_results) - max_entries
            for key, _ in by_created[:overflow]:
                self._idempotency_results.pop(key, None)

    def _idempotency_precheck(self, payload: Any):
        """
        Prüft, ob ein identischer Request bereits verarbeitet wurde.
        """
        idem_key = self._get_idempotency_key()
        if not idem_key:
            return None

        cache_key = f"{request.method}:{request.path}:{idem_key}"
        fingerprint = self._idempotency_request_fingerprint(payload)
        now = time.time()

        with self._idempotency_lock:
            self._prune_idempotency_cache(now)
            existing = self._idempotency_results.get(cache_key)
            if not existing:
                return None

            if str(existing.get('fingerprint', '')) != fingerprint:
                response = jsonify({
                    'success': False,
                    'error': 'idempotency_key_reused_with_different_payload',
                    'message': 'Idempotency-Key wurde bereits mit anderem Payload verwendet'
                })
                response.status_code = 409
                response.headers['Idempotency-Key'] = idem_key
                response.headers['X-Idempotency-Replayed'] = 'false'
                return response

            response = jsonify(existing.get('body', {}))
            response.status_code = int(existing.get('status_code', 200))
            response.headers['Idempotency-Key'] = idem_key
            response.headers['X-Idempotency-Replayed'] = 'true'
            logger.info(
                "Idempotent replay served: req_id=%s path=%s key=%s",
                self._get_request_id(),
                request.path,
                idem_key
            )
            return response

    def _idempotency_store(self, payload: Any, body: Dict[str, Any], status_code: int):
        """Speichert Response für Wiederholungs-Requests mit Idempotency-Key."""
        idem_key = self._get_idempotency_key()
        if not idem_key:
            return
        if int(status_code) >= 500:
            return

        ttl_raw = str(os.getenv('SMARTHOME_IDEMPOTENCY_WINDOW_SECONDS', '30')).strip()
        try:
            ttl_seconds = max(1, int(ttl_raw))
        except Exception:
            ttl_seconds = 30

        now = time.time()
        cache_key = f"{request.method}:{request.path}:{idem_key}"
        entry = {
            'fingerprint': self._idempotency_request_fingerprint(payload),
            'body': body,
            'status_code': int(status_code),
            'created_at': now,
            'expires_at': now + ttl_seconds
        }
        with self._idempotency_lock:
            self._prune_idempotency_cache(now)
            self._idempotency_results[cache_key] = entry

    def _build_idempotent_json_response(self, payload: Any, body: Dict[str, Any], status_code: int = 200):
        """Erstellt JSON-Response und persistiert sie optional für Idempotency-Key."""
        self._idempotency_store(payload, body, status_code)
        response = jsonify(body)
        response.status_code = int(status_code)
        idem_key = self._get_idempotency_key()
        if idem_key:
            response.headers['Idempotency-Key'] = idem_key
            response.headers['X-Idempotency-Replayed'] = 'false'
        return response

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
            data = request.get_json() or {}
            ams_id = data.get('ams_id')
            runtime_type = str(data.get('runtime_type') or '').strip().upper()
            if runtime_type not in ('TC2', 'TC3'):
                runtime_type = 'TC3'
            raw_ams_port = data.get('ams_port', None)
            if raw_ams_port in (None, ''):
                ams_port = 801 if runtime_type == 'TC2' else 851
            else:
                try:
                    ams_port = int(raw_ams_port)
                except Exception:
                    ams_port = 801 if runtime_type == 'TC2' else 851
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
                config_mgr.set_config_value('plc_runtime_type', runtime_type)
                config_mgr.save_config()
                logger.info(f"PLC-Config gespeichert: {ams_id}:{ams_port} ({runtime_type})")

            try:
                plc.configure(ams_net_id=ams_id, port=ams_port)
                success = plc.connect()

                if success:
                    if self.data_gateway:
                        self.data_gateway.sync_widget_subscriptions()
                    return jsonify({'success': True, 'message': 'PLC verbunden', 'runtime_type': runtime_type, 'ams_port': ams_port})
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

        @self.app.route('/api/plc/ads/route/status', methods=['GET'])
        def plc_ads_route_status():
            """Liefert pyads/AMS-Routing Status (lokale AMS-Adresse, Verfügbarkeit)."""
            try:
                try:
                    import pyads
                except Exception as import_err:
                    return jsonify({
                        'success': True,
                        'available': False,
                        'error': f'pyads nicht verfügbar: {import_err}'
                    })

                local_ams_net_id = ''
                try:
                    pyads.open_port()
                    local_addr = pyads.get_local_address()
                    local_ams_net_id = str(getattr(local_addr, 'netid', local_addr) or '')
                finally:
                    try:
                        pyads.close_port()
                    except Exception:
                        pass

                return jsonify({
                    'success': True,
                    'available': True,
                    'local_ams_net_id': local_ams_net_id,
                    'runtime_defaults': {
                        'TC2': 801,
                        'TC3': 851
                    }
                })
            except Exception as e:
                logger.error(f"Fehler bei GET /api/plc/ads/route/status: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/plc/ads/route/add', methods=['POST'])
        def plc_ads_route_add():
            """
            Erstellt ADS-Route lokal und auf der PLC.
            Erwartet: local_ams_net_id, local_ip, plc_ams_net_id, plc_ip, username, password, route_name
            """
            data = request.get_json(silent=True) or {}
            local_ams_net_id = str(data.get('local_ams_net_id') or '').strip()
            local_ip = str(data.get('local_ip') or '').strip()
            plc_ams_net_id = str(data.get('plc_ams_net_id') or '').strip()
            plc_ip = str(data.get('plc_ip') or '').strip()
            username = str(data.get('username') or '').strip()
            password = str(data.get('password') or '')
            route_name = str(data.get('route_name') or 'SmartHomeWeb').strip() or 'SmartHomeWeb'

            if not local_ams_net_id:
                return jsonify({'success': False, 'error': 'local_ams_net_id fehlt'}), 400
            if not plc_ams_net_id:
                return jsonify({'success': False, 'error': 'plc_ams_net_id fehlt'}), 400
            if not plc_ip:
                return jsonify({'success': False, 'error': 'plc_ip fehlt'}), 400
            if not username:
                return jsonify({'success': False, 'error': 'username fehlt'}), 400
            if password == '':
                return jsonify({'success': False, 'error': 'password fehlt'}), 400

            if not local_ip:
                parts = local_ams_net_id.split('.')
                if len(parts) >= 4:
                    local_ip = '.'.join(parts[:4])

            warnings = []

            try:
                import pyads
            except Exception as import_err:
                return jsonify({'success': False, 'error': f'pyads nicht verfügbar: {import_err}'}), 500

            try:
                pyads.open_port()
                pyads.set_local_address(local_ams_net_id)

                try:
                    pyads.add_route(plc_ams_net_id, plc_ip)
                except Exception as add_route_err:
                    if 'exists' not in str(add_route_err).lower():
                        warnings.append(f"Lokale Route: {add_route_err}")

                try:
                    pyads.add_route_to_plc(
                        sending_net_id=local_ams_net_id,
                        adding_host_name=local_ip,
                        ip_address=plc_ip,
                        username=username,
                        password=password,
                        route_name=route_name
                    )
                except Exception as add_plc_err:
                    err_txt = str(add_plc_err)
                    if 'exists' in err_txt.lower():
                        warnings.append('Route existiert bereits auf der PLC')
                    else:
                        return jsonify({'success': False, 'error': f'PLC-Route fehlgeschlagen: {err_txt}', 'warnings': warnings}), 500

                return jsonify({
                    'success': True,
                    'message': 'ADS-Route angelegt',
                    'warnings': warnings,
                    'local_ams_net_id': local_ams_net_id,
                    'plc_ams_net_id': plc_ams_net_id,
                    'plc_ip': plc_ip,
                    'route_name': route_name
                })
            except Exception as e:
                logger.error(f"Fehler bei POST /api/plc/ads/route/add: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e), 'warnings': warnings}), 500
            finally:
                try:
                    pyads.close_port()
                except Exception:
                    pass

        @self.app.route('/api/plc/ads/route/test', methods=['POST'])
        def plc_ads_route_test():
            """Testet ADS-Verbindung via pyads.Connection(..., ip) nach Route-Setup."""
            data = request.get_json(silent=True) or {}
            plc_ams_net_id = str(data.get('plc_ams_net_id') or '').strip()
            plc_ip = str(data.get('plc_ip') or '').strip()
            ams_port_raw = data.get('ams_port', 801)
            try:
                ams_port = int(ams_port_raw)
            except Exception:
                ams_port = 801

            if not plc_ams_net_id:
                return jsonify({'success': False, 'error': 'plc_ams_net_id fehlt'}), 400
            if not plc_ip:
                return jsonify({'success': False, 'error': 'plc_ip fehlt'}), 400

            try:
                import pyads
            except Exception as import_err:
                return jsonify({'success': False, 'error': f'pyads nicht verfügbar: {import_err}'}), 500

            plc = None
            try:
                plc = pyads.Connection(plc_ams_net_id, ams_port, plc_ip)
                plc.set_timeout(6000)
                plc.open()
                name, version = plc.read_device_info()
                return jsonify({
                    'success': True,
                    'device_name': str(name),
                    'version': {
                        'version': int(getattr(version, 'version', 0)),
                        'revision': int(getattr(version, 'revision', 0)),
                        'build': int(getattr(version, 'build', 0))
                    }
                })
            except Exception as e:
                logger.error(f"Fehler bei POST /api/plc/ads/route/test: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
            finally:
                try:
                    if plc:
                        plc.close()
                except Exception:
                    pass

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
                'subscriptions': len(mqtt.subscriptions),
                'ingress': mqtt.get_ingress_stats() if hasattr(mqtt, 'get_ingress_stats') else {}
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
                limit = max(1, min(limit, 500))
                filter_mode = str(request.args.get('filter', 'all') or 'all').strip().lower()

                if filter_mode == 'restart':
                    # Restart-Events sind häufig nur Teilmenge: größeren Suchraum laden
                    # und anschließend serverseitig filtern.
                    search_limit = min(limit * 10, 5000)
                    logs = DatabaseLogger.get_recent_logs(db_path, limit=search_limit)
                    keywords = ('restart', 'neustart')
                    logs = [
                        log for log in logs
                        if any(k in str(log.get('message', '')).lower() for k in keywords)
                    ][:limit]
                else:
                    logs = DatabaseLogger.get_recent_logs(db_path, limit=limit)

                return jsonify(logs)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Logs: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/admin/logs/clear', methods=['POST'])
        def clear_system_logs():
            """Löscht alte Logs mit Schutz für Audit-relevante Einträge."""
            try:
                from modules.core.database_logger import DatabaseLogger

                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                db_path = os.path.join(project_root, 'config', 'system_logs.db')

                data = request.get_json(silent=True) or {}
                replay = self._idempotency_precheck(data)
                if replay is not None:
                    return replay
                keep_count = int(data.get('keep_count', 100))
                keep_count = max(10, min(keep_count, 5000))

                deleted = DatabaseLogger.clear_logs_with_audit_protection(
                    db_path=db_path,
                    keep_count=keep_count
                )

                logger.warning(
                    "Admin logs clear executed: req_id=%s deleted=%s keep_count=%s remote=%s",
                    self._get_request_id(),
                    deleted,
                    keep_count,
                    request.remote_addr
                )

                return self._build_idempotent_json_response(data, {
                    'success': True,
                    'deleted': deleted,
                    'keep_count': keep_count
                }, 200)
            except Exception as e:
                logger.error(f"Fehler bei POST /api/admin/logs/clear: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/admin/service/info')
        def get_service_info():
            """Service-Informationen"""
            try:
                from modules.core.service_manager import ServiceManager
                info = ServiceManager.get_restart_info()
                return jsonify(info)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/admin/service/restart', methods=['POST'])
        def restart_service():
            """Plant einen verzögerten Service-Restart."""
            try:
                from modules.core.service_manager import ServiceManager
                data = request.get_json(silent=True) or {}
                replay = self._idempotency_precheck(data)
                if replay is not None:
                    return replay
                try:
                    delay = int(data.get('delay', 2))
                except Exception:
                    delay = 2
                delay = max(1, min(delay, 30))
                logger.warning(
                    "Admin restart requested: req_id=%s type=app delay=%ss remote=%s ua=%s",
                    self._get_request_id(),
                    delay,
                    request.remote_addr,
                    request.headers.get('User-Agent', '-')
                )
                ServiceManager.schedule_restart(delay_seconds=delay)
                logger.warning(
                    "Admin restart scheduled: req_id=%s type=app delay=%ss remote=%s",
                    self._get_request_id(),
                    delay,
                    request.remote_addr
                )
                return self._build_idempotent_json_response(data, {
                    'success': True,
                    'message': f'Service-Neustart in {delay}s geplant'
                }, 200)
            except Exception as e:
                logger.error(f"Fehler bei POST /api/admin/service/restart: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/admin/service/restart-daemon', methods=['POST'])
        def restart_daemon_service():
            """Plant einen Dienst-Neustart ueber scripts/web_server_ctl.sh restart."""
            try:
                from modules.core.service_manager import ServiceManager
                data = request.get_json(silent=True) or {}
                replay = self._idempotency_precheck(data)
                if replay is not None:
                    return replay
                try:
                    delay = int(data.get('delay', 1))
                except Exception:
                    delay = 1
                logger.warning(
                    "Admin restart requested: req_id=%s type=daemon delay=%ss remote=%s ua=%s",
                    self._get_request_id(),
                    delay,
                    request.remote_addr,
                    request.headers.get('User-Agent', '-')
                )
                ok, message = ServiceManager.schedule_ctl_restart(delay_seconds=delay)
                if not ok:
                    logger.warning(
                        "Admin restart rejected: req_id=%s type=daemon remote=%s reason=%s",
                        self._get_request_id(),
                        request.remote_addr,
                        message
                    )
                    return self._build_idempotent_json_response(
                        data,
                        {'success': False, 'error': message},
                        400
                    )
                logger.warning(
                    "Admin restart scheduled: req_id=%s type=daemon delay=%ss remote=%s",
                    self._get_request_id(),
                    delay,
                    request.remote_addr
                )
                return self._build_idempotent_json_response(
                    data,
                    {'success': True, 'message': message},
                    200
                )
            except Exception as e:
                logger.error(f"Fehler bei POST /api/admin/service/restart-daemon: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

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

            gateway = self.app_context.module_manager.get_module('data_gateway')
            if gateway:
                try:
                    gw_status = gateway.get_system_status()
                    stats['protocols']['gateway'] = {
                        'name': 'Data Gateway',
                        'telemetry_count': gw_status.get('telemetry_count', 0),
                        'telemetry_evictions': gw_status.get('telemetry_evictions', 0),
                        'polling_backpressure_skips': gw_status.get('polling_backpressure_skips', 0),
                        'limits': gw_status.get('limits', {})
                    }
                except Exception:
                    pass

            return jsonify(stats)

        @self.app.route('/api/monitor/latency')
        def measure_latency():
            """Latenz-Messung für Monitoring"""
            return jsonify({
                'timestamp': time.time(),
                'latency_ms': 0.5  # Stub - echte Messung würde über PLC gehen
            })

        @self.app.route('/api/monitor/streams')
        def monitor_streams():
            """Debug/Health-Metriken für RTSP/Ring Streams."""
            try:
                stream_mgr = self.app_context.module_manager.get_module('stream_manager')
                if not stream_mgr:
                    return jsonify({'success': False, 'error': 'stream_manager nicht verfügbar'}), 503

                payload = stream_mgr.get_debug_metrics()
                viewer_counts = self._get_stream_viewer_counts()
                streams = payload.get('streams', {})
                for cam_id, data in streams.items():
                    data['client_count'] = int(viewer_counts.get(cam_id, 0))

                payload['viewer_ttl_seconds'] = 30
                payload['success'] = True
                return jsonify(payload)
            except Exception as e:
                logger.error(f"Fehler bei GET /api/monitor/streams: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

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

        @self.app.route('/api/routing/config', methods=['GET', 'POST'])
        def routing_config():
            """Liest/aktualisiert Routing-Regeln (versioniert, legacy-kompatibel)."""
            try:
                if request.method == 'GET':
                    return jsonify(self._load_routing_config_json())

                data = request.get_json(silent=True) or {}
                payload = data.get('payload') if isinstance(data.get('payload'), dict) else data
                if not isinstance(payload, dict):
                    return jsonify({'success': False, 'error': 'Ungültiges JSON-Payload'}), 400

                source_version = str(payload.get('version') or '1.0')
                ok_version, version_msg = self._validate_routing_import_version(source_version)
                if not ok_version:
                    return jsonify({'success': False, 'error': version_msg}), 400

                raw_routes = payload.get('routes')
                if not isinstance(raw_routes, list):
                    return jsonify({'success': False, 'error': 'routes muss eine Liste sein'}), 400

                normalized_routes, warnings, errors = self._normalize_routing_rules(raw_routes)
                if errors:
                    return jsonify({
                        'success': False,
                        'error': 'Import enthält ungültige Routen',
                        'errors': errors,
                        'warnings': warnings
                    }), 400

                current_cfg = self._load_routing_config_json()
                settings = payload.get('settings') if isinstance(payload.get('settings'), dict) else current_cfg.get('settings', {})
                description = str(payload.get('description') or current_cfg.get('description') or 'Routing-Konfiguration')
                out = {
                    'version': self._routing_schema_version(),
                    'description': description,
                    'routes': normalized_routes,
                    'settings': settings if isinstance(settings, dict) else {}
                }

                path = self._routing_config_path()
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(out, f, indent=2, ensure_ascii=False)

                if self.data_gateway and hasattr(self.data_gateway, '_load_routing_config'):
                    try:
                        self.data_gateway._load_routing_config()
                    except Exception as reload_err:
                        logger.warning(f"Routing-Config gespeichert, Reload fehlgeschlagen: {reload_err}")

                return jsonify({'success': True, 'warnings': warnings, 'config': out})
            except Exception as e:
                logger.error(f"Fehler bei /api/routing/config: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

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
                source_version = str(data.get('version') or '1.0')
                ok_version, version_msg = self._validate_trigger_import_version(source_version)
                if not ok_version:
                    return jsonify({'success': False, 'error': version_msg}), 400

                normalized_rules, warnings, errors = self._normalize_camera_trigger_rules(rules)
                if errors:
                    return jsonify({
                        'success': False,
                        'error': 'Import enthält ungültige Regeln',
                        'errors': errors,
                        'warnings': warnings
                    }), 400

                if self._trigger_store:
                    stored = self._trigger_store.replace_rules(normalized_rules)
                    self._camera_trigger_rules = stored
                    self._camera_trigger_state = {}
                    self._camera_trigger_last_fired = {}
                else:
                    path = os.path.join(os.path.abspath(os.getcwd()), 'config', 'camera_triggers.json')
                    payload = {'version': self._camera_trigger_schema_version(), 'rules': normalized_rules}
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)
                    self._load_camera_trigger_rules()

                return jsonify({'success': True, 'rules': self._camera_trigger_rules, 'warnings': warnings})
            except Exception as e:
                logger.error(f"Fehler bei /api/camera-triggers: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/camera-triggers/export', methods=['GET'])
        def export_camera_triggers():
            """Exportiert versionierte Kamera-Trigger-Regeln als JSON."""
            try:
                self._load_camera_trigger_rules()
                payload = {
                    'format': 'camera_trigger_rules',
                    'version': self._camera_trigger_schema_version(),
                    'exported_at': int(time.time()),
                    'rules': self._camera_trigger_rules
                }
                resp = jsonify(payload)
                resp.headers['Content-Disposition'] = f'attachment; filename="camera_trigger_rules_v{self._camera_trigger_schema_version()}.json"'
                return resp
            except Exception as e:
                logger.error(f"Fehler bei /api/camera-triggers/export: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/camera-triggers/import', methods=['POST'])
        def import_camera_triggers():
            """Importiert versionierte/legacy Kamera-Trigger-Regeln mit Kompatibilitätsprüfung."""
            try:
                data = request.get_json(silent=True) or {}
                payload = data.get('payload') if isinstance(data.get('payload'), dict) else data
                if not isinstance(payload, dict):
                    return jsonify({'success': False, 'error': 'Ungültiges JSON-Payload'}), 400

                source_version = str(payload.get('version') or '1.0')
                ok_version, version_msg = self._validate_trigger_import_version(source_version)
                if not ok_version:
                    return jsonify({'success': False, 'error': version_msg}), 400

                raw_rules = payload.get('rules')
                if not isinstance(raw_rules, list):
                    return jsonify({'success': False, 'error': 'rules muss eine Liste sein'}), 400

                normalized_rules, warnings, errors = self._normalize_camera_trigger_rules(raw_rules)
                if errors:
                    return jsonify({
                        'success': False,
                        'error': 'Import enthält ungültige Regeln',
                        'errors': errors,
                        'warnings': warnings
                    }), 400

                mode = str(data.get('mode') or 'replace').strip().lower()
                if mode not in ('replace', 'merge'):
                    mode = 'replace'

                if mode == 'merge':
                    self._load_camera_trigger_rules()
                    existing = {str(r.get('id')): r for r in self._camera_trigger_rules}
                    for r in normalized_rules:
                        existing[str(r.get('id'))] = r
                    normalized_rules = list(existing.values())

                if self._trigger_store:
                    stored = self._trigger_store.replace_rules(normalized_rules)
                    self._camera_trigger_rules = stored
                    self._camera_trigger_state = {}
                    self._camera_trigger_last_fired = {}
                else:
                    path = os.path.join(os.path.abspath(os.getcwd()), 'config', 'camera_triggers.json')
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump({'version': self._camera_trigger_schema_version(), 'rules': normalized_rules}, f, indent=2, ensure_ascii=False)
                    self._load_camera_trigger_rules()

                return jsonify({
                    'success': True,
                    'imported': len(normalized_rules),
                    'rules': self._camera_trigger_rules,
                    'warnings': warnings,
                    'mode': mode
                })
            except Exception as e:
                logger.error(f"Fehler bei /api/camera-triggers/import: {e}", exc_info=True)
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
                data = request.get_json(silent=True) or {}
                replay = self._idempotency_precheck(data)
                if replay is not None:
                    return replay
                plc_id = data.get('plc_id', 'plc_001')
                variable = data.get('variable')
                value = data.get('value')

                if not variable:
                    return self._build_idempotent_json_response(
                        data,
                        {'status': 'error', 'message': 'Variable fehlt'},
                        400
                    )

                # Gateway-interne Variablen (nicht-PLC) direkt in Telemetrie schreiben
                if variable.startswith('GATEWAY.') and self.data_gateway:
                    self.data_gateway.update_telemetry(variable, value)
                    logger.info(f"✍️  Gateway-Variable geschrieben: {variable} = {value}")
                    return self._build_idempotent_json_response(data, {
                        'status': 'success',
                        'message': 'Gateway-Variable geschrieben',
                        'variable': variable,
                        'value': value,
                        'plc_id': plc_id
                    }, 200)

                # Schreibe über Data Gateway
                success = self.data_gateway.write_variable(variable, value, plc_id)

                if success:
                    logger.info(f"✍️  Variable geschrieben: {plc_id}/{variable} = {value}")
                    return self._build_idempotent_json_response(data, {
                        'status': 'success',
                        'message': 'Variable geschrieben',
                        'variable': variable,
                        'value': value,
                        'plc_id': plc_id
                    }, 200)
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
                emit('request_context', {'correlation_id': f"ws-connect-{client_id[:8]}-{int(time.time() * 1000)}"})

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

    def _routing_config_path(self) -> str:
        return os.path.join(os.path.abspath(os.getcwd()), 'config', 'routing.json')

    @staticmethod
    def _routing_schema_version() -> str:
        return "1.0"

    def _validate_routing_import_version(self, source_version: str):
        """Prüft, ob eine Routing-Import-Version unterstützt wird."""
        try:
            src = str(source_version or '1.0').strip()
            major = int(src.split('.', 1)[0])
            current_major = int(self._routing_schema_version().split('.', 1)[0])
            if major <= current_major:
                return True, ''
            return False, f'Import-Version {src} wird von Schema {self._routing_schema_version()} nicht unterstützt'
        except Exception:
            return False, f'Ungültige Versionsangabe: {source_version}'

    def _load_routing_config_json(self) -> Dict[str, Any]:
        path = self._routing_config_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
                    if isinstance(data, dict):
                        data.setdefault('version', self._routing_schema_version())
                        data.setdefault('description', 'Routing-Konfiguration')
                        data.setdefault('routes', [])
                        data.setdefault('settings', {})
                        return data
            except Exception as e:
                logger.warning(f"Konnte routing.json nicht laden: {e}")
        return {
            'version': self._routing_schema_version(),
            'description': 'Routing-Konfiguration',
            'routes': [],
            'settings': {}
        }

    def _normalize_routing_rules(self, routes: List[Dict[str, Any]]):
        normalized = []
        warnings = []
        errors = []
        used_ids = set()

        for idx, raw in enumerate(routes):
            if not isinstance(raw, dict):
                errors.append(f"Route {idx + 1}: muss ein Objekt sein")
                continue

            route_id = str(raw.get('id') or f"route_{idx + 1}").strip()
            if not route_id:
                route_id = f"route_{idx + 1}"
            if route_id in used_ids:
                suffix = 2
                base_id = route_id
                while f"{base_id}_{suffix}" in used_ids:
                    suffix += 1
                route_id = f"{base_id}_{suffix}"
                warnings.append(f"Doppelte Route-ID erkannt, umbenannt zu {route_id}")
            used_ids.add(route_id)

            from_pattern = str(raw.get('from') or raw.get('pattern') or '').strip()
            if not from_pattern:
                errors.append(f"Route {route_id}: from fehlt")
                continue

            raw_to = raw.get('to')
            if isinstance(raw_to, str):
                to_targets = [t.strip() for t in raw_to.split(',') if t.strip()]
            elif isinstance(raw_to, list):
                to_targets = [str(t).strip() for t in raw_to if str(t).strip()]
            elif raw.get('target'):
                to_targets = [str(raw.get('target')).strip()]
            else:
                to_targets = []

            if not to_targets:
                errors.append(f"Route {route_id}: to fehlt")
                continue

            normalized.append({
                'id': route_id,
                'description': str(raw.get('description') or route_id),
                'from': from_pattern,
                'to': to_targets,
                'enabled': bool(raw.get('enabled', True))
            })

        return normalized, warnings, errors

    def _camera_trigger_config_path(self) -> str:
        return os.path.join(os.path.abspath(os.getcwd()), 'config', 'camera_triggers.json')

    @staticmethod
    def _camera_trigger_schema_version() -> str:
        return "2.0"

    def _validate_trigger_import_version(self, source_version: str):
        """Prüft, ob eine Import-Version unterstützt wird."""
        try:
            src = str(source_version or '1.0').strip()
            major = int(src.split('.', 1)[0])
            current_major = int(self._camera_trigger_schema_version().split('.', 1)[0])
            if major <= current_major:
                return True, ''
            return False, f'Import-Version {src} wird von Schema {self._camera_trigger_schema_version()} nicht unterstützt'
        except Exception:
            return False, f'Ungültige Versionsangabe: {source_version}'

    def _available_camera_ids(self):
        cams = set()
        try:
            path = os.path.join(os.path.abspath(os.getcwd()), 'config', 'cameras.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
                    for cam_id in (data.get('cameras') or {}).keys():
                        cams.add(str(cam_id))
        except Exception:
            pass
        return cams

    def _available_variable_names(self):
        vars_set = set()
        try:
            symbols = []
            if self.symbol_browser:
                symbols = self.symbol_browser.get_symbols('plc_001', force_refresh=False) or []
            symbols.extend(self._get_gateway_virtual_symbols())
            for s in symbols:
                if isinstance(s, dict) and s.get('name'):
                    vars_set.add(str(s.get('name')))
        except Exception:
            pass
        return vars_set

    def _normalize_camera_trigger_rules(self, rules: List[Dict[str, Any]]):
        normalized = []
        warnings = []
        errors = []
        camera_ids = self._available_camera_ids()
        known_variables = self._available_variable_names()

        for idx, raw in enumerate(rules):
            if not isinstance(raw, dict):
                errors.append(f"Regel {idx + 1}: muss ein Objekt sein")
                continue

            rule_id = str(raw.get('id') or f"rule_{idx + 1}").strip()
            if not rule_id:
                errors.append(f"Regel {idx + 1}: id fehlt")
                continue

            variable = str(raw.get('variable') or raw.get('symbol') or raw.get('key') or '').strip()
            if not variable:
                errors.append(f"Regel {rule_id}: variable fehlt")
                continue

            camera_id = str(raw.get('camera_id') or raw.get('cam_id') or raw.get('camera') or '').strip()
            if not camera_id:
                errors.append(f"Regel {rule_id}: camera_id fehlt")
                continue

            operator = str(raw.get('operator') or 'eq').strip().lower()
            if operator not in ('eq', '==', 'ne', '!=', 'gt', '>', 'gte', '>=', 'lt', '<', 'lte', '<=', 'contains'):
                warnings.append(f"Regel {rule_id}: Operator {operator} unbekannt, setze eq")
                operator = 'eq'

            enabled = bool(raw.get('enabled', True))
            if camera_ids and camera_id not in camera_ids:
                warnings.append(f"Regel {rule_id}: Kamera {camera_id} nicht vorhanden, Regel wird deaktiviert")
                enabled = False
            if known_variables and variable not in known_variables:
                warnings.append(f"Regel {rule_id}: Variable {variable} unbekannt, Regel wird deaktiviert")
                enabled = False

            raw_tags = raw.get('tags')
            if isinstance(raw_tags, str):
                tags = [t.strip().lower() for t in raw_tags.split(',') if t.strip()]
            elif isinstance(raw_tags, list):
                tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]
            else:
                tags = []

            category = str(raw.get('category') or raw.get('group') or 'general').strip().lower()
            category = ''.join(ch for ch in category if ch.isalnum() or ch in ('_', '-')) or 'general'

            try:
                duration = max(5, min(int(raw.get('duration_seconds', 30)), 300))
            except Exception:
                duration = 30
            try:
                cooldown = max(0, min(int(raw.get('cooldown_seconds', 0)), 3600))
            except Exception:
                cooldown = 0

            normalized.append({
                'id': rule_id,
                'name': str(raw.get('name') or rule_id),
                'enabled': enabled,
                'variable': variable,
                'operator': operator,
                'on_value': raw.get('on_value', True),
                'category': category,
                'tags': list(dict.fromkeys(tags)),
                'camera_id': camera_id,
                'camera_type': str(raw.get('camera_type') or raw.get('type') or 'ring'),
                'duration_seconds': duration,
                'cooldown_seconds': cooldown
            })

        return normalized, warnings, errors

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

    def broadcast_telemetry(self, key: str, value: Any, correlation_id: str = None):
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
            'timestamp': time.time(),
            'correlation_id': correlation_id or self._get_request_id()
        })
        logger.debug("Socket telemetry_update: key=%s cid=%s", key, correlation_id or self._get_request_id())

    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """
        Sendet Custom Event an alle Clients

        Args:
            event_type: Event-Name
            data: Event-Daten
        """
        if not self.running or not self.socketio:
            return

        payload = dict(data or {})
        payload.setdefault('correlation_id', self._get_request_id())
        self.socketio.emit(event_type, payload)
        logger.info("Socket event emitted: type=%s cid=%s", event_type, payload.get('correlation_id'))

    def broadcast_system_event(self, data: Dict[str, Any]):
        """Broadcastet System-Ereignisse mit Korrelations-ID."""
        self.broadcast_event('system_event', data)

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
