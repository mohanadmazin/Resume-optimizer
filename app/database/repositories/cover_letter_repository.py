"""Repository for cover letter CRUD."""
import logging
from datetime import datetime

from app.database.models import CoverLetter
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CoverLetterRepository(BaseRepository):
    """CRUD for cover letters."""

    def create(
        self,
        resume_id: int,
        job_id: int,
        content: str,
        model: str = "",
    ) -> int:
        row = CoverLetter(
            resume_id=resume_id,
            job_id=job_id,
            content=content,
            model=model,
        )
        self.add(row)
        self.flush()
        logger.info("Created cover letter %d", row.id)
        return row.id

    def get(self, cl_id: int) -> CoverLetter | None:
        return (
            self.session.query(CoverLetter)
            .filter(CoverLetter.id == cl_id)
            .first()
        )

    def update(self, cl_id: int, content: str) -> bool:
        row = self.get(cl_id)
        if row is None:
            return False
        row.content = content
        row.updated_at = datetime.utcnow()
        return True

    def list_all(self) -> list[CoverLetter]:
        return (
            self.session.query(CoverLetter)
            .order_by(CoverLetter.created_at.desc())
            .all()
        )

    def list_for_resume(self, resume_id: int) -> list[CoverLetter]:
        return (
            self.session.query(CoverLetter)
            .filter(CoverLetter.resume_id == resume_id)
            .order_by(CoverLetter.created_at.desc())
            .all()
        )

    def search(
        self,
        query: str = "",
        resume_id: int | None = None,
    ) -> list[CoverLetter]:
        q = self.session.query(CoverLetter)
        if resume_id is not None:
            q = q.filter(CoverLetter.resume_id == resume_id)
        if query:
            q = q.filter(CoverLetter.content.ilike(f"%{query}%"))
        return q.order_by(CoverLetter.created_at.desc()).all()

    def delete(self, cl_id: int) -> bool:
        row = self.get(cl_id)
        if row is None:
            return False
        self.session.delete(row)
        return True
