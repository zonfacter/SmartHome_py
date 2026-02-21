import signal

from modules.core.service_manager import ServiceManager


def test_schedule_ctl_restart_is_disabled_in_container(monkeypatch):
    monkeypatch.setattr(ServiceManager, "is_container_runtime", staticmethod(lambda: True))
    ok, message = ServiceManager.schedule_ctl_restart(delay_seconds=1)
    assert ok is False
    assert "deaktiviert" in message


def test_restart_info_exposes_container_flag(monkeypatch):
    monkeypatch.setattr(ServiceManager, "is_container_runtime", staticmethod(lambda: True))
    info = ServiceManager.get_restart_info()
    assert "is_container_runtime" in info
    assert info["is_container_runtime"] is True


def test_restart_service_uses_sigterm_in_container(monkeypatch):
    calls = []

    monkeypatch.setattr(ServiceManager, "is_container_runtime", staticmethod(lambda: True))
    monkeypatch.setattr("os.kill", lambda pid, sig: calls.append((pid, sig)))

    ok = ServiceManager.restart_service()
    assert ok is True
    assert len(calls) == 1
    assert calls[0][1] == signal.SIGTERM
