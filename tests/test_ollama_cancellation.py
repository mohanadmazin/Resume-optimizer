"""Tests for OllamaClient — cancellation, streaming, retry behavior."""
from __future__ import annotations

import json
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.ai.ollama_client import (
    OllamaCancelledError,
    OllamaClient,
)


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------
class TestOllamaCancellation:
    def test_check_cancelled_raises_when_event_set(self):
        client = OllamaClient(base_url="http://fake:11434", model="test")
        event = threading.Event()
        client.set_cancel_event(event)
        event.set()
        with pytest.raises(OllamaCancelledError):
            client._check_cancelled()

    def test_check_cancelled_noop_when_event_not_set(self):
        client = OllamaClient(base_url="http://fake:11434", model="test")
        event = threading.Event()
        client.set_cancel_event(event)
        client._check_cancelled()  # should not raise

    def test_check_cancelled_noop_when_no_event(self):
        client = OllamaClient(base_url="http://fake:11434", model="test")
        client._check_cancelled()  # should not raise

    def test_cancelled_ollama_request_is_not_retried(self):
        """OllamaCancelledError must be re-raised immediately, not retried."""
        client = OllamaClient(base_url="http://fake:11434", model="test")
        event = threading.Event()
        client.set_cancel_event(event)
        event.set()

        with pytest.raises(OllamaCancelledError):
            client.generate("test prompt")

    def test_cancelled_structured_request_is_not_retried(self):
        """generate_structured must re-raise OllamaCancelledError without retry."""
        client = OllamaClient(base_url="http://fake:11434", model="test")
        event = threading.Event()
        client.set_cancel_event(event)
        event.set()

        from pydantic import BaseModel

        class Dummy(BaseModel):
            name: str

        with pytest.raises(OllamaCancelledError):
            client.generate_structured("test prompt", Dummy)

    def test_streaming_cancellation_mid_stream(self):
        """Streaming loop exits when cancel event is set mid-iteration."""
        client = OllamaClient(base_url="http://fake:11434", model="test")
        event = threading.Event()
        client.set_cancel_event(event)

        # Simulate: first line OK, cancel, second line raises
        lines = [
            json.dumps({"response": "hello", "done": False}).encode(),
            json.dumps({"response": " world", "done": True}).encode(),
        ]

        call_count = 0

        def fake_iter_lines():
            nonlocal call_count
            for line in lines:
                call_count += 1
                if call_count == 2:
                    event.set()
                yield line

        mock_response = MagicMock()
        mock_response.iter_lines = fake_iter_lines
        mock_response.raise_for_status = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.ai.ollama_client.requests.post", return_value=mock_response):
            with pytest.raises(OllamaCancelledError):
                client._generate_impl("test prompt")

    def test_generate_json_cancelled_not_retried_without_format(self):
        """generate_json must re-raise cancellation, not retry without json_mode."""
        client = OllamaClient(base_url="http://fake:11434", model="test")
        event = threading.Event()
        client.set_cancel_event(event)
        event.set()

        with pytest.raises(OllamaCancelledError):
            client.generate_json("test prompt")
