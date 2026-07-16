"""AI resume optimization via Ollama with deterministic fact guard.

The AI rewrites summary, headline, and experience bullets.  A FactGuard
then validates every proposed change against the source resume to catch
unsupported numbers, entities, and skills before the user sees them.
"""
import json
import logging

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import OPTIMIZE_PROMPT, OPTIMIZE_SYSTEM
from app.domain.fact_guard import FactGuardResult
from app.schemas import ResumeData
from app.services.ats_engine import ATSResult
from app.services.fact_guard import FactGuard

logger = logging.getLogger(__name__)


def optimize_resume(
    resume: ResumeData,
    jd_text: str,
    ats: ATSResult,
    client: OllamaClient,
) -> tuple[ResumeData, FactGuardResult]:
    """Optimize resume via AI and validate changes with FactGuard.

    Returns:
        A tuple of (optimized_resume, fact_guard_result).
        The fact_guard_result contains safe and flagged changes.
    """
    logger.info("Optimizing resume for ATS (missing_keywords=%d)", len(ats.missing_keywords))
    payload = {
        "summary": resume.summary,
        "headline": resume.headline,
        "skills": resume.skills,
        "experience": [exp.model_dump() for exp in resume.experience],
    }
    prompt = OPTIMIZE_PROMPT.format(
        skills=", ".join(resume.skills) or "(none listed)",
        job_description=jd_text[:6000],
        missing_keywords=", ".join(ats.missing_keywords[:15]) or "(none)",
        resume_json=json.dumps(payload, indent=2),
    )
    data = client.generate_json(prompt, system=OPTIMIZE_SYSTEM)

    optimized = resume.model_copy(deep=True)
    summary = data.get("summary")
    if isinstance(summary, str) and summary.strip():
        optimized.summary = summary.strip()

    experience = data.get("experience")
    if isinstance(experience, list) and len(experience) == len(optimized.experience):
        for original, rewritten in zip(optimized.experience, experience):
            if not isinstance(rewritten, dict):
                continue
            bullets = rewritten.get("bullets")
            if isinstance(bullets, list) and bullets:
                # Titles, companies and dates are intentionally kept from the
                # original entry so facts can never be altered by the model.
                original.bullets = [str(b).strip() for b in bullets if str(b).strip()]
    headline = data.get("headline")

    if isinstance(headline, str) and headline.strip():
        optimized.headline = headline.strip()

    # Run deterministic fact guard
    guard = FactGuard()
    fact_result = guard.validate(source=resume, optimized=optimized)

    logger.info(
        "FactGuard: %d safe, %d flagged",
        len(fact_result.safe_changes), len(fact_result.flagged_changes),
    )

    return optimized, fact_result
