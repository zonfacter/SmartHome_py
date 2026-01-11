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
    HLS_SEGMENT_TIME = 2  # Sekunden pro Segment
    HLS_LIST_SIZE = 3  # Anzahl Segmente in Playlist
    HLS_FLAGS = "delete_segments+append_list"

    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()

        # Module-Referenzen
        self.data_gateway = None

        # Streams
        self.streams = {}  # camera_id -> {process, rtsp_url, hls_path, etc.}

        # HLS Output-Verzeichnis
        self.hls_dir = 'web/static/hls'

        # Capabilities
        self.has_ffmpeg = self._check_ffmpeg()
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

        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
        print(f"     🎬 FFmpeg: {'Verfügbar' if self.has_ffmpeg else 'NICHT INSTALLIERT'}")
        print(f"     🎮 HW-Accel: {self.hw_accel_mode or 'CPU (Software)'}")
        print(f"     📁 HLS-Dir: {self.hls_dir}")

    def _check_ffmpeg(self) -> bool:
        """Prüft ob FFmpeg installiert ist"""
        return shutil.which('ffmpeg') is not None

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

    def start_stream(self, camera_id: str, rtsp_url: str, force_cpu: bool = False) -> bool:
        """
        Startet RTSP -> HLS Transcoding

        Args:
            camera_id: Eindeutige Kamera-ID (z.B. 'garage')
            rtsp_url: RTSP-URL (z.B. 'rtsp://192.168.1.100/stream')
            force_cpu: Erzwingt CPU-Encoding

        Returns:
            True wenn erfolgreich gestartet
        """
        if not self.has_ffmpeg:
            print(f"  ✗ FFmpeg nicht installiert!")
            return False

        with self.lock:
            # Prüfe ob bereits läuft
            if camera_id in self.streams:
                print(f"  ⚠️  Stream '{camera_id}' läuft bereits!")
                return False

            # HLS-Pfade
            hls_playlist = os.path.join(self.hls_dir, f"{camera_id}.m3u8")
            hls_segment = os.path.join(self.hls_dir, f"{camera_id}_%03d.ts")

            # FFmpeg-Kommando
            cmd = self._build_ffmpeg_cmd(
                rtsp_url,
                hls_playlist,
                hls_segment,
                use_hw_accel=not force_cpu
            )

            try:
                # Starte FFmpeg-Prozess
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL
                )

                # Speichere Stream-Info
                self.streams[camera_id] = {
                    'process': process,
                    'rtsp_url': rtsp_url,
                    'hls_playlist': hls_playlist,
                    'hls_segment': hls_segment,
                    'started_at': time.time(),
                    'hw_accel': self.hw_accel_mode if not force_cpu else None
                }

                print(f"  ▶️  Stream '{camera_id}' gestartet")
                print(f"     🎬 HLS: /static/hls/{camera_id}.m3u8")

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

    def stop_all_streams(self):
        """Stoppt alle laufenden Streams"""
        with self.lock:
            camera_ids = list(self.streams.keys())
            for camera_id in camera_ids:
                self.stop_stream(camera_id)

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
                'rtsp_url': stream['rtsp_url'],
                'hls_url': f"/static/hls/{camera_id}.m3u8",
                'running': self.is_stream_running(camera_id),
                'started_at': stream['started_at'],
                'uptime': time.time() - stream['started_at'],
                'hw_accel': stream['hw_accel']
            }

    def get_all_streams(self) -> Dict[str, Dict[str, Any]]:
        """Gibt alle Stream-Infos zurück"""
        with self.lock:
            return {
                camera_id: self.get_stream_info(camera_id)
                for camera_id in self.streams.keys()
            }

    # ========================================================================
    # FFMPEG
    # ========================================================================

    def _build_ffmpeg_cmd(self, rtsp_url: str, hls_playlist: str,
                          hls_segment: str, use_hw_accel: bool = True) -> list:
        """
        Baut FFmpeg-Kommando

        Args:
            rtsp_url: RTSP-Quelle
            hls_playlist: HLS-Playlist-Pfad
            hls_segment: HLS-Segment-Pfad-Template
            use_hw_accel: Hardware-Beschleunigung nutzen

        Returns:
            FFmpeg-Kommando als Liste
        """
        cmd = ['ffmpeg']

        # Hardware-Beschleunigung (Input)
        if use_hw_accel and self.hw_accel_mode == 'qsv':
            cmd.extend([
                '-hwaccel', 'qsv',
                '-hwaccel_device', '/dev/dri/renderD128',
                '-hwaccel_output_format', 'qsv'
            ])
        elif use_hw_accel and self.hw_accel_mode == 'vaapi':
            cmd.extend([
                '-hwaccel', 'vaapi',
                '-hwaccel_device', '/dev/dri/renderD128',
                '-hwaccel_output_format', 'vaapi'
            ])

        # Input
        cmd.extend([
            '-i', rtsp_url,
            '-rtsp_transport', 'tcp',  # Zuverlässiger als UDP
            '-timeout', '5000000'  # 5s Timeout
        ])

        # Video-Codec
        if use_hw_accel and self.hw_accel_mode == 'qsv':
            cmd.extend(['-c:v', 'h264_qsv'])
        elif use_hw_accel and self.hw_accel_mode == 'vaapi':
            cmd.extend(['-c:v', 'h264_vaapi'])
        else:
            cmd.extend(['-c:v', 'libx264', '-preset', 'veryfast'])

        # Audio (kopieren oder deaktivieren)
        cmd.extend(['-c:a', 'aac', '-b:a', '128k'])

        # HLS-Optionen
        cmd.extend([
            '-f', 'hls',
            '-hls_time', str(self.HLS_SEGMENT_TIME),
            '-hls_list_size', str(self.HLS_LIST_SIZE),
            '-hls_flags', self.HLS_FLAGS,
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
