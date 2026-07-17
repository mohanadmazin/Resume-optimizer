"""Parser fact guard — deterministic check that AI-extracted fields
exist in the source resume text, preventing hallucinated companies,
titles, dates, institutions, and certifications from reaching the database.
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

    # ── experience ──────────────────────────────────────────────────────
    for i, exp in enumerate(resume.experience):
        for field in ("company", "title", "start_date", "end_date"):
            value = getattr(exp, field, "")
            if not _field_found_in_text(value, raw_text):
                hallucinated.append(HallucinatedField(
                    section="experience", index=i, field=field,
                    extracted_value=value,
                ))
                warnings.append(ParseWarning(
                    section="experience", line=0,
                    message=f"AI-invented {field} \"{value}\" not found in source text",
                ))

    # ── education ───────────────────────────────────────────────────────
    for i, edu in enumerate(resume.education):
        for field in ("institution", "degree"):
            value = getattr(edu, field, "")
            if not _field_found_in_text(value, raw_text):
                hallucinated.append(HallucinatedField(
                    section="education", index=i, field=field,
                    extracted_value=value,
                ))
                warnings.append(ParseWarning(
                    section="education", line=0,
                    message=f"AI-invented {field} \"{value}\" not found in source text",
                ))

    # ── certifications ──────────────────────────────────────────────────
    for i, cert in enumerate(resume.certifications):
        if not _field_found_in_text(cert, raw_text):
            hallucinated.append(HallucinatedField(
                section="certifications", index=i, field="certification",
                extracted_value=cert,
            ))
            warnings.append(ParseWarning(
                section="certifications", line=0,
                message=f"AI-invented certification \"{cert}\" not found in source text",
            ))

    if hallucinated:
        logger.warning(
            "Parser fact guard: %d hallucinated field(s) detected",
            len(hallucinated),
        )

    return ParseFactGuardResult(
        hallucinated_fields=hallucinated,
        warnings=warnings,
    )
