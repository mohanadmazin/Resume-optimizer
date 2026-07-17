"""AI resume optimization via Ollama with deterministic fact guard.

The AI rewrites summary, headline, and experience bullets.  A FactGuard
then validates every proposed change against the source resume to catch
unsupported numbers, entities, and skills before the user sees them.

Only safe changes are applied to the optimized resume.  Flagged changes
are kept as proposals for user review.
"""
import json
import logging

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import OPTIMIZE_PROMPT, OPTIMIZE_SYSTEM
from app.domain.analysis import ATSResult
from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
from app.schemas import ResumeData
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
        Only safe changes are applied to optimized_resume.  Flagged changes
        are kept in fact_guard_result for user review.
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

    # Build a candidate with ALL AI changes applied
    candidate = resume.model_copy(deep=True)
    summary = data.get("summary")
    if isinstance(summary, str) and summary.strip():
        candidate.summary = summary.strip()

    experience = data.get("experience")
    if isinstance(experience, list) and len(experience) == len(candidate.experience):
        for original, rewritten in zip(candidate.experience, experience):
            if not isinstance(rewritten, dict):
                continue
            bullets = rewritten.get("bullets")
            if isinstance(bullets, list) and bullets:
                original.bullets = [str(b).strip() for b in bullets if str(b).strip()]

    headline = data.get("headline")
    if isinstance(headline, str) and headline.strip():
        candidate.headline = headline.strip()

    # Run deterministic fact guard on the candidate
    guard = FactGuard()
    fact_result = guard.validate(source=resume, optimized=candidate)

    # Build optimized resume: apply only safe changes
    optimized = resume.model_copy(deep=True)

    for change in fact_result.safe_changes:
        _apply_change(optimized, change)

    logger.info(
        "FactGuard: %d safe (applied), %d flagged (pending review)",
        len(fact_result.safe_changes), len(fact_result.flagged_changes),
    )

    return optimized, fact_result


def apply_accepted_changes(
    resume: ResumeData,
    fact_result: FactGuardResult,
) -> ResumeData:
    """Apply all changes that the user has explicitly accepted.

    Call this after the user has reviewed flagged changes and clicked
    Accept on the ones they want to keep.
    """
    optimized = resume.model_copy(deep=True)
    for change in fact_result.safe_changes:
        _apply_change(optimized, change)
    for change in fact_result.flagged_changes:
        if change.accepted:
            _apply_change(optimized, change)
    return optimized


def _apply_change(resume: ResumeData, change: ProposedChange) -> None:
    """Apply a single ProposedChange to the resume in-place."""
    if change.change_type == ChangeType.SUMMARY:
        resume.summary = change.rewritten
    elif change.change_type == ChangeType.HEADLINE:
        resume.headline = change.rewritten
    elif change.change_type == ChangeType.BULLET:
        # Find the matching experience entry and bullet
        for exp in resume.experience:
            section_name = f"{exp.title or 'Experience'}"
            if change.section.startswith(section_name):
                for i, bullet in enumerate(exp.bullets):
                    if bullet.strip() == change.original.strip():
                        exp.bullets[i] = change.rewritten
                        return
                # If not found by exact match, check by index
                break
