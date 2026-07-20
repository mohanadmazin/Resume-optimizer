"""Score history service — snapshot ATS scores for trend tracking."""
from __future__ import annotations

import logging

from app.domain.scoring import ResumeScoreReport

logger = logging.getLogger(__name__)


def save_score_snapshot(
    resume_id: int,
    ats_score: int,
    score_report: ResumeScoreReport | None = None,
    job_id: int | None = None,
) -> int | None:
    """Save a score snapshot to the database. Returns the snapshot ID."""
    try:
        from app.database import db
        from app.database.models import ScoreSnapshot

        with db.session_scope() as session:
            report_json = score_report.model_dump_json() if score_report else "{}"
            kw_match = 0.0
            skills_match = 0.0
            if score_report:
                for cat in score_report.categories:
                    if cat.category.value == "optimization":
                        kw_match = cat.score / 100.0
                    if cat.category.value == "content":
                        skills_match = cat.score / 100.0

            row = ScoreSnapshot(
                resume_id=resume_id,
                job_id=job_id,
                ats_score=ats_score,
                keyword_match=kw_match,
                skills_match=skills_match,
                score_report_json=report_json,
            )
            session.add(row)
            session.flush()
            logger.info("Saved score snapshot %d (score=%d)", row.id, ats_score)
            return row.id
    except Exception:
        logger.exception("Failed to save score snapshot")
        return None


def get_score_history(resume_id: int) -> list[dict]:
    """Get score history for a resume, ordered by date."""
    try:
        from app.database import db
        from app.database.models import ScoreSnapshot

        with db.session_scope() as session:
            rows = (
                session.query(ScoreSnapshot)
                .filter(ScoreSnapshot.resume_id == resume_id)
                .order_by(ScoreSnapshot.created_at.asc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "ats_score": r.ats_score,
                    "keyword_match": r.keyword_match,
                    "skills_match": r.skills_match,
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                }
                for r in rows
            ]
    except Exception:
        logger.exception("Failed to load score history")
        return []
