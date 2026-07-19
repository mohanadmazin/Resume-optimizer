"""Tests for app/services/diff_highlight.py — word-level and bullet-level diff rendering."""
from __future__ import annotations

from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeData,
)
from app.services.diff_highlight import (
    HIGHLIGHT,
    _diff_bullets_html,
    _diff_words_html,
    resume_diff_html,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_resume(**overrides) -> ResumeData:
    defaults = dict(
        contact=ContactInfo(name="Alice", email="alice@test.com", phone="555-1234"),
        headline="Senior Software Engineer",
        summary="Experienced engineer with 5 years in Python.",
        skills=["python", "sql", "docker"],
        experience=[
            ExperienceItem(
                title="Engineer",
                company="Acme",
                start_date="2020",
                end_date="2024",
                bullets=["Built the data pipeline", "Led a team of 3 engineers"],
            )
        ],
        education=[EducationItem(degree="BS CS", institution="MIT", year="2019")],
        projects=[ProjectItem(title="ProjectX", description="A cool tool")],
        certifications=["AWS Solutions Architect"],
        languages=["English"],
    )
    defaults.update(overrides)
    return ResumeData(**defaults)


# ── _diff_words_html tests ─────────────────────────────────────────────────

def test_identical_words_no_highlighting():
    result = _diff_words_html("hello world", "hello world")
    assert HIGHLIGHT.split("{")[0] not in result
    assert result.strip() == "hello world"


def test_changed_words_are_highlighted():
    result = _diff_words_html("hello world", "hello earth")
    assert "earth" in result
    assert HIGHLIGHT.split("{")[0] in result


def test_added_words_are_highlighted():
    result = _diff_words_html("hello", "hello beautiful world")
    assert "beautiful" in result
    assert "world" in result
    assert HIGHLIGHT.split("{")[0] in result


def test_removed_words_not_in_output():
    result = _diff_words_html("hello beautiful world", "hello")
    assert "beautiful" not in result
    assert "world" not in result


def test_empty_old_highlights_everything():
    result = _diff_words_html("", "new text here")
    assert "new" in result
    assert "text" in result
    assert HIGHLIGHT.split("{")[0] in result


def test_empty_new_returns_empty():
    result = _diff_words_html("old text", "")
    assert result.strip() == ""


# ── _diff_bullets_html tests ───────────────────────────────────────────────

def test_identical_bullets_no_highlighting():
    old = ["Built the pipeline", "Led a team"]
    new = ["Built the pipeline", "Led a team"]
    result = _diff_bullets_html(old, new)
    assert len(result) == 2
    assert HIGHLIGHT.split("{")[0] not in result[0]
    assert HIGHLIGHT.split("{")[0] not in result[1]


def test_replaced_bullet_has_word_diff():
    old = ["Built the pipeline"]
    new = ["Built the data warehouse"]
    result = _diff_bullets_html(old, new)
    assert len(result) == 1
    assert "data warehouse" in result[0]
    assert HIGHLIGHT.split("{")[0] in result[0]


def test_added_bullet_is_highlighted():
    old = ["Built the pipeline"]
    new = ["Built the pipeline", "Led a team of 5"]
    result = _diff_bullets_html(old, new)
    assert len(result) == 2
    assert HIGHLIGHT.split("{")[0] in result[1]


def test_deleted_bullet_not_in_output():
    old = ["Built the pipeline", "Led a team"]
    new = ["Built the pipeline"]
    result = _diff_bullets_html(old, new)
    assert len(result) == 1


# ── resume_diff_html tests ─────────────────────────────────────────────────

def test_identical_resumes_no_highlighting():
    r = _make_resume()
    html = resume_diff_html(r, r)
    assert HIGHLIGHT.split("{")[0] not in html


def test_changed_summary_is_highlighted():
    original = _make_resume()
    optimized = _make_resume(summary="Senior engineer with 8 years of experience.")
    html = resume_diff_html(original, optimized)
    assert HIGHLIGHT.split("{")[0] in html
    assert "8" in html
    assert "experience" in html


def test_changed_headline_is_highlighted():
    original = _make_resume()
    optimized = _make_resume(headline="Principal Software Engineer")
    html = resume_diff_html(original, optimized)
    assert HIGHLIGHT.split("{")[0] in html
    assert "Principal" in html


def test_changed_bullets_are_highlighted():
    original = _make_resume()
    new_exp = ExperienceItem(
        title="Engineer",
        company="Acme",
        start_date="2020",
        end_date="2024",
        bullets=["Built the data warehouse", "Mentored 5 junior engineers"],
    )
    optimized = _make_resume(experience=[new_exp])
    html = resume_diff_html(original, optimized)
    assert HIGHLIGHT.split("{")[0] in html
    assert "warehouse" in html
    assert "Mentored" in html


def test_html_is_well_formed():
    original = _make_resume()
    optimized = _make_resume(summary="Updated summary text.")
    html = resume_diff_html(original, optimized)
    assert html.strip().startswith("<html>")
    assert html.strip().endswith("</html>")
    assert "<head>" in html
    assert "<body>" in html


def test_contact_info_rendered_plain():
    original = _make_resume()
    optimized = _make_resume()
    html = resume_diff_html(original, optimized)
    assert "alice@test.com" in html
    assert "555-1234" in html


def test_skills_rendered_plain():
    original = _make_resume()
    optimized = _make_resume()
    html = resume_diff_html(original, optimized)
    assert "python" in html
    assert "sql" in html
    assert "docker" in html


def test_education_rendered():
    original = _make_resume()
    optimized = _make_resume()
    html = resume_diff_html(original, optimized)
    assert "MIT" in html
    assert "BS CS" in html


def test_certifications_rendered():
    original = _make_resume()
    optimized = _make_resume()
    html = resume_diff_html(original, optimized)
    assert "AWS Solutions Architect" in html
