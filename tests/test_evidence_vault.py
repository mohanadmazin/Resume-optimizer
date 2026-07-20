"""Tests for Career Evidence Vault — service + repositories."""
from __future__ import annotations


import pytest

from app.database.engine import engine
from app.database.models import Base
from app.database.session import get_session
from sqlalchemy import text
from app.domain.evidence import (
    CareerFact,
    EvidenceSource,
    FactConfidence,
    FactType,
    SourceType,
)
from app.services.evidence_vault import EvidenceVault


@pytest.fixture(autouse=True)
def _reset_db():
    """Ensure tables exist and data is clean for each test."""
    Base.metadata.create_all(engine)
    with get_session() as session:
        session.execute(text("DELETE FROM fact_verification_events"))
        session.execute(text("DELETE FROM content_fact_links"))
        session.execute(text("DELETE FROM career_fact_sources"))
        session.execute(text("DELETE FROM evidence_sources"))
        session.execute(text("DELETE FROM career_facts"))
    yield
    with get_session() as session:
        session.execute(text("DELETE FROM fact_verification_events"))
        session.execute(text("DELETE FROM content_fact_links"))
        session.execute(text("DELETE FROM career_fact_sources"))
        session.execute(text("DELETE FROM evidence_sources"))
        session.execute(text("DELETE FROM career_facts"))


class TestFactCRUD:
    def test_add_and_get(self):
        vault = EvidenceVault()
        fid = vault.add_fact(
            CareerFact(
                statement="Led a team of 5 engineers to deliver API v2",
                employer="Acme Corp",
            )
        )
        assert fid > 0
        fact = vault.get_fact(fid)
        assert fact is not None
        assert fact.statement == "Led a team of 5 engineers to deliver API v2"
        assert fact.fact_type == FactType.TEAM
        assert fact.employer == "Acme Corp"

    def test_add_empty_statement_raises(self):
        vault = EvidenceVault()
        with pytest.raises(ValueError, match="empty"):
            vault.add_fact(CareerFact(statement=""))

    def test_list_all_filters(self):
        vault = EvidenceVault()
        vault.add_fact(CareerFact(statement="Saved $1M in costs", employer="A"))
        vault.add_fact(CareerFact(statement="Built React dashboard", employer="B"))
        vault.add_fact(CareerFact(statement="Won tech award", employer="A"))

        all_facts = vault.list_facts()
        assert len(all_facts) == 3

        a_facts = vault.list_facts(employer="A")
        assert len(a_facts) == 2

        tech_facts = vault.list_facts(fact_type="technology")
        assert len(tech_facts) == 1

    def test_update(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Old statement"))
        vault.update_fact(fid, {"employer": "New Co"})
        fact = vault.get_fact(fid)
        assert fact.employer == "New Co"

    def test_delete(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="To be deleted"))
        assert vault.delete_fact(fid) is True
        assert vault.get_fact(fid) is None


class TestAutoClassification:
    def test_metric_detection(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Revenue grew to $2M with 30% profit margin"))
        fact = vault.get_fact(fid)
        assert fact.fact_type == FactType.METRIC
        assert len(fact.metrics_json) > 0

    def test_achievement_detection(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Achieved record quarterly revenue"))
        fact = vault.get_fact(fid)
        assert fact.fact_type == FactType.ACHIEVEMENT

    def test_technology_tagging(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Built Python API with PostgreSQL and Redis"))
        fact = vault.get_fact(fid)
        assert "python" in fact.tags
        assert "postgresql" in fact.tags
        assert "redis" in fact.tags


class TestVerification:
    def test_verify_and_reject(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Verified fact"))
        assert vault.verify_fact(fid, FactConfidence.USER_CONFIRMED) is True
        fact = vault.get_fact(fid)
        assert fact.confidence == FactConfidence.USER_CONFIRMED

        assert vault.reject_fact(fid, "Inaccurate") is True
        fact = vault.get_fact(fid)
        assert fact.confidence == FactConfidence.CONTRADICTORY

    def test_verification_history(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Tracked fact"))
        vault.verify_fact(fid, FactConfidence.USER_CONFIRMED)
        vault.reject_fact(fid, "Changed mind")
        history = vault.get_verification_history(fid)
        assert len(history) == 2
        confidences = {e.new_confidence for e in history}
        assert FactConfidence.USER_CONFIRMED in confidences
        assert FactConfidence.CONTRADICTORY in confidences


class TestSources:
    def test_add_and_link_source(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Fact from source"))
        sid = vault.add_source(
            EvidenceSource(
                source_type=SourceType.DOCUMENT,
                name="Performance Review 2024",
            )
        )
        assert vault.link_source(fid, sid) is True
        fws = vault.get_fact_with_sources(fid)
        assert fws is not None
        assert len(fws.sources) == 1
        assert fws.sources[0].name == "Performance Review 2024"

    def test_unlink_source(self):
        vault = EvidenceVault()
        fid = vault.add_fact(CareerFact(statement="Linked fact"))
        sid = vault.add_source(EvidenceSource(name="Doc"))
        vault.link_source(fid, sid)
        assert vault.unlink_source(fid, sid) is True
        fws = vault.get_fact_with_sources(fid)
        assert len(fws.sources) == 0


class TestSearch:
    def test_search_facts(self):
        vault = EvidenceVault()
        vault.add_fact(CareerFact(statement="Improved system performance by 40%"))
        vault.add_fact(CareerFact(statement="Built React dashboard for clients"))
        results = vault.search_facts("performance")
        assert len(results) == 1
        assert "performance" in results[0].statement.lower()


class TestImport:
    def test_import_from_resume(self):
        vault = EvidenceVault()
        text = (
            "Senior Engineer at Acme Corp\n"
            "• Led team of 8 engineers to deliver microservices platform\n"
            "• Reduced latency by 40% through caching with Redis\n"
            "• Managed $2M annual budget"
        )
        ids = vault.import_facts_from_resume(text, employer="Acme")
        assert len(ids) >= 3
        for fid in ids:
            fact = vault.get_fact(fid)
            assert fact.employer == "Acme"


class TestStats:
    def test_vault_stats(self):
        vault = EvidenceVault()
        vault.add_fact(CareerFact(statement="Fact 1"))
        vault.add_fact(CareerFact(statement="Fact 2"))
        stats = vault.get_vault_stats()
        assert stats["total_facts"] == 2


class TestImportFromResumeData:
    def test_import_experience_bullets(self):
        from app.domain.resume import ResumeData, ExperienceItem
        vault = EvidenceVault()
        resume = ResumeData(
            experience=[
                ExperienceItem(
                    title="Engineer",
                    company="Acme",
                    start_date="2020-01",
                    end_date="2024-01",
                    bullets=["Led team of 5 to deliver project", "Built API v2"],
                ),
            ],
        )
        ids = vault.import_from_resume_data(resume)
        assert len(ids) == 2
        facts = vault.list_facts()
        assert any("Led team" in f.statement for f in facts)
        assert facts[0].employer == "Acme"

    def test_import_skills(self):
        from app.domain.resume import ResumeData
        vault = EvidenceVault()
        resume = ResumeData(skills=["Python", "Docker"])
        ids = vault.import_from_resume_data(resume)
        assert len(ids) == 2
        facts = vault.list_facts()
        assert any("Python" in f.statement for f in facts)

    def test_import_education(self):
        from app.domain.resume import ResumeData, EducationItem
        vault = EvidenceVault()
        resume = ResumeData(
            education=[EducationItem(degree="BS CS", institution="MIT", year="2019")],
        )
        ids = vault.import_from_resume_data(resume)
        assert len(ids) == 1
        fact = vault.get_fact(ids[0])
        assert "MIT" in fact.statement

    def test_import_certifications(self):
        from app.domain.resume import ResumeData
        vault = EvidenceVault()
        resume = ResumeData(certifications=["AWS Solutions Architect"])
        ids = vault.import_from_resume_data(resume)
        assert len(ids) == 1

    def test_deduplication(self):
        from app.domain.resume import ResumeData, ExperienceItem
        vault = EvidenceVault()
        vault.add_fact(CareerFact(
            statement="Led team of 5 to deliver project",
            confidence=FactConfidence.VERIFIED,
        ))
        resume = ResumeData(
            experience=[
                ExperienceItem(bullets=["Led team of 5 to deliver project"]),
            ],
        )
        ids = vault.import_from_resume_data(resume)
        assert len(ids) == 0  # Already exists

    def test_import_invalid_data_returns_empty(self):
        vault = EvidenceVault()
        ids = vault.import_from_resume_data("not a resume")
        assert ids == []

    def test_import_projects(self):
        from app.domain.resume import ResumeData, ProjectItem
        vault = EvidenceVault()
        resume = ResumeData(
            projects=[
                ProjectItem(
                    title="Open Source Tool",
                    description="A tool for X",
                    bullets=["Built with Python"],
                ),
            ],
        )
        ids = vault.import_from_resume_data(resume)
        assert len(ids) == 1


class TestBuildMasterProfile:
    def test_builds_profile_from_facts(self):
        vault = EvidenceVault()
        vault.add_fact(CareerFact(
            statement="Built API v2",
            employer="Acme",
            date_from="2020-01",
            date_to="2024-01",
        ))
        vault.add_fact(CareerFact(
            statement="Led team of 5",
            employer="Acme",
        ))
        vault.add_fact(CareerFact(
            statement="Used Python for scripting",
            fact_type=FactType.TECHNOLOGY,
            tags=["python"],
        ))

        profile = vault.build_master_profile()
        assert len(profile.entries) >= 1
        acme_entry = next(e for e in profile.entries if e.company == "Acme")
        assert len(acme_entry.bullets) == 2
        assert "python" in profile.skills

    def test_certifications_extracted(self):
        vault = EvidenceVault()
        vault.add_fact(CareerFact(
            statement="AWS Solutions Architect",
            fact_type=FactType.CERTIFICATION,
        ))
        profile = vault.build_master_profile()
        assert "AWS Solutions Architect" in profile.certifications

    def test_empty_vault(self):
        vault = EvidenceVault()
        profile = vault.build_master_profile()
        assert profile.entries == []
        assert profile.skills == []

    def test_orphan_facts_grouped(self):
        vault = EvidenceVault()
        vault.add_fact(CareerFact(statement="Random fact without employer"))
        profile = vault.build_master_profile()
        assert len(profile.entries) == 1
        assert profile.entries[0].company == ""
