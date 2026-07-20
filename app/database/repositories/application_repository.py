"""Repository for job application CRUD."""
import logging

from app.database.models import JobApplication
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

VALID_STATUSES = ("draft", "wishlist", "applied", "interview", "offer", "rejected")


class ApplicationRepository(BaseRepository):
    """CRUD for job applications."""

    def create(
        self,
        resume_id: int,
        job_id: int,
        status: str = "draft",
        notes: str = "",
    ) -> int:
        row = JobApplication(
            resume_id=resume_id,
            job_id=job_id,
            status=status,
            notes=notes,
        )
        self.add(row)
        self.flush()
        logger.info("Created application %d", row.id)
        return row.id

    def get(self, app_id: int) -> JobApplication | None:
        return (
            self.session.query(JobApplication)
            .filter(JobApplication.id == app_id)
            .first()
        )

    def list_all(self) -> list[JobApplication]:
        return (
            self.session.query(JobApplication)
            .order_by(JobApplication.created_at.desc())
            .all()
        )

    def list_for_resume(self, resume_id: int) -> list[JobApplication]:
        return (
            self.session.query(JobApplication)
            .filter(JobApplication.resume_id == resume_id)
            .order_by(JobApplication.created_at.desc())
            .all()
        )

    def update_status(self, app_id: int, status: str) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        row = self.get(app_id)
        if row is None:
            return False
        row.status = status
        if status == "applied" and row.applied_at is None:
            from datetime import datetime
            row.applied_at = datetime.utcnow()
        return True

    def update_notes(self, app_id: int, notes: str) -> bool:
        row = self.get(app_id)
        if row is None:
            return False
        row.notes = notes
        return True

    def delete(self, app_id: int) -> bool:
        row = self.get(app_id)
        if row is None:
            return False
        self.session.delete(row)
        return True
