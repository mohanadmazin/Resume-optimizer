"""Tests for background workers, cancellation tokens, and timeout behavior."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from PySide6.QtCore import QCoreApplication

from app.ui.workers import CancellationToken, OperationCancelled, PipelineWorker, Worker


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    """Ensure a QApplication exists for signal delivery across threads."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


# ---------------------------------------------------------------------------
# CancellationToken
# ---------------------------------------------------------------------------
class TestCancellationToken:
    def test_cancel_sets_event(self):
        token = CancellationToken()
        assert not token.event.is_set()
        token.cancel()
        assert token.event.is_set()

    def test_raise_if_cancelled_noop_when_not_cancelled(self):
        token = CancellationToken()
        token.raise_if_cancelled()  # should not raise

    def test_raise_if_cancelled_raises_when_cancelled(self):
        token = CancellationToken()
        token.cancel()
        with pytest.raises(OperationCancelled):
            token.raise_if_cancelled()


# ---------------------------------------------------------------------------
# Worker — timeout and termination
# ---------------------------------------------------------------------------
class TestWorkerTimeout:
    def test_timeout_never_calls_qthread_terminate(self):
        """Timeout cancels cooperatively and never calls QThread.terminate()."""
        call_event = threading.Event()

        def slow_fn():
            call_event.set()
            # Finish naturally; cancellation is checked by Worker afterwards.
            time.sleep(0.05)

        w = Worker(slow_fn, timeout_seconds=0)
        with patch.object(w, "terminate") as mock_terminate:
            w.start()
            assert call_event.wait(timeout=2)
            assert w.wait(2000)
            mock_terminate.assert_not_called()

    def test_worker_cancellation_is_not_global(self):
        """Cancelling one Worker must not affect another worker's token."""
        started = [threading.Event() for _ in range(2)]
        release = [threading.Event() for _ in range(2)]

        def work(idx):
            started[idx].set()
            release[idx].wait(timeout=2)

        workers = [Worker(work, i, timeout_seconds=60) for i in range(2)]
        for worker in workers:
            worker.start()
        assert all(event.wait(timeout=2) for event in started)

        workers[0].cancel()
        release[0].set()
        assert workers[0].wait(2000)

        assert workers[0].cancellation_token.event.is_set()
        assert not workers[1].cancellation_token.event.is_set()
        assert workers[1].isRunning()

        workers[1].cancel()
        release[1].set()
        assert workers[1].wait(2000)

    def test_worker_result_emitted_on_success(self):
        def add(a, b):
            return a + b

        w = Worker(add, 2, 3)
        received = []
        w.result.connect(lambda v: received.append(v))
        w.start()
        assert w.wait(5000)
        QCoreApplication.processEvents()
        assert received == [5]

    def test_worker_error_emitted_on_exception(self):
        def fail():
            raise ValueError("boom")

        w = Worker(fail)
        errors = []
        w.error.connect(lambda e: errors.append(e))
        w.start()
        while w.isRunning():
            time.sleep(0.01)
        QCoreApplication.processEvents()
        assert len(errors) == 1
        assert "boom" in errors[0]

    def test_worker_cancelled_signal_on_cancel(self):
        """Worker.cancel() sets the token; the thread finishes and _emit_once fires."""
        def short_work():
            time.sleep(0.1)

        w = Worker(short_work, timeout_seconds=60)
        w.start()
        w.cancel()
        while w.isRunning():
            time.sleep(0.05)
        assert w._token.event.is_set()


# ---------------------------------------------------------------------------
# PipelineWorker — cancel event reaches Ollama
# ---------------------------------------------------------------------------
class TestPipelineWorker:
    def test_pipeline_cancel_event_reaches_ollama(self):
        """PipelineWorker passes its cancel event to OllamaClient."""
        mock_client = MagicMock()

        pw = PipelineWorker(
            resume=MagicMock(),
            job_text="test",
            job_title="Engineer",
            job_location="NYC",
            job_id=None,
            resume_id=None,
        )
        pw._token.cancel()

        with patch("app.ai.ollama_client.OllamaClient", return_value=mock_client), \
             patch("app.application.optimize_resume.RunPipelineUseCase") as MockPipeline:
            mock_pipeline = MockPipeline.return_value
            mock_pipeline.run.side_effect = OperationCancelled("cancelled")
            pw.run()

        mock_client.set_cancel_event.assert_called_once_with(pw._token.event)
