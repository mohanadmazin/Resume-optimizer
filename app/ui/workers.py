"""Background thread worker so AI calls never block the UI."""
import logging
import threading
import time
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class OperationCancelled(Exception):
    """Raised when a cooperative cancellation is requested."""


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        parent: object = None,
        timeout: int = 180,
        **kwargs: Any,
    ):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._timeout = timeout
        self._cancel_event = threading.Event()
        self._terminal_lock = threading.Lock()
        self._terminal_emitted = False
        self._timer: threading.Timer | None = None

    def cancel(self) -> None:
        self._cancel_event.set()
        self.requestInterruption()

    def run(self) -> None:
        self._timer = threading.Timer(self._timeout, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()
        try:
            value = self._fn(*self._args, **self._kwargs)
            if self._cancel_event.is_set():
                self._emit_cancelled_once()
            else:
                self._emit_result_once(value)
        except OperationCancelled:
            self._emit_cancelled_once()
        except Exception as exc:
            self._emit_error_once(str(exc))
        finally:
            if self._timer is not None:
                self._timer.cancel()

    def _on_timeout(self) -> None:
        logger.warning("Worker timed out after %ds calling %s", self._timeout, self._fn.__name__)
        self._cancel_event.set()
        self.requestInterruption()
        self._emit_error_once(
            f"Operation timed out after {self._timeout} seconds. "
            "The AI model may be loading or unresponsive."
        )

    def _emit_result_once(self, value) -> None:
        with self._terminal_lock:
            if not self._terminal_emitted:
                self._terminal_emitted = True
                self.result.emit(value)

    def _emit_error_once(self, message: str) -> None:
        with self._terminal_lock:
            if not self._terminal_emitted:
                self._terminal_emitted = True
                self.error.emit(message)

    def _emit_cancelled_once(self) -> None:
        with self._terminal_lock:
            if not self._terminal_emitted:
                self._terminal_emitted = True
                self.cancelled.emit()


class PipelineWorker(QThread):
    """Runs the full optimization pipeline: ATS -> Optimize -> Cover Letter -> Skill Gap -> Salary."""

    progress = Signal(str, int)   # (step_name, percentage 0-100)
    result = Signal(object)       # PipelineResult
    error = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        resume,
        job_text: str,
        job_title: str,
        job_location: str,
        job_id: int | None,
        resume_id: int | None,
        parent=None,
    ):
        super().__init__(parent)
        self.resume = resume
        self.job_text = job_text
        self.job_title = job_title
        self.job_location = job_location
        self.job_id = job_id
        self.resume_id = resume_id
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()
        self.requestInterruption()

    def run(self) -> None:
        from app.ai.ollama_client import OllamaClient
        from app.application.optimize_resume import RunPipelineUseCase

        client = OllamaClient()
        client.set_cancel_event(self._cancel_event)

        use_case = RunPipelineUseCase()
        start = time.monotonic()

        try:
            result = use_case.run(
                self.resume,
                self.job_text,
                self.job_title,
                self.job_location,
                self.resume_id,
                self.job_id,
                client,
                cancel_event=self._cancel_event,
                progress=lambda label, percent: self.progress.emit(label, percent),
            )

            if self._cancel_event.is_set():
                self.cancelled.emit()
                return

            duration = time.monotonic() - start
            logger.info("Pipeline completed in %.1fs", duration)
            self.progress.emit("Pipeline complete!", 100)
            self.result.emit(result)

        except OperationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            logger.exception("Pipeline failed")
            self.error.emit(str(exc))
