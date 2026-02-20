# Docker Least-Privilege Runtime

Diese Container-Definition läuft standardmäßig mit minimalen Rechten:

- Non-root User: `10001:10001`
- `read_only: true` für Root-Filesystem
- `cap_drop: [ALL]`
- `no-new-privileges:true`
- begrenzte PID-Anzahl (`pids_limit: 256`)
- explizite RW-Mounts nur für Runtime-State:
  - `./config -> /app/config`
  - `./plc_data -> /app/plc_data`
  - `./web/static/hls -> /app/web/static/hls`

## Start

```bash
docker compose up -d --build
```

## Hinweise

- `.env` wird zur Laufzeit eingebunden (`env_file: .env`), aber nicht ins Image kopiert.
- Für zusätzliche Hardware-/Device-Zugriffe (z. B. Bluetooth/Serial) sollten Rechte gezielt und minimal ergänzt werden, statt pauschal `privileged: true` zu verwenden.
