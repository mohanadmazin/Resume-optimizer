"""Repository for analysis CRUD operations."""
import json
import logging

from app.database.models import Analysis, JobDescription, Resume
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AnalysisRepository(BaseRepository):
    """Handles analysis database operations."""

    def save(self, resume_id: int, job_id: int, result: dict) -> int:
        """Save a new analysis result and return its ID."""
        row = Analysis(
            resume_id=resume_id,
            job_id=job_id,
            ats_score=result["ats_score"],
            keyword_match=result["keyword_match_pct"],
            skills_match=result["skills_match_pct"],
            missing_keywords=json.dumps(result["missing_keywords"]),
            suggestions=json.dumps(result["suggestions"]),
        )
        self.add(row)
        self.flush()
        return row.id

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Get recent analyses with resume and job names."""
        rows = (
            self.session.query(Analysis, Resume.name, JobDescription.title)
            .join(Resume, Analysis.resume_id == Resume.id)
            .join(JobDescription, Analysis.job_id == JobDescription.id)
            .order_by(Analysis.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "created_at": analysis.created_at.strftime("%Y-%m-%d %H:%M"),
                "resume_name": resume_name,
                "job_title": job_title,
                "ats_score": analysis.ats_score,
                "keyword_match": analysis.keyword_match,
                "skills_match": analysis.skills_match,
            }
            for analysis, resume_name, job_title in rows
        ]

    def get_by_id(self, analysis_id: int) -> Analysis | None:
        """Get an analysis by its ID."""
        return self.session.query(Analysis).filter(Analysis.id == analysis_id).first()
