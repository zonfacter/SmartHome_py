import os
import time
from types import SimpleNamespace

from modules.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from modules.gateway.data_gateway import DataGateway
from modules.gateway.stream_manager import StreamManager


class _SymbolInfo:
    symbol_type = "BOOL"


class _DummyVariableManager:
    def get_symbol_info(self, variable_name, plc_id):
        return _SymbolInfo()

    def update_value(self, variable_name, value, plc_id):
        return None


class _FailingPLC:
    connected = True

    def __init__(self):
        self.calls = 0

    def write_by_name(self, variable, value, plc_type=None):
        self.calls += 1
        return False


def test_circuit_breaker_state_transitions():
    breaker = CircuitBreaker(
        name="unit:test",
        config=CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout_seconds=0.05,
            half_open_max_calls=1,
        ),
    )

    breaker.record_failure("e1")
    assert breaker.snapshot()["state"] == "closed"
    breaker.record_failure("e2")
    assert breaker.snapshot()["state"] == "open"
    assert breaker.allow_request() is False

    time.sleep(0.06)
    assert breaker.allow_request() is True
    assert breaker.snapshot()["state"] == "half_open"

    breaker.record_success()
    assert breaker.snapshot()["state"] == "closed"


def test_data_gateway_breaker_blocks_repeated_plc_write_failures(monkeypatch):
    monkeypatch.setenv("SMARTHOME_CB_FAILURE_THRESHOLD", "2")
    monkeypatch.setenv("SMARTHOME_CB_RECOVERY_SECONDS", "60")

    gateway = DataGateway()
    gateway.variable_manager = _DummyVariableManager()
    gateway.plc = _FailingPLC()

    assert gateway.write_variable("MAIN.bTest", True, "plc_001") is False
    assert gateway.write_variable("MAIN.bTest", True, "plc_001") is False

    before_calls = gateway.plc.calls
    assert gateway.write_variable("MAIN.bTest", True, "plc_001") is False
    assert gateway.plc.calls == before_calls

    stats = gateway.get_circuit_breaker_stats()["plc:plc_001:write"]
    assert stats["state"] == "open"
    assert stats["total_rejected"] >= 1


def test_stream_manager_breaker_blocks_repeated_start_failures(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTHOME_STREAM_CB_FAILURE_THRESHOLD", "2")
    monkeypatch.setenv("SMARTHOME_STREAM_CB_RECOVERY_SECONDS", "60")

    import modules.gateway.stream_manager as sm_mod

    popen_calls = {"count": 0}

    def _failing_popen(*args, **kwargs):
        popen_calls["count"] += 1
        raise RuntimeError("ffmpeg start failed")

    monkeypatch.setattr(sm_mod.subprocess, "Popen", _failing_popen)

    sm = StreamManager()
    sm.has_ffmpeg = True
    sm.hls_dir = str(tmp_path / "hls")
    os.makedirs(sm.hls_dir, exist_ok=True)
    sm.data_gateway = SimpleNamespace(capabilities={})

    assert sm.start_stream("cam01", "rtsp://127.0.0.1:554/live") is False
    assert sm.start_stream("cam01", "rtsp://127.0.0.1:554/live") is False

    before_calls = popen_calls["count"]
    assert sm.start_stream("cam01", "rtsp://127.0.0.1:554/live") is False
    assert popen_calls["count"] == before_calls

    stats = sm.get_circuit_breaker_stats()["stream:rtsp:cam01"]
    assert stats["state"] == "open"
    assert stats["total_rejected"] >= 1
