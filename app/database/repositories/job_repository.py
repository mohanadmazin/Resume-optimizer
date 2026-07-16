"""Repository for job description CRUD operations."""
import logging

from app.database.models import JobDescription
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """Handles job description database operations."""

    def save(self, title: str, content: str) -> int:
        """Save a new job description and return its ID."""
        row = JobDescription(title=title, content=content)
        self.add(row)
        self.flush()
        logger.debug("Saved job id=%d title=%s", row.id, title)
        return row.id

    def get_latest(self) -> dict | None:
        """Get the most recently created job description."""
        row = self.session.query(JobDescription).order_by(JobDescription.id.desc()).first()
        if row is None:
            return None
        return {
            "id": row.id,
            "title": row.title,
            "content": row.content,
        }

    def get_by_id(self, job_id: int) -> JobDescription | None:
        """Get a job description by its ID."""
        return self.session.query(JobDescription).filter(JobDescription.id == job_id).first()

    def get_all(self) -> list[dict]:
        """Get all job descriptions ordered by creation date."""
        rows = self.session.query(JobDescription).order_by(JobDescription.id.desc()).all()
        return [
            {
                "id": row.id,
                "title": row.title,
                "created_at": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else None,
            }
            for row in rows
        ]

    def delete(self, job_id: int) -> bool:
        """Delete a job description by ID. Returns True if deleted."""
        row = self.get_by_id(job_id)
        if row is None:
            return False
        self.session.delete(row)
        return True
