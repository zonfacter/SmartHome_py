# 09 Module Boundaries and Ownership (verbindlich)

Dieses Dokument definiert technische Schnittgrenzen und Verantwortlichkeiten pro Modulbereich.

## Architekturgrenzen
- `modules/core`: plattformnahe Kernlogik (Config, Backup, Service, Security, Logging)
- `modules/gateway`: externe Schnittstellen (HTTP API, Socket, Gateway-Orchestrierung)
- `modules/plc`: TwinCAT/ADS Integration, Symbol-/Variablenzugriff
- `modules/integrations`: externe Systeme (z. B. Kamera/Ring)
- `modules/bluetooth`: BMS/Bluetooth-Parser und Protokolladapter
- `modules/ui`: UI-Backend-Logik (nicht Web-Frontend)
- `modules/plugins`: erweiterbare Funktionsmodule

## Ownership-Matrix
| Bereich | Primär-Owner | Sekundär-Owner | Review-Pflicht bei Änderungen |
|---|---|---|---|
| `modules/core` | Platform/Core Team | Security Owner | ja |
| `modules/gateway` | API/Gateway Team | Platform/Core Team | ja |
| `modules/plc` | PLC Integration Team | API/Gateway Team | ja |
| `modules/integrations` | Integrations Team | API/Gateway Team | ja |
| `modules/bluetooth` | Integrations Team | Platform/Core Team | ja |
| `modules/ui` | UI Team | API/Gateway Team | ja |
| `modules/plugins` | Feature Team | API/Gateway Team | bei API-Auswirkung |
| `docs/*` | Maintainer Team | jeweiliger Fach-Owner | ja |

## Schnittstellenregeln
- `core` kennt keine Frontend-spezifischen Details.
- `gateway` ist einzige öffentliche API-/Socket-Kante nach außen.
- `plc` wird nicht direkt vom Frontend konsumiert; Zugriff immer über `gateway`.
- `integrations` publizieren Ereignisse/Telemetrie über `gateway` statt eigener Outbound-APIs.
- Contract-Änderungen benötigen Doku-Update (`docs/05`, `docs/openapi.json`, `docs/08`).

## Change-Impact-Regeln
1. API/Socket-Vertragsänderung:
- Pflicht: `docs/05_api_reference.md`, `docs/openapi.json`, `docs/08_socket_events.md`, Contract-Tests.
2. Security-/Auth-Änderung:
- Pflicht: Security-Review + Regressionstests für Control-Endpunkte.
3. PLC-Routing/Config-Schema-Änderung:
- Pflicht: Migrationspfad + Backward-Compatibility-Check.
4. Stream-/Kamera-Pipeline-Änderung:
- Pflicht: Soak/Restart-Test und Incident-Playbook-Abgleich (`docs/07`).

## Review-Gates
- Jeder PR muss betroffene Module benennen (`Scope: core/gateway/plc/...`).
- Bei Cross-Module-PRs ist mindestens ein zusätzlicher Owner-Review aus betroffenem Bereich nötig.
- Architekturentscheidungen über Modulgrenzen werden als ADR festgehalten (`docs/ADR/README.md`).
