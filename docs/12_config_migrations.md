# 12 Config Schema and Migration Policy (verbindlich)

Dieses Dokument beschreibt die Versionsführung für lokale Konfigurationen.

## Ziel
- sichere Weiterentwicklung von Config-Dateien
- kontrollierte Migration älterer Installationen
- klare Validierung vor Nutzung

## Aktuelles Schema
- Datei: `twincat_config.json`
- Feld: `schema_version`
- Aktuelle Version: `2`

## Migrationspfad
- Legacy ohne `schema_version` wird als Schema `1` behandelt.
- Migration `1 -> 2` ergänzt/normalisiert u. a.:
- `widgets` als Objekt
- `plc.runtime_type` (Default `TC3`)
- `schema_version=2`, `version=2.0`

## Validierung beim Laden
- Config muss JSON-Objekt sein.
- Pflichtstruktur wird validiert (`theme`, `custom_lights`, `widgets`, `plc`).
- Höhere unbekannte `schema_version` wird abgelehnt (Fail-Closed).

## Schreibregeln
- Beim Speichern wird immer `schema_version=2` geschrieben.
- Legacy-Config wird beim Laden migriert und wieder persistiert.

## Tests
- `test_config_migrations.py` deckt ab:
- Migration Alt -> Neu
- Rejection bei Future-Schema
- Default-Config mit Schema-Version
