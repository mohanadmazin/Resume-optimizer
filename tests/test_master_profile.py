"""Tests for Master Career Profile — repository + domain models."""
from __future__ import annotations

import pytest

from app.database.engine import engine
from app.database.models import Base
from app.database.session import get_session
from sqlalchemy import text
from app.domain.master_profile import (
    CareerEntry,
    EducationEntry,
    MasterCareerProfile,
    ResumeCompilerConfig,
    EmphasisType,
    CompiledResume,
    CompiledSection,
    CompiledItem,
    CompiledExclusion,
)
from app.database.repositories.master_profile_repository import MasterProfileRepository


@pytest.fixture(autouse=True)
def _reset_db():
    """Ensure tables exist and data is clean for each test."""
    Base.metadata.create_all(engine)
    with get_session() as session:
        session.execute(text("DELETE FROM master_profiles"))
    yield
    with get_session() as session:
        session.execute(text("DELETE FROM master_profiles"))


def _sample_profile(name: str = "Test Profile") -> MasterCareerProfile:
    return MasterCareerProfile(
        name=name,
        entries=[
            CareerEntry(
                role="Senior Engineer",
                company="Acme Corp",
                date_from="2020-01",
                date_to="2024-01",
                bullets=["Led team of 5", "Built API v2"],
                fact_ids=[1, 2],
                tags=["python", "leadership"],
            ),
            CareerEntry(
                role="Engineer",
                company="Beta Inc",
                date_from="2017-06",
                date_to="2019-12",
                bullets=["Developed web apps"],
                fact_ids=[3],
                tags=["javascript", "react"],
            ),
        ],
        skills=["Python", "JavaScript", "React", "PostgreSQL"],
        education=[
            EducationEntry(degree="BS Computer Science", institution="MIT", year="2017"),
        ],
        certifications=["AWS Solutions Architect"],
        summary="Experienced engineer.",
        headline="Senior Software Engineer",
    )


class TestMasterProfileDomain:
    def test_career_entry_defaults(self):
        entry = CareerEntry()
        assert entry.role == ""
        assert entry.bullets == []
        assert entry.fact_ids == []

    def test_master_profile_roundtrip(self):
        profile = _sample_profile()
        data = profile.model_dump()
        restored = MasterCareerProfile.model_validate(data)
        assert restored.name == profile.name
        assert len(restored.entries) == 2
        assert restored.entries[0].role == "Senior Engineer"
        assert restored.skills == ["Python", "JavaScript", "React", "PostgreSQL"]

    def test_compiler_config_defaults(self):
        config = ResumeCompilerConfig()
        assert config.max_pages == 1
        assert config.emphasis == EmphasisType.BALANCED
        assert config.exclude_roles == []

    def test_compiled_resume_model(self):
        compiled = CompiledResume(
            sections=[
                CompiledSection(
                    section_name="Experience",
                    items=[
                        CompiledItem(text="Led team", relevance_score=0.9),
                    ],
                    budget_pct=0.3,
                )
            ],
            exclusions=[
                CompiledExclusion(text="Old role", reason="Low relevance"),
            ],
            total_items=1,
        )
        assert compiled.total_items == 1
        assert len(compiled.exclusions) == 1
        assert compiled.exclusions[0].reason == "Low relevance"


class TestMasterProfileRepository:
    def test_save_and_get(self):
        repo = MasterProfileRepository()
        profile = _sample_profile()
        pid = repo.save(profile)
        assert pid > 0

        loaded = repo.get(pid)
        assert loaded is not None
        assert loaded.name == "Test Profile"
        assert len(loaded.entries) == 2
        assert loaded.entries[0].company == "Acme Corp"
        assert loaded.skills == ["Python", "JavaScript", "React", "PostgreSQL"]

    def test_upsert_updates_existing(self):
        repo = MasterProfileRepository()
        profile = _sample_profile("Original")
        pid = repo.save(profile)
        assert pid > 0

        profile.name = "Updated"
        profile.skills.append("TypeScript")
        pid2 = repo.save(profile)
        assert pid2 == pid

        loaded = repo.get(pid)
        assert loaded is not None
        assert loaded.name == "Updated"
        assert "TypeScript" in loaded.skills

    def test_get_default_returns_first(self):
        repo = MasterProfileRepository()
        repo.save(_sample_profile("First"))

        loaded = repo.get()
        assert loaded is not None
        assert loaded.name == "First"

    def test_delete(self):
        repo = MasterProfileRepository()
        pid = repo.save(_sample_profile())
        assert repo.delete(pid) is True
        assert repo.get(pid) is None

    def test_delete_nonexistent(self):
        repo = MasterProfileRepository()
        assert repo.delete(9999) is False

    def test_list_all(self):
        repo = MasterProfileRepository()
        repo.save(_sample_profile("P1"))
        all_profiles = repo.list_all()
        assert len(all_profiles) == 1
        assert all_profiles[0].name == "P1"

    def test_get_id(self):
        repo = MasterProfileRepository()
        assert repo.get_id() is None
        pid = repo.save(_sample_profile())
        assert repo.get_id() == pid

    def test_empty_profile_roundtrip(self):
        repo = MasterProfileRepository()
        profile = MasterCareerProfile(name="Empty")
        pid = repo.save(profile)
        loaded = repo.get(pid)
        assert loaded is not None
        assert loaded.entries == []
        assert loaded.skills == []
