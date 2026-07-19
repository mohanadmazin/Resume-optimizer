"""Cover letter generation via Ollama with fact guard."""
import json
import logging
import re
from dataclasses import dataclass

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import COVER_LETTER_PROMPT, COVER_LETTER_SYSTEM
from app.schemas import ResumeData
from app.services.job_context import select_job_context

logger = logging.getLogger(__name__)

# Numbers that appear in the cover letter but not in the resume
_NUMBER_RE = re.compile(
    r"(?:"
    r"\$[\d,]+(?:\.\d+)?"
    r"|\d{1,3}(?:,\d{3})+"
    r"|\d+%"
    r"|\d+(?:\.\d+)?"
    r")"
)


@dataclass(frozen=True, slots=True)
class CoverLetterResult:
    """Structured cover letter output with warnings kept separate."""
    text: str
    warnings: tuple[str, ...] = ()


def _check_cover_letter_facts(
    letter: str,
    resume: ResumeData,
    allowed_organizations: set[str] | None = None,
    allowed_text: str = "",
) -> tuple[str, ...]:
    """Return a tuple of warnings for unsupported claims in the cover letter.

    The target employer is always included in *allowed_organizations* so
    it is never flagged as suspicious.
    """
    warnings: list[str] = []

    # Check for new numbers not in the resume
    resume_text = resume.model_dump_json().lower()
    letter_numbers = set(_NUMBER_RE.findall(letter))
    supported_numbers = set(_NUMBER_RE.findall(resume_text + " " + allowed_text.lower()))
    new_numbers = letter_numbers - supported_numbers
    if new_numbers:
        warnings.append(
            f"Cover letter contains numbers not found in resume: {', '.join(sorted(new_numbers))}"
        )

    # Check for company names not in resume (simple heuristic)
    resume_companies = {
        exp.company.lower() for exp in resume.experience if exp.company
    }
    resume_institutions = {
        edu.institution.lower() for edu in resume.education if edu.institution
    }
    known_orgs = resume_companies | resume_institutions
    normalized_resume = resume.model_dump_json().casefold()
    normalized_allowed_text = allowed_text.casefold()

    # Add allowed organizations (target employer, hiring manager's company, etc.)
    if allowed_organizations:
        known_orgs.update(org.strip().lower() for org in allowed_organizations if org.strip())

    # Candidate's own name should not be flagged
    candidate_name = (resume.contact.name or "").lower()

    # Generic phrases that should never be flagged
    _SAFE_PHRASES = {
        "dear hiring manager", "your company", "the team",
        "your organization", "your team", "the company",
        "dear recruitment", "dear recruiter", "hiring team",
    }

    # Look for capitalized multi-word proper nouns that might be company names.
    # Also catch single-word orgs that start with a capital letter followed by
    # a known suffix (Corp, Inc, etc.) or standalone proper nouns that are
    # clearly organization names.
    company_pattern = re.compile(
        r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+"
        r"(?:\s+(?:Corp|Inc|Ltd|LLC|Co|Company|Group|Technologies|"
        r"Systems|Labs|Studio|Associates|Partners))?)\b"
    )
    letter_orgs = set(company_pattern.findall(letter))
    for org in letter_orgs:
        org_lower = org.lower()
        if (
            org_lower not in known_orgs
            and org_lower not in normalized_resume
            and org_lower not in normalized_allowed_text
            and org_lower not in _SAFE_PHRASES
            and org_lower != candidate_name
            and not any(word in org_lower for word in candidate_name.split())
        ):
            warnings.append(f"Cover letter mentions organization not in resume: {org}")

    return tuple(warnings)


def generate_cover_letter(
    resume: ResumeData,
    jd_text: str,
    client: OllamaClient,
    target_company: str | None = None,
    job_title: str | None = None,
) -> CoverLetterResult:
    """Generate a cover letter and return structured result with separate warnings.

    *target_company* is the employer from the job description.  It is always
    added to the allowed-organizations set so the fact-checker does not flag
    the target employer as suspicious.
    """
    logger.info("Generating cover letter for %s", resume.contact.name or "unknown")
    data = resume.model_dump()
    data.pop("raw_text", None)

    candidate_name = (
        resume.contact.name.strip()
        if resume.contact.name
        else ""
    )

    prompt = COVER_LETTER_PROMPT.format(
        resume_json=json.dumps(data, indent=2),
        job_description=select_job_context(jd_text),
        candidate_name=candidate_name,
        headline=resume.headline or "",
    )

    letter = client.generate(
        prompt,
        system=COVER_LETTER_SYSTEM
    )

    letter = re.sub(
        r"Sincerely,.*$",
        f"Sincerely,\n{candidate_name}",
        letter,
        flags=re.S | re.M,
    )

    # Fact-check the generated cover letter — always include the target employer
    # so it is never flagged as an unknown organization.
    allowed: set[str] = set()
    if target_company and target_company.strip():
        allowed.add(target_company.strip())

    warnings = _check_cover_letter_facts(
        letter,
        resume,
        allowed_organizations=allowed,
        allowed_text=jd_text,
    )

    if warnings:
        for w in warnings:
            logger.warning("Cover letter fact check: %s", w)

    return CoverLetterResult(text=letter, warnings=warnings)
