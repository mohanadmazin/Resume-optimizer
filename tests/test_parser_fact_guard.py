"""Tests for the parser fact guard — anti-hallucination layer."""
from unittest.mock import patch

import pytest

from app.domain.fact_guard import ParseFactGuardResult
from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ParseWarning,
    ResumeData,
)
from app.services.parser_fact_guard import _field_found_in_text, verify_parse


# ── _field_found_in_text unit tests ─────────────────────────────────────


class TestFieldFoundInText:
    def test_empty_value_always_passes(self):
        assert _field_found_in_text("", "some text") is True

    def test_whitespace_only_always_passes(self):
        assert _field_found_in_text("   ", "some text") is True

    def test_exact_match(self):
        assert _field_found_in_text("Google", "Worked at Google for 3 years") is True

    def test_case_insensitive_long_value(self):
        assert _field_found_in_text("Google", "worked at google inc") is True

    def test_fuzzy_whitespace_match(self):
        assert _field_found_in_text("New York", "Location: New  York, NY") is True

    def test_short_value_case_sensitive(self):
        assert _field_found_in_text("Go", "I use Go daily") is True
        assert _field_found_in_text("Go", "I use golang daily") is False

    def test_missing_value_returns_false(self):
        assert _field_found_in_text("Meta Platforms", "Worked at Google") is False

    def test_punctuation_flexibility(self):
        assert _field_found_in_text("Node.js", "Skills: Node.js, React") is True
        assert _field_found_in_text("Node.js", "Skills: Node JS, React") is True


# ── verify_parse integration tests ──────────────────────────────────────


def _make_resume(**overrides) -> ResumeData:
    defaults = dict(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        summary="Python developer",
        skills=["Python"],
        experience=[
            ExperienceItem(
                title="Engineer",
                company="Google",
                start_date="2020",
                end_date="2023",
                bullets=["Built things"],
            )
        ],
        education=[
            EducationItem(degree="BS CS", institution="MIT", year="2019"),
        ],
        certifications=["AWS Solutions Architect"],
    )
    defaults.update(overrides)
    return ResumeData(**defaults)


class TestVerifyParse:
    def test_clean_parse_no_hallucinations(self):
        raw = (
            "Jane Doe\njane@example.com\n\n"
            "Experience\nEngineer at Google (2020 - 2023)\n- Built things\n\n"
            "Education\nBS CS, MIT, 2019\n\n"
            "Certifications\nAWS Solutions Architect"
        )
        resume = _make_resume()
        result = verify_parse(resume, raw)
        assert not result.has_hallucinations
        assert result.hallucinated_fields == []

    def test_hallucinated_company_detected(self):
        raw = "Experience\nEngineer at Facebook (2020 - 2023)\n- Built things"
        resume = _make_resume()
        resume.experience[0].company = "Meta"
        result = verify_parse(resume, raw)
        assert result.has_hallucinations
        assert any(h.field == "company" for h in result.hallucinated_fields)

    def test_hallucinated_title_detected(self):
        raw = "Experience\nEngineer at Google (2020 - 2023)\n- Built things"
        resume = _make_resume()
        resume.experience[0].title = "Senior Staff Engineer"
        result = verify_parse(resume, raw)
        assert result.has_hallucinations
        assert any(h.field == "title" for h in result.hallucinated_fields)

    def test_hallucinated_date_detected(self):
        raw = "Experience\nEngineer at Google\n- Built things"
        resume = _make_resume()
        resume.experience[0].start_date = "2018"
        resume.experience[0].end_date = "2024"
        result = verify_parse(resume, raw)
        assert result.has_hallucinations
        halluc_dates = [h for h in result.hallucinated_fields if h.field in ("start_date", "end_date")]
        assert len(halluc_dates) == 2

    def test_hallucinated_cert_detected(self):
        raw = (
            "Experience\nEngineer at Google (2020 - 2023)\n- Built things\n\n"
            "Education\nBS CS, MIT, 2019"
        )
        resume = _make_resume()
        resume.certifications = ["CISSP", "PMP"]
        result = verify_parse(resume, raw)
        assert result.has_hallucinations
        cert_halls = [h for h in result.hallucinated_fields if h.section == "certifications"]
        assert len(cert_halls) == 2

    def test_hallucinated_institution_detected(self):
        raw = (
            "Experience\nEngineer at Google (2020 - 2023)\n- Built things\n\n"
            "Education\nBS CS, Stanford, 2019\n\n"
            "Certifications\nAWS Solutions Architect"
        )
        resume = _make_resume()
        resume.education[0].institution = "MIT"
        result = verify_parse(resume, raw)
        assert result.has_hallucinations
        assert any(h.field == "institution" for h in result.hallucinated_fields)

    def test_mixed_hallucination_and_clean(self):
        raw = (
            "Experience\nEngineer at Google (2020 - 2023)\n- Built things\n\n"
            "Education\nBS CS, MIT, 2019\n\n"
            "Certifications\nAWS Solutions Architect"
        )
        resume = _make_resume()
        resume.experience[0].title = "Senior Staff Engineer"  # hallucinated
        result = verify_parse(resume, raw)
        assert result.has_hallucinations
        assert len(result.hallucinated_fields) == 1
        assert result.hallucinated_fields[0].field == "title"

    def test_parse_warnings_generated(self):
        raw = "Experience\nEngineer at Facebook\n- Built things"
        resume = _make_resume()
        resume.experience[0].company = "Meta"
        result = verify_parse(resume, raw)
        assert len(result.warnings) >= 1
        assert any("Meta" in w.message for w in result.warnings)

    def test_empty_fields_skip_check(self):
        raw = (
            "Experience\nEngineer at Google (2020 - 2023)\n- Built things\n\n"
            "Education\nBS CS, MIT, 2019\n\n"
            "Certifications\nAWS Solutions Architect"
        )
        resume = _make_resume()
        resume.experience[0].company = ""
        resume.experience[0].title = ""
        result = verify_parse(resume, raw)
        assert not result.has_hallucinations

    def test_bullets_not_checked(self):
        raw = (
            "Experience\nEngineer at Google (2020 - 2023)\n- Built things\n\n"
            "Education\nBS CS, MIT, 2019\n\n"
            "Certifications\nAWS Solutions Architect"
        )
        resume = _make_resume()
        resume.experience[0].bullets = [
            "Led a team of 50 engineers",  # completely invented bullet
            "Reduced costs by 40%",         # invented metric
        ]
        result = verify_parse(resume, raw)
        # Bullets are NOT checked — only company, title, dates
        assert not result.has_hallucinations
