# 08 Socket/Event Contracts (verbindlich)

Dieses Dokument definiert die stabilen Socket.IO-Verträge für externe Clients.

## Verbindung
- Transport: Socket.IO
- Namespace: Default (`/`)
- Verbindungsaufbau: Standard Socket.IO Handshake

## Server -> Client Events

### `initial_telemetry`
- Zeitpunkt: direkt nach `connect`
- Payload:
```json
{
  "ANY.KEY": "any value"
}
```

### `request_context`
- Zeitpunkt: direkt nach `connect`
- Payload:
```json
{
  "correlation_id": "ws-connect-<id>-<epoch_ms>"
}
```

### `telemetry_update`
- Zeitpunkt: bei Telemetrie-Änderungen
- Payload:
```json
{
  "key": "Light.Light_EG_WZ.bOn",
  "value": true,
  "timestamp": 1700000000.123,
  "timestamp_utc": "2026-02-21T16:00:00Z",
  "correlation_id": "..."
}
```

### `camera_alert`
- Zeitpunkt: Kamera-/Ring-Alarm
- Payload: Event-spezifisch, mit Standardfeldern:
```json
{
  "cam_id": "cam01",
  "source": "ring|rtsp|manual",
  "timestamp": 1700000000.123,
  "timestamp_utc": "2026-02-21T16:00:00Z",
  "correlation_id": "..."
}
```

### `system_event`
- Zeitpunkt: systemische Status-/Betriebsereignisse
- Payload: frei, jedoch immer mit `correlation_id`; bei `timestamp` wird `timestamp_utc` ergänzt.

### `variable_update`
- Zeitpunkt: nach erfolgreichem `subscribe_variable` (sofortiger Cache-Wert)
- Payload:
```json
{
  "widget_id": "widget_123",
  "variable": "Light.Light_EG_WZ.bOn",
  "value": true,
  "timestamp": 1700000000.123,
  "type": "BOOL",
  "plc_id": "plc_001"
}
```

### `subscribe_success`
```json
{
  "widget_id": "widget_123",
  "variable": "Light.Light_EG_WZ.bOn",
  "plc_id": "plc_001"
}
```

### `unsubscribe_success`
```json
{
  "widget_id": "widget_123"
}
```

### `error`
```json
{
  "message": "Fehlerbeschreibung"
}
```

## Client -> Server Events

### `subscribe_variable`
```json
{
  "widget_id": "widget_123",
  "variable": "Light.Light_EG_WZ.bOn",
  "plc_id": "plc_001"
}
```

### `unsubscribe_variable`
```json
{
  "widget_id": "widget_123"
}
```

## Stabilitätsregeln
- Neue Felder dürfen ergänzt werden (abwärtskompatibel).
- Entfernen/Umbenennen bestehender Felder gilt als Breaking Change.
- Breaking Socket-Änderungen folgen der API-Lifecycle-Policy (`docs/06_api_lifecycle_policy.md`).
