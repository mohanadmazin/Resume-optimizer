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


# ── generate_cover_letter (mocked) ───────────────────────────────────────────


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_calls_client(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate.return_value = "Dear Hiring Manager,\nI am interested.\nSincerely,\nJane"

    resume = _resume()
    letter = generate_cover_letter(resume, "Looking for a Python developer", mock_client)

    mock_client.generate.assert_called_once()
    assert "Jane" in letter.text


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_appends_fact_check_warnings(mock_client_cls):
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


@patch("app.services.cover_letter.OllamaClient")
def test_generate_cover_letter_no_warnings_for_clean(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate.return_value = (
        "Dear Hiring Manager,\nI worked at Acme Corp.\nSincerely,\nJane"
    )

    resume = _resume()
    result = generate_cover_letter(resume, "Job description", mock_client)

    assert len(result.warnings) == 0


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
