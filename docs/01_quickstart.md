# 01 Quickstart (Web-HMI)

Dies ist der verbindliche Startpfad fuer neue Installationen.

## Voraussetzungen
- Linux Host oder Docker Runtime
- Python 3.11+
- Node.js/npm (nur fuer Ring-Bridge Runtime)
- ffmpeg (Kamera-Streams)

## Installation (native Linux)
```bash
cd /opt/Smarthome-Web
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
npm ci --omit=dev --ignore-scripts
cp .env.example .env
```

## Start
```bash
. .venv/bin/activate
python start_web_hmi.py --host 0.0.0.0 --port 5000
```

## Healthcheck
```bash
curl -fsS http://127.0.0.1:5000/api/system/status
```

## Docker-Alternative
Siehe `docs/DOCKER_DEPLOYMENT.md`.

## Nächster Schritt
1. TwinCAT einrichten: `docs/02_twincat_setup.md`
2. Kameras einbinden: `docs/03_camera_setup.md`
3. Gateway-Integration: `docs/04_gateway_integration.md`
4. API-Referenz: `docs/05_api_reference.md`
