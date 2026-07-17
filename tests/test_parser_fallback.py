"""Tests for the resume parser AI fallback and parser edge cases."""

from unittest.mock import MagicMock, patch

from app.ai.ollama_client import OllamaError
from app.services.resume_parser import parse_resume, parse_resume_ai


# ── AI parser fallback ───────────────────────────────────────────────────────


@patch("app.services.resume_parser.OllamaClient")
def test_parse_resume_ai_falls_back_on_ollama_error(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate_json.side_effect = OllamaError("Connection refused")

    text = "John Smith\njohn@example.com\n\nSummary\nExperienced developer.\n\nSkills\nPython\n"
    result = parse_resume_ai(text, mock_client)

    # Should fall back to heuristic parser without raising
    assert result.contact.name == "John Smith"
    assert "Python" in result.skills
    assert result.raw_text == text


@patch("app.services.resume_parser.OllamaClient")
def test_parse_resume_ai_falls_back_on_validation_error(mock_client_cls):
    from pydantic import ValidationError
    mock_client = mock_client_cls.return_value
    # Return data that will cause ResumeData.model_validate to raise ValidationError
    mock_client.generate_json.return_value = {
        "contact": "not a dict",  # Should be a dict, causing validation error
    }

    text = "Jane Doe\njane@example.com\n\nSkills\nPython, Django\n"
    result = parse_resume_ai(text, mock_client)

    # Should fall back to heuristic parser
    assert result.raw_text == text
    assert "Python" in result.skills


@patch("app.services.resume_parser.OllamaClient")
def test_parse_resume_ai_falls_back_on_value_error(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate_json.side_effect = ValueError("Bad JSON")

    text = "Test User\ntest@example.com\n\nSummary\nA summary.\n"
    result = parse_resume_ai(text, mock_client)

    assert result.raw_text == text


@patch("app.services.resume_parser.OllamaClient")
def test_parse_resume_ai_falls_back_on_type_error(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate_json.side_effect = TypeError("Unexpected type")

    text = "Test User\ntest@example.com\n\nSummary\nA summary.\n"
    result = parse_resume_ai(text, mock_client)

    assert result.raw_text == text


@patch("app.services.resume_parser.OllamaClient")
def test_parse_resume_ai_success(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.generate_json.return_value = {
        "contact": {"name": "AI Parsed User", "email": "ai@test.com", "phone": "", "location": "", "linkedin": "", "website": ""},
        "headline": "AI Engineer",
        "summary": "AI-generated summary.",
        "skills": ["Machine Learning", "Python"],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "languages": [],
    }

    text = "AI Parsed User ai@test.com Machine Learning Python Some resume text"
    result = parse_resume_ai(text, mock_client)

    assert result.contact.name == "AI Parsed User"
    assert result.summary == "AI-generated summary."
    assert "Machine Learning" in result.skills
    assert result.raw_text == text


# ── Heuristic parser edge cases ──────────────────────────────────────────────


def test_parse_resume_empty_text():
    result = parse_resume("")
    assert result.contact.name == ""
    assert result.summary == ""
    assert result.skills == []


def test_parse_resume_experience_new_entry_detection():
    """A new title-like line after bullets should start a new experience entry."""
    text = """John Smith
john@example.com

Experience
Software Engineer | Acme Corp | 2020 - 2022
- Built REST APIs
- Managed database
Senior Developer | Beta Inc | 2022 - Present
- Led team of 5
"""
    result = parse_resume(text)
    assert len(result.experience) == 2
    assert result.experience[0].title == "Software Engineer"
    assert result.experience[1].title == "Senior Developer"


def test_parse_resume_projects_new_entry_detection():
    """A new title-like line in projects should start a new project entry."""
    text = """John Smith
john@example.com

Projects
Project Alpha
- Built frontend with React
- Deployed to AWS
Project Beta
- Designed database schema
"""
    result = parse_resume(text)
    assert len(result.projects) == 2
    assert result.projects[0].title == "Project Alpha"
    assert result.projects[1].title == "Project Beta"
