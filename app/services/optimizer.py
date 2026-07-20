"""AI resume optimization via Ollama with deterministic fact guard.

The AI rewrites summary, headline, and experience bullets using indexed
operations (experience_index, bullet_index) instead of text matching.
A FactGuard then validates every proposed change against the source resume
to catch unsupported numbers, entities, and skills before the user sees them.

No proposed changes are applied until the user reviews them.
"""
import json
import logging

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import OPTIMIZE_PROMPT, OPTIMIZE_SYSTEM
from app.domain.analysis import ATSResult
from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
from app.domain.optimization import OptimizationAIOutput
from app.schemas import ResumeData
from app.engines.fact_guard import FactGuard
from app.services.job_context import select_job_context

logger = logging.getLogger(__name__)


def optimize_resume(
    resume: ResumeData,
    jd_text: str,
    ats: ATSResult,
    client: OllamaClient,
) -> tuple[ResumeData, FactGuardResult]:
    """Optimize resume via AI and validate changes with FactGuard.

    Uses preventive constraints (extracted immutable facts) injected into
    the prompt BEFORE generation to reduce hallucinations.  Post-generation
    validation still runs as a safety net.

    Returns:
        A tuple of the unchanged resume copy and the proposed changes.
    """
    logger.info("Optimizing resume for ATS (missing_keywords=%d)", len(ats.missing_keywords))

    guard = FactGuard()

    # Step 1: Extract immutable facts and inject into prompt (preventive)
    constraints = guard.create_constraints(resume)
    logger.info("FactGuard constraints: %d chars", len(constraints))

    payload = {
        "summary": resume.summary,
        "headline": resume.headline,
        "skills": resume.skills,
        "experience": [exp.model_dump() for exp in resume.experience],
    }
    prompt = OPTIMIZE_PROMPT.format(
        skills=", ".join(resume.skills) or "(none listed)",
        job_description=select_job_context(jd_text),
        missing_keywords=", ".join(ats.missing_keywords[:15]) or "(none)",
        resume_json=json.dumps(payload, indent=2),
    )

    # Inject constraints into prompt
    prompt = guard.inject_into_prompt(prompt, constraints)

    # Step 2: Generate with constraints
    ai_output = client.generate_structured(prompt, OptimizationAIOutput, system=OPTIMIZE_SYSTEM)

    # Step 3: Build candidate from AI output using indexed operations
    candidate = resume.model_copy(deep=True)

    if ai_output.summary.strip():
        candidate.summary = ai_output.summary.strip()

    if ai_output.headline.strip():
        candidate.headline = ai_output.headline.strip()

    for operation in ai_output.bullet_rewrites:
        if operation.experience_index >= len(candidate.experience):
            logger.warning(
                "Rejected invalid experience index: %d",
                operation.experience_index,
            )
            continue

        experience = candidate.experience[operation.experience_index]

        if operation.bullet_index >= len(experience.bullets):
            logger.warning(
                "Rejected invalid bullet index: %d",
                operation.bullet_index,
            )
            continue

        experience.bullets[operation.bullet_index] = operation.rewritten.strip()

    # Step 4: Post-generation validation (safety net)
    fact_result = guard.validate(source=resume, optimized=candidate)

    logger.info(
        "FactGuard: %d supported, %d flagged (all pending review)",
        len(fact_result.safe_changes), len(fact_result.flagged_changes),
    )
    return resume.model_copy(deep=True), fact_result


def apply_accepted_changes(
    resume: ResumeData,
    fact_result: FactGuardResult,
) -> ResumeData:
    """Apply all changes that the user has explicitly accepted.

    Call this after the user has reviewed flagged changes and clicked
    Accept on the ones they want to keep.
    """
    result = resume.model_copy(deep=True)
    accepted = [change for change in fact_result.all_changes if change.accepted is True]
    non_deletions = [change for change in accepted if change.rewritten]
    deletions = sorted(
        (change for change in accepted if not change.rewritten),
        key=lambda change: (
            change.experience_index if change.experience_index is not None else -1,
            change.bullet_index if change.bullet_index is not None else -1,
        ),
        reverse=True,
    )
    for change in non_deletions + deletions:
        _apply_change(result, change)
    return result


def _apply_change(resume: ResumeData, change: ProposedChange) -> None:
    """Apply a single ProposedChange to the resume in-place."""
    if change.change_type == ChangeType.SUMMARY:
        resume.summary = change.rewritten
    elif change.change_type == ChangeType.HEADLINE:
        resume.headline = change.rewritten
    elif change.change_type in (ChangeType.BULLET, ChangeType.REWRITE,
                                ChangeType.METRIC_ADD, ChangeType.EMPLOYER_ADD):
        # Apply by immutable coordinates
        if change.experience_index is not None and change.bullet_index is not None:
            if change.experience_index < len(resume.experience):
                experience = resume.experience[change.experience_index]
                if change.bullet_index < len(experience.bullets):
                    if change.rewritten:
                        experience.bullets[change.bullet_index] = change.rewritten
                    else:
                        del experience.bullets[change.bullet_index]
                    return
        logger.warning(
            "Could not apply change: invalid coordinates (exp=%s, bullet=%s)",
            change.experience_index, change.bullet_index,
        )
    elif change.change_type == ChangeType.SKILL_ADD:
        # Append the rewritten skill (the original skill entry is replaced)
        if change.original and change.original in resume.skills:
            idx = resume.skills.index(change.original)
            resume.skills[idx] = change.rewritten
        elif change.rewritten and change.rewritten not in resume.skills:
            resume.skills.append(change.rewritten)
