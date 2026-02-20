"""
Simple circuit breaker utility for connector isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, Any, Dict


class CircuitBreakerOpenError(RuntimeError):
    """Raised when an operation is rejected because the breaker is open."""


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_max_calls: int = 1


class CircuitBreaker:
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = str(name or "unnamed")
        self.config = config
        self._lock = threading.RLock()
        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._opened_at = 0.0
        self._last_failure_at = 0.0
        self._last_error = ""
        self._total_success = 0
        self._total_failure = 0
        self._total_rejected = 0

    def _transition_to_open(self, error_message: str = ""):
        now = time.time()
        self._state = self.STATE_OPEN
        self._opened_at = now
        self._last_failure_at = now
        self._half_open_calls = 0
        if error_message:
            self._last_error = str(error_message)

    def _transition_to_half_open_if_ready(self):
        if self._state != self.STATE_OPEN:
            return
        if (time.time() - self._opened_at) >= float(self.config.recovery_timeout_seconds):
            self._state = self.STATE_HALF_OPEN
            self._half_open_calls = 0

    def allow_request(self) -> bool:
        with self._lock:
            self._transition_to_half_open_if_ready()
            if self._state == self.STATE_OPEN:
                self._total_rejected += 1
                return False
            if self._state == self.STATE_HALF_OPEN:
                if self._half_open_calls >= max(1, int(self.config.half_open_max_calls)):
                    self._total_rejected += 1
                    return False
                self._half_open_calls += 1
            return True

    def record_success(self):
        with self._lock:
            self._total_success += 1
            self._failure_count = 0
            self._last_error = ""
            if self._state in (self.STATE_OPEN, self.STATE_HALF_OPEN):
                self._state = self.STATE_CLOSED
            self._half_open_calls = 0

    def record_failure(self, error_message: str = ""):
        with self._lock:
            self._total_failure += 1
            self._failure_count += 1
            self._last_failure_at = time.time()
            if error_message:
                self._last_error = str(error_message)

            threshold = max(1, int(self.config.failure_threshold))
            if self._state == self.STATE_HALF_OPEN or self._failure_count >= threshold:
                self._transition_to_open(error_message=error_message)

    def call(self, operation: Callable[[], Any]) -> Any:
        if not self.allow_request():
            raise CircuitBreakerOpenError(f"circuit_open:{self.name}")
        try:
            result = operation()
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(error_message=str(exc))
            raise

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._transition_to_half_open_if_ready()
            return {
                "name": self.name,
                "state": self._state,
                "failure_count": int(self._failure_count),
                "opened_at": float(self._opened_at),
                "last_failure_at": float(self._last_failure_at),
                "last_error": str(self._last_error or ""),
                "total_success": int(self._total_success),
                "total_failure": int(self._total_failure),
                "total_rejected": int(self._total_rejected),
                "config": {
                    "failure_threshold": int(self.config.failure_threshold),
                    "recovery_timeout_seconds": float(self.config.recovery_timeout_seconds),
                    "half_open_max_calls": int(self.config.half_open_max_calls),
                },
            }
