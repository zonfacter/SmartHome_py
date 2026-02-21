# 02 TwinCAT Setup

Verbindlicher Ablauf fuer ADS/TwinCAT (TC2/TC3).

## Setup in der Web-UI
Pfad: `Setup -> PLC-Konfiguration`

- Runtime waehlen:
  - `TC2` -> Standard-Port `801`
  - `TC3` -> Standard-Port `851`
- `AMS Net ID` und optional `IP-Adresse` setzen
- `Verbinden`

## ADS-Routen
Pfad: `Setup -> ADS TwinCAT Routen`

- `Status` pruefen
- Route anlegen (`/api/plc/ads/route/add`)
- Route testen (`/api/plc/ads/route/test`)

## Minimale API-Flows
### Verbindung
`POST /api/plc/connect`
```json
{
  "ams_id": "192.168.2.162.1.1",
  "runtime_type": "TC3"
}
```

### Trennen
`POST /api/plc/disconnect`

### Symbol-Livewerte
`POST /api/plc/symbols/live`

## Troubleshooting
- Route nicht erreichbar: `GET /api/plc/ads/route/status`
- Runtime falsch: Port gegen TC2/TC3 abgleichen
- PLC-Schreibtest: `POST /api/variables/write`
