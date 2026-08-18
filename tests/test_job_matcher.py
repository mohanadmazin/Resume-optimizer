"""Tests for Job Matcher — scoring a job against the Master Profile."""
from __future__ import annotations

from app.domain.evidence import CareerFact, FactConfidence, FactType
from app.domain.job_match import MatchCategory, MatchStrength
from app.domain.master_profile import CareerEntry, MasterCareerProfile
from app.services.job_matcher import match_job


def _profile(
    skills: list[str] | None = None,
    entries: list[CareerEntry] | None = None,
) -> MasterCareerProfile:
    return MasterCareerProfile(
        name="Test",
        skills=skills or ["python", "sql", "fastapi", "aws"],
        entries=entries
        or [
            CareerEntry(
                role="Senior Backend Engineer",
                company="Acme",
                date_from="2019",
                date_to="2024",
                bullets=["Built Python services"],
            )
        ],
    )


def _fact(stmt: str, fid: int = 1) -> CareerFact:
    return CareerFact(
        id=fid,
        statement=stmt,
        fact_type=FactType.ACHIEVEMENT,
        confidence=FactConfidence.VERIFIED,
    )


_JOB = (
    "Senior Python Engineer responsible for building scalable services. "
    "Must have 5 years experience. Skills: Python, SQL, AWS. "
    "Manage cloud infrastructure."
)


class TestMatchJob:
    def test_returns_six_categories(self):
        match = match_job(
            job_text=_JOB,
            job_title="Senior Python Engineer",
            profile=_profile(),
        )
        assert {cat.category for cat in match.categories} == set(MatchCategory)
        assert 0.0 <= match.overall_score <= 1.0

    def test_skills_aliases_match_canonical(self):
        match = match_job(
            job_text="Backend engineer. Skills: Python, AWS, Kubernetes.",
            job_title="Backend Engineer",
            profile=_profile(skills=["python", "amazon web services", "kubernetes"]),
        )
        skill_names = {s.skill for s in match.strengths}
        assert {"python", "aws"} <= skill_names

    def test_gaps_are_missing_skills(self):
        match = match_job(
            job_text="Engineer. Skills: Terraform, Kubernetes.",
            job_title="DevOps Engineer",
            profile=_profile(skills=["python"]),
        )
        assert {"terraform", "kubernetes"} <= {g.skill for g in match.gaps}

    def test_experience_satisfied_when_profile_years_exceed(self):
        match = match_job(
            job_text="Must have 3 years experience.",
            job_title="Engineer",
            profile=_profile(
                entries=[
                    CareerEntry(role="Eng", date_from="2018", date_to="2024")
                ]
            ),
        )
        exp = next(c for c in match.categories if c.category == MatchCategory.EXPERIENCE)
        assert exp.score == 1.0

    def test_evidence_boost_when_facts_present(self):
        match_no_facts = match_job(
            job_text=_JOB, job_title="Senior Python Engineer", profile=_profile()
        )
        match_with_facts = match_job(
            job_text=_JOB,
            job_title="Senior Python Engineer",
            profile=_profile(),
            facts=[_fact("Designed Python microservices on AWS")],
        )
        assert match_with_facts.overall_score > match_no_facts.overall_score

    def test_strong_match_recommendation(self):
        match = match_job(
            job_text="Skills: Python, SQL, AWS, Docker. Senior role.",
            job_title="Senior Backend Engineer",
            profile=_profile(
                skills=["python", "sql", "aws", "docker"],
                entries=[
                    CareerEntry(role="Senior Backend Engineer", date_from="2018", date_to="2024")
                ],
            ),
        )
        assert match.strength in (MatchStrength.STRONG, MatchStrength.GOOD)
        assert match.recommendation

    def test_weak_match_recommendation(self):
        match = match_job(
            job_text="Skills: Terraform, Kubernetes, Rust.",
            job_title="SRE",
            profile=_profile(skills=["python"]),
        )
        assert match.strength == MatchStrength.WEAK