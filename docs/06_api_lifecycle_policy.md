# 06 API Lifecycle Policy (verbindlich)

Dieses Dokument definiert das verbindliche Kompatibilitätsmodell für öffentliche Gateway-APIs.

## Ziele
- Integrationen bleiben über Minor/Patch-Releases stabil.
- Breaking Changes sind planbar und haben klare Migrationspfade.
- Deprecated Endpunkte sind zur Laufzeit und in der Doku eindeutig markiert.

## Versionsstrategie
- Aktueller API-Major: `v1`
- Aktueller stabiler Namespace: `/api/*` (semantisch `v1`)
- Neue Breaking Changes werden nur als neuer Major eingeführt:
- Beispiel: `/api/v2/*`
- `v1` bleibt während der Übergangsphase weiterhin verfügbar.

## Deprecation-Policy
- Mindestlaufzeit zwischen Deprecation und Removal: `90` Tage
- Jeder deprecated Endpunkt braucht:
- Sunset-Datum (UTC, ISO 8601)
- dokumentierten Replacement-Pfad (wenn verfügbar)
- Begründung/Migrationshinweis
- Runtime-Signal für deprecated Endpunkte:
- `Deprecation: true`
- `Sunset: <RFC1123-Datum>`
- optional `X-API-Replacement`, `X-API-Deprecation-Reason`

## Breaking-Change-Prozess
1. Änderung als Issue + ADR dokumentieren (Scope, Risiko, Migration).
2. Neue Major-Route bereitstellen (`/api/vN/...`) und Contract-Tests ergänzen.
3. Alte Route als deprecated markieren (Header + Doku + Changelog).
4. Nach Ablauf des Sunset-Fensters alte Route entfernen.
5. Entfernen als Breaking Change im Release klar kennzeichnen.

## Runtime-Verträge
- Alle `/api/*`-Responses liefern:
- `X-API-Version`
- `X-API-Major-Version`
- `X-API-Compatibility-Model`
- `X-API-Lifecycle-Policy`
- Policy-Discovery-Endpunkt:
- `GET /api/system/versioning`

## Konfiguration
- Deprecated Endpunkte können über Umgebungsvariable gesetzt werden:
- `SMARTHOME_API_DEPRECATED_ENDPOINTS`
- Format:

```json
{
  "/api/example/legacy": {
    "sunset": "2026-12-31T00:00:00Z",
    "replacement": "/api/v2/example",
    "reason": "v2 uses normalized payload schema"
  }
}
```
