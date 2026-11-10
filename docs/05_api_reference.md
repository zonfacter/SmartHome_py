# 05 API Reference (verbindlich)

Nur hier gelistete Endpunkte gelten als dokumentierter API-Stand.

## Versionierung und Deprecation
- Aktueller stabiler API-Major: `v1`
- Aktueller Namespace: `/api/*` (entspricht `v1`)
- Breaking Changes nur über neuen Major-Namespace (z. B. `/api/v2/*`)
- Deprecation-Fenster vor Entfernen: mindestens `90` Tage
- Laufende Policy und Sunset-Regeln: `docs/06_api_lifecycle_policy.md`
- OpenAPI-Vertrag: `docs/openapi.json`
- Socket/Event-Verträge: `docs/08_socket_events.md`
- Runtime-Signale:
- `X-API-Version`, `X-API-Major-Version`, `X-API-Compatibility-Model` auf allen `/api/*`-Responses
- Für deprecated Endpunkte zusätzlich: `Deprecation`, `Sunset`, optional `X-API-Replacement`

## Fehlercode-Baseline
- `400`: Payload ungültig oder Pflichtfelder fehlen
- `401`: Authentifizierung für geschützte Control-API fehlt/ungültig
- `403`: Origin-/Autorisierungsregeln verletzt
- `404`: Ressource/Route nicht gefunden
- `429`: Rate-Limit auf kritischen Endpunkten überschritten
- `500`: Interner Fehler

## System
- `GET /api/system/status`
- `GET /api/system/dependencies`
- `GET /api/system/versioning`
- `GET /api/system/feature-flags`
- `GET /api/telemetry`

## Heizung / Eurocontrol
- `GET /api/heating/state`
- `GET /api/heating/history`
- `GET /api/heating/statistics`
- `GET /api/heating/pumps`
- `GET /api/heating/observer`
- `GET /api/heating/observer/history`
- `GET /api/heating/observer/dhw-history`
- `GET /api/heating/gas-readings`
- `POST /api/heating/gas-readings`
- `POST /api/heating/schedule/preview`
- `POST /api/heating/schedule/apply`

`state` liefert den gemeinsamen, nur lesenden LPB-Zwischenspeicher für EG/M,
OG/K und Anlage sowie ioBroker-/Tado-Status. Kein Browser-Refresh erzwingt
zusätzliche Busabfragen. `history?hours=1|6|24` liefert höchstens 360 lokal
gespeicherte Messpunkte. Ungültige Messwerte bleiben `null`; Qualität und
Messzeitpunkt werden separat ausgegeben. `schedule_control.enabled` zeigt, ob
gezielte Zeitprogramm-Übernahmen aktiviert sind; `read_only` ist dann `false`.
Andere Parameter bleiben ausschließlich lesbar. Dazu gehören Diagnosecodes,
Regleruhren, Wettergrößen, Kessel-/Warmwasserparameter und LPB-Rohblöcke.
`statistics?hours=1|6|24` wertet den gespeicherten Startzähler und K4/K5 gemeinsam
aus. Es liefert beobachtete Starts, Relaisminuten, Raten, Datenabdeckung und
Zeitabschnitte; Lücken ohne gültige gemeinsame Daten bleiben `null`. Zählerüberlauf
an der 16-Bit-Grenze und erkennbare Rücksetzungen werden getrennt behandelt.
Die Rate bezieht sich auf beobachtete Zeit, nicht ungeprüft auf das ganze Fenster.
Es ist eine Relais-/Zählerstatistik, keine Flammen- oder Energiemessung.

`pumps?hours=1|6|24` liefert die Pumpendiagnose je Heizkreis sowie maximal 40
lokale Änderungsereignisse pro Kreis. Die API liest nur den gemeinsamen Cache
und SQLite. Feldwerte und Attributbits sind getrennt; `effective:null` und
`cause_status:"unresolved"` verhindern eine ungeprüfte Ursachenzuweisung.
Die aktuelle Diagnose steht außerdem unter `state.floors.<eg|og>.pump_diagnosis`.
Der Mitschnitt beginnt mit dieser Erweiterung und wird sieben Tage aufbewahrt.

`observer?hours=1|6|24` liefert den ausdrücklich nicht steuernden Lernstand für
EG, OG und Warmwasser, Aufzeichnungsabdeckung, Raumkennungen und eine unkalibrierte
Nennleistungs-/Gasäquivalentrechnung. `mode:"observe"` und `can_control:false`
sind fest. `observer/history?hours=1|6|24` liefert höchstens 360 Beobachtungen mit
Tado-Ist-/Sollwerten, Feuchte, Heizbedarf, Quellenzeitpunkten und Datenqualität.
Ab Beobachtungsschema 2 enthält jeder Raum `window` mit Zustand, Qualität,
Quelle und Trainingsfreigabe. EG-/OG-Modelle liefern `window_policy` sowie je
Raum `window_filter` mit Ausschlusszahlen. Nur belastbar geschlossene Kontakte
geben Raum-Lernfenster frei; Tado-Timeouts bestätigen keine Schließung. Alte
Raumdaten bleiben im Verlauf und werden ohne Fensterbeleg nicht neu trainiert.
`observer/dhw-history?days=1|7|30|90` liefert den gemessenen Warmwasserverlauf
in maximal 720 Abschnitten mit Mittelwert, Minimum, Maximum und Datenlücken.
Die Routen lesen ausschließlich die lokale Datenbank; es gibt keine POST-Route.

`GET /api/heating/gas-readings` zeigt dauerhaft gespeicherte kumulative Gasstände
(neueste 100), die letzte reale Verbrauchsdifferenz und eine getrennte, unkalibrierte
Relaisreferenz mit Datenabdeckung für denselben Zeitraum. `POST` speichert ausschließlich
einen lokalen Stützwert: JSON `{measured_at:"2024-05-05T12:00",volume_m3:"1234,567"}`,
Header `X-Heating-Meter: 1`, gleichbleibender Origin, maximal 2 KB. Datum ohne Offset
gilt als Europe/Berlin; mehrdeutige/nicht existente Ortszeiten werden abgelehnt.
Stände haben höchstens drei Nachkommastellen und müssen zu beiden zeitlichen Nachbarn
passen. Gleicher Zeitpunkt/Stand ist idempotent, widersprüchliche Werte ergeben 409.
Es gibt keine Interpolation, automatische Kalibrierung oder Heizungs-Stellbefehle.

`preview` erhält `{area:"eg"|"og", base:[7 Tagesprogramme], days:[7 Tagesprogramme]}`.
Ein Tagesprogramm ist eine Liste von maximal drei Objekten mit `start`/`end` im
Format HH:MM. Die Basis wird frisch mit dem Regler verglichen. Die Antwort enthält
einen an den Client gebundenen, drei Minuten gültigen Token und die Tagesänderungen.
`apply` erhält ausschließlich `{token:"..."}` und schreibt nach erneuter Prüfung
nur die geänderten Tage. Erfolg enthält `verified_days`, `changed_days` und eine
Transaktions-ID. Wiederholte identische Bestätigungen schreiben nicht erneut.
Beide POSTs verwenden die bestehende Control-Authentifizierung, JSON und den
Header `X-Heating-Schedule: 1`. `409` bedeutet Konflikt/abgelaufene Vorschau,
`502` einen Übertragungsfehler mit `restored` als Wiederherstellungsergebnis,
`503` deaktivierten/unerreichbaren Regler oder ausstehende Wiederherstellung.
Details: `docs/16_heating_dashboard.md`.

## PLC / TwinCAT
- `GET /api/plc/config`
- `POST /api/plc/config`
- `POST /api/plc/connect`
- `POST /api/plc/disconnect`
- `GET /api/plc/ads/route/status`
- `POST /api/plc/ads/route/add`
- `POST /api/plc/ads/route/test`
- `GET /api/plc/symbols`
- `POST /api/plc/symbols/upload`
- `POST /api/plc/symbols/live`

## Variablen
- `GET /api/variables/search`
- `POST /api/variables/write`
- `POST /api/variables/read`
- `GET /api/variables/statistics`

## Kamera / Ring
- `GET /api/cameras`
- `POST /api/cameras`
- `PUT /api/cameras/<cam_id>`
- `DELETE /api/cameras/<cam_id>`
- `POST /api/cameras/scan`
- `POST /api/cameras/diagnose`
- `POST /api/cameras/alert`
- `GET /api/cameras/<cam_id>/snapshot`
- `POST /api/cameras/<cam_id>/start`
- `POST /api/cameras/<cam_id>/stop`
- `GET /api/ring/status`
- `POST /api/ring/auth`
- `GET /api/ring/cameras`
- `POST /api/ring/cameras/import`

## Routing / Trigger
- `GET /api/routing/config`
- `POST /api/routing/config`
- `GET /api/camera-triggers`
- `POST /api/camera-triggers`
- `GET /api/camera-triggers/export`
- `POST /api/camera-triggers/import`

## Widgets / UI Layout
- `GET /api/widgets`
- `POST /api/widgets`
- `PUT /api/widgets/<widget_id>`
- `DELETE /api/widgets/<widget_id>`
- `GET /api/pages`
- `POST /api/pages`
- `PUT /api/pages/<page_id>`
- `DELETE /api/pages/<page_id>`
- `POST /api/pages/reorder`
- `GET /api/ui-settings`
- `PUT /api/ui-settings`

## Admin
- `GET /api/admin/plcs`
- `POST /api/admin/plcs`
- `GET /api/admin/logs`
- `GET /api/admin/logs/verify`
- `GET /api/admin/logs/export`
- `POST /api/admin/logs/clear`
- `GET /api/admin/service/info`
- `POST /api/admin/service/restart`
- `POST /api/admin/service/restart-daemon`
- `POST /api/admin/feature-flags`

## Monitoring
- `GET /api/monitor/dataflow`
- `GET /api/monitor/latency`
- `GET /api/monitor/slo`
- `GET /api/monitor/streams`
- `GET /api/monitor/dlq`
- `POST /api/monitor/dlq/reprocess`
- `POST /api/monitor/dlq/clear`
