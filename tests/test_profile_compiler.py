"""Tests for Profile Compiler — evidence ranking and resume generation."""
from __future__ import annotations

from app.domain.evidence import CareerFact, FactConfidence, FactType
from app.domain.job_requirements import JobRequirements, Requirement
from app.domain.master_profile import (
    CareerEntry,
    CompiledResume,
    EducationEntry,
    MasterCareerProfile,
    ResumeCompilerConfig,
    EmphasisType,
)
from app.services.profile_compiler import (
    compile_resume,
    rank_facts,
    _normalize,
    _tokenize,
    _parse_year,
    _seniority_level,
)


def _make_fact(
    statement: str,
    fact_type: FactType = FactType.RESPONSIBILITY,
    confidence: FactConfidence = FactConfidence.USER_CONFIRMED,
    employer: str = "",
    date_from: str = "",
    date_to: str = "",
    fact_id: int | None = None,
) -> CareerFact:
    return CareerFact(
        id=fact_id,
        statement=statement,
        fact_type=fact_type,
        confidence=confidence,
        employer=employer,
        date_from=date_from,
        date_to=date_to,
    )


def _make_job(**kwargs) -> JobRequirements:
    defaults = dict(
        required_skills=[
            Requirement(name="Python"),
            Requirement(name="AWS"),
            Requirement(name="PostgreSQL"),
        ],
        preferred_skills=[
            Requirement(name="Docker"),
            Requirement(name="Kubernetes"),
        ],
        responsibilities=["Build scalable APIs", "Lead engineering team"],
    )
    defaults.update(kwargs)
    return JobRequirements(**defaults)


def _make_profile() -> MasterCareerProfile:
    return MasterCareerProfile(
        name="Test Profile",
        entries=[
            CareerEntry(
                id=1,
                role="Senior Engineer",
                company="Acme Corp",
                date_from="2022-01",
                date_to="2024-06",
                bullets=[
                    "Led team of 8 engineers to deliver microservices on AWS",
                    "Built Python APIs with PostgreSQL serving 1M daily requests",
                    "Reduced deployment time by 60% using Docker and Kubernetes",
                ],
                fact_ids=[1, 2, 3],
                tags=["python", "aws", "leadership"],
            ),
            CareerEntry(
                id=2,
                role="Engineer",
                company="Beta Inc",
                date_from="2019-06",
                date_to="2021-12",
                bullets=[
                    "Developed React frontend applications",
                    "Wrote documentation for internal tools",
                ],
                fact_ids=[4, 5],
                tags=["javascript", "react"],
            ),
        ],
        skills=["Python", "AWS", "PostgreSQL", "Docker", "React", "JavaScript"],
        education=[
            EducationEntry(
                degree="BS Computer Science",
                institution="MIT",
                year="2019",
            ),
        ],
        certifications=["AWS Solutions Architect"],
        summary="Experienced engineer with 5+ years building scalable systems.",
        headline="Senior Software Engineer",
    )


# ── Helper tests ─────────────────────────────────────────────────────────────


class TestHelpers:
    def test_normalize(self):
        assert _normalize("Hello, World!") == "hello world"
        assert _normalize("C++ / C#") == "c++ c#"
        assert _normalize("  spaces  ") == "spaces"

    def test_tokenize(self):
        tokens = _tokenize("Built Python APIs with PostgreSQL")
        assert "built" in tokens
        assert "python" in tokens
        assert "apis" in tokens
        assert "postgresql" in tokens

    def test_parse_year(self):
        assert _parse_year("2020-01") == 2020
        assert _parse_year("2024") == 2024
        assert _parse_year("1999-12") == 1999
        assert _parse_year("no year") is None

    def test_seniority_level(self):
        assert _seniority_level("Senior Software Engineer") == 3
        assert _seniority_level("Principal Architect") == 4
        assert _seniority_level("Junior Developer") == 1
        assert _seniority_level("VP of Engineering") == 5
        assert _seniority_level("Staff Engineer") == 4


# ── Evidence ranking tests ──────────────────────────────────────────────────


class TestRankFacts:
    def test_exact_keyword_match(self):
        facts = [
            _make_fact("Built Python web applications", fact_id=1),
            _make_fact("Managed office supplies", fact_id=2),
        ]
        job = _make_job(
            required_skills=[Requirement(name="Python")],
            preferred_skills=[],
        )
        ranked = rank_facts(facts, job)
        assert ranked[0][0].id == 1
        assert ranked[0][1] > ranked[1][1]

    def test_related_skill_match(self):
        facts = [
            _make_fact("Used Amazon Web Services for cloud deployment", fact_id=1),
            _make_fact("Wrote documentation", fact_id=2),
        ]
        job = _make_job(
            required_skills=[Requirement(name="AWS")],
            preferred_skills=[],
        )
        ranked = rank_facts(facts, job)
        assert ranked[0][0].id == 1

    def test_recency_bonus(self):
        facts = [
            _make_fact("Built APIs", date_to="2024", fact_id=1),
            _make_fact("Built APIs", date_to="2018", fact_id=2),
        ]
        job = _make_job()
        ranked = rank_facts(facts, job, reference_year=2024)
        assert ranked[0][0].id == 1
        assert ranked[0][1] > ranked[1][1]

    def test_fact_type_achievement_bonus(self):
        facts = [
            _make_fact("Achieved 99.9% uptime", fact_type=FactType.ACHIEVEMENT, fact_id=1),
            _make_fact("Maintained servers", fact_type=FactType.RESPONSIBILITY, fact_id=2),
        ]
        job = _make_job()
        ranked = rank_facts(facts, job)
        assert ranked[0][0].id == 1

    def test_confidence_multiplier(self):
        facts = [
            _make_fact("Built APIs", confidence=FactConfidence.VERIFIED, fact_id=1),
            _make_fact("Built APIs", confidence=FactConfidence.UNSUPPORTED, fact_id=2),
        ]
        job = _make_job()
        ranked = rank_facts(facts, job)
        assert ranked[0][0].id == 1
        assert ranked[0][1] > ranked[1][1]

    def test_empty_facts(self):
        ranked = rank_facts([], _make_job())
        assert ranked == []

    def test_no_matching_keywords(self):
        facts = [
            _make_fact("Cooked dinner at home", fact_id=1),
        ]
        job = _make_job()
        ranked = rank_facts(facts, job)
        assert len(ranked) == 1
        assert ranked[0][1] >= 0

    def test_multiple_keyword_matches_score_higher(self):
        facts = [
            _make_fact(
                "Built Python APIs on AWS with PostgreSQL",
                fact_id=1,
            ),
            _make_fact(
                "Used Python for scripting",
                fact_id=2,
            ),
        ]
        job = _make_job()
        ranked = rank_facts(facts, job)
        assert ranked[0][0].id == 1
        assert ranked[0][1] > ranked[1][1]

    def test_preferred_skills_score_lower_than_required(self):
        facts = [
            _make_fact("Used Docker for containerization", fact_id=1),
            _make_fact("Built Python applications", fact_id=2),
        ]
        job = _make_job(
            required_skills=[Requirement(name="Python")],
            preferred_skills=[Requirement(name="Docker")],
        )
        ranked = rank_facts(facts, job)
        assert ranked[0][0].id == 2

    def test_ranking_sorts_descending(self):
        facts = [
            _make_fact("Irrelevant fact", fact_id=1),
            _make_fact("Python developer with AWS experience", fact_id=2),
            _make_fact("PostgreSQL database administration", fact_id=3),
        ]
        job = _make_job()
        ranked = rank_facts(facts, job)
        scores = [s for _, s in ranked]
        assert scores == sorted(scores, reverse=True)


# ── Resume compilation tests ────────────────────────────────────────────────


class TestCompileResume:
    def test_basic_compilation(self):
        profile = _make_profile()
        job = _make_job()
        result = compile_resume(profile, job)

        assert isinstance(result, CompiledResume)
        assert result.total_items > 0
        assert len(result.sections) > 0
        assert result.rationale  # has rationale

    def test_experience_section_populated(self):
        profile = _make_profile()
        job = _make_job()
        result = compile_resume(profile, job)

        exp = next(s for s in result.sections if s.section_name == "Experience")
        assert len(exp.items) > 0
        assert exp.budget_pct > 0

    def test_skills_section_populated(self):
        profile = _make_profile()
        job = _make_job()
        result = compile_resume(profile, job)

        skills = next(s for s in result.sections if s.section_name == "Skills")
        assert len(skills.items) > 0

    def test_skills_prioritized_by_job_match(self):
        profile = _make_profile()
        job = _make_job(
            required_skills=[Requirement(name="Python"), Requirement(name="Rust")],
            preferred_skills=[],
        )
        result = compile_resume(profile, job)

        skills = next(s for s in result.sections if s.section_name == "Skills")
        skill_texts = [i.text for i in skills.items]
        assert "Python" in skill_texts
        # Python (required) should rank higher than React (not in job)
        python_idx = skill_texts.index("Python")
        if "React" in skill_texts:
            react_idx = skill_texts.index("React")
            assert python_idx < react_idx

    def test_education_included(self):
        profile = _make_profile()
        job = _make_job()
        result = compile_resume(profile, job)

        edu = next(s for s in result.sections if s.section_name == "Education")
        assert len(edu.items) == 1
        assert "MIT" in edu.items[0].text

    def test_certifications_included(self):
        profile = _make_profile()
        job = _make_job()
        result = compile_resume(profile, job)

        certs = next(s for s in result.sections if s.section_name == "Certifications")
        assert len(certs.items) == 1
        assert "AWS" in certs.items[0].text

    def test_summary_included(self):
        profile = _make_profile()
        job = _make_job()
        result = compile_resume(profile, job)

        summary = next(s for s in result.sections if s.section_name == "Summary")
        assert len(summary.items) == 1
        assert "5+ years" in summary.items[0].text

    def test_excludes_items_below_threshold(self):
        profile = MasterCareerProfile(
            entries=[
                CareerEntry(
                    id=1,
                    role="Irrelevant Role",
                    company="NonTech Corp",
                    bullets=["Cooked food", "Cleaned tables"],
                    fact_ids=[1, 2],
                ),
            ],
            skills=["Cooking", "Cleaning"],
        )
        job = _make_job()
        config = ResumeCompilerConfig(min_relevance_score=50.0)
        result = compile_resume(profile, job, config)
        assert len(result.exclusions) > 0

    def test_max_pages_affects_budget(self):
        profile = _make_profile()
        job = _make_job()

        small = compile_resume(profile, job, ResumeCompilerConfig(max_pages=1))
        large = compile_resume(profile, job, ResumeCompilerConfig(max_pages=2))

        assert large.total_items >= small.total_items

    def test_emphasis_changes_budget(self):
        profile = _make_profile()
        job = _make_job()

        balanced = compile_resume(profile, job, ResumeCompilerConfig(emphasis=EmphasisType.BALANCED))
        skills_focus = compile_resume(profile, job, ResumeCompilerConfig(emphasis=EmphasisType.SKILLS))

        bal_skills = next(s for s in balanced.sections if s.section_name == "Skills")
        skf_skills = next(s for s in skills_focus.sections if s.section_name == "Skills")
        assert skf_skills.budget_pct > bal_skills.budget_pct

    def test_exclude_roles_filters_entries(self):
        profile = MasterCareerProfile(
            entries=[
                CareerEntry(id=1, role="Engineer", company="A", bullets=["Built API"], fact_ids=[1]),
                CareerEntry(id=2, role="Cook", company="B", bullets=["Cooked food"], fact_ids=[2]),
            ],
            skills=["Python"],
        )
        job = _make_job()
        config = ResumeCompilerConfig(exclude_roles=["Cook"])
        result = compile_resume(profile, job, config)

        exp = next(s for s in result.sections if s.section_name == "Experience")
        for item in exp.items:
            assert "Cooked food" not in item.text

    def test_empty_profile(self):
        profile = MasterCareerProfile(name="Empty")
        job = _make_job()
        result = compile_resume(profile, job)
        assert result.total_items >= 0
        assert len(result.sections) > 0

    def test_config_used_reflected(self):
        profile = _make_profile()
        job = _make_job()
        config = ResumeCompilerConfig(max_pages=2, emphasis=EmphasisType.EXPERIENCE)
        result = compile_resume(profile, job, config)
        assert result.config_used.max_pages == 2
        assert result.config_used.emphasis == EmphasisType.EXPERIENCE

    def test_experience_items_have_rationale(self):
        profile = _make_profile()
        job = _make_job()
        result = compile_resume(profile, job)

        exp = next(s for s in result.sections if s.section_name == "Experience")
        for item in exp.items:
            assert item.rationale
            assert item.relevance_score >= 0
