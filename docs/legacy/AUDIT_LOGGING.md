# Audit Logging

Dieses Projekt nutzt eine manipulationserschwerende Audit-Log-Kette in `config/system_logs.db`.

## Eigenschaften

- Log-Einträge enthalten `prev_hash` und `entry_hash` (SHA-256 Hash-Kette)
- Kritische Admin-Aktionen werden als `level=AUDIT` gespeichert
- Retention wird nach Alter und Max-Anzahl durchgesetzt

## Relevante Endpunkte

- `GET /api/admin/logs?limit=100`
- `GET /api/admin/logs/verify`
- `GET /api/admin/logs/export?format=json|csv&limit=1000`
- `POST /api/admin/logs/clear`

## Retention

Konfigurierbar via `.env`:

- `SMARTHOME_AUDIT_RETENTION_DAYS` (default `90`)
- `SMARTHOME_AUDIT_RETENTION_MAX_ENTRIES` (default `20000`)

`POST /api/admin/logs/clear` akzeptiert optional:

- `keep_count`
- `max_age_days`

## Kettenprüfung

`GET /api/admin/logs/verify` liefert:

- `ok`: `true/false`
- `checked`: Anzahl geprüfter Einträge
- `broken_at_id`: betroffene Zeile bei Kettenbruch
