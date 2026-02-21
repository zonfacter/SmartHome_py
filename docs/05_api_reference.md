# 05 API Reference (verbindlich)

Nur hier gelistete Endpunkte gelten als dokumentierter API-Stand.

## Versionierung und Deprecation
- Aktueller stabiler API-Major: `v1`
- Aktueller Namespace: `/api/*` (entspricht `v1`)
- Breaking Changes nur über neuen Major-Namespace (z. B. `/api/v2/*`)
- Deprecation-Fenster vor Entfernen: mindestens `90` Tage
- Laufende Policy und Sunset-Regeln: `docs/06_api_lifecycle_policy.md`
- OpenAPI-Vertrag: `docs/openapi.json`
- Socket/Event-Verträge: `docs/08_socket_events.md`
- Runtime-Signale:
- `X-API-Version`, `X-API-Major-Version`, `X-API-Compatibility-Model` auf allen `/api/*`-Responses
- Für deprecated Endpunkte zusätzlich: `Deprecation`, `Sunset`, optional `X-API-Replacement`

## Fehlercode-Baseline
- `400`: Payload ungültig oder Pflichtfelder fehlen
- `401`: Authentifizierung für geschützte Control-API fehlt/ungültig
- `403`: Origin-/Autorisierungsregeln verletzt
- `404`: Ressource/Route nicht gefunden
- `429`: Rate-Limit auf kritischen Endpunkten überschritten
- `500`: Interner Fehler

## System
- `GET /api/system/status`
- `GET /api/system/dependencies`
- `GET /api/system/versioning`
- `GET /api/telemetry`

## PLC / TwinCAT
- `GET /api/plc/config`
- `POST /api/plc/config`
- `POST /api/plc/connect`
- `POST /api/plc/disconnect`
- `GET /api/plc/ads/route/status`
- `POST /api/plc/ads/route/add`
- `POST /api/plc/ads/route/test`
- `GET /api/plc/symbols`
- `POST /api/plc/symbols/upload`
- `POST /api/plc/symbols/live`

## Variablen
- `GET /api/variables/search`
- `POST /api/variables/write`
- `POST /api/variables/read`
- `GET /api/variables/statistics`

## Kamera / Ring
- `GET /api/cameras`
- `POST /api/cameras`
- `PUT /api/cameras/<cam_id>`
- `DELETE /api/cameras/<cam_id>`
- `POST /api/cameras/scan`
- `POST /api/cameras/diagnose`
- `POST /api/cameras/alert`
- `GET /api/cameras/<cam_id>/snapshot`
- `POST /api/cameras/<cam_id>/start`
- `POST /api/cameras/<cam_id>/stop`
- `GET /api/ring/status`
- `POST /api/ring/auth`
- `GET /api/ring/cameras`
- `POST /api/ring/cameras/import`

## Routing / Trigger
- `GET /api/routing/config`
- `POST /api/routing/config`
- `GET /api/camera-triggers`
- `POST /api/camera-triggers`
- `GET /api/camera-triggers/export`
- `POST /api/camera-triggers/import`

## Admin
- `GET /api/admin/plcs`
- `POST /api/admin/plcs`
- `GET /api/admin/logs`
- `GET /api/admin/logs/verify`
- `GET /api/admin/logs/export`
- `POST /api/admin/logs/clear`
- `GET /api/admin/service/info`
- `POST /api/admin/service/restart`
- `POST /api/admin/service/restart-daemon`

## Monitoring
- `GET /api/monitor/dataflow`
- `GET /api/monitor/latency`
- `GET /api/monitor/slo`
- `GET /api/monitor/streams`
- `GET /api/monitor/dlq`
- `POST /api/monitor/dlq/reprocess`
- `POST /api/monitor/dlq/clear`
