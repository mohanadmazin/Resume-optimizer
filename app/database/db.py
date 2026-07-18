"""Database access layer — backward-compatible re-exports.

New code should import from:
  - app.database.engine
  - app.database.session
  - app.database.repositories
"""
import json
import logging

from app.database.engine import engine
from app.database.session import SessionLocal, get_session
from app.database.models import Base, Resume, JobDescription, Analysis, Optimization

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Legacy CRUD helpers — delegate to repositories for backward compatibility
# ---------------------------------------------------------------------------

def save_resume(
    name: str,
    data_json: str,
    raw_text: str = "",
    source_type: str = "import",
    source_filename: str = "",
) -> int:
    from app.database.repositories import ResumeRepository
    with get_session() as session:
        return ResumeRepository(session).save(
            name, data_json, raw_text, source_type, source_filename
        )


def save_job(title: str, content: str) -> int:
    from app.database.repositories import JobRepository
    with get_session() as session:
        return JobRepository(session).save(title, content)


def save_analysis(resume_id: int, job_id: int, result: dict) -> int:
    from app.database.repositories import AnalysisRepository
    with get_session() as session:
        return AnalysisRepository(session).save(resume_id, job_id, result)


def save_optimization(resume_id: int, job_id: int, model: str, optimized_json: str) -> int:
    from app.database.models import Optimization
    with get_session() as session:
        row = Optimization(resume_id=resume_id, job_id=job_id, model=model, optimized_json=optimized_json)
        session.add(row)
        session.flush()
        return row.id


def latest_resume() -> dict | None:
    from app.database.repositories import ResumeRepository
    with get_session() as session:
        return ResumeRepository(session).get_latest()


def latest_job() -> dict | None:
    from app.database.repositories import JobRepository
    with get_session() as session:
        return JobRepository(session).get_latest()


def recent_analyses(limit: int = 10) -> list[dict]:
    from app.database.repositories import AnalysisRepository
    with get_session() as session:
        return AnalysisRepository(session).get_recent(limit)
