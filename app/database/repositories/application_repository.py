"""Repository for job application CRUD."""
from __future__ import annotations

import logging
from datetime import datetime

from app.database.models import JobApplication, JobDescription, Resume
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

VALID_STATUSES = (
    "draft", "wishlist", "applied", "interview", "offer", "rejected", "withdrawn",
)


class ApplicationRepository(BaseRepository):
    """CRUD for job applications and web-ready tracker records."""

    def create(
        self,
        resume_id: int,
        job_id: int,
        status: str = "draft",
        notes: str = "",
    ) -> int:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        existing = (
            self.session.query(JobApplication)
            .filter(
                JobApplication.resume_id == resume_id,
                JobApplication.job_id == job_id,
            )
            .order_by(JobApplication.id.desc())
            .first()
        )
        if existing is not None:
            existing.status = status
            existing.notes = notes
            if status == "applied" and existing.applied_at is None:
                existing.applied_at = datetime.utcnow()
            self.flush()
            return int(existing.id)

        row = JobApplication(
            resume_id=resume_id,
            job_id=job_id,
            status=status,
            notes=notes,
        )
        if status == "applied":
            row.applied_at = datetime.utcnow()
        self.add(row)
        self.flush()
        logger.info("Created application %d", row.id)
        return int(row.id)

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

    def list_detailed(self) -> list[dict]:
        rows = (
            self.session.query(JobApplication, Resume, JobDescription)
            .join(Resume, Resume.id == JobApplication.resume_id)
            .join(JobDescription, JobDescription.id == JobApplication.job_id)
            .order_by(JobApplication.created_at.desc())
            .all()
        )
        return [
            {
                "id": application.id,
                "resume_id": application.resume_id,
                "resume_name": resume.name,
                "job_id": application.job_id,
                "job_title": job.title,
                "company": job.company or "",
                "location": job.location or "",
                "source_url": job.source_url or "",
                "status": application.status,
                "notes": application.notes or "",
                "applied_at": application.applied_at.strftime("%Y-%m-%d") if application.applied_at else "",
                "created_at": application.created_at.strftime("%Y-%m-%d %H:%M") if application.created_at else "",
            }
            for application, resume, job in rows
        ]

    def list_for_resume(self, resume_id: int) -> list[JobApplication]:
        return (
            self.session.query(JobApplication)
            .filter(JobApplication.resume_id == resume_id)
            .order_by(JobApplication.created_at.desc())
            .all()
        )

    def update(self, app_id: int, *, status: str, notes: str) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        row = self.get(app_id)
        if row is None:
            return False
        row.status = status
        row.notes = notes
        if status == "applied" and row.applied_at is None:
            row.applied_at = datetime.utcnow()
        return True

    def update_status(self, app_id: int, status: str) -> bool:
        row = self.get(app_id)
        return self.update(app_id, status=status, notes=row.notes if row else "")

    def update_notes(self, app_id: int, notes: str) -> bool:
        row = self.get(app_id)
        if row is None:
            return False
        return self.update(app_id, status=row.status, notes=notes)

    def delete(self, app_id: int) -> bool:
        row = self.get(app_id)
        if row is None:
            return False
        self.session.delete(row)
        return True
