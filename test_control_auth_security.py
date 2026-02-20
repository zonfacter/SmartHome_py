import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.gateway.web_manager import WebManager


class _DummyModuleManager:
    def __init__(self, modules=None):
        self._modules = modules or {}

    def get_module(self, name):
        return self._modules.get(name)


class _DummyGateway:
    def __init__(self):
        self.writes = []

    def write_variable(self, variable, value, plc_id):
        self.writes.append((plc_id, variable, value))
        return True

    def set_correlation_id(self, correlation_id):
        return None

    def clear_correlation_id(self):
        return None


@pytest.fixture()
def security_fixture(monkeypatch):
    monkeypatch.setenv("SMARTHOME_ADMIN_API_KEY", "super-secret")
    monkeypatch.setenv("SMARTHOME_ALLOW_LOOPBACK_WITHOUT_KEY", "false")
    monkeypatch.setenv("SMARTHOME_CONTROL_RATE_LIMIT_MAX_REQUESTS", "500")

    wm = WebManager()
    wm.data_gateway = _DummyGateway()
    wm.variable_manager = object()
    wm.app_context = SimpleNamespace(module_manager=_DummyModuleManager({}))
    wm._setup_flask()

    return wm, wm.app.test_client()


def test_control_api_rejects_non_loopback_without_api_key(security_fixture):
    _, client = security_fixture
    res = client.post(
        "/api/variables/write",
        json={"plc_id": "plc_001", "variable": "Light.Test.bOn", "value": True},
        environ_overrides={"REMOTE_ADDR": "10.0.0.42"},
    )
    assert res.status_code == 401
    payload = res.get_json()
    assert payload["success"] is False
    assert payload["error"] == "unauthorized"


def test_control_api_rejects_loopback_without_api_key_when_disabled(security_fixture):
    _, client = security_fixture
    res = client.post(
        "/api/admin/service/restart",
        json={"delay": 2},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert res.status_code == 401
    payload = res.get_json()
    assert payload["success"] is False
    assert payload["error"] == "unauthorized"


def test_control_api_accepts_valid_api_key(security_fixture):
    wm, client = security_fixture
    res = client.post(
        "/api/variables/write",
        json={"plc_id": "plc_001", "variable": "Light.Test.bOn", "value": True},
        headers={"X-API-Key": "super-secret"},
        environ_overrides={"REMOTE_ADDR": "10.0.0.42"},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["status"] == "success"
    assert wm.data_gateway.writes == [("plc_001", "Light.Test.bOn", True)]
