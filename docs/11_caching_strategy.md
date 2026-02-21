# 11 Caching Strategy for Read Endpoints (verbindlich)

Dieses Dokument beschreibt die Read-Cache-Strategie für häufig genutzte API-Endpunkte.

## Ziele
- Antwortzeiten stabilisieren
- CPU-Last bei Polling-Endpunkten senken
- Datenkorrektheit durch kurze TTL und Invalidation erhalten

## Hot Endpoints
- `GET /api/system/status`
- `GET /api/telemetry`
- `GET /api/monitor/slo`
- `GET /api/monitor/streams`

## TTL-Regeln
- `system/status`: Standard `1.0s`
- `telemetry`: Standard `0.5s`
- `monitor/slo`: Standard `1.0s`
- `monitor/streams`: Standard `1.0s`

Konfiguration über ENV:
- `SMARTHOME_READ_CACHE_TTL_SECONDS`
- `SMARTHOME_READ_CACHE_TTL_SYSTEM_STATUS`
- `SMARTHOME_READ_CACHE_TTL_TELEMETRY`
- `SMARTHOME_READ_CACHE_TTL_MONITOR_SLO`
- `SMARTHOME_READ_CACHE_TTL_MONITOR_STREAMS`
- `SMARTHOME_READ_CACHE_MAX_ENTRIES` (Default `256`)

## Invalidation-Regel
- Jeder API-Request mit Methode `POST|PUT|PATCH|DELETE` invalidiert den Read-Cache vollständig.
- Dadurch sind Folge-Reads nach schreibenden Operationen konsistent.

## Beobachtbarkeit
- Response-Header `X-Read-Cache: HIT|MISS` auf gecachten Endpunkten.
- Contract-Test sichert Verhalten ab (`test_api_contracts.py`).

## Messung Vor/Nach
Empfohlene Lastmessung (lokal/staging):
```bash
# warm-up
for i in $(seq 1 50); do curl -s http://127.0.0.1:5000/api/system/status >/dev/null; done

# einfacher Latenzvergleich
for i in $(seq 1 200); do curl -s -o /dev/null -w "%{time_total}\n" http://127.0.0.1:5000/api/system/status; done
```

Erwartung:
- niedrigere Median-/p95-Latenz bei Polling-Last
- geringere CPU-Spitzen ohne Funktionsverlust
