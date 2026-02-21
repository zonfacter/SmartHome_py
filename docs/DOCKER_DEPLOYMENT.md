# Docker Deployment (First-Class Path)

Diese Anleitung beschreibt den offiziellen Container-Betrieb als Alternative zum nativen `systemd`-Setup.

## Voraussetzungen

- Docker Engine + Compose Plugin
- Ports: `5000/tcp`

## Start (Compose)

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

## Healthcheck

- Container-Healthcheck und Endpoint nutzen:
  - `GET /api/system/status`

Prüfen:

```bash
curl -fsS http://127.0.0.1:5000/api/system/status
```

## Persistente Daten

Folgende Verzeichnisse sind als RW-Volumes vorgesehen:

- `./config -> /app/config`
- `./plc_data -> /app/plc_data`
- `./web/static/hls -> /app/web/static/hls`

Damit bleiben Konfigurationen/State bei Container-Neustarts erhalten.

## Restart-Semantik in Docker

- `POST /api/admin/service/restart`:
  - Beendet den Hauptprozess kontrolliert.
  - Docker `restart: unless-stopped` startet den Container neu.
- `POST /api/admin/service/restart-daemon`:
  - Im Container bewusst deaktiviert.
  - API liefert klare Fehlermeldung (HTTP 400) und schreibt ein Audit-Event.

## Native Linux vs Docker

- Native Linux (`systemd`): `deploy/systemd/*`, `scripts/web_server_ctl.sh`
- Docker: `Dockerfile` + `docker-compose.yml`

Die Betriebsarten sind getrennt; Docker benötigt kein host-seitiges `systemd`.
