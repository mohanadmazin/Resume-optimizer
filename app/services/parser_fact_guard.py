"""Parser fact guard — deterministic check that AI-extracted fields
exist in the source resume text, preventing hallucinated companies,
titles, dates, institutions, certifications, contact details, skills,
projects, and languages from reaching the database.
"""
import logging
import re
from typing import List

from app.domain.fact_guard import HallucinatedField, ParseFactGuardResult
from app.domain.resume import ParseWarning, ResumeData

logger = logging.getLogger(__name__)

# Punctuation and whitespace normalizer for substring matching.
_NORM_RE = re.compile(r"[\s/\-.,;:()]+")
_SHORT_THRESHOLD = 3


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace/punctuation into single spaces."""
    return _NORM_RE.sub(" ", text.lower()).strip()


def _field_found_in_text(value: str, raw_text: str) -> bool:
    """Return True if *value* appears as a substring of *raw_text*.

    Empty/whitespace-only values always pass (nothing to check).
    Short values (<= SHORT_THRESHOLD chars) use case-sensitive match
    to avoid false positives on things like "C++" or "Go".
    """
    if not value or not value.strip():
        return True
    if len(value) <= _SHORT_THRESHOLD:
        return value in raw_text
    return _normalize(value) in _normalize(raw_text)


def verify_parse(resume: ResumeData, raw_text: str) -> ParseFactGuardResult:
    """Check every high-risk extracted field against the source text.

    Returns a ParseFactGuardResult listing any hallucinated fields.
    """
    hallucinated: List[HallucinatedField] = []
    warnings: List[ParseWarning] = []

    def verify(section: str, index: int, field: str, value: str) -> None:
        if value and not _field_found_in_text(value, raw_text):
            hallucinated.append(HallucinatedField(
                section=section, index=index, field=field,
                extracted_value=value,
            ))
            warnings.append(ParseWarning(
                section=section, line=0,
                message=f'Unsupported extracted {field}: "{value}"',
            ))

    # ── contact ─────────────────────────────────────────────────────────
    for field in ("name", "email", "phone", "location", "linkedin", "website"):
        verify("contact", 0, field, getattr(resume.contact, field, ""))

    # ── skills ──────────────────────────────────────────────────────────
    for i, skill in enumerate(resume.skills):
        verify("skills", i, "skill", skill)

    # ── experience ──────────────────────────────────────────────────────
    for i, exp in enumerate(resume.experience):
        for field in ("company", "title", "start_date", "end_date", "location"):
            verify("experience", i, field, getattr(exp, field, ""))
        for bullet_index, bullet in enumerate(exp.bullets):
            verify(f"experience_bullets:{i}", bullet_index, "bullet", bullet)

    # ── education ───────────────────────────────────────────────────────
    for i, edu in enumerate(resume.education):
        for field in ("institution", "degree", "year"):
            verify("education", i, field, getattr(edu, field, ""))

    # ── certifications ──────────────────────────────────────────────────
    for i, cert in enumerate(resume.certifications):
        verify("certifications", i, "certification", cert)

    # ── projects ────────────────────────────────────────────────────────
    for i, proj in enumerate(resume.projects):
        verify("projects", i, "title", proj.title)
        for field in ("meta", "start_date", "end_date", "description"):
            verify("projects", i, field, getattr(proj, field, ""))
        for bullet_index, bullet in enumerate(proj.bullets):
            verify(f"project_bullets:{i}", bullet_index, "bullet", bullet)

    # ── languages ───────────────────────────────────────────────────────
    for i, lang in enumerate(resume.languages):
        verify("languages", i, "language", lang)

    if hallucinated:
        logger.warning(
            "Parser fact guard: %d hallucinated field(s) detected",
            len(hallucinated),
        )

    return ParseFactGuardResult(
        hallucinated_fields=hallucinated,
        warnings=warnings,
    )
