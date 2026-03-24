from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List


logger = logging.getLogger(__name__)

RING_LOGIN_URL = "https://account.ring.com/account/login"
RING_HELP_URL = "https://support.help.ring.com/"


def _find_keyword_in_payload(payload: Any, keywords: set[str]) -> str:
    stack = [payload]
    visited = set()
    while stack:
        current = stack.pop()
        obj_id = id(current)
        if obj_id in visited:
            continue
        visited.add(obj_id)

        if isinstance(current, dict):
            for value in current.values():
                stack.append(value)
            continue
        if isinstance(current, (list, tuple, set)):
            for value in current:
                stack.append(value)
            continue

        text = str(current or '').strip().lower()
        if not text:
            continue
        for keyword in keywords:
            if keyword in text:
                return keyword
    return ''


def _derive_ring_trigger(event: Dict[str, Any]) -> str:
    kind = str(event.get('kind') or 'unknown').strip().lower() or 'unknown'
    if kind == 'ding':
        return 'ding'

    package_hint = _find_keyword_in_payload(
        {
            'subtype': event.get('subtype'),
            'event_type': event.get('event_type'),
            'event_subtype': event.get('event_subtype'),
            'detection_type': event.get('detection_type'),
            'object_type': event.get('object_type'),
            'cv_detection_type': event.get('cv_detection_type'),
            'label': event.get('label'),
            'category': event.get('category'),
            'properties': event.get('properties'),
            'attributes': event.get('attributes'),
            'cv_properties': event.get('cv_properties'),
        },
        {'package', 'parcel', 'delivery'}
    )
    if package_hint:
        return 'package'

    if kind == 'motion':
        return 'motion'
    if kind == 'on_demand':
        return 'on_demand'
    return kind


def _normalize_ring_event_entry(
    cam_id: str,
    cam_name: str,
    device_id: str,
    event: Dict[str, Any],
    source: str = "ring_api",
) -> Dict[str, Any]:
    kind = str(event.get('kind') or 'unknown').strip() or 'unknown'
    return {
        'id': str(event.get('id') or '').strip(),
        'cam_id': str(cam_id or '').strip(),
        'camera_name': str(cam_name or cam_id or 'Ring Kamera').strip(),
        'device_id': str(device_id or '').strip(),
        'kind': kind,
        'trigger': str(event.get('trigger') or _derive_ring_trigger(event) or kind).strip() or kind,
        'created_at': event.get('created_at'),
        'created_at_local': event.get('created_at_local'),
        'ding_ts': event.get('ding_ts'),
        'answered': event.get('answered'),
        'state': event.get('state'),
        'source': str(source or event.get('source') or 'ring_api').strip() or 'ring_api',
        'subtype': event.get('subtype'),
        'event_type': event.get('event_type'),
        'event_subtype': event.get('event_subtype'),
        'detection_type': event.get('detection_type'),
        'object_type': event.get('object_type'),
        'cv_detection_type': event.get('cv_detection_type'),
        'label': event.get('label'),
        'category': event.get('category'),
        'properties': event.get('properties') if isinstance(event.get('properties'), dict) else None,
        'attributes': event.get('attributes') if isinstance(event.get('attributes'), dict) else None,
        'cv_properties': event.get('cv_properties') if isinstance(event.get('cv_properties'), dict) else None,
    }


def _build_ring_issue_hints(error_text: Any) -> List[Dict[str, str]]:
    message = str(error_text or "").strip()
    if not message:
        return []

    normalized = message.lower()
    hints: List[Dict[str, str]] = []

    if "406" in normalized and "session" in normalized:
        hints.extend([
            {
                "level": "warning",
                "title": "Ring-Session wird abgelehnt",
                "message": "Ring verweigert aktuell die Session-Erstellung. Meist hilft eine frische Anmeldung oder eine Bestätigung im Ring-Konto.",
            },
            {
                "level": "info",
                "title": "Neu authentifizieren",
                "message": "Auf der Kameraseite Ring Benutzer, Passwort und bei Bedarf den 2FA-Code eintragen und danach 'Ring verbinden' erneut ausführen.",
            },
            {
                "level": "info",
                "title": "Ring-Konto prüfen",
                "message": "Falls Ring eine Gerätefreigabe, Sicherheitsabfrage oder Konto-Bestätigung verlangt, diese zuerst im Ring-Login oder Help-Center abschließen.",
            },
        ])
    elif "2fa" in normalized or "otp" in normalized or "verification" in normalized:
        hints.append({
            "level": "warning",
            "title": "2FA / Verifizierung erforderlich",
            "message": "Bitte den aktuellen Ring-Verifizierungscode eingeben und die Anmeldung erneut starten.",
        })
    elif "401" in normalized or "unauthorized" in normalized or "auth" in normalized:
        hints.append({
            "level": "warning",
            "title": "Ring-Authentifizierung prüfen",
            "message": "Die gespeicherte Ring-Anmeldung scheint ungültig zu sein. Bitte Ring neu verbinden.",
        })
    elif "timeout" in normalized:
        hints.append({
            "level": "warning",
            "title": "Ring antwortet zu langsam",
            "message": "Die History-Anfrage lief in ein Timeout. Später erneut versuchen oder die Anmeldung erneuern.",
        })

    return hints


def _extract_ring_error_code(error_text: Any) -> str:
    message = str(error_text or "").lower()
    if "406" in message:
        return "406"
    if "401" in message:
        return "401"
    if "timeout" in message:
        return "timeout"
    if "2fa" in message or "otp" in message or "verification" in message:
        return "2fa"
    return ""


def _record_ring_health_snapshot(
    manager: Any,
    *,
    success: bool,
    error_text: str = "",
    reauth_recommended: bool = False,
) -> Dict[str, Any]:
    now = time.time()
    previous = manager._get_ring_event_health() or {}
    snapshot = {
        'last_pull_attempt_at': now,
        'last_successful_pull_at': previous.get('last_successful_pull_at'),
        'last_error_at': previous.get('last_error_at'),
        'last_error_message': previous.get('last_error_message') or '',
        'last_error_code': previous.get('last_error_code') or '',
        'estimated_reauth_by': previous.get('estimated_reauth_by'),
        'reauth_recommended': bool(previous.get('reauth_recommended')),
    }
    if success:
        snapshot.update({
            'last_successful_pull_at': now,
            'last_error_at': None,
            'last_error_message': '',
            'last_error_code': '',
            'estimated_reauth_by': now + (30 * 24 * 60 * 60),
            'reauth_recommended': False,
        })
    else:
        snapshot.update({
            'last_error_at': now,
            'last_error_message': str(error_text or '').strip(),
            'last_error_code': _extract_ring_error_code(error_text),
            'reauth_recommended': bool(reauth_recommended),
        })
    return manager._record_ring_event_health(snapshot)


def register_ring_routes(
    manager: Any,
    load_cameras_config: Callable[[], Dict[str, Any]],
    save_cameras_config: Callable[[Dict[str, Any]], None],
) -> None:
    app = manager.app
    request = _get_flask_request()
    jsonify = _get_flask_jsonify()

    @app.route('/api/ring/status', methods=['GET'])
    def ring_status():
        try:
            from modules.integrations.ring_module import get_ring_status

            status = get_ring_status()
            status['live_enabled'] = is_ring_live_enabled(manager._load_feature_flags)
            status['live_on_ding'] = is_ring_live_on_ding_enabled(manager, manager._load_feature_flags)
            status['live_on_ding_seconds'] = ring_live_on_ding_seconds(manager)
            status['live_on_ding_active'] = [
                cam_id for cam_id, until in manager._ring_live_until.items()
                if until and time.time() < float(until)
            ]
            status['help_links'] = {
                'login_url': RING_LOGIN_URL,
                'help_url': RING_HELP_URL,
            }
            return jsonify(status)
        except Exception as e:
            logger.error("Fehler bei GET /api/ring/status: %s", e, exc_info=True)
            return jsonify({'available': False, 'configured': False, 'error': str(e)}), 500

    @app.route('/api/gateway/ring-live-settings', methods=['GET', 'POST'])
    def gateway_ring_live_settings():
        try:
            if request.method == 'GET':
                return jsonify({'success': True, 'settings': manager._load_gateway_settings()})

            payload = request.get_json(silent=True) or {}
            saved = manager._save_gateway_settings(payload)
            return jsonify({'success': True, 'settings': saved})
        except Exception as e:
            logger.error("Fehler bei /api/gateway/ring-live-settings: %s", e, exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/ring/auth', methods=['POST'])
    def ring_auth():
        try:
            data = request.json or {}
            username = (data.get('username') or '').strip()
            password = data.get('password') or ''
            otp_raw = (data.get('otp') or '').strip()
            otp = ''.join(ch for ch in otp_raw if ch.isdigit()) or None
            user_agent = (data.get('user_agent') or '').strip() or None

            from modules.integrations.ring_module import authenticate_ring

            result = authenticate_ring(username, password, otp=otp, user_agent=user_agent)
            status = 200 if result.get('success') else (400 if 'Keine gespeicherten Ring-Zugangsdaten' in str(result.get('error') or '') else 401)
            return jsonify(result), status
        except Exception as e:
            logger.error("Fehler bei POST /api/ring/auth: %s", e, exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/ring/cameras', methods=['GET'])
    def ring_list_cameras():
        try:
            from modules.integrations.ring_module import list_ring_cameras

            result = list_ring_cameras()
            if result.get('success'):
                return jsonify(result)
            return jsonify(result), 401
        except Exception as e:
            logger.error("Fehler bei GET /api/ring/cameras: %s", e, exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/ring/events', methods=['GET'])
    def ring_list_events():
        try:
            limit = max(1, min(int(request.args.get('limit', 25)), 100))
            kinds = str(request.args.get('kinds', '') or '').strip()
            result = manager._list_ring_events(limit=limit, kinds=kinds)
            status = 200 if result.get('success') else 500
            return jsonify(result), status
        except Exception as e:
            logger.error("Fehler bei GET /api/ring/events: %s", e, exc_info=True)
            return jsonify({'success': False, 'error': str(e), 'events': []}), 500

    @app.route('/api/ring/diagnostics', methods=['GET'])
    def ring_diagnostics():
        try:
            limit = max(1, min(int(request.args.get('limit', 10)), 25))
            from modules.integrations.ring_module import get_ring_history_diagnostics

            diagnostics = []
            for cam in get_ring_camera_configs(manager):
                result = get_ring_history_diagnostics(cam['device_id'], limit=limit)
                checks = result.get('checks') if isinstance(result, dict) else {}
                if isinstance(checks, dict):
                    for check in checks.values():
                        if isinstance(check, dict):
                            check['hints'] = _build_ring_issue_hints(check.get('error'))
                diagnostics.append({
                    'cam_id': cam['cam_id'],
                    'camera_name': cam['name'],
                    'device_id': cam['device_id'],
                    **result,
                })

            success = any(item.get('success') for item in diagnostics) if diagnostics else True
            aggregated_hints: List[Dict[str, str]] = []
            seen_hint_keys = set()
            first_error = ''
            reauth_recommended = False
            for item in diagnostics:
                checks = item.get('checks') if isinstance(item, dict) else {}
                if not isinstance(checks, dict):
                    continue
                for check in checks.values():
                    if not isinstance(check, dict):
                        continue
                    if not first_error and check.get('error'):
                        first_error = str(check.get('error') or '').strip()
                    for hint in check.get('hints') or []:
                        if not isinstance(hint, dict):
                            continue
                        key = (hint.get('title'), hint.get('message'))
                        if key in seen_hint_keys:
                            continue
                        seen_hint_keys.add(key)
                        aggregated_hints.append(hint)
                        if str(hint.get('title') or '').lower().startswith('ring-session') or 'auth' in str(hint.get('title') or '').lower():
                            reauth_recommended = True
            health = _record_ring_health_snapshot(
                manager,
                success=success,
                error_text=first_error,
                reauth_recommended=reauth_recommended,
            )
            return jsonify({
                'success': success,
                'diagnostics': diagnostics,
                'storage': manager._get_ring_event_storage_status(),
                'health': health,
                'help_links': {
                    'login_url': RING_LOGIN_URL,
                    'help_url': RING_HELP_URL,
                },
                'guidance': {
                    'reauth_recommended': bool(aggregated_hints),
                    'hints': aggregated_hints,
                },
            })
        except Exception as e:
            logger.error("Fehler bei GET /api/ring/diagnostics: %s", e, exc_info=True)
            return jsonify({'success': False, 'error': str(e), 'diagnostics': []}), 500

    @app.route('/api/ring/cameras/import', methods=['POST'])
    def ring_import_camera():
        try:
            data = request.json or {}
            ring_device_id = str(data.get('ring_device_id', '')).strip()
            if not ring_device_id:
                return jsonify({'success': False, 'error': 'ring_device_id erforderlich'}), 400

            cam_id = str(data.get('id', '')).strip() or f"ring_{ring_device_id}"
            cam_name = data.get('name') or f"Ring {ring_device_id}"

            config = load_cameras_config()
            config.setdefault('cameras', {})
            config['cameras'][cam_id] = {
                'name': cam_name,
                'url': f"/api/cameras/{cam_id}/snapshot",
                'type': 'ring',
                'autostart': False,
                'ring': {'device_id': ring_device_id}
            }
            save_cameras_config(config)

            return jsonify({'success': True, 'camera_id': cam_id})
        except Exception as e:
            logger.error("Fehler bei POST /api/ring/cameras/import: %s", e, exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


def is_ring_live_enabled(load_feature_flags: Callable[[], Dict[str, Any]]) -> bool:
    flags_doc = load_feature_flags()
    flags = flags_doc.get('flags', {}) if isinstance(flags_doc, dict) else {}
    return bool(flags.get('ui.ring.webrtc', False))


def is_ring_live_on_ding_enabled(manager: Any, load_feature_flags: Callable[[], Dict[str, Any]]) -> bool:
    settings = manager._load_gateway_settings()
    ring_live = settings.get('ring_live', {}) if isinstance(settings, dict) else {}
    if 'on_ding_enabled' in ring_live:
        return bool(ring_live.get('on_ding_enabled'))
    flags_doc = load_feature_flags()
    flags = flags_doc.get('flags', {}) if isinstance(flags_doc, dict) else {}
    return bool(flags.get('ui.ring.live_on_ding', True))


def ring_live_on_ding_seconds(manager: Any) -> int:
    settings = manager._load_gateway_settings()
    ring_live = settings.get('ring_live', {}) if isinstance(settings, dict) else {}
    return max(5, min(int(ring_live.get('on_ding_seconds', 30)), 300))


def is_ring_live_allowed_for_camera(manager: Any, cam_id: str, load_feature_flags: Callable[[], Dict[str, Any]]) -> bool:
    if is_ring_live_enabled(load_feature_flags):
        return True
    if not is_ring_live_on_ding_enabled(manager, load_feature_flags):
        return False
    until = manager._ring_live_until.get(cam_id)
    return bool(until and time.time() < float(until))


def get_ring_camera_configs(manager: Any) -> List[Dict[str, str]]:
    config = manager._load_cameras_config_for_monitor()
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


def default_gateway_settings() -> Dict[str, Any]:
    return {
        "version": "1.0",
        "ring_live": {
            "on_ding_enabled": True,
            "on_ding_seconds": 30,
            "on_trigger_enabled": True,
            "on_trigger_use_rule_duration": True,
            "on_trigger_seconds": 30
        }
    }


def load_gateway_settings(manager: Any) -> Dict[str, Any]:
    path = manager._gateway_settings_path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f) or {}
                if isinstance(loaded, dict):
                    data = loaded
        except Exception as e:
            logger.warning("Konnte gateway_settings.json nicht laden: %s", e)

    defaults = default_gateway_settings()
    ring_live = data.get('ring_live') if isinstance(data.get('ring_live'), dict) else {}
    return {
        "version": str(data.get('version') or defaults['version']),
        "ring_live": {
            "on_ding_enabled": bool(ring_live.get("on_ding_enabled", defaults["ring_live"]["on_ding_enabled"])),
            "on_ding_seconds": max(5, min(int(ring_live.get("on_ding_seconds", defaults["ring_live"]["on_ding_seconds"])), 300)),
            "on_trigger_enabled": bool(ring_live.get("on_trigger_enabled", defaults["ring_live"]["on_trigger_enabled"])),
            "on_trigger_use_rule_duration": bool(ring_live.get("on_trigger_use_rule_duration", defaults["ring_live"]["on_trigger_use_rule_duration"])),
            "on_trigger_seconds": max(5, min(int(ring_live.get("on_trigger_seconds", defaults["ring_live"]["on_trigger_seconds"])), 300)),
        }
    }


def save_gateway_settings(manager: Any, settings: Dict[str, Any]) -> Dict[str, Any]:
    merged = default_gateway_settings()
    if isinstance(settings, dict):
        merged = manager._load_gateway_settings()
        incoming = settings.get('ring_live') if isinstance(settings.get('ring_live'), dict) else settings
        if isinstance(incoming, dict):
            ring_live = merged['ring_live']
            if 'on_ding_enabled' in incoming:
                ring_live['on_ding_enabled'] = bool(incoming.get('on_ding_enabled'))
            if 'on_ding_seconds' in incoming:
                ring_live['on_ding_seconds'] = max(5, min(int(incoming.get('on_ding_seconds')), 300))
            if 'on_trigger_enabled' in incoming:
                ring_live['on_trigger_enabled'] = bool(incoming.get('on_trigger_enabled'))
            if 'on_trigger_use_rule_duration' in incoming:
                ring_live['on_trigger_use_rule_duration'] = bool(incoming.get('on_trigger_use_rule_duration'))
            if 'on_trigger_seconds' in incoming:
                ring_live['on_trigger_seconds'] = max(5, min(int(incoming.get('on_trigger_seconds')), 300))

    path = manager._gateway_settings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    return merged


def set_ring_doorbell_state(manager: Any, cam_id: str, cam_name: str, event_id: str, ding_ts: Any, active: bool) -> None:
    if not manager.data_gateway:
        return

    base = f"GATEWAY.RING.{cam_id}"
    manager.data_gateway.update_telemetry(f"{base}.doorbell", bool(active))
    if event_id:
        manager.data_gateway.update_telemetry(f"{base}.last_event_id", str(event_id))
    if ding_ts is not None:
        manager.data_gateway.update_telemetry(f"{base}.last_ding_ts", ding_ts)

    if active:
        try:
            stream_mgr = manager.app_context.module_manager.get_module('stream_manager') if manager.app_context else None
            if stream_mgr:
                from modules.integrations.ring_module import get_ring_refresh_token

                refresh_token = get_ring_refresh_token()
                ring_cams = {c['cam_id']: c for c in manager._get_ring_camera_configs()}
                ring_cfg = ring_cams.get(cam_id)
                if ring_cfg and refresh_token:
                    stream_mgr.start_ring_stream(cam_id, ring_cfg['device_id'], refresh_token)
        except Exception:
            pass

        manager.broadcast_event('camera_alert', {
            'cam_id': cam_id,
            'name': cam_name,
            'type': 'ring',
            'source': 'ring_doorbell',
            'event_id': event_id,
            'timestamp': int(time.time()),
            'timestamp_utc': manager._utc_iso()
        })


def record_ring_event(manager: Any, cam_id: str, cam_name: str, device_id: str, event: Dict[str, Any]) -> None:
    entry = _normalize_ring_event_entry(cam_id, cam_name, device_id, event, source=event.get('source') or 'ring_api')
    event_id = str(entry.get('id') or '').strip()
    if not event_id:
        return
    manager._store_ring_event(entry)


def list_ring_events(manager: Any, limit: int = 25, kinds: str = '') -> Dict[str, Any]:
    ring_cams = manager._get_ring_camera_configs()

    requested_limit = max(1, min(int(limit), 100))
    per_camera_limit = max(5, min(requested_limit, 50))
    kind_filter = {part.strip().lower() for part in str(kinds or '').split(',') if part.strip()}
    api_success = False
    first_error = ''

    if ring_cams:
        try:
            from modules.integrations.ring_module import get_ring_history

            for cam in ring_cams:
                for history_kind in (None, 'ding', 'motion', 'on_demand'):
                    result = get_ring_history(cam['device_id'], limit=per_camera_limit, kind=history_kind)
                    if not result.get('success'):
                        if not first_error:
                            first_error = str(result.get('error') or '').strip()
                        continue
                    api_success = True
                    for event in result.get('events') or []:
                        normalized = _normalize_ring_event_entry(
                            cam['cam_id'],
                            cam['name'],
                            cam['device_id'],
                            event,
                            source='ring_api',
                        )
                        if not normalized['id']:
                            continue
                        if kind_filter and normalized['kind'].lower() not in kind_filter and normalized['trigger'].lower() not in kind_filter:
                            continue
                        manager._store_ring_event(normalized)
        except Exception as e:
            logger.warning("Ring-Ereignisse konnten nicht von der API geladen werden: %s", e)
            if not first_error:
                first_error = str(e)

    merged = manager._read_ring_events(limit=requested_limit, kinds=sorted(kind_filter))
    if kind_filter:
        merged = [
            event for event in merged
            if str(event.get('kind') or '').lower() in kind_filter
            or str(event.get('trigger') or '').lower() in kind_filter
        ][:requested_limit]
    health = _record_ring_health_snapshot(
        manager,
        success=bool(api_success or merged),
        error_text=first_error,
        reauth_recommended=bool(_build_ring_issue_hints(first_error)),
    )

    return {
        'success': True,
        'events': merged[:requested_limit],
        'storage': manager._get_ring_event_storage_status(),
        'health': health,
    }


def ring_event_loop(manager: Any) -> None:
    while manager._ring_event_active:
        try:
            ring_cams = manager._get_ring_camera_configs()
            if not ring_cams:
                time.sleep(3.0)
                continue

            for cam in ring_cams:
                cam_id = cam['cam_id']
                device_id = cam['device_id']
                cam_name = cam['name']

                until = manager._ring_doorbell_until.get(cam_id)
                if until and time.time() >= until:
                    manager._ring_doorbell_until.pop(cam_id, None)
                    manager._set_ring_doorbell_state(cam_id, cam_name, manager._ring_last_event_ids.get(cam_id), None, False)

                live_until = manager._ring_live_until.get(cam_id)
                if live_until and time.time() >= live_until:
                    manager._ring_live_until.pop(cam_id, None)

                try:
                    from modules.integrations.ring_module import get_ring_history

                    result = get_ring_history(device_id, limit=6)
                except Exception:
                    continue

                if not result.get('success'):
                    continue
                events = result.get('events') or []
                if not events:
                    continue

                newest_ding = None
                for event in events:
                    normalized = _normalize_ring_event_entry(cam_id, cam_name, device_id, event, source='ring_api')
                    event_id = str(normalized.get('id') or '')
                    if not event_id:
                        continue
                    manager._store_ring_event(normalized)
                    if str(normalized.get('kind') or '').lower() == 'ding' and newest_ding is None:
                        newest_ding = normalized

                if newest_ding and manager._ring_last_event_ids.get(cam_id) != newest_ding['id']:
                    manager._ring_last_event_ids[cam_id] = newest_ding['id']
                    ding_ts = newest_ding.get('ding_ts')
                    manager._ring_doorbell_until[cam_id] = time.time() + manager._ring_doorbell_pulse_seconds
                    if manager._load_gateway_settings().get('ring_live', {}).get('on_ding_enabled', True):
                        ding_window = max(5, min(int(manager._load_gateway_settings().get('ring_live', {}).get('on_ding_seconds', 30)), 300))
                        manager._ring_live_until[cam_id] = time.time() + ding_window
                    manager._set_ring_doorbell_state(cam_id, cam_name, newest_ding['id'], ding_ts, True)

            time.sleep(2.0)
        except Exception as e:
            logger.warning("Ring-Event-Monitor Fehler: %s", e)
            time.sleep(3.0)


def start_ring_event_monitor(manager: Any) -> None:
    if manager._ring_event_active:
        return

    manager._load_camera_trigger_rules()
    if manager.data_gateway:
        for cam in manager._get_ring_camera_configs():
            manager._set_ring_doorbell_state(cam['cam_id'], cam['name'], '', None, False)
    manager._ring_event_active = True
    manager._ring_event_thread = threading.Thread(target=manager._ring_event_loop, daemon=True)
    manager._ring_event_thread.start()
    logger.info("Ring Event Monitor gestartet")


def _get_flask_request():
    from flask import request

    return request


def _get_flask_jsonify():
    from flask import jsonify

    return jsonify
