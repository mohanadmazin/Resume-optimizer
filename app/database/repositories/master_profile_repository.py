"""Master career profile repository."""
from __future__ import annotations

import json

from app.database.session import get_session
from app.database.models import MasterProfile as MasterProfileModel
from app.domain.master_profile import MasterCareerProfile


class MasterProfileRepository:
    """CRUD for the master career profile (stored as JSON)."""

    def save(self, profile: MasterCareerProfile) -> int:
        """Upsert the master profile. Returns the profile ID."""
        with get_session() as session:
            existing = session.query(MasterProfileModel).first()
            if existing is not None:
                existing.name = profile.name or existing.name
                existing.profile_json = profile.model_dump_json()
                session.flush()
                return existing.id
            row = MasterProfileModel(
                name=profile.name or "Default Profile",
                profile_json=profile.model_dump_json(),
            )
            session.add(row)
            session.flush()
            return row.id

    def get(self, profile_id: int | None = None) -> MasterCareerProfile | None:
        """Retrieve the master profile. If profile_id is None, returns the first."""
        with get_session() as session:
            if profile_id is not None:
                row = session.get(MasterProfileModel, profile_id)
            else:
                row = session.query(MasterProfileModel).first()
            if row is None:
                return None
            return self._to_domain(row)

    def get_id(self) -> int | None:
        """Return the ID of the existing master profile, or None."""
        with get_session() as session:
            row = session.query(MasterProfileModel).first()
            return row.id if row else None

    def delete(self, profile_id: int) -> bool:
        with get_session() as session:
            row = session.get(MasterProfileModel, profile_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def list_all(self) -> list[MasterCareerProfile]:
        with get_session() as session:
            rows = (
                session.query(MasterProfileModel)
                .order_by(MasterProfileModel.created_at.desc())
                .all()
            )
            return [self._to_domain(r) for r in rows]

    @staticmethod
    def _to_domain(row: MasterProfileModel) -> MasterCareerProfile:
        try:
            data = json.loads(row.profile_json or "{}")
            profile = MasterCareerProfile.model_validate(data)
        except Exception:
            profile = MasterCareerProfile(name=row.name or "Default Profile")
        profile.id = row.id
        profile.created_at = str(row.created_at) if row.created_at else ""
        profile.updated_at = str(row.updated_at) if row.updated_at else ""
        return profile
