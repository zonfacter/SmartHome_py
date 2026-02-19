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

    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()

        # Module-Referenzen
        self.data_gateway = None

        # Streams
        self.streams = {}  # camera_id -> {process, rtsp_url, hls_path, etc.}
        self._delayed_stop_timers = {}  # camera_id -> Timer

        # HLS Output-Verzeichnis
        self.hls_dir = 'web/static/hls'

        # Capabilities
        self.has_ffmpeg = self._check_ffmpeg()
        self.has_node = self._check_node()
        self.hw_accel_mode = None

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

    def _check_ffmpeg(self) -> bool:
        """Prüft ob FFmpeg installiert ist"""
        return shutil.which('ffmpeg') is not None

    def _check_node(self) -> bool:
        """Prüft ob Node.js installiert ist"""
        return shutil.which('node') is not None

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

                del self.streams[camera_id]
                self._cleanup_hls_files(camera_id)

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
                    'resolution': resolution
                }

                print(f"  ▶️  Stream '{camera_id}' gestartet")
                print(f"     🎬 HLS: /static/hls/{camera_id}.m3u8")

                # Kurz prüfen, ob FFmpeg sofort wieder beendet wurde.
                time.sleep(0.4)
                if process.poll() is not None:
                    del self.streams[camera_id]
                    self._cleanup_hls_files(camera_id)
                    print(f"  ✗ Stream '{camera_id}' direkt beendet")
                    return False

                return True

            except Exception as e:
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
            if camera_id not in self.streams:
                return False

            stream = self.streams[camera_id]
            process = stream['process']

            # Beende FFmpeg
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            # Cleanup HLS-Dateien
            if cleanup:
                self._cleanup_hls_files(camera_id)

            # Entferne aus Liste
            del self.streams[camera_id]

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
            if camera_id in self.streams:
                current = self.streams[camera_id]
                process = current.get('process')
                is_running = process is not None and process.poll() is None
                same_source = (
                    current.get('source_type') == 'ring' and
                    str(current.get('ring_device_id')) == str(ring_device_id)
                )
                if is_running and same_source:
                    return True
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
                    'resolution': None
                }

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
                    print(f"  ✗ Ring-Stream '{camera_id}' direkt beendet")
                    if err_text:
                        first = err_text.splitlines()[0] if err_text.splitlines() else err_text
                        print(f"    RingBridge: {first}")
                    return False

                print(f"  ▶️  Ring-Stream '{camera_id}' gestartet")
                print(f"     🎬 HLS: /static/hls/{camera_id}.m3u8")
                return True
            except Exception as e:
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

    def get_status(self) -> Dict[str, Any]:
        """Status für Web-API"""
        with self.lock:
            return {
                'ffmpeg_available': self.has_ffmpeg,
                'hw_accel_mode': self.hw_accel_mode,
                'active_streams': len(self.streams),
                'streams': self.get_all_streams()
            }

    def shutdown(self):
        """Cleanup"""
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
