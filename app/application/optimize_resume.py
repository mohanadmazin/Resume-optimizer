"""Optimize resume use-case: AI rewrite + fact guard validation."""
import logging
import threading

from app.domain.analysis import ATSResult
from app.domain.pipeline import PipelineResult
from app.domain.resume import ResumeData
from app.services.ats_engine import analyze
from app.services.optimizer import optimize_resume
from app.services.cover_letter import generate_cover_letter

logger = logging.getLogger(__name__)


def _checkpoint(cancel_event: threading.Event | None = None) -> None:
    """Raise OperationCancelled if the event is set."""
    if cancel_event is not None and cancel_event.is_set():
        from app.ui.workers import OperationCancelled
        raise OperationCancelled("Operation cancelled by user")


class OptimizeResumeUseCase:
    """Run AI optimization with fact-guard validation."""

    def run(self, resume: ResumeData, jd_text: str, ats_result: ATSResult, client):
        return optimize_resume(resume, jd_text, ats_result, client)

    def generate_cover_letter(self, resume: ResumeData, jd_text: str, client, target_company: str | None = None):
        return generate_cover_letter(resume, jd_text, client, target_company=target_company)


class RunPipelineUseCase:
    """Full optimization pipeline: ATS -> Optimize -> Cover Letter -> Skill Gap -> Salary -> Save."""

    def run(
        self,
        resume: ResumeData,
        jd_text: str,
        job_title: str,
        job_location: str,
        resume_id: int | None,
        job_id: int | None,
        client=None,
        cancel_event: threading.Event | None = None,
        progress=None,
        job_company: str | None = None,
    ) -> PipelineResult:
        import time
        start = time.monotonic()

        if client is None:
            from app.ai.ollama_client import OllamaClient
            client = OllamaClient()

        def _emit(label: str, pct: int) -> None:
            if progress is not None:
                progress(label, pct)

        _emit("Running ATS analysis", 10)
        _checkpoint(cancel_event)

        ats_result = analyze(resume, jd_text)

        _emit("Optimizing resume with AI", 30)
        _checkpoint(cancel_event)

        optimized, fact_result = optimize_resume(resume, jd_text, ats_result, client)

        _emit("Generating cover letter", 55)
        _checkpoint(cancel_event)

        cover_letter_result = generate_cover_letter(optimized, jd_text, client, target_company=job_company)

        _emit("Analyzing skill gap", 70)
        _checkpoint(cancel_event)

        skill_gap_result = None
        if job_title:
            from app.services.skill_gap import analyze_skill_gap
            try:
                skill_gap_result = analyze_skill_gap(resume, jd_text, job_title)
            except Exception:
                logger.warning("Skill gap analysis failed, continuing pipeline", exc_info=True)

        _emit("Estimating salary range", 80)
        _checkpoint(cancel_event)

        salary_result = None
        location = job_location or "Not specified"
        if job_title:
            from app.services.salary_estimator import estimate_salary
            try:
                salary_result = estimate_salary(resume, job_title, location)
            except Exception:
                logger.warning("Salary estimation failed, continuing pipeline", exc_info=True)

        _emit("Running post-optimization ATS", 90)
        _checkpoint(cancel_event)

        ats_after = analyze(optimized, jd_text)

        requires_review = fact_result.flagged_count > 0

        _emit("Saving results", 95)
        _checkpoint(cancel_event)

        if resume_id and job_id and not requires_review:
            from app.database import db
            from app.core.settings import settings_service
            model = settings_service.model
            db.save_optimization(
                resume_id, job_id, model,
                optimized.model_dump_json(),
            )

        duration = time.monotonic() - start
        _emit("Pipeline complete!", 100)
        return PipelineResult(
            ats_before=ats_result,
            optimized=optimized,
            cover_letter=cover_letter_result.text,
            cover_letter_warnings=cover_letter_result.warnings,
            fact_guard=fact_result,
            ats_after_score=ats_after.ats_score,
            skill_gap=skill_gap_result,
            salary_estimate=salary_result,
            duration_seconds=round(duration, 1),
            requires_review=requires_review,
        )
