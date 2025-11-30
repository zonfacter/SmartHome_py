"""
RTSP Camera Stream Module
Version: 1.0.0
Zeigt RTSP Kamera-Streams in GUI Cards
"""

from module_manager import BaseModule
from typing import Dict, Any, Optional
import threading


class RTSPIntegration(BaseModule):
    NAME = "rtsp_integration"
    VERSION = "1.0.0"
    DESCRIPTION = "RTSP Kamera-Streams"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = []
    
    def __init__(self):
        super().__init__()
        self.streams = {}  # camera_id -> stream_info
    
    def initialize(self, app_context: Any):
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def add_camera(self, camera_id: str, rtsp_url: str, name: str = None):
        """
        Fügt RTSP-Kamera hinzu
        
        Args:
            camera_id: Eindeutige ID
            rtsp_url: rtsp://user:pass@ip:port/stream
            name: Anzeige-Name
        """
        self.streams[camera_id] = {
            'url': rtsp_url,
            'name': name or camera_id,
            'active': False,
            'thread': None
        }
        print(f"  ✓ Kamera hinzugefügt: {name or camera_id}")
    
    def get_frame(self, camera_id: str):
        """Holt aktuelles Frame (für GUI)"""
        try:
            import cv2
            
            if camera_id not in self.streams:
                return None
            
            stream_info = self.streams[camera_id]
            cap = cv2.VideoCapture(stream_info['url'])
            
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                return frame
            return None
            
        except ImportError:
            print("  ⚠️  opencv-python nicht installiert! pip install opencv-python")
            return None
        except Exception as e:
            print(f"  ✗ Fehler bei {camera_id}: {e}")
            return None
    
    def shutdown(self):
        """Stoppt alle Streams"""
        for camera_id in self.streams:
            # Stop threads if running
            pass
        print("  ✓ RTSP Streams gestoppt")


def register(module_manager):
    module_manager.register_module(
        RTSPIntegration.NAME,
        RTSPIntegration.VERSION,
        RTSPIntegration.DESCRIPTION,
        RTSPIntegration,
        author=RTSPIntegration.AUTHOR
    )
