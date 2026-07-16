"""Tests for skill gap analysis and salary estimation schemas."""
from app.schemas import (
    ResumeData,
    ContactInfo,
    ExperienceItem,
    EducationItem,
    SkillGapItem,
    SkillGapResult,
    SalaryEstimate,
)


def _resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        summary="Backend developer.",
        skills=["Python", "SQL", "Docker", "AWS"],
        experience=[
            ExperienceItem(
                title="Developer",
                company="Acme",
                start_date="2020",
                end_date="Present",
                bullets=["Built things"],
            )
        ],
        education=[EducationItem(degree="BSc CS", institution="MIT", year="2019")],
    )


def test_skill_gap_result_model():
    result = SkillGapResult(
        target_role="Senior Engineer",
        market_skills=["Python", "Go", "Kubernetes", "AWS"],
        your_skills=["Python", "SQL", "Docker", "AWS"],
        matched=["Python", "AWS"],
        missing=[
            SkillGapItem(
                skill="Go",
                importance="high",
                recommendation="Learn Go via official tour",
            )
        ],
        summary="Good foundation, missing Go and Kubernetes.",
    )
    assert result.target_role == "Senior Engineer"
    assert len(result.matched) == 2
    assert len(result.missing) == 1
    assert result.missing[0].importance == "high"


def test_skill_gap_result_defaults():
    result = SkillGapResult()
    assert result.target_role == ""
    assert result.market_skills == []
    assert result.matched == []
    assert result.missing == []
    assert result.summary == ""


def test_salary_estimate_model():
    est = SalaryEstimate(
        role="Software Engineer",
        location="Kuala Lumpur, Malaysia",
        experience_years="Mid-level (3-6 years)",
        salary_range="60000 - 120000",
        salary_min="60000",
        salary_max="120000",
        currency="MYR",
        factors=["Python skills", "Cloud experience"],
        notes="Market rate for mid-level engineers in KL.",
    )
    assert est.role == "Software Engineer"
    assert est.currency == "MYR"
    assert len(est.factors) == 2


def test_salary_estimate_defaults():
    est = SalaryEstimate()
    assert est.role == ""
    assert est.salary_range == ""
    assert est.factors == []


def test_resume_skills_used_in_gap():
    resume = _resume()
    assert "Python" in resume.skills
    assert "Go" not in resume.skills
