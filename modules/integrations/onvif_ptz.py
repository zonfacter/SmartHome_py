"""
ONVIF PTZ Controller
Steuert PTZ-Kameras ueber das ONVIF-Protokoll.
"""

import logging
import threading

logger = logging.getLogger(__name__)


class OnvifPTZController:
    """
    ONVIF PTZ Controller fuer eine einzelne Kamera.
    Verbindet sich per ONVIF SOAP und steuert Pan/Tilt/Zoom.
    """

    def __init__(self, host, port=80, user='admin', password='admin'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

        self._camera = None
        self._media_service = None
        self._ptz_service = None
        self._media_profile = None
        self._profile_token = None

        self.has_ptz = False
        self.connected = False
        self._lock = threading.Lock()

    def connect(self):
        """Verbindet zur Kamera und ermittelt PTZ-Faehigkeiten."""
        try:
            from onvif import ONVIFCamera

            logger.info(f"ONVIF: Verbinde zu {self.host}:{self.port}...")
            self._camera = ONVIFCamera(self.host, self.port, self.user, self.password)

            # Media-Service holen
            self._media_service = self._camera.create_media_service()
            profiles = self._media_service.GetProfiles()

            if not profiles:
                logger.warning(f"ONVIF: Keine Media-Profile gefunden auf {self.host}")
                self.connected = True
                self.has_ptz = False
                return True

            # Suche PTZ-faehiges Profil
            for profile in profiles:
                if hasattr(profile, 'PTZConfiguration') and profile.PTZConfiguration is not None:
                    self._media_profile = profile
                    self._profile_token = profile.token
                    break

            if self._profile_token is None:
                # Fallback: erstes Profil verwenden
                self._media_profile = profiles[0]
                self._profile_token = profiles[0].token
                logger.info(f"ONVIF: Kein PTZ-Profil gefunden, verwende erstes Profil: {self._profile_token}")

            # PTZ-Service holen
            try:
                self._ptz_service = self._camera.create_ptz_service()
                # Teste ob PTZ wirklich verfuegbar ist
                self._ptz_service.GetConfigurations()
                self.has_ptz = True
                logger.info(f"ONVIF: PTZ verfuegbar auf {self.host}, Profil: {self._profile_token}")
            except Exception as e:
                logger.info(f"ONVIF: Kein PTZ-Service auf {self.host}: {e}")
                self.has_ptz = False

            self.connected = True
            return True

        except Exception as e:
            logger.error(f"ONVIF: Verbindungsfehler zu {self.host}: {e}")
            self.connected = False
            self.has_ptz = False
            return False

    def get_ptz_status(self):
        """Aktuelle PTZ-Position abfragen."""
        if not self.has_ptz or not self._ptz_service:
            return None

        with self._lock:
            try:
                status = self._ptz_service.GetStatus({'ProfileToken': self._profile_token})
                result = {
                    'pan': 0.0,
                    'tilt': 0.0,
                    'zoom': 0.0
                }
                if hasattr(status, 'Position') and status.Position:
                    pos = status.Position
                    if hasattr(pos, 'PanTilt') and pos.PanTilt:
                        result['pan'] = float(pos.PanTilt.x)
                        result['tilt'] = float(pos.PanTilt.y)
                    if hasattr(pos, 'Zoom') and pos.Zoom:
                        result['zoom'] = float(pos.Zoom.x)
                return result
            except Exception as e:
                logger.error(f"ONVIF: GetStatus Fehler: {e}")
                return None

    def continuous_move(self, pan_speed=0.0, tilt_speed=0.0, zoom_speed=0.0, timeout_ms=250):
        """Kontinuierliche Bewegung starten (fuer Richtungs-Buttons)."""
        if not self.has_ptz or not self._ptz_service:
            return False

        with self._lock:
            try:
                request = self._ptz_service.create_type('ContinuousMove')
                request.ProfileToken = self._profile_token
                request.Velocity = {
                    'PanTilt': {'x': float(pan_speed), 'y': float(tilt_speed)},
                    'Zoom': {'x': float(zoom_speed)}
                }
                # Safety timeout: camera stops automatically even if Stop request is delayed/lost.
                timeout_ms = max(100, min(int(timeout_ms), 2000))
                request.Timeout = f"PT{timeout_ms/1000:.3f}S"
                self._ptz_service.ContinuousMove(request)
                return True
            except Exception as e:
                logger.error(f"ONVIF: ContinuousMove Fehler: {e}")
                return False

    def stop(self):
        """Alle PTZ-Bewegungen stoppen."""
        if not self.has_ptz or not self._ptz_service:
            return False

        with self._lock:
            try:
                request = self._ptz_service.create_type('Stop')
                request.ProfileToken = self._profile_token
                request.PanTilt = True
                request.Zoom = True
                self._ptz_service.Stop(request)
                return True
            except Exception as e:
                logger.error(f"ONVIF: Stop Fehler: {e}")
                return False

    def relative_move(self, pan=0.0, tilt=0.0, zoom=0.0):
        """Relative Bewegung ausfuehren."""
        if not self.has_ptz or not self._ptz_service:
            return False

        with self._lock:
            try:
                request = self._ptz_service.create_type('RelativeMove')
                request.ProfileToken = self._profile_token
                request.Translation = {
                    'PanTilt': {'x': float(pan), 'y': float(tilt)},
                    'Zoom': {'x': float(zoom)}
                }
                self._ptz_service.RelativeMove(request)
                return True
            except Exception as e:
                logger.error(f"ONVIF: RelativeMove Fehler: {e}")
                return False

    def go_to_preset(self, preset_token):
        """Zu einem gespeicherten Preset fahren."""
        if not self.has_ptz or not self._ptz_service:
            return False

        with self._lock:
            try:
                request = self._ptz_service.create_type('GotoPreset')
                request.ProfileToken = self._profile_token
                request.PresetToken = str(preset_token)
                self._ptz_service.GotoPreset(request)
                return True
            except Exception as e:
                logger.error(f"ONVIF: GotoPreset Fehler: {e}")
                return False

    def set_preset(self, preset_name):
        """Aktuellen Standort als Preset speichern."""
        if not self.has_ptz or not self._ptz_service:
            return None

        with self._lock:
            try:
                request = self._ptz_service.create_type('SetPreset')
                request.ProfileToken = self._profile_token
                request.PresetName = str(preset_name)
                result = self._ptz_service.SetPreset(request)
                token = str(result) if result else None
                logger.info(f"ONVIF: Preset gespeichert: {preset_name} -> {token}")
                return token
            except Exception as e:
                logger.error(f"ONVIF: SetPreset Fehler: {e}")
                return None

    def get_presets(self):
        """Liste aller gespeicherten Presets."""
        if not self.has_ptz or not self._ptz_service:
            return []

        with self._lock:
            try:
                presets = self._ptz_service.GetPresets({'ProfileToken': self._profile_token})
                result = []
                if presets:
                    for p in presets:
                        result.append({
                            'token': str(p.token) if hasattr(p, 'token') else str(p._token),
                            'name': str(p.Name) if hasattr(p, 'Name') and p.Name else f"Preset {p.token}"
                        })
                return result
            except Exception as e:
                logger.error(f"ONVIF: GetPresets Fehler: {e}")
                return []

    def go_home(self):
        """Home-Position anfahren."""
        if not self.has_ptz or not self._ptz_service:
            return False

        with self._lock:
            try:
                request = self._ptz_service.create_type('GotoHomePosition')
                request.ProfileToken = self._profile_token
                self._ptz_service.GotoHomePosition(request)
                return True
            except Exception as e:
                logger.warning(f"ONVIF: GotoHomePosition nicht unterstuetzt, versuche Preset 1: {e}")
                # Fallback: Preset 1 anfahren
                return self.go_to_preset('1')
