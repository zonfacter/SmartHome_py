# Web Setup Guide: Routing-Regeln und ADS TwinCAT Routen

Diese Anleitung beschreibt den produktiven Ablauf im Web-Setup:

- PLC Runtime-Konfiguration (TC2/TC3)
- ADS-Routenverwaltung (Linux/pyads)
- Routing-Regeln (`config/routing.json`) über die UI

## 1. PLC Runtime im Setup

Im Menü `Setup -> PLC-Konfiguration`:

- `Runtime` wählen:
  - `TC2` -> Standard-Port `801`
  - `TC3` -> Standard-Port `851`
- `AMS Net ID`, `AMS Port`, `IP-Adresse` setzen
- `Verbinden`

Hinweis:
- Der Port kann manuell überschrieben werden.
- Der Runtime-Wert wird als `plc_runtime_type` gespeichert.

## 2. ADS TwinCAT Routen über Web-UI

Im Menü `Setup -> ADS TwinCAT Routen`:

Felder:
- `Lokale AMS Net ID` (Linux-Host/VM)
- `Lokale IP`
- `PLC AMS Net ID`
- `PLC IP`
- `PLC User` / `PLC Passwort`
- `Route Name`

Buttons:
- `Status`: pyads-Verfügbarkeit + lokale AMS-Adresse prüfen
- `Route anlegen`: lokale Route + PLC-Route anlegen
- `Route testen`: ADS-Verbindung mit `pyads.Connection(..., ip)` prüfen

Wichtig:
- Auf Linux muss die PLC-IP beim Connect verwendet werden.
- TwinCAT 2 und TwinCAT 3 unterscheiden sich bei Runtime-Port (801/851), nicht per Fallback mischen.

## 3. Routing-Regeln über UI

Im Menü `Setup -> Routing-Regeln`:

- Regel auswählen oder `Neu`
- Felder:
  - `ID`
  - `Beschreibung`
  - `From Pattern`
  - `To Targets (CSV)`
  - `Aktiv`
- `Speichern` schreibt nach `config/routing.json`
- Nach Speichern wird die Routing-Engine live neu geladen

Format in `config/routing.json`:

```json
{
  "version": "1.0",
  "description": "Routing-Konfiguration",
  "routes": [
    {
      "id": "example_passthrough",
      "description": "Beispiel",
      "from": "*",
      "to": ["unified_data_space"],
      "enabled": true
    }
  ],
  "settings": {
    "max_pps_per_source": 500,
    "enable_spam_protection": true,
    "log_all_routes": false
  }
}
```

## 4. Relevante API-Endpunkte

### PLC Connect
- `POST /api/plc/connect`
- Payload:

```json
{
  "ams_id": "192.168.2.162.1.1",
  "ams_port": 801,
  "ip_address": "192.168.2.162",
  "runtime_type": "TC2"
}
```

### ADS Route Management
- `GET /api/plc/ads/route/status`
- `POST /api/plc/ads/route/add`
- `POST /api/plc/ads/route/test`

Beispiel `add`:

```json
{
  "local_ams_net_id": "192.168.2.123.1.1",
  "local_ip": "192.168.2.123",
  "plc_ams_net_id": "192.168.2.162.1.1",
  "plc_ip": "192.168.2.162",
  "username": "Administrator",
  "password": "******",
  "route_name": "SmartHomeWeb"
}
```

### Routing Config
- `GET /api/routing/config`
- `POST /api/routing/config`

Versionierung:
- `version` wird geprüft.
- Höhere Major-Versionen werden abgewiesen (Legacy-Schutz).

## 5. Betrieb nach Deploy

```bash
cd /opt/Smarthome-Web
git pull
sudo systemctl restart smarthome-web
curl -i http://127.0.0.1:5000/api/routing/config
```

Erwartung:
- HTTP 200
- `Content-Type: application/json`

