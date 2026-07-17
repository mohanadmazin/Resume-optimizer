"""Background thread worker so AI calls never block the UI."""
import logging
import threading
import time
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

# Global cancellation event shared across workers for pipeline cancellation.
_cancel_event = threading.Event()


def request_cancel() -> None:
    """Signal cancellation to all active pipeline workers."""
    _cancel_event.set()


def reset_cancel() -> None:
    """Clear any pending cancellation."""
    _cancel_event.clear()


def is_cancelled() -> bool:
    """Check if cancellation has been requested."""
    return _cancel_event.is_set()


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)

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
        self._timer: threading.Timer | None = None

    def run(self) -> None:
        self._timer = threading.Timer(self._timeout, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.error.emit(str(exc))
        finally:
            if self._timer is not None:
                self._timer.cancel()

    def _on_timeout(self) -> None:
        logger.warning("Worker timed out after %ds calling %s", self._timeout, self._fn.__name__)
        self.error.emit(f"Operation timed out after {self._timeout} seconds. The AI model may be loading or unresponsive.")
        self.terminate()


class PipelineWorker(QThread):
    """Runs the full optimization pipeline: ATS -> Optimize -> Cover Letter."""

    progress = Signal(str, int)   # (step_name, percentage 0-100)
    result = Signal(object)       # PipelineResult
    error = Signal(str)

    STEPS = (
        "Running ATS Analysis",
        "Optimizing resume with AI",
        "Generating cover letter",
        "Saving results",
    )

    def __init__(
        self,
        resume,
        job_text: str,
        job_title: str,
        job_id: int | None,
        resume_id: int | None,
        parent=None,
    ):
        super().__init__(parent)
        self.resume = resume
        self.job_text = job_text
        self.job_title = job_title
        self.job_id = job_id
        self.resume_id = resume_id
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        request_cancel()

    def run(self) -> None:
        from app.application.optimize_resume import RunPipelineUseCase

        reset_cancel()
        use_case = RunPipelineUseCase()
        start = time.monotonic()

        try:
            self.progress.emit(self.STEPS[0], 10)

            from app.ai.ollama_client import OllamaClient
            client = OllamaClient()

            self.progress.emit(f"{self.STEPS[0]} ...", 25)
            self.progress.emit(self.STEPS[1], 30)

            if self._cancelled:
                return
            self.progress.emit(f"{self.STEPS[1]} ...", 60)
            self.progress.emit(self.STEPS[2], 65)

            if self._cancelled:
                return
            self.progress.emit(f"{self.STEPS[2]} ...", 90)
            self.progress.emit(self.STEPS[3], 95)

            result = use_case.run(
                self.resume, self.job_text, self.job_title,
                self.resume_id, self.job_id, client,
            )

            if self._cancelled:
                return

            duration = time.monotonic() - start
            self.progress.emit("Pipeline complete!", 100)
            self.result.emit(result)

        except Exception as exc:
            logger.exception("Pipeline failed")
            self.error.emit(str(exc))
