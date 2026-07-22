"""Repository for resume CRUD operations."""
import hashlib
import logging

from app.database.models import Resume
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ResumeRepository(BaseRepository):
    """Handles resume database operations."""

    def save(
        self,
        name: str,
        data_json: str,
        raw_text: str = "",
        source_type: str = "import",
        source_filename: str = "",
    ) -> int:
        """Save a new resume and return its ID."""
        source_hash = hashlib.sha256(raw_text.encode()).hexdigest() if raw_text else ""
        row = Resume(
            name=name,
            data_json=data_json,
            raw_text=raw_text,
            source_type=source_type,
            source_filename=source_filename,
            source_hash=source_hash,
            is_original=True,
        )
        self.add(row)
        self.flush()
        logger.debug("Saved resume id=%d name=%s", row.id, name)
        return row.id

    def get_latest(self) -> dict | None:
        """Get the most recently created resume."""
        row = self.session.query(Resume).order_by(Resume.id.desc()).first()
        if row is None:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "data_json": row.data_json,
            "raw_text": row.raw_text,
        }

    def get_by_id(self, resume_id: int) -> Resume | None:
        """Get a resume by its ID."""
        return self.session.query(Resume).filter(Resume.id == resume_id).first()

    def get_all(self) -> list[dict]:
        """Get all resumes ordered by creation date."""
        rows = self.session.query(Resume).order_by(Resume.id.desc()).all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "source_type": row.source_type or "import",
                "source_filename": row.source_filename or "",
                "created_at": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else None,
            }
            for row in rows
        ]

    def delete(self, resume_id: int) -> bool:
        """Delete a resume by ID. Returns True if deleted."""
        row = self.get_by_id(resume_id)
        if row is None:
            return False
        self.session.delete(row)
        return True

    def update(
        self,
        resume_id: int,
        data_json: str,
        *,
        name: str | None = None,
        raw_text: str | None = None,
        source_type: str | None = None,
    ) -> bool:
        """Update a saved resume while preserving its identity and history."""
        row = self.get_by_id(resume_id)
        if row is None:
            return False
        row.data_json = data_json
        if name is not None:
            row.name = name
        if raw_text is not None:
            row.raw_text = raw_text
            row.source_hash = hashlib.sha256(raw_text.encode()).hexdigest() if raw_text else ""
        if source_type is not None:
            row.source_type = source_type
        return True

    def create_variant(
        self,
        source_id: int,
        variant_label: str,
    ) -> int | None:
        """Create an independent variant copy of an existing resume.

        The variant is a full copy with name = "{original_name} ({variant_label})".
        Returns the new resume ID, or None if source not found.
        """
        source = self.get_by_id(source_id)
        if source is None:
            return None
        variant_name = f"{source.name} ({variant_label})"
        return self.save(
            name=variant_name,
            data_json=source.data_json,
            raw_text=source.raw_text,
            source_type="variant",
            source_filename=str(source_id),
        )

    def list_variants(self, source_id: int) -> list[dict]:
        """List resumes that are variants of the given resume (by source_filename)."""
        rows = (
            self.session.query(Resume)
            .filter(Resume.source_type == "variant", Resume.source_filename == str(source_id))
            .order_by(Resume.created_at.desc())
            .all()
        )
        return [
            {
                "id": row.id,
                "name": row.name,
                "created_at": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else None,
            }
            for row in rows
        ]
