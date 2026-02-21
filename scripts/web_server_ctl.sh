#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  echo "Kein Python-Interpreter in venv/.venv gefunden" >&2
  exit 1
fi
APP_CMD=("start_web_hmi.py" "--host" "0.0.0.0" "--port" "5000")
PID_FILE="/tmp/smarthome-web.pid"
LOG_FILE="/tmp/smarthome-web.log"
HEALTH_URL="http://127.0.0.1:5000/api/system/status"
SERVER_PATTERN="(^|[[:space:]])${PYTHON_BIN}([[:space:]].*)?[[:space:]](/opt/Smarthome-Web/)?start_web_hmi\\.py --host 0\\.0\\.0\\.0 --port 5000([[:space:]]|$)"

find_server_pid() {
  pgrep -u "$(id -u)" -f "$SERVER_PATTERN" | head -n1 || true
}

get_pid() {
  if [[ -f "$PID_FILE" ]]; then
    cat "$PID_FILE" 2>/dev/null || true
    return
  fi
  find_server_pid
}

is_running() {
  local pid
  pid="$(get_pid)"
  [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null
}

wait_for_health() {
  local tries=30
  for _ in $(seq 1 "$tries"); do
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_server() {
  if is_running; then
    echo "Server läuft bereits (PID $(get_pid))"
    return 0
  fi

  cd "$ROOT_DIR"
  echo "Starte Server..."
  : > "$LOG_FILE"
  PYTHONUNBUFFERED=1 nohup "$PYTHON_BIN" "${APP_CMD[@]}" >>"$LOG_FILE" 2>&1 &
  local pid=$!
  echo "$pid" > "$PID_FILE"

  if wait_for_health; then
    echo "Server läuft (PID $pid)"
    return 0
  fi

  echo "Server-Start fehlgeschlagen. Letzte Log-Zeilen:"
  tail -n 80 "$LOG_FILE" || true
  return 1
}

stop_server() {
  if ! is_running; then
    echo "Server läuft nicht"
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid="$(get_pid)"
  echo "Stoppe Server (PID $pid)..."
  kill "$pid" 2>/dev/null || true

  for _ in $(seq 1 15); do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "Server gestoppt"
      return 0
    fi
    sleep 1
  done

  echo "Force-Kill Server (PID $pid)..."
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "Server gestoppt (force)"
}

status_server() {
  if is_running; then
    echo "Server läuft (PID $(get_pid))"
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
      echo "Healthcheck: OK"
    else
      echo "Healthcheck: FEHLER"
      return 1
    fi
  else
    echo "Server läuft nicht"
    return 1
  fi
}

case "${1:-}" in
  start) start_server ;;
  stop) stop_server ;;
  restart) stop_server; start_server ;;
  status) status_server ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 2
    ;;
esac
