"""Repository for job description CRUD operations."""
from __future__ import annotations

import logging
from datetime import datetime

from app.database.models import JobDescription
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """Handles job description CRUD including application metadata."""

    def save(
        self,
        title: str,
        content: str,
        *,
        company: str = "",
        location: str = "",
        source_url: str = "",
        employment_type: str = "",
        salary: str = "",
        date_posted: str = "",
        status: str = "saved",
    ) -> int:
        row = JobDescription(
            title=title or "Untitled role",
            content=content,
            company=company,
            location=location,
            source_url=source_url,
            employment_type=employment_type,
            salary=salary,
            date_posted=date_posted,
            status=status or "saved",
        )
        self.add(row)
        self.flush()
        logger.debug("Saved job id=%d title=%s", row.id, title)
        return int(row.id)

    def update(self, job_id: int, **values) -> bool:
        row = self.get_by_id(job_id)
        if row is None:
            return False
        allowed = {
            "title", "content", "company", "location", "source_url",
            "employment_type", "salary", "date_posted", "status",
        }
        for key, value in values.items():
            if key in allowed:
                setattr(row, key, value)
        row.updated_at = datetime.utcnow()
        return True

    def get_latest(self) -> dict | None:
        row = self.session.query(JobDescription).order_by(JobDescription.id.desc()).first()
        return self._as_dict(row) if row else None

    def get_by_id(self, job_id: int) -> JobDescription | None:
        return self.session.query(JobDescription).filter(JobDescription.id == job_id).first()

    def get_all(self) -> list[dict]:
        rows = self.session.query(JobDescription).order_by(JobDescription.id.desc()).all()
        return [self._as_dict(row, include_content=False) for row in rows]

    @staticmethod
    def _as_dict(row: JobDescription, *, include_content: bool = True) -> dict:
        data = {
            "id": row.id,
            "title": row.title,
            "company": row.company or "",
            "location": row.location or "",
            "source_url": row.source_url or "",
            "employment_type": row.employment_type or "",
            "salary": row.salary or "",
            "date_posted": row.date_posted or "",
            "status": row.status or "saved",
            "created_at": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else None,
            "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M") if row.updated_at else None,
        }
        if include_content:
            data["content"] = row.content
        return data

    def delete(self, job_id: int) -> bool:
        row = self.get_by_id(job_id)
        if row is None:
            return False
        self.session.delete(row)
        return True
