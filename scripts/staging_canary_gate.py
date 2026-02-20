#!/usr/bin/env python3
"""
Staging canary gate for core flows.

Produces a machine-readable go/no-go report and exits non-zero on failure.
"""

import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.gateway.web_manager import WebManager


class _DummyModuleManager:
    def __init__(self, modules=None):
        self._modules = modules or {}

    def get_module(self, name):
        return self._modules.get(name)


class _DummyGateway:
    def __init__(self):
        self.writes = []
        self._telemetry = {"SYSTEM.HEALTH": 1}

    def get_system_status(self):
        return {
            "status": "connected",
            "plc": {"connected": True},
            "capabilities": {"mode": "staging-canary"},
            "blob_stats": {"count": 0},
            "telemetry_count": len(self._telemetry),
            "uptime": 1.0,
        }

    def write_variable(self, variable, value, plc_id):
        self.writes.append((plc_id, variable, value))
        return True

    def update_telemetry(self, key, value):
        self._telemetry[key] = value

    def set_correlation_id(self, correlation_id):
        return None

    def clear_correlation_id(self):
        return None


class _DummyVarManager:
    pass


def _run_checks():
    os.environ["SMARTHOME_ADMIN_API_KEY"] = os.getenv("SMARTHOME_ADMIN_API_KEY", "staging-secret")
    os.environ["SMARTHOME_ALLOW_LOOPBACK_WITHOUT_KEY"] = "false"
    os.environ["SMARTHOME_CONTROL_RATE_LIMIT_MAX_REQUESTS"] = "500"

    wm = WebManager()
    gateway = _DummyGateway()
    wm.data_gateway = gateway
    wm.variable_manager = _DummyVarManager()
    wm.app_context = SimpleNamespace(module_manager=_DummyModuleManager({"stream_manager": None}))
    wm._setup_flask()
    client = wm.app.test_client()

    checks = []

    def add(name, passed, details=""):
        checks.append({"name": name, "passed": bool(passed), "details": str(details or "")})

    res = client.get("/api/system/status")
    add("system_status_available", res.status_code == 200, f"status={res.status_code}")

    res = client.get("/api/monitor/slo")
    add("monitor_slo_available", res.status_code == 200, f"status={res.status_code}")

    res = client.post(
        "/api/variables/write",
        json={"plc_id": "plc_001", "variable": "MAIN.bTest", "value": True},
        environ_overrides={"REMOTE_ADDR": "10.0.0.55"},
    )
    add("control_rejects_unauthorized", res.status_code == 401, f"status={res.status_code}")

    res = client.post(
        "/api/variables/write",
        json={"plc_id": "plc_001", "variable": "MAIN.bTest", "value": True},
        headers={"X-API-Key": os.environ["SMARTHOME_ADMIN_API_KEY"]},
        environ_overrides={"REMOTE_ADDR": "10.0.0.55"},
    )
    add("control_accepts_authorized", res.status_code == 200, f"status={res.status_code}")

    res = client.get(
        "/api/admin/service/info",
        headers={"X-API-Key": os.environ["SMARTHOME_ADMIN_API_KEY"]},
        environ_overrides={"REMOTE_ADDR": "10.0.0.55"},
    )
    add("admin_info_with_key", res.status_code == 200, f"status={res.status_code}")

    return checks


def main():
    started = time.time()
    checks = _run_checks()
    failed = [c for c in checks if not c["passed"]]
    passed = len(failed) == 0
    report = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - started, 3),
        "gate": "staging_canary",
        "go_no_go": "GO" if passed else "NO_GO",
        "total_checks": len(checks),
        "failed_checks": len(failed),
        "checks": checks,
    }

    report_path = ROOT / "artifacts" / "staging_gate_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
