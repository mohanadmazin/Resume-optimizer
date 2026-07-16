"""Background thread worker so AI calls never block the UI."""
import logging
import time
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, parent: object = None, **kwargs: Any):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.error.emit(str(exc))


class PipelineWorker(QThread):
    """Runs the full optimization pipeline: ATS → Optimize → Cover Letter."""

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

    def run(self) -> None:
        from app import config
        from app.ai.ollama_client import OllamaClient
        from app.database import db
        from app.domain.pipeline import PipelineResult
        from app.services.ats_engine import analyze
        from app.services.cover_letter import generate_cover_letter
        from app.services.optimizer import optimize_resume

        start = time.monotonic()

        try:
            # Step 1 — ATS Analysis (fast, CPU-only)
            self.progress.emit(self.STEPS[0], 10)
            ats_result = analyze(self.resume, self.job_text)
            if self._cancelled:
                return
            self.progress.emit(f"{self.STEPS[0]} ✓", 25)

            # Step 2 — AI Optimization (slow)
            self.progress.emit(self.STEPS[1], 30)
            client = OllamaClient()
            optimized = optimize_resume(
                self.resume, self.job_text, ats_result, client
            )
            if self._cancelled:
                return
            self.progress.emit(f"{self.STEPS[1]} ✓", 60)

            # Step 3 — Cover Letter (slow)
            self.progress.emit(self.STEPS[2], 65)
            cover_letter = generate_cover_letter(
                self.resume, self.job_text, client
            )
            if self._cancelled:
                return
            self.progress.emit(f"{self.STEPS[2]} ✓", 90)

            # Step 4 — Persist results
            self.progress.emit(self.STEPS[3], 95)
            model = config.load_config()["model"]
            if self.resume_id and self.job_id:
                db.save_optimization(
                    self.resume_id, self.job_id, model,
                    optimized.model_dump_json(),
                )

            # Compute after-score
            ats_after = analyze(optimized, self.job_text)

            duration = time.monotonic() - start
            self.progress.emit("Pipeline complete!", 100)

            self.result.emit(PipelineResult(
                ats_before=ats_result,
                optimized=optimized,
                cover_letter=cover_letter,
                ats_after_score=ats_after.ats_score,
                duration_seconds=round(duration, 1),
            ))

        except Exception as exc:
            logger.exception("Pipeline failed")
            self.error.emit(str(exc))
