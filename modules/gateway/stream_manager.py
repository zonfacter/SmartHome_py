"""
Stream Manager Module v1.0.0
RTSP zu HLS Transcoding mit On-Demand Start/Stop

📁 SPEICHERORT: modules/gateway/stream_manager.py

Features:
- FFmpeg Subprocess Management
- RTSP -> HLS Transcoding
- Intel QuickSync Support (Docker)
- CPU Fallback (VM)
- On-Demand Stream Start/Stop
"""

from module_manager import BaseModule
from typing import Any, Dict, Optional
import subprocess
import threading
import time
import os
import shutil
import random
import logging
import glob
from modules.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


class StreamManager(BaseModule):
    """
    Stream Manager v1.0.0

    RTSP zu HLS Transcoding für IP-Kameras

    Features:
    - FFmpeg-basiertes Transcoding
    - Hardware-Beschleunigung (QuickSync/VAAPI)
    - CPU-Fallback für VM
    - On-Demand Start/Stop
    - Automatisches Cleanup
    """

    NAME = "stream_manager"
    VERSION = "1.0.0"
    DESCRIPTION = "RTSP zu HLS Transcoding"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['data_gateway']

    # HLS-Konfiguration
    HLS_SEGMENT_TIME = 1  # Sekunden pro Segment
    HLS_LIST_SIZE = 4  # Anzahl Segmente in Playlist (geringere Latenz)
    HLS_DELETE_THRESHOLD = 8  # Kurze Historie, aber genug Puffer gegen 404
    HLS_FLAGS = "delete_segments+omit_endlist+independent_segments"
    RECOVERY_WINDOW_SECONDS = 180.0

    logger = logging.getLogger("StreamManager")

    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()

        # Module-Referenzen
        self.data_gateway = None

        # Streams
        self.streams = {}  # camera_id -> {process, rtsp_url, hls_path, etc.}
        self._desired_streams = {}  # camera_id -> restart spec
        self._delayed_stop_timers = {}  # camera_id -> Timer
        self._recovery_state = {}  # camera_id -> retry/cooldown state
        self._recovery_thread = None
        self._recovery_active = False
        self._stream_metrics = {}  # camera_id -> metrics

        # HLS Output-Verzeichnis
        self.hls_dir = 'web/static/hls'

        # Capabilities
        self.has_ffmpeg = self._check_ffmpeg()
        self.has_node = self._check_node()
        self.hw_accel_mode = None
        self.recovery_enabled = str(os.getenv('STREAM_AUTO_RECOVERY_ENABLED', 'true')).lower() in (
            '1', 'true', 'yes', 'on'
        )
        self.recovery_interval = max(0.5, float(os.getenv('STREAM_RECOVERY_CHECK_INTERVAL_SECONDS', '2.0')))
        self.recovery_max_retries = max(1, int(os.getenv('STREAM_RECOVERY_MAX_RETRIES', '5')))
        self.recovery_cooldown_seconds = max(10.0, float(os.getenv('STREAM_RECOVERY_COOLDOWN_SECONDS', '120')))
        self.recovery_backoff_base = max(0.2, float(os.getenv('STREAM_RECOVERY_BACKOFF_BASE_SECONDS', '1.5')))
        self.recovery_backoff_max = max(1.0, float(os.getenv('STREAM_RECOVERY_BACKOFF_MAX_SECONDS', '20')))
        self.recovery_jitter_max = max(0.0, float(os.getenv('STREAM_RECOVERY_JITTER_MAX_SECONDS', '0.6')))
        self._stream_breakers: Dict[str, CircuitBreaker] = {}
        self.cb_failure_threshold = max(1, int(os.getenv('SMARTHOME_STREAM_CB_FAILURE_THRESHOLD', '3')))
        self.cb_recovery_seconds = max(1.0, float(os.getenv('SMARTHOME_STREAM_CB_RECOVERY_SECONDS', '30')))
        self.cb_half_open_max_calls = max(1, int(os.getenv('SMARTHOME_STREAM_CB_HALF_OPEN_MAX_CALLS', '1')))

    def initialize(self, app_context: Any):
        """Initialisiert Stream Manager"""
        super().initialize(app_context)

        # Hole Data Gateway
        self.data_gateway = app_context.module_manager.get_module('data_gateway')
        if not self.data_gateway:
            raise RuntimeError("data_gateway Modul nicht gefunden!")

        # Erkenne Hardware-Beschleunigung
        self.hw_accel_mode = self._detect_hw_accel()

        # Erstelle HLS-Verzeichnis
        os.makedirs(self.hls_dir, exist_ok=True)
        # Stale HLS-Artefakte aus vorherigen Läufen entfernen
        self._cleanup_all_hls_files()

        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
        print(f"     🎬 FFmpeg: {'Verfügbar' if self.has_ffmpeg else 'NICHT INSTALLIERT'}")
        print(f"     🟩 Node.js: {'Verfügbar' if self.has_node else 'NICHT INSTALLIERT'}")
        print(f"     🎮 HW-Accel: {self.hw_accel_mode or 'CPU (Software)'}")
        print(f"     📁 HLS-Dir: {self.hls_dir}")
        print(f"     🔁 Auto-Recovery: {'Aktiv' if self.recovery_enabled else 'Deaktiviert'}")
        if self.recovery_enabled:
            self._start_recovery_monitor()

    def _check_ffmpeg(self) -> bool:
        """Prüft ob FFmpeg installiert ist"""
        return shutil.which('ffmpeg') is not None

    def _check_node(self) -> bool:
        """Prüft ob Node.js installiert ist"""
        return shutil.which('node') is not None

    def _ensure_metrics(self, camera_id: str) -> Dict[str, Any]:
        metrics = self._stream_metrics.get(camera_id)
        if metrics:
            return metrics
        metrics = {
            'starts_total': 0,
            'stops_total': 0,
            'restarts_total': 0,
            'recovery_success_total': 0,
            'recovery_failed_total': 0,
            'last_start_ts': 0.0,
            'last_stop_ts': 0.0,
            'last_exit_code': None,
            'last_error': '',
            'last_recovery_attempt_ts': 0.0,
            'cooldown_until': 0.0,
        }
        self._stream_metrics[camera_id] = metrics
        return metrics

    def _stream_breaker_key(self, camera_id: str, source_type: str) -> str:
        return f"stream:{source_type}:{camera_id}"

    def _get_stream_breaker(self, camera_id: str, source_type: str) -> CircuitBreaker:
        key = self._stream_breaker_key(camera_id, source_type)
        breaker = self._stream_breakers.get(key)
        if breaker:
            return breaker
        cfg = CircuitBreakerConfig(
            failure_threshold=self.cb_failure_threshold,
            recovery_timeout_seconds=self.cb_recovery_seconds,
            half_open_max_calls=self.cb_half_open_max_calls
        )
        breaker = CircuitBreaker(name=key, config=cfg)
        self._stream_breakers[key] = breaker
        return breaker

    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        return {
            key: breaker.snapshot()
            for key, breaker in self._stream_breakers.items()
        }

    def _detect_hw_accel(self) -> Optional[str]:
        """
        Erkennt verfügbare Hardware-Beschleunigung

        Returns:
            'qsv' (QuickSync), 'vaapi', oder None (CPU)
        """
        if not self.data_gateway:
            return None

        caps = self.data_gateway.capabilities

        # Intel QuickSync (bevorzugt)
        if caps.get('has_quicksync', False):
            return 'qsv'

        # VAAPI (Fallback)
        if caps.get('has_vaapi', False):
            return 'vaapi'

        return None

    # ========================================================================
    # STREAM CONTROL
    # ========================================================================

    def start_stream(self, camera_id: str, rtsp_url: str, force_cpu: bool = False, resolution: Optional[str] = None) -> bool:
        """
        Startet RTSP -> HLS Transcoding

        Args:
            camera_id: Eindeutige Kamera-ID (z.B. 'garage')
            rtsp_url: RTSP-URL (z.B. 'rtsp://192.168.1.100/stream')
            force_cpu: Erzwingt CPU-Encoding
            resolution: Ziel-Auflösung (z.B. '640x360') oder None für Original/Passthrough

        Returns:
            True wenn erfolgreich gestartet
        """
        if not self.has_ffmpeg:
            print(f"  ✗ FFmpeg nicht installiert!")
            return False

        with self.lock:
            self._cancel_delayed_stop(camera_id)
            metrics = self._ensure_metrics(camera_id)
            breaker = self._get_stream_breaker(camera_id, 'rtsp')
            if not breaker.allow_request():
                metrics['last_error'] = 'circuit_open'
                self.logger.warning("Stream start blocked by circuit breaker: camera=%s", camera_id)
                return False
            desired_spec = {
                'type': 'rtsp',
                'camera_id': camera_id,
                'rtsp_url': rtsp_url,
                'force_cpu': bool(force_cpu),
                'resolution': resolution
            }
            # Prüfe ob bereits läuft
            if camera_id in self.streams:
                current = self.streams[camera_id]
                process = current.get('process')
                is_running = process is not None and process.poll() is None
                same_source = (
                    current.get('rtsp_url') == rtsp_url and
                    current.get('resolution') == resolution
                )

                if is_running and same_source:
                    # Bereits mit derselben Quelle aktiv -> idempotent success.
                    self._desired_streams[camera_id] = desired_spec
                    breaker.record_success()
                    print(f"  ⚠️  Stream '{camera_id}' läuft bereits (gleiche Quelle)")
                    return True

                # Quelle/Profil geändert oder Prozess hängt -> sauber neu starten.
                try:
                    if is_running:
                        process.terminate()
                        process.wait(timeout=5)
                    else:
                        try:
                            process.kill()
                        except Exception:
                            pass
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception:
                    pass
                try:
                    metrics['last_exit_code'] = process.poll()
                except Exception:
                    pass

                del self.streams[camera_id]
                self._cleanup_hls_files(camera_id)
                metrics['restarts_total'] += 1

            # HLS-Pfade
            hls_playlist = os.path.join(self.hls_dir, f"{camera_id}.m3u8")
            hls_segment = os.path.join(self.hls_dir, f"{camera_id}_%03d.ts")

            # Alte HLS-Dateien loeschen (verhindert Wiedergabe von altem Material)
            self._cleanup_hls_files(camera_id)

            # FFmpeg-Kommando
            cmd = self._build_ffmpeg_cmd(
                rtsp_url,
                hls_playlist,
                hls_segment,
                use_hw_accel=not force_cpu,
                resolution=resolution
            )

            try:
                # Starte FFmpeg-Prozess
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )

                # Speichere Stream-Info
                self.streams[camera_id] = {
                    'process': process,
                    'source_type': 'rtsp',
                    'rtsp_url': rtsp_url,
                    'hls_playlist': hls_playlist,
                    'hls_segment': hls_segment,
                    'started_at': time.time(),
                    'hw_accel': self.hw_accel_mode if not force_cpu else None,
                    'resolution': resolution,
                    'desired_spec': desired_spec
                }
                self._desired_streams[camera_id] = desired_spec
                self._reset_recovery_state(camera_id)
                metrics['starts_total'] += 1
                metrics['last_start_ts'] = time.time()
                metrics['last_error'] = ''

                print(f"  ▶️  Stream '{camera_id}' gestartet")
                print(f"     🎬 HLS: /static/hls/{camera_id}.m3u8")

                # Kurz prüfen, ob FFmpeg sofort wieder beendet wurde.
                time.sleep(0.4)
                if process.poll() is not None:
                    err_text = ""
                    try:
                        _, err = process.communicate(timeout=1)
                        err_text = (err or b"").decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                    del self.streams[camera_id]
                    self._cleanup_hls_files(camera_id)
                    metrics['last_exit_code'] = process.poll()
                    metrics['last_error'] = 'early_exit'
                    breaker.record_failure('early_exit')
                    print(f"  ✗ Stream '{camera_id}' direkt beendet")
                    if err_text:
                        print(f"    FFmpeg: {err_text.splitlines()[:1][0]}")
                    return False

                breaker.record_success()
                return True

            except Exception as e:
                metrics['last_error'] = str(e)
                breaker.record_failure(str(e))
                print(f"  ✗ Fehler beim Starten von '{camera_id}': {e}")
                return False

    def stop_stream(self, camera_id: str, cleanup: bool = True) -> bool:
        """
        Stoppt RTSP -> HLS Transcoding

        Args:
            camera_id: Kamera-ID
            cleanup: Lösche HLS-Dateien

        Returns:
            True wenn erfolgreich gestoppt
        """
        with self.lock:
            self._cancel_delayed_stop(camera_id)
            self._desired_streams.pop(camera_id, None)
            self._recovery_state.pop(camera_id, None)
            if camera_id not in self.streams:
                return False

            stream = self.streams[camera_id]
            process = stream['process']
            metrics = self._ensure_metrics(camera_id)

            # Beende FFmpeg
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                metrics['last_error'] = str(e)

            # Cleanup HLS-Dateien
            if cleanup:
                self._cleanup_hls_files(camera_id)

            # Entferne aus Liste
            del self.streams[camera_id]
            metrics['stops_total'] += 1
            metrics['last_stop_ts'] = time.time()
            try:
                metrics['last_exit_code'] = process.poll()
            except Exception:
                pass

            print(f"  ⏸️  Stream '{camera_id}' gestoppt")
            return True

    def _cancel_delayed_stop(self, camera_id: str):
        timer = self._delayed_stop_timers.pop(camera_id, None)
        if timer:
            try:
                timer.cancel()
            except Exception:
                pass

    def schedule_stop_stream(self, camera_id: str, delay_seconds: float = 45.0, cleanup: bool = True) -> bool:
        """Plant ein verzögertes Stoppen (Warm-Stream für schnelleren Re-Start)."""
        with self.lock:
            if camera_id not in self.streams:
                return False

            self._cancel_delayed_stop(camera_id)

            def _delayed():
                try:
                    self.stop_stream(camera_id, cleanup=cleanup)
                except Exception:
                    pass

            timer = threading.Timer(max(1.0, float(delay_seconds)), _delayed)
            timer.daemon = True
            self._delayed_stop_timers[camera_id] = timer
            timer.start()
            return True

    def stop_all_streams(self):
        """Stoppt alle laufenden Streams"""
        with self.lock:
            self._desired_streams.clear()
            self._recovery_state.clear()
            camera_ids = list(self.streams.keys())
            for camera_id in camera_ids:
                self.stop_stream(camera_id)

    def start_ring_stream(self, camera_id: str, ring_device_id: str, refresh_token: str) -> bool:
        """Startet Ring -> HLS Bridge via Node (ring-client-api)."""
        if not self.has_ffmpeg or not self.has_node:
            return False
        if not refresh_token:
            return False

        script_path = os.path.join(os.path.abspath(os.getcwd()), 'scripts', 'ring_hls_bridge.js')
        if not os.path.exists(script_path):
            print(f"  ✗ Ring-Bridge Script fehlt: {script_path}")
            return False

        with self.lock:
            self._cancel_delayed_stop(camera_id)
            metrics = self._ensure_metrics(camera_id)
            breaker = self._get_stream_breaker(camera_id, 'ring')
            if not breaker.allow_request():
                metrics['last_error'] = 'circuit_open'
                self.logger.warning("Ring stream start blocked by circuit breaker: camera=%s", camera_id)
                return False
            desired_spec = {
                'type': 'ring',
                'camera_id': camera_id,
                'ring_device_id': str(ring_device_id),
                'refresh_token': refresh_token
            }
            if camera_id in self.streams:
                current = self.streams[camera_id]
                process = current.get('process')
                is_running = process is not None and process.poll() is None
                same_source = (
                    current.get('source_type') == 'ring' and
                    str(current.get('ring_device_id')) == str(ring_device_id)
                )
                if is_running and same_source:
                    self._desired_streams[camera_id] = desired_spec
                    breaker.record_success()
                    return True
                metrics['restarts_total'] += 1
                self.stop_stream(camera_id, cleanup=True)

            hls_playlist = os.path.join(self.hls_dir, f"{camera_id}.m3u8")
            hls_segment = os.path.join(self.hls_dir, f"{camera_id}_%03d.ts")
            self._cleanup_hls_files(camera_id)

            cmd = [
                'node', script_path,
                '--camera-id', str(ring_device_id),
                '--playlist', hls_playlist,
                '--segment-pattern', hls_segment,
                '--ffmpeg', 'ffmpeg'
            ]

            try:
                env = os.environ.copy()
                env['RING_REFRESH_TOKEN'] = refresh_token
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )

                self.streams[camera_id] = {
                    'process': process,
                    'source_type': 'ring',
                    'ring_device_id': str(ring_device_id),
                    'hls_playlist': hls_playlist,
                    'hls_segment': hls_segment,
                    'started_at': time.time(),
                    'hw_accel': None,
                    'resolution': None,
                    'desired_spec': desired_spec
                }
                self._desired_streams[camera_id] = desired_spec
                self._reset_recovery_state(camera_id)
                metrics['starts_total'] += 1
                metrics['last_start_ts'] = time.time()
                metrics['last_error'] = ''

                # Early-fail check
                time.sleep(1.2)
                if process.poll() is not None:
                    err_text = ""
                    try:
                        _, err = process.communicate(timeout=1)
                        err_text = (err or b"").decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                    del self.streams[camera_id]
                    self._cleanup_hls_files(camera_id)
                    metrics['last_exit_code'] = process.poll()
                    metrics['last_error'] = 'early_exit'
                    breaker.record_failure('early_exit')
                    print(f"  ✗ Ring-Stream '{camera_id}' direkt beendet")
                    if err_text:
                        first = err_text.splitlines()[0] if err_text.splitlines() else err_text
                        print(f"    RingBridge: {first}")
                    return False

                print(f"  ▶️  Ring-Stream '{camera_id}' gestartet")
                print(f"     🎬 HLS: /static/hls/{camera_id}.m3u8")
                breaker.record_success()
                return True
            except Exception as e:
                metrics['last_error'] = str(e)
                breaker.record_failure(str(e))
                print(f"  ✗ Fehler beim Starten des Ring-Streams '{camera_id}': {e}")
                return False

    def is_stream_running(self, camera_id: str) -> bool:
        """Prüft ob Stream läuft"""
        with self.lock:
            if camera_id not in self.streams:
                return False

            process = self.streams[camera_id]['process']
            return process.poll() is None  # None = noch aktiv

    def get_stream_info(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt Stream-Info

        Args:
            camera_id: Kamera-ID

        Returns:
            Stream-Info oder None
        """
        with self.lock:
            if camera_id not in self.streams:
                return None

            stream = self.streams[camera_id]
            return {
                'camera_id': camera_id,
                'rtsp_url': stream.get('rtsp_url'),
                'source_type': stream.get('source_type', 'rtsp'),
                'hls_url': f"/static/hls/{camera_id}.m3u8",
                'running': self.is_stream_running(camera_id),
                'started_at': stream['started_at'],
                'uptime': time.time() - stream['started_at'],
                'hw_accel': stream.get('hw_accel')
            }

    def get_all_streams(self) -> Dict[str, Dict[str, Any]]:
        """Gibt alle Stream-Infos zurück"""
        with self.lock:
            return {
                camera_id: self.get_stream_info(camera_id)
                for camera_id in self.streams.keys()
            }

    def capture_snapshot(self, rtsp_url: str, timeout: int = 6) -> Optional[bytes]:
        """Erstellt ein einzelnes JPEG-Snapshot aus einer RTSP-Quelle."""
        if not self.has_ffmpeg:
            return None

        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-fflags', 'nobuffer',
            '-rtsp_transport', 'tcp',
            '-timeout', '5000000',
            '-i', rtsp_url,
            '-frames:v', '1',
            '-q:v', '3',
            '-f', 'image2pipe',
            '-vcodec', 'mjpeg',
            'pipe:1'
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=max(2, min(timeout, 15)),
                check=False
            )
            if proc.returncode != 0:
                return None
            return proc.stdout or None
        except Exception:
            return None

    # ========================================================================
    # RECOVERY
    # ========================================================================

    def _start_recovery_monitor(self):
        if self._recovery_active:
            return
        self._recovery_active = True
        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True,
            name="StreamRecoveryMonitor"
        )
        self._recovery_thread.start()

    def _stop_recovery_monitor(self):
        self._recovery_active = False
        if self._recovery_thread:
            self._recovery_thread.join(timeout=max(2.0, self.recovery_interval * 2))
            self._recovery_thread = None

    def _reset_recovery_state(self, camera_id: str):
        self._recovery_state[camera_id] = {
            'retry_timestamps': [],
            'cooldown_until': 0.0
        }

    def _recovery_loop(self):
        while self._recovery_active:
            try:
                self._recovery_tick()
            except Exception as e:
                self.logger.warning("Recovery tick failed: %s", e)
            time.sleep(self.recovery_interval)

    def _recovery_tick(self):
        now = time.time()
        restart_queue = []

        with self.lock:
            for camera_id, desired_spec in list(self._desired_streams.items()):
                stream = self.streams.get(camera_id)
                running = False
                exit_code = None

                if stream:
                    process = stream.get('process')
                    if process is not None:
                        exit_code = process.poll()
                        running = exit_code is None

                if running:
                    continue

                state = self._recovery_state.get(camera_id)
                if not state:
                    state = {'retry_timestamps': [], 'cooldown_until': 0.0}
                    self._recovery_state[camera_id] = state

                retry_timestamps = state.get('retry_timestamps', [])
                retry_timestamps = [t for t in retry_timestamps if now - t <= self.RECOVERY_WINDOW_SECONDS]
                state['retry_timestamps'] = retry_timestamps

                if now < float(state.get('cooldown_until', 0.0)):
                    continue

                if len(retry_timestamps) >= self.recovery_max_retries:
                    state['cooldown_until'] = now + self.recovery_cooldown_seconds
                    metrics = self._ensure_metrics(camera_id)
                    metrics['cooldown_until'] = state['cooldown_until']
                    metrics['last_error'] = 'recovery_cooldown'
                    self.logger.error(
                        "Stream recovery escalated: camera=%s retries=%s cooldown=%ss",
                        camera_id,
                        len(retry_timestamps),
                        int(self.recovery_cooldown_seconds)
                    )
                    continue

                attempt = len(retry_timestamps) + 1
                delay = min(self.recovery_backoff_max, self.recovery_backoff_base * (2 ** (attempt - 1)))
                if self.recovery_jitter_max > 0:
                    delay += random.uniform(0.0, self.recovery_jitter_max)

                state['retry_timestamps'].append(now)
                restart_queue.append((camera_id, desired_spec, max(0.0, delay), exit_code, attempt))
                metrics = self._ensure_metrics(camera_id)
                metrics['last_recovery_attempt_ts'] = now
                metrics['last_exit_code'] = exit_code

                # Toten Prozess/Artefakte aufräumen, bevor Restart versucht wird.
                if camera_id in self.streams:
                    del self.streams[camera_id]
                self._cleanup_hls_files(camera_id)

        for camera_id, desired_spec, delay, exit_code, attempt in restart_queue:
            self.logger.warning(
                "Stream recovery scheduled: camera=%s type=%s attempt=%s delay=%.1fs exit_code=%s",
                camera_id,
                desired_spec.get('type'),
                attempt,
                delay,
                exit_code
            )
            time.sleep(delay)
            ok = self._restart_from_desired_spec(desired_spec)
            with self.lock:
                metrics = self._ensure_metrics(camera_id)
                if ok:
                    metrics['recovery_success_total'] += 1
                else:
                    metrics['recovery_failed_total'] += 1
            if ok:
                self.logger.info("Stream recovery successful: camera=%s attempt=%s", camera_id, attempt)
            else:
                self.logger.error("Stream recovery failed: camera=%s attempt=%s", camera_id, attempt)

    def _restart_from_desired_spec(self, desired_spec: Dict[str, Any]) -> bool:
        spec_type = str(desired_spec.get('type', '')).strip().lower()
        if spec_type == 'rtsp':
            return self.start_stream(
                camera_id=str(desired_spec.get('camera_id')),
                rtsp_url=str(desired_spec.get('rtsp_url')),
                force_cpu=bool(desired_spec.get('force_cpu', False)),
                resolution=desired_spec.get('resolution')
            )
        if spec_type == 'ring':
            return self.start_ring_stream(
                camera_id=str(desired_spec.get('camera_id')),
                ring_device_id=str(desired_spec.get('ring_device_id')),
                refresh_token=str(desired_spec.get('refresh_token', ''))
            )
        return False

    # ========================================================================
    # FFMPEG
    # ========================================================================

    def _build_ffmpeg_cmd(self, rtsp_url: str, hls_playlist: str,
                          hls_segment: str, use_hw_accel: bool = True,
                          resolution: Optional[str] = None) -> list:
        """
        Baut FFmpeg-Kommando

        Args:
            rtsp_url: RTSP-Quelle
            hls_playlist: HLS-Playlist-Pfad
            hls_segment: HLS-Segment-Pfad-Template
            use_hw_accel: Hardware-Beschleunigung nutzen
            resolution: Ziel-Auflösung (z.B. '640x360') oder None für Passthrough

        Returns:
            FFmpeg-Kommando als Liste
        """
        cmd = ['ffmpeg']
        cmd.extend(['-hide_banner', '-loglevel', 'warning'])

        # Hardware-Beschleunigung (Input) - nur wenn kein Scaling nötig
        if use_hw_accel and not resolution and self.hw_accel_mode == 'qsv':
            cmd.extend([
                '-hwaccel', 'qsv',
                '-hwaccel_device', '/dev/dri/renderD128',
                '-hwaccel_output_format', 'qsv'
            ])
        elif use_hw_accel and not resolution and self.hw_accel_mode == 'vaapi':
            cmd.extend([
                '-hwaccel', 'vaapi',
                '-hwaccel_device', '/dev/dri/renderD128',
                '-hwaccel_output_format', 'vaapi'
            ])

        # Input-Optionen (MÜSSEN vor -i stehen!)
        cmd.extend([
            '-fflags', 'nobuffer',
            '-flags', 'low_delay',
            '-probesize', '32768',
            '-analyzeduration', '1000000',
            '-rtsp_transport', 'tcp',  # Zuverlässiger als UDP
            '-timeout', '5000000',  # 5s Timeout
            '-i', rtsp_url
        ])

        if resolution:
            # Skalierung aktiv: Software-Encoding mit Scale-Filter
            width, height = resolution.split('x')
            cmd.extend([
                '-vf', f'scale={width}:{height}',
                '-c:v', 'libx264',
                # Erzwinge kurze GOP für stabile 1s-HLS-Segmente und schnellen Start.
                '-g', '25',
                '-keyint_min', '25',
                '-sc_threshold', '0',
                '-force_key_frames', 'expr:gte(t,n_forced*1)',
                '-preset', 'veryfast',
                '-tune', 'zerolatency',
                '-b:v', '800k'
            ])
        elif use_hw_accel and self.hw_accel_mode == 'qsv':
            cmd.extend(['-c:v', 'h264_qsv'])
        elif use_hw_accel and self.hw_accel_mode == 'vaapi':
            cmd.extend(['-c:v', 'h264_vaapi'])
        else:
            # Passthrough: copy ohne Re-Encoding
            cmd.extend(['-c:v', 'copy'])

        # Audio deaktivieren (G.726 aus IP-Kameras verursacht Probleme)
        cmd.append('-an')

        # HLS-Optionen
        cmd.extend([
            '-f', 'hls',
            '-hls_time', str(self.HLS_SEGMENT_TIME),
            '-hls_list_size', str(self.HLS_LIST_SIZE),
            '-hls_delete_threshold', str(self.HLS_DELETE_THRESHOLD),
            '-hls_flags', self.HLS_FLAGS,
            '-muxdelay', '0',
            '-muxpreload', '0',
            '-hls_segment_filename', hls_segment,
            hls_playlist
        ])

        return cmd

    def _cleanup_hls_files(self, camera_id: str):
        """Löscht HLS-Dateien einer Kamera"""
        import glob

        patterns = [
            os.path.join(self.hls_dir, f"{camera_id}.m3u8"),
            os.path.join(self.hls_dir, f"{camera_id}_*.ts")
        ]

        for pattern in patterns:
            for file_path in glob.glob(pattern):
                try:
                    os.remove(file_path)
                except:
                    pass

    def _cleanup_all_hls_files(self):
        """Löscht alle HLS-Dateien im Ausgabeverzeichnis."""
        import glob
        for pattern in (
            os.path.join(self.hls_dir, "*.m3u8"),
            os.path.join(self.hls_dir, "*.ts"),
        ):
            for file_path in glob.glob(pattern):
                try:
                    os.remove(file_path)
                except:
                    pass

    # ========================================================================
    # SYSTEM
    # ========================================================================

    def get_debug_metrics(self) -> Dict[str, Any]:
        with self.lock:
            now = time.time()
            per_stream = {}
            camera_ids = set(self._stream_metrics.keys()) | set(self._desired_streams.keys()) | set(self.streams.keys())
            for cam_id in sorted(camera_ids):
                state = self._recovery_state.get(cam_id, {})
                retry_timestamps = list(state.get('retry_timestamps', []))
                cooldown_until = float(state.get('cooldown_until', 0.0) or 0.0)
                metrics = dict(self._stream_metrics.get(cam_id, {}))
                metrics.setdefault('cooldown_until', cooldown_until)
                hls_files = glob.glob(os.path.join(self.hls_dir, f"{cam_id}_*.ts"))
                playlist_exists = os.path.exists(os.path.join(self.hls_dir, f"{cam_id}.m3u8"))

                stream = self.streams.get(cam_id)
                running = False
                process_pid = None
                if stream and stream.get('process') is not None:
                    process = stream.get('process')
                    process_pid = getattr(process, 'pid', None)
                    running = process.poll() is None

                per_stream[cam_id] = {
                    'running': running,
                    'process_pid': process_pid,
                    'source_type': (stream or {}).get('source_type') or (self._desired_streams.get(cam_id, {}).get('type')),
                    'desired': self._desired_streams.get(cam_id),
                    'metrics': metrics,
                    'recovery': {
                        'retries_in_window': len([t for t in retry_timestamps if now - t <= self.RECOVERY_WINDOW_SECONDS]),
                        'cooldown_until': cooldown_until,
                        'in_cooldown': now < cooldown_until,
                    },
                    'hls': {
                        'playlist_exists': playlist_exists,
                        'segment_count': len(hls_files),
                    }
                }

            return {
                'timestamp': now,
                'auto_recovery_enabled': self.recovery_enabled,
                'recovery_check_interval_seconds': self.recovery_interval,
                'recovery_max_retries': self.recovery_max_retries,
                'recovery_cooldown_seconds': self.recovery_cooldown_seconds,
                'circuit_breakers': self.get_circuit_breaker_stats(),
                'streams': per_stream,
            }

    def get_status(self) -> Dict[str, Any]:
        """Status für Web-API"""
        with self.lock:
            return {
                'ffmpeg_available': self.has_ffmpeg,
                'hw_accel_mode': self.hw_accel_mode,
                'auto_recovery_enabled': self.recovery_enabled,
                'active_streams': len(self.streams),
                'streams': self.get_all_streams()
            }

    def shutdown(self):
        """Cleanup"""
        self._stop_recovery_monitor()
        print(f"  🛑 Stoppe alle Streams...")
        self.stop_all_streams()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        StreamManager.NAME,
        StreamManager.VERSION,
        StreamManager.DESCRIPTION,
        StreamManager,
        author=StreamManager.AUTHOR,
        dependencies=StreamManager.DEPENDENCIES
    )
