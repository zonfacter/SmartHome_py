# Backup & Restore

Automatische Backups und Restore für Konfiguration und Log-DB.

## Gesicherte Dateien

- `config/plc_connections.json`
- `config/plc_configs.json`
- `config/twincat_layout.json`
- `config/routing.json`
- `config/cameras.json`
- `config/camera_triggers.json`
- `config/alias_mappings.json`
- `config/system_logs.db`
- `config/automation_rules.db`

## API Endpunkte

- `GET /api/admin/backup/list?limit=50`
- `POST /api/admin/backup/create`
- `GET /api/admin/backup/verify?file=<name>.tar.gz`
- `POST /api/admin/backup/restore`
- `GET /api/admin/backup/download?file=<name>.tar.gz`

## Restore Payload

```json
{
  "file": "smarthome_backup_20260220_220000Z.tar.gz",
  "dry_run": false,
  "create_pre_restore_backup": true,
  "keep_count": 30
}
```

## Integritätsprüfung

Jedes Backup enthält `BACKUP_MANIFEST.json` mit SHA-256 Prüfsummen.
`/api/admin/backup/verify` prüft alle enthaltenen Dateien gegen das Manifest.

## Aufbewahrung

`SMARTHOME_BACKUP_KEEP_COUNT` (default `30`) steuert, wie viele Backup-Archive behalten werden.
