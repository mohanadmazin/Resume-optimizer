"""Background thread worker so AI calls never block the UI."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class OperationCancelled(Exception):
    """Raised when a cooperative operation is cancelled."""


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def event(self) -> threading.Event:
        return self._event

    def cancel(self) -> None:
        self._event.set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise OperationCancelled("Operation cancelled.")


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        timeout_seconds: int = 180,
        parent: object = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._timeout_seconds = timeout_seconds
        self._token = CancellationToken()

        self._terminal_lock = threading.Lock()
        self._terminal_emitted = False

    @property
    def cancellation_token(self) -> CancellationToken:
        return self._token

    def cancel(self) -> None:
        self._token.cancel()
        self.requestInterruption()

    def run(self) -> None:
        timeout_timer = threading.Timer(
            self._timeout_seconds,
            self.cancel,
        )
        timeout_timer.daemon = True
        timeout_timer.start()

        try:
            value = self._fn(*self._args, **self._kwargs)
            self._token.raise_if_cancelled()
            self._emit_once(self.result, value)
        except OperationCancelled:
            self._emit_once(self.cancelled)
        except Exception as exc:
            logger.exception("Background operation failed")
            self._emit_once(self.error, str(exc))
        finally:
            timeout_timer.cancel()

    def _emit_once(self, signal: Signal, value: Any = None) -> None:
        with self._terminal_lock:
            if self._terminal_emitted:
                return

            self._terminal_emitted = True

            if value is None:
                signal.emit()
            else:
                signal.emit(value)


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
        job_company: str | None = None,
    ):
        super().__init__(parent)
        self.resume = resume
        self.job_text = job_text
        self.job_title = job_title
        self.job_location = job_location
        self.job_id = job_id
        self.resume_id = resume_id
        self.job_company = job_company
        self._token = CancellationToken()

    def cancel(self) -> None:
        self._token.cancel()
        self.requestInterruption()

    def run(self) -> None:
        from app.ai.ollama_client import OllamaClient
        from app.application.optimize_resume import RunPipelineUseCase

        client = OllamaClient()
        client.set_cancel_event(self._token.event)

        try:
            result = RunPipelineUseCase().run(
                self.resume,
                self.job_text,
                self.job_title,
                self.job_location,
                self.resume_id,
                self.job_id,
                client,
                cancel_event=self._token.event,
                progress=lambda name, percent: self.progress.emit(
                    name,
                    percent,
                ),
                job_company=self.job_company,
            )
            self._token.raise_if_cancelled()
            self.result.emit(result)
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            logger.exception("Pipeline failed")
            self.error.emit(str(exc))
