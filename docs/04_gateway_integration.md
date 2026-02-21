# 04 Gateway Integration

Dieser Vertrag beschreibt, wie externe Systeme ans interne Gateway andocken.

## DataGateway Kernidee
`route_data(source, tag, value, metadata)` normalisiert Daten und verteilt sie an Ziele (z. B. UI, MQTT, PLC).

## Routing-Konfiguration
Datei: `config/routing.json`

Beispiel:
```json
{
  "version": "1.0",
  "routes": [
    {
      "id": "camera_alert_to_mqtt",
      "from": "Alarm.Camera.*",
      "to": ["websocket", "mqtt"],
      "enabled": true
    }
  ]
}
```

## Relevante API-Endpunkte
- Routing lesen/schreiben: `GET|POST /api/routing/config`
- Variablen schreiben: `POST /api/variables/write`
- Variablen lesen: `POST /api/variables/read`
- Telemetrie: `GET /api/telemetry`
- Datenfluss/Monitoring: `GET /api/monitor/dataflow`, `GET /api/monitor/latency`

## Kamera-Gateway-Use-Case
Kameraevents und Stream-Status koennen wie andere Signale geroutet werden.
Damit ist "Gateway managt auch Kamera-Streams" technisch und dokumentarisch offizieller Bestandteil.

## Fehlerverhalten
- Rate-Limits und Auth gelten fuer Control-Endpunkte
- DLQ-Funktionen fuer Reprocess/Clear:
  - `GET /api/monitor/dlq`
  - `POST /api/monitor/dlq/reprocess`
  - `POST /api/monitor/dlq/clear`
