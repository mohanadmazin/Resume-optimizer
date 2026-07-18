"""Tests for the resume optimizer service (safe-only apply, apply_accepted_changes)."""

import json
from unittest.mock import MagicMock, patch

from app.domain.analysis import ATSResult
from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
from app.domain.resume import ContactInfo, ExperienceItem, ResumeData
from app.services.optimizer import _apply_change, apply_accepted_changes, optimize_resume


# ── Helpers ──────────────────────────────────────────────────────────────────


def _resume(**overrides) -> ResumeData:
    defaults = dict(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        summary="Experienced software engineer.",
        skills=["Python", "Django", "PostgreSQL"],
        experience=[
            ExperienceItem(
                title="Senior Developer",
                company="Acme Corp",
                bullets=[
                    "Built REST APIs with Django",
                    "Managed database migrations",
                ],
            )
        ],
    )
    defaults.update(overrides)
    return ResumeData(**defaults)


def _ats() -> ATSResult:
    return ATSResult(
        ats_score=65,
        keyword_match_pct=50.0,
        skills_match_pct=40.0,
        matched_keywords=["python", "django"],
        missing_keywords=["docker", "kubernetes", "aws"],
        missing_skills=["docker", "kubernetes"],
        suggestions=["Add Docker experience"],
    )


# ── _apply_change ────────────────────────────────────────────────────────────


def test_apply_change_summary():
    resume = _resume()
    change = ProposedChange(
        change_type=ChangeType.SUMMARY,
        section="Summary",
        original="Experienced software engineer.",
        rewritten="Senior software engineer with cloud expertise.",
    )
    _apply_change(resume, change)
    assert resume.summary == "Senior software engineer with cloud expertise."


def test_apply_change_headline():
    resume = _resume(headline="Software Engineer")
    change = ProposedChange(
        change_type=ChangeType.HEADLINE,
        section="Headline",
        original="Software Engineer",
        rewritten="Senior Software Engineer",
    )
    _apply_change(resume, change)
    assert resume.headline == "Senior Software Engineer"


def test_apply_change_bullet():
    resume = _resume()
    change = ProposedChange(
        change_type=ChangeType.BULLET,
        section="Senior Developer #1",
        original="Built REST APIs with Django",
        rewritten="Developed scalable REST APIs using Django serving 2M users",
        experience_index=0,
        bullet_index=0,
    )
    _apply_change(resume, change)
    assert resume.experience[0].bullets[0] == "Developed scalable REST APIs using Django serving 2M users"
    # Second bullet should be untouched
    assert resume.experience[0].bullets[1] == "Managed database migrations"


def test_apply_change_does_not_mutate_original():
    resume = _resume()
    original_summary = resume.summary
    change = ProposedChange(
        change_type=ChangeType.SUMMARY,
        section="Summary",
        original=original_summary,
        rewritten="New summary",
    )
    result = resume.model_copy(deep=True)
    _apply_change(result, change)
    # Original resume untouched
    assert resume.summary == original_summary
    # Copy was modified
    assert result.summary == "New summary"


# ── apply_accepted_changes ───────────────────────────────────────────────────


def test_apply_accepted_changes_only_applies_accepted_flagged():
    resume = _resume()
    safe = ProposedChange(
        change_type=ChangeType.SUMMARY,
        section="Summary",
        original="Experienced software engineer.",
        rewritten="Senior software engineer.",
    )
    flagged_accepted = ProposedChange(
        change_type=ChangeType.HEADLINE,
        section="Headline",
        original="Software Engineer",
        rewritten="Senior Software Engineer | Cloud Expert",
        has_new_numbers=True,
        accepted=True,
    )
    flagged_rejected = ProposedChange(
        change_type=ChangeType.BULLET,
        section="Senior Developer #1",
        original="Built REST APIs with Django",
        rewritten="Built APIs with Kubernetes",
        has_new_skills=True,
        accepted=False,
    )
    fact_result = FactGuardResult(
        safe_changes=[safe],
        flagged_changes=[flagged_accepted, flagged_rejected],
    )

    result = apply_accepted_changes(resume, fact_result)

    # Safe change applied
    assert result.summary == "Senior software engineer."
    # Accepted flagged change applied
    assert result.headline == "Senior Software Engineer | Cloud Expert"
    # Rejected flagged change NOT applied
    assert result.experience[0].bullets[0] == "Built REST APIs with Django"


def test_apply_accepted_changes_does_not_mutate_original():
    resume = _resume()
    original_summary = resume.summary
    fact_result = FactGuardResult(
        safe_changes=[
            ProposedChange(change_type=ChangeType.SUMMARY, section="s",
                           original=original_summary, rewritten="New summary")
        ],
        flagged_changes=[],
    )
    result = apply_accepted_changes(resume, fact_result)
    assert resume.summary == original_summary
    assert result.summary == "New summary"


# ── optimize_resume (mocked) ─────────────────────────────────────────────────


@patch("app.services.optimizer.FactGuard")
@patch("app.services.optimizer.OllamaClient")
def test_optimize_resume_only_applies_safe_changes(mock_client_cls, mock_guard_cls):
    """The optimizer should apply safe changes but leave flagged ones as proposals."""
    from app.domain.optimization import BulletRewrite, OptimizationAIOutput

    # Mock AI response as structured output with indexed bullet rewrites
    ai_output = OptimizationAIOutput(
        summary="Expert Python developer with 10 years.",
        bullet_rewrites=[
            BulletRewrite(
                experience_index=0,
                bullet_index=0,
                rewritten="Built Django APIs serving 2M users daily",
            ),
            BulletRewrite(
                experience_index=0,
                bullet_index=1,
                rewritten="Managed team of 5 engineers",
            ),
        ],
    )
    mock_client = mock_client_cls.return_value
    mock_client.generate_structured.return_value = ai_output

    # Mock FactGuard to return one safe and one flagged change
    safe_change = ProposedChange(
        change_type=ChangeType.SUMMARY,
        section="Summary",
        original="Experienced software engineer.",
        rewritten="Expert Python developer with 10 years.",
    )
    flagged_change = ProposedChange(
        change_type=ChangeType.BULLET,
        section="Senior Developer #1",
        original="Managed database migrations",
        rewritten="Increased revenue by 40%",
        has_new_numbers=True,
        experience_index=0,
        bullet_index=1,
    )
    mock_guard = mock_guard_cls.return_value
    mock_guard.validate.return_value = FactGuardResult(
        safe_changes=[safe_change],
        flagged_changes=[flagged_change],
    )

    result_resume, result_fact = optimize_resume(_resume(), "some jd text", _ats(), mock_client)

    # Safe change applied
    assert result_resume.summary == "Expert Python developer with 10 years."
    # Flagged change NOT applied
    assert result_fact.flagged_count == 1
    assert len(result_fact.safe_changes) == 1
