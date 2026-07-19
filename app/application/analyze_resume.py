"""Analyze resume use-case: ATS scoring, keyword extraction, suggestions."""
import logging

from app.domain.analysis import ATSResult
from app.domain.resume import ResumeData
from app.services.ats_engine import analyze

logger = logging.getLogger(__name__)


class AnalyzeResumeUseCase:
    """Run deterministic ATS analysis against a job description."""

    def run(self, resume: ResumeData, jd_text: str) -> ATSResult:
        return analyze(resume, jd_text)

    def persist(self, resume_id: int, job_id: int, result: ATSResult) -> None:
        from app.database import db
        db.save_analysis(resume_id, job_id, result.to_dict())
        logger.info("Persisted ATS analysis resume=%d job=%d", resume_id, job_id)
