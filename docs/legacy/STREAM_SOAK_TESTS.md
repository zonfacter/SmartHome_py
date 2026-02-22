# Stream/Ring Lasttest

Dieses Repo enthält ein Lasttest-Skript für Langzeitbetrieb:
- `scripts/stream_soak_test.py`

Ziele:
- reproduzierbare 6h/12h Soak-Szenarien
- gleichzeitige Clients pro Kamera
- CPU/RAM Trend- und Fehlerquote-Auswertung

## Voraussetzungen

- laufender Web-Server (`start_web_hmi.py`)
- konfigurierte Kameras in `config/cameras.json`
- optional API-Key (`SMARTHOME_ADMIN_API_KEY`), falls Loopback ohne Key deaktiviert ist

## Beispiele

Quick-Check (15 Minuten):

```bash
python3 scripts/stream_soak_test.py --preset quick --clients-per-camera 2
```

6h Soak:

```bash
python3 scripts/stream_soak_test.py --preset 6h --clients-per-camera 3
```

12h Soak (nur Ring-Kameras, expliziter Key):

```bash
python3 scripts/stream_soak_test.py \
  --preset 12h \
  --include-ring \
  --api-key "<ADMIN_API_KEY>" \
  --clients-per-camera 4
```

Nur bestimmte Kameras:

```bash
python3 scripts/stream_soak_test.py \
  --camera-ids cam01,ring_frontdoor \
  --duration-seconds 3600 \
  --clients-per-camera 3
```

## Ergebnisdatei

Standard-Ausgabe:
- `config/soak_reports/stream_soak_<timestamp>.json`

Inhalt:
- pro Kamera: Request-Fehlerquote, Stutter-Events, Latenz (p50/p95/max)
- global: CPU/RAM Trend (avg/max) aus `/api/monitor/dataflow`

