"""Cover letter generation via Ollama with fact guard."""
import json
import logging
import re

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import COVER_LETTER_PROMPT, COVER_LETTER_SYSTEM
from app.schemas import ResumeData

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


def _check_cover_letter_facts(letter: str, resume: ResumeData) -> list[str]:
    """Return a list of warnings for unsupported claims in the cover letter."""
    warnings: list[str] = []

    # Check for new numbers not in the resume
    resume_text = resume.model_dump_json().lower()
    letter_numbers = set(_NUMBER_RE.findall(letter))
    resume_numbers = set(_NUMBER_RE.findall(resume_text))
    new_numbers = letter_numbers - resume_numbers
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

    # Candidate's own name should not be flagged as an unknown organization
    candidate_name = (resume.contact.name or "").lower()

    # Look for capitalized multi-word proper nouns that might be company names
    company_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+(?:\s+(?:Corp|Inc|Ltd|LLC|Co|Company|Group|Technologies|Systems))?)\b")
    letter_orgs = set(company_pattern.findall(letter))
    for org in letter_orgs:
        if org.lower() not in known_orgs and org.lower() not in {
            "dear hiring manager", "your company", "the team",
        } and org.lower() != candidate_name:
            warnings.append(f"Cover letter mentions organization not in resume: {org}")

    return warnings


def generate_cover_letter(
    resume,
    jd_text,
    client
):
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
        job_description=jd_text[:6000],
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

    # Fact-check the generated cover letter
    warnings = _check_cover_letter_facts(letter, resume)
    if warnings:
        for w in warnings:
            logger.warning("Cover letter fact check: %s", w)
        disclaimer = "\n\n---\nFact-check warnings:\n" + "\n".join(f"- {w}" for w in warnings)
        letter += disclaimer

    return letter
