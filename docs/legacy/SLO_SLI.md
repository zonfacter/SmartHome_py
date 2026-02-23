# SLO / SLI Definitionen

Diese Seite definiert die Betriebsqualität für API und Streams.

## Endpoint

- `GET /api/monitor/slo`

Liefert:

- aktuelle SLI-Werte
- konfigurierte SLO-Targets
- aktive Alert-Verletzungen

## SLI-Definitionen

1. API Availability Ratio  
   Formel: `non_5xx_responses / total_api_responses` im Zeitfenster

2. API p95 Latency (ms)  
   Formel: p95 der API-Responsezeit im Zeitfenster

3. Stream Health Ratio  
   Formel: `running_streams / active_streams`

## Standard-SLOs

- `api_availability_ratio >= 0.995`
- `api_p95_latency_ms <= 500`
- `stream_health_ratio >= 0.99`

## Konfiguration (`.env`)

- `SLO_WINDOW_SECONDS` (default `3600`)
- `SLO_API_AVAILABILITY` (default `0.995`)
- `SLO_API_P95_LATENCY_MS` (default `500`)
- `SLO_STREAM_HEALTH_RATIO` (default `0.99`)

## Alerting-Regeln

- `api_availability_below_target` => `critical`
- `api_latency_above_target` => `warning`
- `stream_health_below_target` => `critical`
