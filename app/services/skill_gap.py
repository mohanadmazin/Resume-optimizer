"""Skill gap analysis service — compares candidate skills vs market demand."""
import logging

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import SKILL_GAP_PROMPT, SKILL_GAP_SYSTEM
from app.schemas import ResumeData, SkillGapResult

logger = logging.getLogger(__name__)


def _experience_summary(resume: ResumeData) -> str:
    parts = []
    for exp in resume.experience:
        parts.append(f"{exp.title} at {exp.company} ({exp.start_date}-{exp.end_date})")
    return "; ".join(parts) if parts else "No experience listed"


def analyze_skill_gap(
    resume: ResumeData,
    job_description_or_role: str,
    target_role: str | None = None,
    client: OllamaClient | None = None,
) -> SkillGapResult:
    """Use Ollama to compare the candidate's skills against market demand."""
    # Backward compatibility: older callers supplied only (resume, role).
    job_description = job_description_or_role if target_role is not None else ""
    target_role = target_role or job_description_or_role
    client = client or OllamaClient()

    candidate_skills = ", ".join(resume.skills) if resume.skills else "None listed"
    experience_summary = _experience_summary(resume)

    prompt = SKILL_GAP_PROMPT.format(
        target_role=target_role,
        candidate_skills=candidate_skills,
        experience_summary=experience_summary,
        job_description=job_description,
    )

    logger.info("Running skill gap analysis for role: %s", target_role)
    data = client.generate_json(prompt, system=SKILL_GAP_SYSTEM)

    result = SkillGapResult(
        target_role=target_role,
        market_skills=data.get("required_skills", data.get("market_skills", [])),
        matched=data.get("matched", []),
        missing=data.get("missing", []),
        summary=data.get("summary", ""),
    )
    result.your_skills = resume.skills

    logger.info(
        "Skill gap: matched=%d missing=%d",
        len(result.matched),
        len(result.missing),
    )
    return result
