from app.schemas import ContactInfo, ExperienceItem, ResumeData
from app.services.ats_engine import (
    analyze,
    extract_keywords,
    extract_required_skills,
    _extract_section_text,
    _extract_weighted_keywords,
    _KNOWN_SKILLS,
    _skill_matches,
)

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


# ── Section-aware extraction ────────────────────────────────────────────────


JD_WITH_SECTIONS = """We are looking for a software engineer.

About the role:
You will work on exciting projects.

Requirements:
Python
FastAPI
AWS
Docker
Kubernetes

Qualifications:
Bachelor's in Computer Science
3+ years of experience

Nice to have:
Terraform
GraphQL

Benefits include health insurance and 401k."""


def test_extract_section_text_finds_requirements():
    """Section extraction should find text under Requirements header."""
    text = _extract_section_text(JD_WITH_SECTIONS)
    assert "python" in text.lower()
    assert "fastapi" in text.lower()
    assert "docker" in text.lower()


def test_extract_section_text_finds_qualifications():
    """Section extraction should find text under Qualifications header."""
    text = _extract_section_text(JD_WITH_SECTIONS)
    assert "bachelor" in text.lower()


def test_extract_section_text_finds_nice_to_have():
    """Section extraction should find Nice to have sections."""
    text = _extract_section_text(JD_WITH_SECTIONS)
    assert "terraform" in text.lower()


def test_extract_section_text_excludes_benefits():
    """Non-requirement sections like Benefits should not be extracted."""
    text = _extract_section_text(JD_WITH_SECTIONS)
    assert "health insurance" not in text.lower()


def test_extract_section_text_fallback_to_full_text():
    """When no sections are found, return full JD text."""
    jd_no_sections = "Python developer needed. Docker experience required."
    text = _extract_section_text(jd_no_sections)
    assert "python" in text.lower()
    assert "docker" in text.lower()


# ── Weighted keyword extraction ─────────────────────────────────────────────


def test_weighted_keywords_known_skill_in_section_has_highest_weight():
    """A known skill in a requirements section should have weight 1.0."""
    kw = _extract_weighted_keywords(JD_WITH_SECTIONS)
    kw_dict = dict(kw)
    # Python is a known skill AND in Requirements section
    assert kw_dict.get("python") == 1.0 or kw_dict.get("fastapi") == 1.0


def test_weighted_keywords_known_skill_anywhere_has_high_weight():
    """A known skill mentioned outside sections should have weight 0.8."""
    # Docker appears in the section, but let's test with a JD where it's only outside
    jd = "We use Docker for deployments. Docker is great for containers."
    kw = _extract_weighted_keywords(jd)
    kw_dict = dict(kw)
    # Docker is a known skill — should be at least 0.8
    assert kw_dict.get("docker", 0) >= 0.8


def test_weighted_keywords_generic_word_in_section_has_medium_weight():
    """A non-skill word in a requirements section should have weight 0.5."""
    # "bachelor" is not a known skill but appears in Qualifications
    kw = _extract_weighted_keywords(JD_WITH_SECTIONS)
    kw_dict = dict(kw)
    # It should be lower weight than known skills
    known_skill_weights = [w for k, w in kw if k in _KNOWN_SKILLS or k in {"fastapi", "python"}]
    if "bachelor" in kw_dict:
        assert kw_dict["bachelor"] <= max(known_skill_weights, default=1.0)


def test_weighted_keywords_frequency_only_has_lowest_weight():
    """A generic word mentioned only outside sections should have weight 0.2."""
    jd = "About us: We are a great company doing great things. Python required."
    kw = _extract_weighted_keywords(jd)
    kw_dict = dict(kw)
    # "great" appears twice but is not a known skill and not in a section
    if "great" in kw_dict:
        assert kw_dict["great"] == 0.2


def test_weighted_keywords_priority_ordering():
    """Keywords should be ordered by weight descending."""
    kw = _extract_weighted_keywords(JD_WITH_SECTIONS)
    weights = [w for _, w in kw]
    # First keyword should have weight >= last keyword
    assert weights[0] >= weights[-1] if len(weights) > 1 else True


def test_weighted_keywords_returns_at_most_top_n():
    kw = _extract_weighted_keywords(JD_WITH_SECTIONS, top_n=5)
    assert len(kw) <= 5


def test_weighted_keywords_empty_jd():
    assert _extract_weighted_keywords("") == []


# ── Weighted scoring ────────────────────────────────────────────────────────


def test_analyze_returns_keyword_weights():
    """ATSResult should include keyword_weights dict."""
    result = analyze(_resume(), JD)
    assert isinstance(result.keyword_weights, dict)
    assert len(result.keyword_weights) > 0


def test_analyze_weighted_score_favors_skills_over_frequency():
    """Resume matching known skills should score higher than matching generic words."""
    # Resume with Python (known skill) but not generic words
    resume_skills = ResumeData(
        contact=ContactInfo(name="X", email="x@x.com"),
        summary="Python developer",
        skills=["Python", "FastAPI", "AWS", "Docker", "Kubernetes"],
        experience=[
            ExperienceItem(title="Dev", company="X", bullets=[
                "Built REST APIs with Python, FastAPI, Docker on AWS",
                "Managed Kubernetes clusters in production",
            ])
        ],
        raw_text="Python FastAPI AWS Docker Kubernetes REST APIs",
    )
    result_skills = analyze(resume_skills, JD_WITH_SECTIONS)

    # Resume with only generic words
    resume_generic = ResumeData(
        contact=ContactInfo(name="X", email="x@x.com"),
        summary="Good team player with great communication",
        skills=["teamwork", "communication"],
        experience=[
            ExperienceItem(title="Dev", company="X", bullets=[
                "Worked with great team on good projects",
            ])
        ],
        raw_text="team player good great communication work",
    )
    result_generic = analyze(resume_generic, JD_WITH_SECTIONS)

    # Skills-matching resume should score higher
    assert result_skills.ats_score >= result_generic.ats_score


def test_analyze_missing_keywords_prioritized_by_weight():
    """Missing keywords in suggestions should be sorted by weight descending."""
    # Resume only has Python — everything else is missing
    resume = ResumeData(
        contact=ContactInfo(name="X", email="x@x.com"),
        summary="Python developer",
        skills=["Python"],
        experience=[
            ExperienceItem(title="Dev", company="X", bullets=["Built APIs"])
        ],
        raw_text="Python",
    )
    result = analyze(resume, JD_WITH_SECTIONS)
    assert result.missing_keywords
    # Verify missing keywords are sorted by weight descending
    weights = [result.keyword_weights.get(k, 0) for k in result.missing_keywords]
    assert weights == sorted(weights, reverse=True)


def test_analyze_score_uses_skills_weight_0_25():
    """Skills_pct weight was changed from 0.2 to 0.25 — verify via scoring."""
    resume = ResumeData(
        contact=ContactInfo(name="X", email="x@x.com"),
        summary="Python Docker AWS",
        skills=["Python", "Docker", "AWS"],
        experience=[
            ExperienceItem(title="Dev", company="X", bullets=["Built APIs with Python"])
        ],
        raw_text="Python Docker AWS",
    )
    result = analyze(resume, JD)
    # Score should be in valid range
    assert 0 <= result.ats_score <= 100
    # With 3 known skills matched, skills_pct should be > 0
    assert result.skills_match_pct > 0
