import threading
import time
from unittest.mock import patch

import pytest
import requests
from circuitbreaker import CircuitBreakerMonitor

from app.ai.ollama_client import AIBusyError, OllamaClient, OllamaError


@pytest.fixture()
def client():
    c = OllamaClient(base_url="http://localhost:11434", model="test-model")
    cb = CircuitBreakerMonitor.get("OllamaClient._generate_impl")
    if cb:
        cb.reset()
    return c


def test_generate_raises_ai_busy_when_locked(client):
    """AIBusyError is raised if another generate() call holds the lock."""
    client._generation_lock.acquire()
    try:
        with pytest.raises(AIBusyError, match="already in progress"):
            client.generate("hello")
    finally:
        client._generation_lock.release()


def test_concurrent_generate_raises_ai_busy(client):
    """Second thread calling generate() while first is running gets AIBusyError."""
    gate = threading.Event()
    release = threading.Event()
    second_result = {}

    def slow_generate():
        client._generation_lock.acquire()
        gate.set()
        release.wait(timeout=5)
        client._generation_lock.release()

    def try_generate():
        try:
            client.generate("hello")
            second_result["error"] = None
        except AIBusyError as exc:
            second_result["error"] = exc

    t1 = threading.Thread(target=slow_generate)
    t2 = threading.Thread(target=try_generate)
    t1.start()
    gate.wait(timeout=5)
    t2.start()
    t2.join(timeout=5)
    release.set()
    t1.join(timeout=5)

    assert second_result.get("error") is not None
    assert "already in progress" in str(second_result["error"])


def test_generate_releases_lock_on_success(client):
    """Lock is released after a successful generate() call."""
    with patch("app.ai.ollama_client.requests.post") as mock_post:
        mock_resp = mock_post.return_value
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = {"response": "hi", "done": True}

        client.generate("hello")
        assert not client._generation_lock.locked()


def test_generate_releases_lock_on_error(client):
    """Lock is released even when generate() raises an exception."""
    with patch("app.ai.ollama_client.requests.post", side_effect=ConnectionError("fail")):
        with pytest.raises(Exception):
            client.generate("hello")
        assert not client._generation_lock.locked()


# ── Circuit breaker tests ───────────────────────────────────────────────


class TestCircuitBreaker:
    def test_circuit_opens_after_5_failures(self, client):
        """After 5 consecutive failures, circuit opens and fails fast."""
        with patch("app.ai.ollama_client.requests.post", side_effect=requests.ConnectionError("down")):
            for _ in range(5):
                with pytest.raises(OllamaError, match="Ollama request failed"):
                    client.generate("test")

            # 6th call should fail immediately with circuit breaker message
            with pytest.raises(OllamaError, match="circuit breaker"):
                client.generate("test")

    def test_circuit_resets_after_recovery(self, client):
        """After recovery_timeout, circuit allows one trial request."""
        # Trip the circuit
        with patch("app.ai.ollama_client.requests.post", side_effect=requests.ConnectionError("down")):
            for _ in range(5):
                with pytest.raises(OllamaError):
                    client.generate("test")

        # Manually fast-forward the circuit breaker
        cb = CircuitBreakerMonitor.get("OllamaClient._generate_impl")
        # Set _opened far in the past so open_remaining <= 0 → HALF_OPEN
        cb._opened = time.monotonic() - 200

        # Next successful call should half-close and then close the circuit
        with patch("app.ai.ollama_client.requests.post") as mock_post:
            mock_resp = mock_post.return_value
            mock_resp.status_code = 200
            mock_resp.raise_for_status = lambda: None
            mock_resp.json.return_value = {"response": "ok", "done": True}

            result = client.generate("test")
            assert result == "ok"

    def test_circuit_does_not_trip_on_success(self, client):
        """Successful calls never trip the circuit."""
        with patch("app.ai.ollama_client.requests.post") as mock_post:
            mock_resp = mock_post.return_value
            mock_resp.status_code = 200
            mock_resp.raise_for_status = lambda: None
            mock_resp.json.return_value = {"response": "hi", "done": True}

            for _ in range(10):
                client.generate("test")

        cb = CircuitBreakerMonitor.get("OllamaClient._generate_impl")
        assert cb.state == "closed"
