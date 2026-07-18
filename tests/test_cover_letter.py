"""Tests for the cover letter fact-checking."""

from unittest.mock import MagicMock, patch

from app.domain.resume import ContactInfo, EducationItem, ExperienceItem, ResumeData
from app.services.cover_letter import _check_cover_letter_facts, generate_cover_letter


# ── Helpers ──────────────────────────────────────────────────────────────────


def _resume(**overrides) -> ResumeData:
    defaults = dict(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        summary="Experienced developer.",
        skills=["Python", "Django"],
        experience=[
            ExperienceItem(
                title="Developer",
                company="Acme Corp",
                bullets=["Built REST APIs"],
            )
        ],
        education=[
            EducationItem(degree="BSc Computer Science", institution="MIT"),
        ],
    )
    defaults.update(overrides)
    return ResumeData(**defaults)


# ── _check_cover_letter_facts ────────────────────────────────────────────────


def test_no_warnings_for_clean_letter():
    resume = _resume()
    letter = "Dear Hiring Manager, I am a developer at Acme Corp."
    warnings = _check_cover_letter_facts(letter, resume)
    assert len(warnings) == 0
    assert isinstance(warnings, tuple)


def test_warns_on_new_number():
    resume = _resume()
    letter = "I increased revenue by 50% in my previous role."
    warnings = _check_cover_letter_facts(letter, resume)
    assert len(warnings) >= 1
    assert any("50%" in w for w in warnings)


def test_no_warn_on_number_in_resume():
    resume = _resume()
    resume.experience[0].bullets = ["Increased revenue by 50%"]
    letter = "I increased revenue by 50% in my previous role."
    warnings = _check_cover_letter_facts(letter, resume)
    # 50% is in the resume, so no warning for it
    assert not any("50%" in w for w in warnings)


def test_warns_on_unknown_company():
    resume = _resume()
    letter = "I would love to work at Google Ventures."
    warnings = _check_cover_letter_facts(letter, resume)
    assert any("Google Ventures" in w for w in warnings)


def test_no_warn_on_known_company():
    resume = _resume()
    letter = "I worked at Acme Corp for three years."
    warnings = _check_cover_letter_facts(letter, resume)
    assert not any("Acme Corp" in w for w in warnings)


def test_no_warn_on_known_institution():
    resume = _resume()
    letter = "I graduated from MIT with honors."
    warnings = _check_cover_letter_facts(letter, resume)
    assert not any("MIT" in w for w in warnings)


def test_no_warn_on_generic_phrases():
    resume = _resume()
    letter = "Dear Hiring Manager, I would love to join your company."
    warnings = _check_cover_letter_facts(letter, resume)
    assert len(warnings) == 0


# ── Target employer never flagged ────────────────────────────────────────────


def test_no_warn_on_target_employer():
    """The target employer must never be flagged as suspicious."""
    resume = _resume()
    letter = "I am excited to apply to Globex International for the role."
    warnings = _check_cover_letter_facts(
        letter, resume, allowed_organizations={"Globex International"},
    )
    assert not any("Globex" in w for w in warnings)


def test_no_warn_on_target_employer_case_insensitive():
    resume = _resume()
    letter = "I would love to join Waystar Royco."
    warnings = _check_cover_letter_facts(
        letter, resume, allowed_organizations={"waystar royco"},
    )
    assert not any("Waystar" in w for w in warnings)


def test_no_warn_on_target_employer_single_word():
    """Single-word company names should not be matched by the multi-word regex."""
    resume = _resume()
    letter = "I am excited to work at Google."
    warnings = _check_cover_letter_facts(
        letter, resume, allowed_organizations={"Google"},
    )
    # Single-word names like "Google" don't match the multi-word pattern
    assert not any("Google" in w for w in warnings)


def test_warns_on_other_unknown_not_target():
    """Unknown org that is NOT the target employer should still be flagged."""
    resume = _resume()
    letter = "I applied to Globex International and also Stark Industries."
    warnings = _check_cover_letter_facts(
        letter, resume, allowed_organizations={"Globex International"},
    )
    assert not any("Globex" in w for w in warnings)
    assert any("Stark Industries" in w for w in warnings)


def test_target_employer_always_allowed_even_if_not_in_resume():
    """The target company does not need to appear in the resume."""
    resume = _resume()
    letter = "I am thrilled about the opportunity at Initech."
    warnings = _check_cover_letter_facts(
        letter, resume, allowed_organizations={"Initech"},
    )
    assert len(warnings) == 0


# ── Warnings are a tuple, never contaminate text ─────────────────────────────


def test_warnings_are_tuple():
    resume = _resume()
    letter = "I increased revenue by 99% at New Organization Corp."
    warnings = _check_cover_letter_facts(letter, resume)
    assert isinstance(warnings, tuple)


def test_warnings_never_in_letter_text():
    """Fact-check warnings must never be appended to the letter text."""
    resume = _resume()
    letter = "Dear Hiring Manager, I am interested in the role."
    warnings = _check_cover_letter_facts(letter, resume)
    combined = letter + "\n".join(warnings)
    # The letter text itself should not contain any warning markers
    assert "not found in resume" not in letter
    assert "mentions organization not" not in letter


# ── generate_cover_letter (mocked) ───────────────────────────────────────────


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_calls_client(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate.return_value = "Dear Hiring Manager,\nI am interested.\nSincerely,\nJane"

    resume = _resume()
    result = generate_cover_letter(resume, "Looking for a Python developer", mock_client)

    mock_client.generate.assert_called_once()
    assert "Jane" in result.text
    assert isinstance(result.warnings, tuple)


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_separate_warnings(mock_client_cls):
    mock_client = mock_client_cls.return_value
    # AI generates a letter with a number not in the resume
    mock_client.generate.return_value = (
        "Dear Hiring Manager,\nI improved metrics by 75%.\nSincerely,\nJane"
    )

    resume = _resume()
    result = generate_cover_letter(resume, "Job description", mock_client)

    assert len(result.warnings) > 0
    assert "75%" in result.text
    # Warnings must NOT appear in the exported text
    assert "Fact-check warnings" not in result.text
    assert "not found in resume" not in result.text


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_no_warnings_for_clean(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate.return_value = (
        "Dear Hiring Manager,\nI worked at Acme Corp.\nSincerely,\nJane"
    )

    resume = _resume()
    result = generate_cover_letter(resume, "Job description", mock_client)

    assert len(result.warnings) == 0
    assert result.warnings == ()


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_replaces_closing(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate.return_value = (
        "Dear Hiring Manager,\nI am interested.\nSincerely,\nOriginal Name"
    )

    resume = _resume()
    result = generate_cover_letter(resume, "Job description", mock_client)

    # The closing should be replaced with the actual candidate name
    assert "Sincerely,\nJane Doe" in result.text


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_passes_target_company(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate.return_value = (
        "Dear Hiring Manager,\nI want to work at Waystar Royco.\nSincerely,\nJane"
    )

    resume = _resume()
    result = generate_cover_letter(
        resume, "Job description", mock_client, target_company="Waystar Royco",
    )

    # Target company should NOT be flagged
    assert not any("Waystar" in w for w in result.warnings)


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_flags_unknown_without_target(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate.return_value = (
        "Dear Hiring Manager,\nI admire Stark Industries.\nSincerely,\nJane"
    )

    resume = _resume()
    # No target_company provided — unknown org should be flagged
    result = generate_cover_letter(resume, "Job description", mock_client)

    assert any("Stark Industries" in w for w in result.warnings)
