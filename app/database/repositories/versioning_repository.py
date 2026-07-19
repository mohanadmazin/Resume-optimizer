"""Repository for resume versioning, targeting sessions, and suggestions."""
import logging

from sqlalchemy import func

from app.database.models import (
    ResumeVersion,
    SuggestionRecord,
    TargetingSession,
)
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class VersioningRepository(BaseRepository):
    """Handles immutable resume versions and targeting sessions."""

    def create_version(
        self,
        resume_id: int,
        data_json: str,
        change_summary: str = "",
    ) -> int:
        """Create a new immutable resume version.

        Version numbers are sequential starting at 1.
        """
        max_version = (
            self.session.query(func.max(ResumeVersion.version_number))
            .filter(ResumeVersion.resume_id == resume_id)
            .scalar()
        )
        next_version = (max_version or 0) + 1

        row = ResumeVersion(
            resume_id=resume_id,
            version_number=next_version,
            data_json=data_json,
            change_summary=change_summary,
        )
        self.add(row)
        self.flush()
        logger.info(
            "Created resume version %d for resume %d", next_version, resume_id
        )
        return row.id

    def get_version(self, version_id: int) -> ResumeVersion | None:
        return (
            self.session.query(ResumeVersion)
            .filter(ResumeVersion.id == version_id)
            .first()
        )

    def get_latest_version(self, resume_id: int) -> ResumeVersion | None:
        return (
            self.session.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )

    def get_versions(self, resume_id: int) -> list[ResumeVersion]:
        return (
            self.session.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.asc())
            .all()
        )

    def create_targeting_session(
        self,
        resume_version_id: int,
        job_id: int,
        requirements_json: str,
        score_report_json: str,
    ) -> int:
        row = TargetingSession(
            resume_version_id=resume_version_id,
            job_id=job_id,
            requirements_json=requirements_json,
            score_report_json=score_report_json,
        )
        self.add(row)
        self.flush()
        logger.info(
            "Created targeting session %d (version=%d, job=%d)",
            row.id, resume_version_id, job_id,
        )
        return row.id

    def get_targeting_session(self, session_id: int) -> TargetingSession | None:
        return (
            self.session.query(TargetingSession)
            .filter(TargetingSession.id == session_id)
            .first()
        )

    def get_targeting_sessions_for_version(
        self, resume_version_id: int
    ) -> list[TargetingSession]:
        return (
            self.session.query(TargetingSession)
            .filter(TargetingSession.resume_version_id == resume_version_id)
            .order_by(TargetingSession.created_at.desc())
            .all()
        )

    def add_suggestion(
        self,
        targeting_session_id: int,
        document_path: str,
        original_text: str,
        suggested_text: str,
        evidence_json: str,
    ) -> int:
        row = SuggestionRecord(
            targeting_session_id=targeting_session_id,
            document_path=document_path,
            original_text=original_text,
            suggested_text=suggested_text,
            evidence_json=evidence_json,
            status="pending",
        )
        self.add(row)
        self.flush()
        return row.id

    def update_suggestion_status(
        self, suggestion_id: int, status: str
    ) -> bool:
        row = (
            self.session.query(SuggestionRecord)
            .filter(SuggestionRecord.id == suggestion_id)
            .first()
        )
        if row is None:
            return False
        row.status = status
        return True

    def get_suggestions(
        self, targeting_session_id: int
    ) -> list[SuggestionRecord]:
        return (
            self.session.query(SuggestionRecord)
            .filter(SuggestionRecord.targeting_session_id == targeting_session_id)
            .order_by(SuggestionRecord.id.asc())
            .all()
        )
