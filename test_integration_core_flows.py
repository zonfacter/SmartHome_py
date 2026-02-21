import json
import os
from types import SimpleNamespace

import pytest

from modules.gateway.web_manager import WebManager


class _DummyModuleManager:
    def __init__(self, modules=None):
        self._modules = modules or {}

    def get_module(self, name):
        return self._modules.get(name)


class _DummyPLC:
    def __init__(self):
        self.configure_calls = []
        self.connect_calls = 0
        self.disconnect_calls = 0

    def configure(self, ams_net_id, port):
        self.configure_calls.append((ams_net_id, port))

    def connect(self):
        self.connect_calls += 1
        return True

    def disconnect(self):
        self.disconnect_calls += 1


class _DummyConfigManager:
    def __init__(self):
        self.values = {}
        self.saved = 0

    def set_config_value(self, key, value):
        self.values[key] = value

    def save_config(self):
        self.saved += 1
        return True


class _DummyStreamManager:
    def __init__(self):
        self.has_ffmpeg = True
        self.start_calls = []
        self.stop_calls = []
        self.scheduled_stop_calls = []
        self.ring_start_calls = []

    def start_stream(self, cam_id, stream_url, resolution=None):
        self.start_calls.append((cam_id, stream_url, resolution))
        return True

    def stop_stream(self, cam_id):
        self.stop_calls.append(cam_id)
        return True

    def schedule_stop_stream(self, cam_id, delay_seconds=45.0, cleanup=True):
        self.scheduled_stop_calls.append((cam_id, delay_seconds, cleanup))
        return True

    def start_ring_stream(self, cam_id, device_id, refresh_token):
        self.ring_start_calls.append((cam_id, device_id, refresh_token))
        return True


class _DummyGateway:
    def __init__(self):
        self.writes = []
        self.telemetry = {}
        self.sync_count = 0
        self.routing_reload_count = 0
        self.correlation_id = None

    def write_variable(self, variable, value, plc_id):
        self.writes.append((plc_id, variable, value))
        return True

    def update_telemetry(self, key, value):
        self.telemetry[key] = value

    def set_correlation_id(self, correlation_id):
        self.correlation_id = correlation_id

    def clear_correlation_id(self):
        self.correlation_id = None

    def sync_widget_subscriptions(self):
        self.sync_count += 1

    def _load_routing_config(self):
        self.routing_reload_count += 1


@pytest.fixture()
def integration_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTHOME_ADMIN_API_KEY", "")
    monkeypatch.setenv("SMARTHOME_ALLOW_LOOPBACK_WITHOUT_KEY", "true")
    monkeypatch.setenv("SMARTHOME_CONTROL_RATE_LIMIT_MAX_REQUESTS", "500")
    monkeypatch.chdir(tmp_path)

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "cameras.json").write_text(
        json.dumps(
            {
                "cameras": {
                    "cam01": {
                        "url": "rtsp://127.0.0.1:554/live",
                        "type": "rtsp",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    plc = _DummyPLC()
    config_mgr = _DummyConfigManager()
    stream_mgr = _DummyStreamManager()
    gateway = _DummyGateway()

    module_manager = _DummyModuleManager(
        {
            "plc_communication": plc,
            "config_manager": config_mgr,
            "stream_manager": stream_mgr,
        }
    )

    wm = WebManager()
    wm.app_context = SimpleNamespace(module_manager=module_manager)
    wm.data_gateway = gateway
    wm.variable_manager = object()
    wm._setup_flask()

    return wm.app.test_client(), plc, config_mgr, stream_mgr, gateway


def test_integration_plc_connect_write_disconnect(integration_fixture):
    client, plc, config_mgr, _, gateway = integration_fixture

    connect = client.post(
        "/api/plc/connect",
        json={"ams_id": "1.2.3.4.5.6", "runtime_type": "TC3"},
    )
    assert connect.status_code == 200
    connect_payload = connect.get_json()
    assert connect_payload["success"] is True
    assert connect_payload["ams_port"] == 851
    assert plc.configure_calls == [("1.2.3.4.5.6", 851)]
    assert plc.connect_calls == 1
    assert gateway.sync_count == 1
    assert config_mgr.values["plc_ams_net_id"] == "1.2.3.4.5.6"
    assert config_mgr.saved == 1

    write = client.post(
        "/api/variables/write",
        json={
            "plc_id": "plc_001",
            "variable": "Light.Light_EG_WZ.bOn",
            "value": True,
        },
    )
    assert write.status_code == 200
    write_payload = write.get_json()
    assert write_payload["status"] == "success"
    assert gateway.writes == [("plc_001", "Light.Light_EG_WZ.bOn", True)]

    disconnect = client.post("/api/plc/disconnect", json={})
    assert disconnect.status_code == 200
    assert disconnect.get_json()["success"] is True
    assert plc.disconnect_calls == 1


def test_integration_routing_config_reload_flow(integration_fixture, tmp_path):
    client, _, _, _, gateway = integration_fixture
    payload = {
        "version": "1.0",
        "description": "Integration Test",
        "routes": [
            {
                "id": "route_cam_alert",
                "from": "Alarm.Camera.*",
                "to": ["websocket", "mqtt"],
                "enabled": True,
            }
        ],
        "settings": {"default_target": "websocket"},
    }

    res = client.post("/api/routing/config", json=payload)
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["config"]["routes"][0]["id"] == "route_cam_alert"
    assert gateway.routing_reload_count == 1

    routing_file = tmp_path / "config" / "routing.json"
    assert routing_file.exists()
    stored = json.loads(routing_file.read_text(encoding="utf-8"))
    assert stored["description"] == "Integration Test"
    assert stored["routes"][0]["to"] == ["websocket", "mqtt"]


def test_integration_stream_start_stop_flow(integration_fixture):
    client, _, _, stream_mgr, _ = integration_fixture

    start = client.post("/api/cameras/cam01/start", json={"resolution": "640x360"})
    assert start.status_code == 200
    start_payload = start.get_json()
    assert start_payload["success"] is True
    assert start_payload["hls_url"] == "/static/hls/cam01.m3u8"
    assert stream_mgr.start_calls == [("cam01", "rtsp://127.0.0.1:554/live", "640x360")]

    stop = client.post("/api/cameras/cam01/stop", json={"immediate": True})
    assert stop.status_code == 200
    stop_payload = stop.get_json()
    assert stop_payload["success"] is True
    assert stream_mgr.stop_calls == ["cam01"]


def test_integration_admin_restart_actions_are_audited(integration_fixture, monkeypatch):
    client, _, _, _, _ = integration_fixture
    captured = {"audit": [], "restart_delays": [], "daemon_delays": []}

    from modules.core.database_logger import DatabaseLogger
    from modules.core.service_manager import ServiceManager

    def _fake_audit(db_path, action, actor, details=None):
        captured["audit"].append(
            {
                "db_path": db_path,
                "action": action,
                "actor": actor,
                "details": details or {},
            }
        )
        return 1

    def _fake_schedule_restart(delay_seconds=2):
        captured["restart_delays"].append(delay_seconds)
        return True

    def _fake_schedule_ctl_restart(delay_seconds=1):
        captured["daemon_delays"].append(delay_seconds)
        return True, f"Dienst-Neustart via Script in {delay_seconds}s geplant"

    monkeypatch.setattr(DatabaseLogger, "audit_event", staticmethod(_fake_audit))
    monkeypatch.setattr(ServiceManager, "schedule_restart", staticmethod(_fake_schedule_restart))
    monkeypatch.setattr(ServiceManager, "schedule_ctl_restart", staticmethod(_fake_schedule_ctl_restart))

    restart = client.post(
        "/api/admin/service/restart",
        json={"delay": 3},
        headers={"X-Admin-User": "pytest-admin"},
    )
    assert restart.status_code == 200
    assert restart.get_json()["success"] is True
    assert captured["restart_delays"] == [3]

    daemon_restart = client.post(
        "/api/admin/service/restart-daemon",
        json={"delay": 999},
        headers={"X-Admin-User": "pytest-admin"},
    )
    assert daemon_restart.status_code == 200
    assert daemon_restart.get_json()["success"] is True
    assert captured["daemon_delays"] == [30]

    assert len(captured["audit"]) == 2
    assert captured["audit"][0]["action"] == "service_restart_scheduled"
    assert captured["audit"][1]["action"] == "daemon_restart_scheduled"
    assert captured["audit"][0]["actor"] == "pytest-admin"
    assert captured["audit"][1]["actor"] == "pytest-admin"
    assert captured["audit"][0]["details"]["delay_seconds"] == 3
    assert captured["audit"][1]["details"]["delay_seconds"] == 30
    assert "request_id" in captured["audit"][0]["details"]


def test_integration_admin_daemon_restart_rejection_is_audited(integration_fixture, monkeypatch):
    client, _, _, _, _ = integration_fixture
    captured = {"audit": []}

    from modules.core.database_logger import DatabaseLogger
    from modules.core.service_manager import ServiceManager

    def _fake_audit(db_path, action, actor, details=None):
        captured["audit"].append(
            {
                "db_path": db_path,
                "action": action,
                "actor": actor,
                "details": details or {},
            }
        )
        return 1

    monkeypatch.setattr(DatabaseLogger, "audit_event", staticmethod(_fake_audit))
    monkeypatch.setattr(ServiceManager, "is_container_runtime", staticmethod(lambda: True))

    daemon_restart = client.post(
        "/api/admin/service/restart-daemon",
        json={"delay": 999},
        headers={"X-Admin-User": "pytest-admin"},
    )
    assert daemon_restart.status_code == 400
    body = daemon_restart.get_json()
    assert body["success"] is False
    assert "deaktiviert" in body["error"]
    assert len(captured["audit"]) == 1
    assert captured["audit"][0]["action"] == "daemon_restart_rejected"
    assert captured["audit"][0]["actor"] == "pytest-admin"
    assert captured["audit"][0]["details"]["delay_seconds"] == 30
    assert "request_id" in captured["audit"][0]["details"]
