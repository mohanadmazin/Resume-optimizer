"""Repository for persistent ATS analyses."""
from __future__ import annotations

import json
import logging

from app.database.models import Analysis, JobDescription, Resume
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AnalysisRepository(BaseRepository):
    def save(self, resume_id: int, job_id: int, result: dict) -> int:
        row = Analysis(
            resume_id=resume_id,
            job_id=job_id,
            ats_score=int(result.get("ats_score", 0)),
            keyword_match=float(result.get("keyword_match_pct", 0.0)),
            skills_match=float(result.get("skills_match_pct", 0.0)),
            missing_keywords=json.dumps(result.get("missing_keywords", [])),
            suggestions=json.dumps(result.get("suggestions", [])),
            result_json=json.dumps(result, ensure_ascii=False, default=str),
        )
        self.add(row)
        self.flush()
        return int(row.id)

    def get_recent(self, limit: int = 10) -> list[dict]:
        rows = (
            self.session.query(Analysis, Resume.name, JobDescription.title, JobDescription.company)
            .join(Resume, Analysis.resume_id == Resume.id)
            .join(JobDescription, Analysis.job_id == JobDescription.id)
            .order_by(Analysis.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": analysis.id,
                "resume_id": analysis.resume_id,
                "job_id": analysis.job_id,
                "created_at": analysis.created_at.strftime("%Y-%m-%d %H:%M") if analysis.created_at else "",
                "resume_name": resume_name,
                "job_title": job_title,
                "job_company": company or "",
                "ats_score": analysis.ats_score,
                "keyword_match": analysis.keyword_match,
                "skills_match": analysis.skills_match,
            }
            for analysis, resume_name, job_title, company in rows
        ]

    def get_by_id(self, analysis_id: int) -> Analysis | None:
        return self.session.query(Analysis).filter(Analysis.id == analysis_id).first()

    def get_latest_for_pair(self, resume_id: int, job_id: int) -> Analysis | None:
        return (
            self.session.query(Analysis)
            .filter(Analysis.resume_id == resume_id, Analysis.job_id == job_id)
            .order_by(Analysis.id.desc())
            .first()
        )
