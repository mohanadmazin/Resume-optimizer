from app.schemas import ContactInfo, ExperienceItem, ResumeData
from app.services.ats_engine import analyze, extract_keywords

JD = """We are looking for a Python developer with Django experience.
Must know Docker, PostgreSQL and AWS. Kubernetes is a plus.
Experience with REST APIs and Python required. Python and Django used daily."""


def _resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com", phone="+1 234 567 8901"),
        summary="Python developer experienced with Django and REST APIs.",
        skills=["Python", "Django", "PostgreSQL"],
        experience=[
            ExperienceItem(
                title="Developer",
                company="X",
                bullets=["Built REST APIs with Django serving 1M users"],
            )
        ],
        raw_text="Python developer experienced with Django, PostgreSQL and REST APIs.",
    )


def test_extract_keywords():
    keywords = extract_keywords(JD)
    assert "python" in keywords
    assert "django" in keywords
    assert "the" not in keywords


def test_analyze_scores_in_range():
    result = analyze(_resume(), JD)
    assert 0 <= result.ats_score <= 100
    assert 0 <= result.keyword_match_pct <= 100
    assert 0 <= result.skills_match_pct <= 100


def test_analyze_detects_missing_keywords():
    result = analyze(_resume(), JD)
    assert result.keyword_match_pct > 0
    assert any("docker" in k for k in result.missing_keywords)
    assert result.suggestions


def test_analyze_empty_job_description():
    result = analyze(_resume(), "")
    assert 0 <= result.ats_score <= 100
