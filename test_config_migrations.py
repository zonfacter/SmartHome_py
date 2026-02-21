import json
import os
from pathlib import Path

from modules.core.config_manager import ConfigManager


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_config_manager_migrates_legacy_schema(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    mgr = ConfigManager()
    legacy = {
        "version": "1.0",
        "theme": "blue",
        "plc": {"ams_net_id": "1.2.3.4.5.6", "port": 851},
        "custom_lights": {},
    }
    _write_json(Path(mgr.config_file), legacy)

    assert mgr.load_config() is True
    assert mgr.config.get("schema_version") == 2
    assert mgr.config.get("version") == "2.0"
    assert isinstance(mgr.config.get("widgets"), dict)
    assert mgr.config.get("plc", {}).get("runtime_type") in ("TC2", "TC3")


def test_config_manager_rejects_future_schema(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    mgr = ConfigManager()
    future_cfg = {
        "schema_version": 99,
        "version": "99.0",
        "theme": "blue",
        "custom_lights": {},
        "widgets": {},
    }
    _write_json(Path(mgr.config_file), future_cfg)

    assert mgr.load_config() is False


def test_default_config_has_schema_version(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    mgr = ConfigManager()
    assert mgr.load_config() is False

    saved = json.loads(Path(mgr.config_file).read_text(encoding="utf-8"))
    assert saved.get("schema_version") == 2
    assert saved.get("version") == "2.0"
