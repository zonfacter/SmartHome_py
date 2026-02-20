"""
Contract tests for frontend <-> gateway API behavior.

Focus:
- response schema checks
- error code contracts
- socket event payload validation
"""

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.core.database_logger import DatabaseLogger
from modules.gateway.web_manager import WebManager


class _DummyModuleManager:
    def __init__(self, modules=None):
        self._modules = modules or {}

    def get_module(self, name):
        return self._modules.get(name)


class _DummyGateway:
    def __init__(self):
        self._telemetry = {"SYSTEM.HEALTH": 1}
        self._writes = []
        self._correlation_id = None

    def get_system_status(self):
        return {
            "status": "connected",
            "plc": {"connected": True},
            "capabilities": {"mode": "contract-test"},
            "blob_stats": {"count": 0},
            "telemetry_count": len(self._telemetry),
            "uptime": 1.23,
        }

    def get_all_telemetry(self):
        return dict(self._telemetry)

    def write_variable(self, variable, value, plc_id):
        self._writes.append((plc_id, variable, value))
        return True

    def update_telemetry(self, key, value):
        self._telemetry[key] = value

    def set_correlation_id(self, correlation_id):
        self._correlation_id = correlation_id

    def clear_correlation_id(self):
        self._correlation_id = None


class _DummySymbolInfo:
    symbol_type = "BOOL"


class _DummyVariableManager:
    def __init__(self):
        self._subs = {}

    def subscribe_widget(self, widget_id, variable, plc_id):
        self._subs[widget_id] = (variable, plc_id)

    def unsubscribe_widget(self, widget_id):
        self._subs.pop(widget_id, None)

    def get_cached_value(self, variable, plc_id):
        return True, 1700000000.0

    def get_symbol_info(self, variable, plc_id):
        return _DummySymbolInfo()


@pytest.fixture()
def web_fixture(monkeypatch):
    monkeypatch.setenv("SMARTHOME_ADMIN_API_KEY", "")
    monkeypatch.setenv("SMARTHOME_ALLOW_LOOPBACK_WITHOUT_KEY", "true")
    monkeypatch.setenv("SMARTHOME_CONTROL_RATE_LIMIT_MAX_REQUESTS", "500")

    root = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(root, "config", "system_logs.db")
    DatabaseLogger.setup(db_path=db_path)
    DatabaseLogger.audit_event(db_path, "contract_test_seed", "pytest", {"suite": "api_contracts"})

    wm = WebManager()
    wm.data_gateway = _DummyGateway()
    wm.variable_manager = _DummyVariableManager()
    wm.app_context = SimpleNamespace(module_manager=_DummyModuleManager({"stream_manager": None}))
    wm._setup_flask()
    wm._setup_socketio()
    client = wm.app.test_client()
    return wm, client


def test_contract_system_status_schema(web_fixture):
    _, client = web_fixture
    res = client.get("/api/system/status")
    assert res.status_code == 200
    payload = res.get_json()
    assert isinstance(payload, dict)
    for key in ("status", "plc", "capabilities", "blob_stats", "telemetry_count", "uptime"):
        assert key in payload
    assert isinstance(payload["plc"], dict)
    assert isinstance(payload["plc"].get("connected"), bool)


def test_contract_monitor_slo_schema(web_fixture):
    _, client = web_fixture
    res = client.get("/api/monitor/slo")
    assert res.status_code == 200
    payload = res.get_json()
    assert isinstance(payload, dict)
    for key in ("timestamp", "timestamp_utc", "targets", "sli", "alerts", "status"):
        assert key in payload
    assert payload["status"] in ("ok", "degraded")
    assert isinstance(payload["targets"], dict)
    assert isinstance(payload["sli"], dict)
    assert "api" in payload["sli"]
    assert "streams" in payload["sli"]


def test_contract_error_code_for_missing_variable(web_fixture):
    _, client = web_fixture
    res = client.post("/api/variables/write", json={"plc_id": "plc_001", "value": True})
    assert res.status_code == 400
    payload = res.get_json()
    assert payload["status"] == "error"
    assert "Variable fehlt" in payload["message"]


def test_contract_admin_logs_verify_shape(web_fixture):
    _, client = web_fixture
    res = client.get("/api/admin/logs/verify")
    assert res.status_code == 200
    payload = res.get_json()
    assert isinstance(payload, dict)
    for key in ("ok", "checked", "broken_at_id"):
        assert key in payload
    assert isinstance(payload["ok"], bool)
    assert isinstance(payload["checked"], int)


def test_contract_idempotency_for_logs_clear(web_fixture):
    _, client = web_fixture
    headers = {"Idempotency-Key": "contract-clear-1"}
    body = {"keep_count": 200, "max_age_days": 90}

    first = client.post("/api/admin/logs/clear", json=body, headers=headers)
    assert first.status_code == 200
    assert first.headers.get("X-Idempotency-Replayed") == "false"
    first_payload = first.get_json()

    second = client.post("/api/admin/logs/clear", json=body, headers=headers)
    assert second.status_code == 200
    assert second.headers.get("X-Idempotency-Replayed") == "true"
    assert second.get_json() == first_payload


def test_contract_socket_payloads(web_fixture):
    wm, _ = web_fixture
    captured = []

    def _capture(event_name, payload):
        captured.append((event_name, payload))

    wm.running = True
    wm.socketio.emit = _capture

    wm.broadcast_telemetry("Light.Light_EG_WZ.bOn", True)
    wm.broadcast_event("camera_alert", {"cam_id": "cam01", "source": "contract-test"})

    assert len(captured) == 2

    telemetry_event, telemetry_payload = captured[0]
    assert telemetry_event == "telemetry_update"
    for key in ("key", "value", "timestamp"):
        assert key in telemetry_payload

    custom_event, custom_payload = captured[1]
    assert custom_event == "camera_alert"
    assert custom_payload["cam_id"] == "cam01"
    assert custom_payload["source"] == "contract-test"
