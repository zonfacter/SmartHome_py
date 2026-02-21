# Staging Gate

Dieses Dokument beschreibt den reproduzierbaren Staging-Gate vor einem Produktiv-Release.

## Ziel

- Risiko vor Prod-Deploy reduzieren
- Kernflüsse unter stagingnahen Bedingungen prüfen
- Eindeutige Go/No-Go-Entscheidung erzeugen
- Übergabe in Blue-Green-Cutover vorbereiten (`docs/10_blue_green_atomic_deployment.md`)

## Workflow

- GitHub Actions Workflow: `.github/workflows/staging-gate.yml`
- Trigger:
  - `workflow_dispatch` (manuell)
  - Push auf Tag `v*`
- Stufen:
  1. `staging-smoke`
  2. `staging-canary-go-no-go`

## Staging-Konfiguration

- Vorlage: `ops/staging.env.example`
- Diese Datei bildet die sichere Staging-Basis (API-Key Pflicht, restriktive Origins, Circuit-Breaker-Defaults).

## Go/No-Go Kriterien

Die Canary-Stufe (`scripts/staging_canary_gate.py`) prüft:

- `system_status_available`
- `monitor_slo_available`
- `control_rejects_unauthorized`
- `control_accepts_authorized`
- `admin_info_with_key`

Wenn eine Prüfung fehlschlägt:

- Workflow schlägt fehl
- Ergebnis ist `NO_GO`

Wenn alle Prüfungen erfolgreich sind:

- Ergebnis ist `GO`

## Artefakt

Der Workflow publiziert:

- `artifacts/staging_gate_report.json`

Beispiel-Felder:

- `go_no_go`
- `failed_checks`
- `checks[]`
- `timestamp_utc`

## Lokaler Dry-Run

```bash
python3 scripts/staging_canary_gate.py
cat artifacts/staging_gate_report.json
```

## Hinweis

Der Staging-Gate ist bewusst hardware-unabhängig gehalten (keine echte PLC/Kamera erforderlich), damit die Freigabe reproduzierbar und stabil in CI läuft.
