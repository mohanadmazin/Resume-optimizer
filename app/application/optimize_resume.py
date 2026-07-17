"""Optimize resume use-case: AI rewrite + fact guard validation."""
import logging
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.analysis import ATSResult
from app.domain.fact_guard import FactGuardResult
from app.domain.pipeline import PipelineResult
from app.domain.resume import ResumeData
from app.services.ats_engine import analyze
from app.services.fact_guard import FactGuard
from app.services.optimizer import optimize_resume
from app.services.cover_letter import generate_cover_letter

logger = logging.getLogger(__name__)


class OptimizeResumeUseCase:
    """Run AI optimization with fact-guard validation."""

    def run(self, resume: ResumeData, jd_text: str, ats_result: ATSResult, client):
        return optimize_resume(resume, jd_text, ats_result, client)

    def generate_cover_letter(self, resume: ResumeData, jd_text: str, client):
        return generate_cover_letter(resume, jd_text, client)


class RunPipelineUseCase:
    """Full optimization pipeline: ATS -> Optimize -> Cover Letter -> Save."""

    def run(self, resume: ResumeData, jd_text: str, job_title: str,
            resume_id: int | None, job_id: int | None, client=None) -> PipelineResult:
        import time
        start = time.monotonic()

        if client is None:
            from app.ai.ollama_client import OllamaClient
            client = OllamaClient()

        ats_result = analyze(resume, jd_text)
        optimized, fact_result = optimize_resume(resume, jd_text, ats_result, client)
        cover_letter = generate_cover_letter(resume, jd_text, client)
        ats_after = analyze(optimized, jd_text)

        requires_review = fact_result.flagged_count > 0

        if resume_id and job_id and not requires_review:
            from app.database import db
            from app.core.settings import settings_service
            model = settings_service.model
            db.save_optimization(
                resume_id, job_id, model,
                optimized.model_dump_json(),
            )

        duration = time.monotonic() - start
        return PipelineResult(
            ats_before=ats_result,
            optimized=optimized,
            cover_letter=cover_letter,
            fact_guard=fact_result,
            ats_after_score=ats_after.ats_score,
            duration_seconds=round(duration, 1),
            requires_review=requires_review,
        )
