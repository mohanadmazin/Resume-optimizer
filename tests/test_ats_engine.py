from app.schemas import ContactInfo, ExperienceItem, ResumeData
from app.services.ats_engine import analyze, extract_keywords, extract_required_skills, _KNOWN_SKILLS, _skill_matches

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


# ── Structured-only scoring (Bug #4) ────────────────────────────────────────


def test_analyze_uses_structured_data_over_raw_text():
    """ATS scoring should prefer structured resume fields over raw_text."""
    resume = ResumeData(
        contact=ContactInfo(name="Jane", email="jane@test.com"),
        summary="Python developer",
        skills=["Python", "Docker"],
        experience=[
            ExperienceItem(title="Dev", company="X", bullets=["Built APIs with Docker"])
        ],
        raw_text="",  # Empty raw_text — structured data should still work
    )
    result = analyze(resume, JD)
    # Should still find matches from structured fields
    assert result.ats_score > 0
    assert result.skills_match_pct > 0


def test_analyze_empty_structured_falls_back_to_raw_text():
    """When structured fields are empty, raw_text should be used as fallback."""
    resume = ResumeData(
        contact=ContactInfo(name="Jane"),
        raw_text="Python Django Docker AWS PostgreSQL REST APIs experience",
    )
    result = analyze(resume, JD)
    assert result.ats_score > 0


# ── Known skills extraction (Bug #20) ───────────────────────────────────────


def test_extract_required_skills_filters_to_known():
    """Only known technical skills should be extracted from JDs."""
    jd = "Looking for Python developer. Must be proactive and a team player."
    skills = extract_required_skills(jd)
    assert "python" in skills
    # Generic words should NOT be extracted as skills
    assert "proactive" not in skills
    assert "team" not in skills
    assert "player" not in skills


def test_extract_required_skills_includes_aliases():
    """Skills with known aliases should be extracted."""
    jd = "Experience with JS, React, K8s, and Terraform required."
    skills = extract_required_skills(jd)
    assert "js" in skills or "react" in skills or "k8s" in skills


def test_extract_required_skills_empty_jd():
    assert extract_required_skills("") == []


def test_known_skills_vocabulary_size():
    """The known skills vocabulary should be a reasonable size."""
    assert len(_KNOWN_SKILLS) > 50


# ── Skill matching with aliases ──────────────────────────────────────────────


def test_skill_matches_with_alias():
    assert _skill_matches("I know javascript well", "js")
    assert _skill_matches("I know javascript well", "javascript")
    assert _skill_matches("Used kubernetes in production", "k8s")
    assert _skill_matches("Used kubernetes in production", "kubernetes")


def test_skill_matches_returns_false_for_missing():
    assert _skill_matches("I know Python well", "rust") is False


# ── Suggestions ──────────────────────────────────────────────────────────────


def test_suggests_summary_when_missing():
    resume = ResumeData(
        contact=ContactInfo(name="X", email="x@x.com"),
        skills=["Python"],
    )
    result = analyze(resume, JD)
    assert any("summary" in s.lower() for s in result.suggestions)


def test_suggests_bullets_when_missing():
    resume = ResumeData(
        contact=ContactInfo(name="X", email="x@x.com"),
        summary="Developer",
        skills=["Python"],
        experience=[ExperienceItem(title="Dev", company="Y", bullets=[])],
    )
    result = analyze(resume, JD)
    assert any("bullet" in s.lower() for s in result.suggestions)


def test_suggests_quantify_when_no_numbers():
    resume = ResumeData(
        contact=ContactInfo(name="X", email="x@x.com"),
        summary="Developer",
        skills=["Python"],
        experience=[ExperienceItem(title="Dev", company="Y", bullets=["Did stuff"])],
    )
    result = analyze(resume, JD)
    assert any("number" in s.lower() or "quantify" in s.lower() for s in result.suggestions)
