"""Ring Doorbell integration helpers.

Provides token-based auth, camera listing, snapshot retrieval and WebRTC bridge
for the Flask web API.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from aiohttp import ClientSession
    from ring_doorbell import Auth, AuthenticationError, Requires2FAError, Ring
    from ring_doorbell.const import (
        API_URI,
        DEVICES_ENDPOINT,
        SNAPSHOT_ENDPOINT,
        SNAPSHOT_TIMESTAMP_ENDPOINT,
    )

    RING_AVAILABLE = True
except ImportError:
    ClientSession = None
    RING_AVAILABLE = False


_DEFAULT_USER_AGENT = "android:com.ringapp"
_LEGACY_DEFAULT_USER_AGENT = "android:com.ringapp"
_LOCK = threading.RLock()
_RING_WEBRTC_SUPPORTED = False


def _normalize_user_agent(value: Optional[str]) -> str:
    if not value:
        return _DEFAULT_USER_AGENT

    # HTTP header values should be ASCII-safe. Strip non-ASCII and control chars.
    ascii_value = value.encode("ascii", "ignore").decode("ascii")
    ascii_value = "".join(ch for ch in ascii_value if 32 <= ord(ch) <= 126).strip()
    return ascii_value or _DEFAULT_USER_AGENT


def _normalize_otp(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


class _AsyncRuntime:
    """Single persistent asyncio loop for long-lived Ring WebRTC sessions."""

    def __init__(self):
        self._loop = None
        self._thread = None
        self._start_lock = threading.Lock()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _ensure_started(self):
        if self._thread and self._thread.is_alive() and self._loop:
            return

        with self._start_lock:
            if self._thread and self._thread.is_alive() and self._loop:
                return

            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            # Wait until loop is ready
            for _ in range(200):
                if self._loop:
                    return
                time.sleep(0.01)
            raise RuntimeError("Konnte Async-Runtime nicht starten")

    def run(self, coro, timeout: float = 60.0):
        self._ensure_started()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as e:
            future.cancel()
            raise RuntimeError("Ring-Operation Timeout") from e


_RUNTIME = _AsyncRuntime()
_WEBRTC_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _config_path() -> str:
    root_dir = os.path.abspath(os.getcwd())
    cache_dir = os.path.join(root_dir, "config", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "ring_auth.json")


def _load_auth_data() -> Dict[str, Any]:
    path = _config_path()
    if not os.path.exists(path):
        return {"user_agent": _DEFAULT_USER_AGENT, "token": None}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"user_agent": _DEFAULT_USER_AGENT, "token": None}
            return {
                "user_agent": _normalize_user_agent(data.get("user_agent")),
                "token": data.get("token"),
                "updated_at": data.get("updated_at"),
            }
    except Exception:
        return {"user_agent": _DEFAULT_USER_AGENT, "token": None}


def _save_auth_data(user_agent: str, token: Optional[Dict[str, Any]]) -> None:
    payload = {
        "user_agent": _normalize_user_agent(user_agent),
        "token": token,
        "updated_at": int(time.time()),
    }

    with open(_config_path(), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _extract_sdp_session_id(sdp_offer: str) -> Optional[str]:
    # SDP origin line format: o=<username> <session-id> <session-version> ...
    match = re.search(r"^o=[^\s]+\s+(\d+)\s+", sdp_offer, flags=re.MULTILINE)
    return match.group(1) if match else None


def _build_http_headers(user_agent: str) -> Dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9,de-DE;q=0.8",
        "Connection": "keep-alive",
    }


async def _new_http_session(user_agent: str):
    if ClientSession is None:
        return None
    return ClientSession(headers=_build_http_headers(user_agent))


async def _close_http_session(http_session: Any) -> None:
    if http_session is not None:
        await http_session.close()


async def _async_with_ring() -> tuple[Any, Any, Any]:
    auth_data = _load_auth_data()
    token = auth_data.get("token")
    if not token:
        raise RuntimeError("Ring nicht konfiguriert. Bitte zuerst authentifizieren.")

    ua = auth_data.get("user_agent") or _DEFAULT_USER_AGENT

    def _token_updated(new_token: Dict[str, Any]) -> None:
        _save_auth_data(ua, new_token)

    http_session = await _new_http_session(ua)
    auth = Auth(ua, token, _token_updated, http_client_session=http_session)
    ring = Ring(auth)
    try:
        await ring.async_create_session()
        await ring.async_update_data()
        return auth, ring, http_session
    except Exception as e:
        msg = str(e)
        # Ring may reject non-mobile user agents for session validation (406).
        # Retry once with mobile UA and persist that UA for subsequent calls.
        if "406" not in msg or ua == _LEGACY_DEFAULT_USER_AGENT:
            await auth.async_close()
            await _close_http_session(http_session)
            raise

        await auth.async_close()
        await _close_http_session(http_session)
        fallback_ua = _LEGACY_DEFAULT_USER_AGENT

        def _fallback_token_updated(new_token: Dict[str, Any]) -> None:
            _save_auth_data(fallback_ua, new_token)

        fallback_http_session = await _new_http_session(fallback_ua)
        fallback_auth = Auth(
            fallback_ua,
            token,
            _fallback_token_updated,
            http_client_session=fallback_http_session,
        )
        fallback_ring = Ring(fallback_auth)
        await fallback_ring.async_create_session()
        await fallback_ring.async_update_data()
        _save_auth_data(fallback_ua, token)
        return fallback_auth, fallback_ring, fallback_http_session


async def _async_with_auth() -> tuple[Any, Any]:
    auth_data = _load_auth_data()
    token = auth_data.get("token")
    if not token:
        raise RuntimeError("Ring nicht konfiguriert. Bitte zuerst authentifizieren.")

    ua = auth_data.get("user_agent") or _DEFAULT_USER_AGENT

    def _token_updated(new_token: Dict[str, Any]) -> None:
        _save_auth_data(ua, new_token)

    http_session = await _new_http_session(ua)
    auth = Auth(ua, token, _token_updated, http_client_session=http_session)
    return auth, http_session


def get_ring_status() -> Dict[str, Any]:
    auth_data = _load_auth_data()
    token = auth_data.get("token")
    return {
        "available": RING_AVAILABLE,
        "configured": bool(token),
        "user_agent": _normalize_user_agent(auth_data.get("user_agent", _DEFAULT_USER_AGENT)),
        "webrtc_available": _RING_WEBRTC_SUPPORTED,
    }


def get_ring_refresh_token() -> Optional[str]:
    auth_data = _load_auth_data()
    token = auth_data.get("token") or {}
    return token.get("refresh_token")


async def _async_authenticate(
    username: str,
    password: str,
    otp: Optional[str],
    user_agent: str,
) -> Dict[str, Any]:
    http_session = await _new_http_session(user_agent)
    auth = Auth(user_agent, None, None, http_client_session=http_session)
    try:
        token = await auth.async_fetch_token(username, password, otp)
    finally:
        await auth.async_close()
        await _close_http_session(http_session)
    _save_auth_data(user_agent, token)
    return {"success": True}


def authenticate_ring(
    username: str,
    password: str,
    otp: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Dict[str, Any]:
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}

    ua = _normalize_user_agent(user_agent or _load_auth_data().get("user_agent"))
    otp = _normalize_otp(otp)

    with _LOCK:
        try:
            return _RUNTIME.run(_async_authenticate(username, password, otp, ua), timeout=60)
        except Requires2FAError:
            return {"success": False, "requires_2fa": True, "error": "2FA-Code erforderlich"}
        except AuthenticationError as e:
            msg = str(e)
            # Ring occasionally rejects custom user agents with 406.
            # Retry once with the known mobile app UA to improve reliability.
            if "406" in msg and ua != _LEGACY_DEFAULT_USER_AGENT:
                try:
                    return _RUNTIME.run(
                        _async_authenticate(username, password, otp, _LEGACY_DEFAULT_USER_AGENT),
                        timeout=60,
                    )
                except AuthenticationError as e2:
                    return {"success": False, "error": f"Authentifizierung fehlgeschlagen: {e2}"}
                except Exception as e2:
                    return {"success": False, "error": str(e2)}
            return {"success": False, "error": f"Authentifizierung fehlgeschlagen: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _async_list_cameras() -> List[Dict[str, Any]]:
    auth, http_session = await _async_with_auth()
    try:
        resp = await auth.async_query(f"{API_URI}{DEVICES_ENDPOINT}")
        data = resp.json() if resp else {}
        video_groups = ("doorbots", "authorized_doorbots", "stickup_cams")
        cameras = []
        for group in video_groups:
            for cam in (data.get(group) or []):
                cameras.append(
                    {
                        "device_id": str(cam.get("id")),
                        "name": cam.get("description") or cam.get("name") or f"Ring {cam.get('id')}",
                        "family": cam.get("family") or "camera",
                        "kind": cam.get("kind"),
                        "has_subscription": bool(cam.get("subscribed") or cam.get("subscribed_motions")),
                        "battery_life": cam.get("battery_life"),
                    }
                )
        return cameras
    finally:
        await auth.async_close()
        await _close_http_session(http_session)


def list_ring_cameras() -> Dict[str, Any]:
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}

    with _LOCK:
        try:
            cameras = _RUNTIME.run(_async_list_cameras(), timeout=90)
            return {"success": True, "cameras": cameras}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _async_get_snapshot(
    device_id: str,
    retries: int = 3,
    delay: int = 1,
    prefer_cached: bool = True,
) -> Optional[bytes]:
    auth, http_session = await _async_with_auth()
    try:
        target_id = str(device_id)
        if prefer_cached:
            # Fast path: latest available snapshot is usually much quicker than
            # waiting for a freshly generated snapshot timestamp.
            img = await auth.async_query(
                f"{API_URI}{SNAPSHOT_ENDPOINT.format(target_id)}",
                raise_for_status=False,
            )
            if img and img.status_code == 200 and img.content:
                return img.content

        payload = {"doorbot_ids": [int(target_id)]}
        await auth.async_query(
            f"{API_URI}{SNAPSHOT_TIMESTAMP_ENDPOINT}",
            method="POST",
            json=payload,
        )
        request_time = time.time()

        for _ in range(retries):
            await asyncio.sleep(delay)
            resp = await auth.async_query(
                f"{API_URI}{SNAPSHOT_TIMESTAMP_ENDPOINT}",
                method="POST",
                json=payload,
            )
            data = resp.json() if resp else {}
            timestamps = data.get("timestamps") or []
            if timestamps and (timestamps[0].get("timestamp", 0) / 1000) > request_time:
                img = await auth.async_query(f"{API_URI}{SNAPSHOT_ENDPOINT.format(target_id)}")
                return img.content if img else None
        # Fallback: try latest snapshot directly even when timestamp did not advance.
        img = await auth.async_query(f"{API_URI}{SNAPSHOT_ENDPOINT.format(target_id)}", raise_for_status=False)
        return img.content if img and img.status_code == 200 else None
    finally:
        await auth.async_close()
        await _close_http_session(http_session)


def get_ring_snapshot(
    device_id: str,
    retries: int = 3,
    delay: int = 1,
    timeout_seconds: Optional[int] = None,
    prefer_cached: bool = True,
) -> Dict[str, Any]:
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}

    with _LOCK:
        try:
            computed_timeout = (max(1, int(retries)) * max(1, int(delay))) + 6
            if timeout_seconds is None:
                timeout = max(8, min(12, computed_timeout))
            else:
                timeout = max(4, min(int(timeout_seconds), 30))
            data = _RUNTIME.run(
                _async_get_snapshot(
                    device_id,
                    retries=retries,
                    delay=delay,
                    prefer_cached=prefer_cached,
                ),
                timeout=timeout,
            )
            if not data:
                return {"success": False, "error": "Kein Snapshot von Ring erhalten"}
            return {"success": True, "content": data}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _async_get_latest_ding(device_id: str) -> Dict[str, Any]:
    auth, ring, http_session = await _async_with_ring()
    try:
        target_id = str(device_id)
        camera = next((c for c in ring.video_devices() if str(c.device_api_id) == target_id), None)
        if not camera:
            raise RuntimeError(f"Ring-Kamera mit device_id '{device_id}' nicht gefunden")

        events = await camera.async_history(
            limit=1,
            kind="ding",
            enforce_limit=True,
            retry=1,
            convert_timezone=False,
        )
        if not events:
            return {"success": True, "event": None}

        event = events[0] or {}
        created_at = event.get("created_at")
        ding_ts = None
        if isinstance(created_at, datetime):
            ding_ts = int(created_at.timestamp())
        elif isinstance(created_at, str):
            # Fallback: keep raw string when datetime conversion is unavailable.
            ding_ts = created_at

        return {
            "success": True,
            "event": {
                "id": str(event.get("id")) if event.get("id") is not None else None,
                "kind": event.get("kind"),
                "ding_ts": ding_ts,
                "created_at": str(created_at) if created_at is not None else None,
            },
        }
    finally:
        await auth.async_close()
        await _close_http_session(http_session)


def get_ring_latest_ding(device_id: str) -> Dict[str, Any]:
    """Liefert das letzte Ring-Klingel-Event (kind=ding) fuer ein Device."""
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}

    try:
        # Keep timeout bounded so event polling cannot starve foreground snapshot calls.
        return _RUNTIME.run(_async_get_latest_ding(device_id), timeout=12)
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _async_start_webrtc(device_id: str, sdp_offer: str, keep_alive_timeout: int = 30) -> Dict[str, Any]:
    session_id = _extract_sdp_session_id(sdp_offer)
    if not session_id:
        raise RuntimeError("Session-ID konnte aus SDP Offer nicht extrahiert werden")

    # Replace existing session id cleanly
    if session_id in _WEBRTC_SESSIONS:
        old = _WEBRTC_SESSIONS.pop(session_id)
        try:
            await old["camera"].close_webrtc_stream(session_id)
        finally:
            await old["auth"].async_close()
            await _close_http_session(old.get("http_session"))

    auth, ring, http_session = await _async_with_ring()
    try:
        target_id = str(device_id)
        camera = next((c for c in ring.video_devices() if str(c.device_api_id) == target_id), None)
        if not camera:
            await auth.async_close()
            await _close_http_session(http_session)
            raise RuntimeError(f"Ring-Kamera mit device_id '{device_id}' nicht gefunden")

        answer = await camera.generate_webrtc_stream(sdp_offer, keep_alive_timeout=keep_alive_timeout)
        ice_servers = camera.get_ice_servers()

        _WEBRTC_SESSIONS[session_id] = {
            "auth": auth,
            "http_session": http_session,
            "camera": camera,
            "device_id": target_id,
            "created_at": time.time(),
        }

        return {
            "success": True,
            "session_id": session_id,
            "answer": answer,
            "ice_servers": ice_servers,
        }
    except Exception:
        try:
            await auth.async_close()
            await _close_http_session(http_session)
        except Exception:
            pass
        raise


def start_ring_webrtc(device_id: str, sdp_offer: str, keep_alive_timeout: int = 30) -> Dict[str, Any]:
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}
    if not _RING_WEBRTC_SUPPORTED:
        return {
            "success": False,
            "error": "Ring WebRTC ist derzeit deaktiviert (Ring /clients_api/session liefert 406). Snapshot-Modus aktiv.",
        }

    with _LOCK:
        try:
            return _RUNTIME.run(_async_start_webrtc(device_id, sdp_offer, keep_alive_timeout=keep_alive_timeout), timeout=120)
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _async_webrtc_candidate(session_id: str, candidate: str, mline_index: int) -> bool:
    session = _WEBRTC_SESSIONS.get(session_id)
    if not session:
        raise RuntimeError("Unbekannte WebRTC Session")

    await session["camera"].on_webrtc_candidate(session_id, candidate, mline_index)
    return True


def send_ring_webrtc_candidate(session_id: str, candidate: str, mline_index: int) -> Dict[str, Any]:
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}

    with _LOCK:
        try:
            _RUNTIME.run(_async_webrtc_candidate(session_id, candidate, mline_index), timeout=20)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _async_webrtc_keepalive(session_id: str) -> bool:
    session = _WEBRTC_SESSIONS.get(session_id)
    if not session:
        return False

    await session["camera"].keep_alive_webrtc_stream(session_id)
    return True


def keepalive_ring_webrtc(session_id: str) -> Dict[str, Any]:
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}

    with _LOCK:
        try:
            ok = _RUNTIME.run(_async_webrtc_keepalive(session_id), timeout=20)
            return {"success": ok}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def _async_stop_webrtc(session_id: str) -> bool:
    session = _WEBRTC_SESSIONS.pop(session_id, None)
    if not session:
        return False

    try:
        await session["camera"].close_webrtc_stream(session_id)
    finally:
        await session["auth"].async_close()
        await _close_http_session(session.get("http_session"))

    return True


def stop_ring_webrtc(session_id: str) -> Dict[str, Any]:
    if not RING_AVAILABLE:
        return {"success": False, "error": "ring_doorbell nicht installiert"}

    with _LOCK:
        try:
            ok = _RUNTIME.run(_async_stop_webrtc(session_id), timeout=20)
            return {"success": ok}
        except Exception as e:
            return {"success": False, "error": str(e)}
