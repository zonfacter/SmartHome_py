# 13 Feature Flags Rollout/Rollback (verbindlich)

Dieses Dokument beschreibt den Einsatz von UI-Feature-Flags für riskante Änderungen.

## Ziel
- neue UI-Funktionen ohne Redeploy aktivieren/deaktivieren
- kontrollierter Rollout und schneller Rollback

## API
- Lesen: `GET /api/system/feature-flags`
- Aktualisieren: `POST /api/admin/feature-flags`

## Payload
```json
{
  "flags": {
    "ui.page.camera-wall": true,
    "ui.page.monitor": true,
    "ui.page.admin": true,
    "ui.ring.webrtc": true
  }
}
```

## Laufzeitverhalten
- Flags werden im Frontend zur Laufzeit geladen.
- Deaktivierte Seiten werden in der Navigation ausgeblendet.
- Ein Aufruf deaktivierter Seiten fällt auf Dashboard zurück.
- Ring WebRTC wird über `ui.ring.webrtc` hart abschaltbar.

## Rollout-Vorgehen
1. Feature default `false` lassen.
2. In Staging aktivieren und beobachten.
3. In Prod schrittweise aktivieren.
4. Bei Fehlern sofort per Flag zurück auf `false`.

## Rollback
- API-Update mit betroffenen Flags auf `false`.
- Kein Redeploy notwendig.
