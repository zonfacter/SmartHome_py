# Security Incident: Historischer Sentry-DSN Leak

## Hintergrund

Im Projekt wurde historisch ein echter Sentry-DSN in früheren Commits/Dokumenten veröffentlicht.

## Remediation-Status

- Aktive Dateien bereinigt (keine echten DSNs in `.env.example`/Doku).
- CI-Secret-Scanning aktiv (`gitleaks`).
- Zusätzlicher Repo-Test aktiv: `test_secret_hygiene.py` (blockiert real aussehende Sentry-DSNs).
- Branch-Protection verlangt `gitleaks` als Required Check.

## Sofortmaßnahmen (betrieblich, außerhalb des Repos)

1. DSN im betroffenen Sentry-Projekt rotieren/revoken.
2. Unerwartete Event-Last/Traffic im betroffenen Zeitraum prüfen.
3. Falls nötig: Inbound Filters, Rate Limits, Quota Alerts im Sentry-Projekt schärfen.

## Präventionsregeln

- Keine echten Secrets in:
  - `.env.example`
  - `docs/*.md`
  - Tests/Skripten
- Reale Secrets nur lokal in `.env` oder über Secret-Store/CI-Secrets.
- Jede Änderung mit Security-Bezug muss `gitleaks` + `test_secret_hygiene.py` grün halten.

## Hinweis zur Historie

Eine Git-History-Rewrite-Bereinigung ist optional und nur nötig, wenn Compliance dies verlangt.
Standardstrategie bleibt: Rotation + Prävention + Monitoring.
