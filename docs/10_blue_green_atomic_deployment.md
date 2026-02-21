# 10 Blue-Green / Atomic Deployment (verbindlich)

Dieses Dokument definiert das Standard-Deploy-Pattern für nahezu ausfallfreie Releases.

## Ziel
- Umschalten ohne spürbare Downtime
- Health-basiertes Cutover
- Schneller, deterministischer Rollback

## Deploy-Pattern
- `blue`: aktuell produktive Instanz
- `green`: neue Kandidaten-Instanz
- Traffic wird erst nach erfolgreichem Health-Check auf `green` umgeschaltet.
- Rollback bedeutet reines Zurückschalten auf `blue`.

## Voraussetzungen
- Reverse Proxy vor App (z. B. NGINX/Traefik/Caddy)
- Separater Upstream pro Farbe (`blue`, `green`)
- Health-Endpunkt: `GET /api/system/status`
- Staging-Gate muss erfolgreich sein (`docs/STAGING_GATE.md`)

## Health-basierter Umschaltpunkt
`green` gilt als "ready" wenn alle Bedingungen erfüllt sind:
1. HTTP 200 auf `/api/system/status`
2. API antwortet stabil für mindestens 30 Sekunden
3. Basistests gegen `green` erfolgreich (mind. system status + monitor slo)

Erst danach wird der Proxy-Upstream atomar umgeschaltet.

## Referenzablauf (Docker)
1. `green` deployen (parallel zu `blue`), anderer Service-Name/Port.
2. Health prüfen:
```bash
curl -fsS http://green-host:5000/api/system/status
curl -fsS http://green-host:5000/api/monitor/slo
```
3. Proxy-Konfiguration auf `green` wechseln.
4. Proxy reloaden (ohne Full-Restart).
5. Traffic + Fehlerquote 5-15 Minuten beobachten.
6. `blue` als warmen Fallback noch nicht sofort entfernen.

## Rollback-Prozedur
Rollback auslösen bei:
- Fehleranstieg (5xx/Timeouts)
- kritische Control-Endpunkte instabil
- funktionale Kernflüsse fehlschlagen

Schritte:
1. Proxy-Upstream sofort zurück auf `blue`.
2. Gesundheit von `blue` bestätigen.
3. Incident eröffnen und `green` isoliert analysieren.
4. Fehlerbehebung in neuem Build, dann erneutes Green-Deploy.

## Atomicity-Regeln
- Keine In-Place-Updates des aktiven Containers.
- Umschaltung nur über Proxy-Target/Service-Alias.
- Daten-/Schemaänderungen müssen rückwärtskompatibel sein.
- Irreversible Migrationsschritte erst nach stabiler Green-Phase.

## Minimal-Checklist (Go-Live)
1. Staging-Gate = GO
2. Green health = OK
3. Umschalten durchgeführt
4. Post-switch Monitoring = OK
5. Rollback-Plan verifiziert
