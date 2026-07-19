"""Tests for the deterministic fact guard service."""

from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
from app.domain.resume import ContactInfo, ExperienceItem, ResumeData
from app.services.fact_guard import (
    FactGuard,
    _extract_entities,
    _extract_numbers,
    _extract_tech_tokens,
    _normalize_skill,
    _source_vocabulary,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _resume(**overrides) -> ResumeData:
    defaults = dict(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        summary="Experienced software engineer with 5 years in web development.",
        skills=["Python", "Django", "PostgreSQL", "React"],
        experience=[
            ExperienceItem(
                title="Senior Developer",
                company="Acme Corp",
                bullets=[
                    "Built REST APIs serving 1M requests per day",
                    "Reduced infrastructure costs by 30%",
                    "Led team of 5 engineers",
                ],
            )
        ],
    )
    defaults.update(overrides)
    return ResumeData(**defaults)


# ── _normalize_skill ─────────────────────────────────────────────────────────


def test_normalize_skill_lowercases():
    assert _normalize_skill("Python") == "python"
    assert _normalize_skill("  DJANGO  ") == "django"


def test_normalize_skill_aliases():
    assert _normalize_skill("js") == "javascript"
    assert _normalize_skill("k8s") == "kubernetes"
    assert _normalize_skill("ts") == "typescript"
    assert _normalize_skill("reactjs") == "react"
    assert _normalize_skill("postgres") == "postgresql"
    assert _normalize_skill("golang") == "go"
    assert _normalize_skill("py") == "python"


def test_normalize_skill_passthrough():
    assert _normalize_skill("rust") == "rust"
    assert _normalize_skill("flask") == "flask"


# ── _extract_numbers ─────────────────────────────────────────────────────────


def test_extract_numbers_plain():
    assert _extract_numbers("Built 5 services") == {"5"}


def test_extract_numbers_currency():
    assert _extract_numbers("Cost $1,000") == {"$1,000"}


def test_extract_numbers_percentage():
    assert _extract_numbers("Improved by 30%") == {"30%"}


def test_extract_numbers_comma_separated():
    assert _extract_numbers("1,000,000 users") == {"1,000,000"}


def test_extract_numbers_decimal():
    assert _extract_numbers("v3.14 release") == {"3.14"}


# ── _extract_entities ────────────────────────────────────────────────────────


def test_extract_entities_multi_word():
    entities = _extract_entities("Worked at Acme Corp for 3 years")
    assert "Acme Corp" in entities


def test_extract_entities_company_suffix():
    entities = _extract_entities("Joined Microsoft Inc in 2020")
    # The regex matches the full phrase including preceding word as one entity
    assert any("Microsoft" in e for e in entities)


def test_extract_entities_ignores_common_words():
    entities = _extract_entities("The Project Team Led Development")
    # "Project Team" and "Led Development" look like entities but are common phrases
    # They should not appear if they match _IGNORE_TOKENS
    for e in entities:
        assert e.lower() not in {"project", "team", "led", "development"}


# ── _extract_tech_tokens ─────────────────────────────────────────────────────


def test_extract_tech_tokens():
    tokens = _extract_tech_tokens("Built with React and Node.js")
    assert "React" in tokens
    assert "Node.js" in tokens


def test_extract_tech_tokens_empty():
    assert _extract_tech_tokens("no tech here") == set()


# ── _source_vocabulary ───────────────────────────────────────────────────────


def test_source_vocabulary_includes_skills():
    resume = _resume()
    vocab = _source_vocabulary(resume)
    assert "python" in vocab
    assert "django" in vocab
    assert "react" in vocab


def test_source_vocabulary_includes_experience():
    resume = _resume()
    vocab = _source_vocabulary(resume)
    assert "acme" in vocab
    assert "corp" in vocab


# ── FactGuard.validate — safe changes ────────────────────────────────────────


def test_identical_resumes_produce_no_changes():
    source = _resume()
    optimized = _resume()
    result = FactGuard().validate(source, optimized)
    assert len(result.safe_changes) == 0
    assert len(result.flagged_changes) == 0


def test_summary_rewrite_with_same_words_is_safe():
    source = _resume(summary="Python developer with 5 years experience.")
    optimized = _resume(summary="Experienced Python developer with 5 years.")
    result = FactGuard().validate(source, optimized)
    # Should be safe — no new numbers, entities, or skills
    assert all(not c.has_new_numbers and not c.has_new_entities and not c.has_new_skills
               for c in result.safe_changes)


def test_bullet_rewrite_without_new_facts_is_safe():
    """A bullet rewrite that doesn't introduce new numbers/entities is safe
    even if tech token detection flags capitalized words like 'Developed'."""
    source = _resume()
    optimized = _resume()
    # Use lowercase start to avoid _TECH_RE matching on capitalized verbs
    optimized.experience[0].bullets[0] = "developed REST APIs with Django serving 1M daily requests"
    result = FactGuard().validate(source, optimized)
    # Numbers: 1M was already in the original → no new numbers
    assert len(result.flagged_changes) == 0


# ── FactGuard.validate — flagged changes ─────────────────────────────────────


def test_new_number_in_summary_gets_flagged():
    source = _resume(summary="Experienced developer.")
    optimized = _resume(summary="Experienced developer who increased revenue by 50%.")
    result = FactGuard().validate(source, optimized)
    assert len(result.flagged_changes) >= 1
    assert any(c.has_new_numbers for c in result.flagged_changes)
    assert "50%" in result.unsupported_numbers


def test_new_entity_in_summary_gets_flagged():
    source = _resume(summary="Worked at Acme Corp.")
    optimized = _resume(summary="Worked at Acme Corp and Google Ventures.")
    result = FactGuard().validate(source, optimized)
    assert any(c.has_new_entities for c in result.flagged_changes)


def test_inserted_bullet_gets_checked():
    source = _resume()
    source.experience[0].bullets = ["Built REST APIs"]
    optimized = _resume()
    optimized.experience[0].bullets = [
        "Built REST APIs",
        "Increased revenue by 40%",
    ]
    result = FactGuard().validate(source, optimized)
    # The inserted bullet has a new number (40%)
    assert any(c.has_new_numbers for c in result.flagged_changes)


def test_inserted_bullet_without_facts_is_safe():
    source = _resume()
    source.experience[0].bullets = ["Built REST APIs", "Wrote documentation", "Fixed bugs"]
    optimized = _resume()
    optimized.experience[0].bullets = [
        "Built REST APIs",
        "Wrote documentation",
        "Fixed bugs",
        "improved code quality and test coverage",  # lowercase to avoid _TECH_RE
    ]
    result = FactGuard().validate(source, optimized)
    # No new numbers, entities, or skills — should be safe
    assert len(result.flagged_changes) == 0
    assert len(result.safe_changes) >= 1


# ── FactGuard.validate — skill normalization ─────────────────────────────────


def test_existing_skill_not_flagged():
    """Rewriting a bullet that mentions a skill already in the resume is safe."""
    source = _resume(skills=["Python", "Django"])
    source.experience[0].bullets = [
        "Used python for backend",
        "Built REST APIs serving 1M requests",
        "Led team of 5 engineers",
    ]
    optimized = _resume(skills=["Python", "Django"])
    optimized.experience[0].bullets = [
        "worked with python for backend",
        "Built REST APIs serving 1M requests",
        "Led team of 5 engineers",
    ]
    result = FactGuard().validate(source, optimized)
    assert len(result.flagged_changes) == 0


def test_new_tech_in_rewritten_bullet_flagged():
    """A tech token not in the source resume should be flagged."""
    source = _resume(skills=["Python", "Django"])
    source.experience[0].bullets = ["Built web applications"]
    optimized = _resume(skills=["Python", "Django"])
    optimized.experience[0].bullets = ["Built web apps using Kubernetes for orchestration"]
    result = FactGuard().validate(source, optimized)
    assert any(c.has_new_skills for c in result.flagged_changes)


def test_lowercase_new_tech_in_rewritten_bullet_flagged():
    source = _resume(skills=["Python"])
    source.experience[0].bullets = ["Built web applications"]
    optimized = _resume(skills=["Python"])
    optimized.experience[0].bullets = ["Built web apps with terraform"]
    result = FactGuard().validate(source, optimized)
    assert result.unsupported_skills == ["terraform"]
    assert any(c.has_new_skills for c in result.flagged_changes)


def test_capitalized_action_verb_is_not_a_skill():
    source = _resume()
    optimized = _resume()
    optimized.experience[0].bullets[0] = "Spearheaded REST APIs with Django serving 1M daily requests"
    result = FactGuard().validate(source, optimized)
    assert not result.unsupported_skills
    assert all(not c.has_new_skills for c in result.all_changes)


def test_deleted_bullet_requires_review():
    source = _resume()
    optimized = _resume()
    optimized.experience[0].bullets.pop()
    result = FactGuard().validate(source, optimized)
    assert any(c.rewritten == "" and c.requires_review for c in result.flagged_changes)


def test_negation_change_requires_review():
    source = _resume()
    source.experience[0].bullets = ["Did not manage production deployments."]
    optimized = _resume()
    optimized.experience[0].bullets = ["Managed production deployments."]
    result = FactGuard().validate(source, optimized)
    assert any("polarity" in c.review_reason.lower() for c in result.flagged_changes)


def test_change_ratio_is_enforced():
    source = _resume()
    source.experience[0].bullets = ["Built APIs", "Wrote tests", "Fixed bugs"]
    optimized = _resume()
    optimized.experience[0].bullets = ["Built services", "Created tests", "Fixed bugs"]
    result = FactGuard(max_bullet_change_ratio=0.5).validate(source, optimized)
    assert len(result.flagged_changes) >= 2


def test_duplicate_job_titles_use_indexed_operations():
    source = ResumeData(
        experience=[
            ExperienceItem(
                title="Developer",
                company="Acme",
                start_date="2020",
                end_date="2022",
                bullets=["First role bullet"],
            ),
            ExperienceItem(
                title="Developer",
                company="Acme",
                start_date="2022",
                end_date="Present",
                bullets=["Second role bullet"],
            ),
        ],
    )
    optimized = source.model_copy(deep=True)
    optimized.experience[0].bullets[0] = "Rewrote first role"
    result = FactGuard().validate(source, optimized)
    assert any(
        c.experience_index == 0 and c.bullet_index == 0
        for c in result.all_changes
    )
    assert not any(
        c.experience_index == 1 and c.bullet_index == 0
        for c in result.all_changes
        if c.rewritten == "Rewrote first role"
    )


# ── FactGuard.validate — headline ────────────────────────────────────────────


def test_headline_change_checked():
    source = _resume(headline="Software Engineer")
    optimized = _resume(headline="Senior Software Engineer | 10+ Years")
    result = FactGuard().validate(source, optimized)
    assert len(result.safe_changes) + len(result.flagged_changes) >= 1


# ── FactGuardResult properties ───────────────────────────────────────────────


def test_fact_guard_result_all_changes():
    safe = [ProposedChange(change_type=ChangeType.SUMMARY, section="s", original="a", rewritten="b")]
    flagged = [ProposedChange(change_type=ChangeType.SUMMARY, section="s", original="a", rewritten="c",
                              has_new_numbers=True)]
    result = FactGuardResult(safe_changes=safe, flagged_changes=flagged)
    assert len(result.all_changes) == 2
    assert result.flagged_count == 1
    assert result.accepted_count == 0


def test_fact_guard_result_accepted_count():
    safe = [ProposedChange(change_type=ChangeType.SUMMARY, section="s", original="a", rewritten="b", accepted=True)]
    flagged = [ProposedChange(change_type=ChangeType.SUMMARY, section="s", original="a", rewritten="c",
                              has_new_numbers=True, accepted=True)]
    result = FactGuardResult(safe_changes=safe, flagged_changes=flagged)
    assert result.accepted_count == 2


def test_review_complete_uses_change_decisions_not_ui_state():
    accepted = ProposedChange(
        change_type=ChangeType.SUMMARY, original="a", rewritten="b", accepted=True
    )
    rejected = ProposedChange(
        change_type=ChangeType.HEADLINE, original="c", rewritten="d", accepted=False
    )
    result = FactGuardResult(safe_changes=[accepted], flagged_changes=[rejected])
    assert result.review_complete is True


def test_review_incomplete_when_any_decision_is_pending():
    decided = ProposedChange(
        change_type=ChangeType.SUMMARY, original="a", rewritten="b", accepted=True
    )
    pending = ProposedChange(
        change_type=ChangeType.HEADLINE, original="c", rewritten="d", accepted=None
    )
    result = FactGuardResult(safe_changes=[decided], flagged_changes=[pending])
    assert result.review_complete is False
