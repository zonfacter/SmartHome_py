# 03 Camera Setup (RTSP + Ring)

Kamera-Streams sind ein First-Class-Use-Case des Gateways.

## RTSP Kamera
### UI
Pfad: `Setup -> Kameras`

- Kamera anlegen (ID + URL)
- Testen via Diagnose
- Stream starten

### API
- Kamera speichern: `POST /api/cameras`
- Liste: `GET /api/cameras`
- Diagnose: `POST /api/cameras/diagnose`
- Auto-Scan: `POST /api/cameras/scan`
- Stream starten: `POST /api/cameras/<cam_id>/start`
- Stream stoppen: `POST /api/cameras/<cam_id>/stop`

## Ring Kamera
### Voraussetzungen
- `ring-client-api` via npm
- `RING_REFRESH_TOKEN` gesetzt

### API
- Auth setzen: `POST /api/ring/auth`
- Ring-Kameras abrufen: `GET /api/ring/cameras`
- Ring-Kameras importieren: `POST /api/ring/cameras/import`

## PTZ (ONVIF)
- Status: `GET /api/cameras/<cam_id>/ptz/status`
- Move: `POST /api/cameras/<cam_id>/ptz/move`
- Stop: `POST /api/cameras/<cam_id>/ptz/stop`

## Troubleshooting
- Leere HLS-Ausgabe: ffmpeg vorhanden?
- Ring stockt: Node/Ring-Abhaengigkeiten und Token pruefen
- Stream instabil: `GET /api/monitor/streams` und `/api/monitor/slo`
