# ADR 0001: API Lifecycle Policy und Contract-First Dokumentation

- Status: accepted
- Date: 2026-02-21
- Deciders: Maintainer Team
- Technical Story: #24, #14

## Context

Externe Integratoren brauchen stabile HTTP- und Socket-Verträge. Bisher waren Endpunkte dokumentiert, aber ohne maschinenlesbare OpenAPI-Spezifikation und ohne standardisierte Lifecycle-Regeln.

## Decision Drivers

- Integrationssicherheit für Drittclients
- Nachvollziehbarer Deprecation-/Breaking-Change-Prozess
- CI-gesicherte Drift-Erkennung zwischen Doku und Umsetzung

## Considered Options

- Option A: Nur prose-Dokumentation
- Option B: Contract-first mit OpenAPI + Socket-Event-Schema + Drift-Checks

## Decision

Wir verwenden Option B.

Konkrete Artefakte:
- `docs/openapi.json`
- `docs/08_socket_events.md`
- `docs/06_api_lifecycle_policy.md`
- CI-Checks: `scripts/check_api_doc_drift.py`, `scripts/check_openapi_contract_drift.py`

## Consequences

- Positiv: Integrationsverträge sind maschinenlesbar und CI-validiert.
- Negativ: Zusätzlicher Pflegeaufwand bei API-Änderungen.
- Risiko/Mitigation: Vertragsdrift wird über CI-Checks früh erkannt.

## References

- `docs/05_api_reference.md`
- `docs/06_api_lifecycle_policy.md`
- `docs/08_socket_events.md`
- `docs/openapi.json`
