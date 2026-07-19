"""Standalone summary generation from resume data."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel

from app.ai.prompts import GENERATE_SUMMARY_PROMPT, GENERATE_SUMMARY_SYSTEM
from app.domain.resume import ResumeData

logger = logging.getLogger(__name__)


class SummaryAIOutput(BaseModel):
    summary: str


@dataclass
class SummaryResult:
    summary: str


def generate_summary(
    resume: ResumeData,
    jd_text: str = "",
    client: object | None = None,
) -> SummaryResult:
    """Generate a professional summary from resume experience and skills.

    Parameters
    ----------
    resume:
        The current resume data.
    jd_text:
        Optional job description text for tailoring.
    client:
        OllamaClient instance.  Created from settings if *None*.
    """
    if client is None:
        from app.ai.ollama_client import OllamaClient
        from app.core.settings import settings_service

        client = OllamaClient(settings_service.ollama_url, settings_service.model)

    experience_text = "\n".join(
        f"{e.title} at {e.company} ({e.start_date}-{e.end_date}): "
        + "; ".join(e.bullets)
        for e in resume.experience
    )
    education_text = "\n".join(
        f"{e.degree} — {e.institution} ({e.year})" for e in resume.education
    )

    prompt = GENERATE_SUMMARY_PROMPT.format(
        candidate_name=resume.contact.name,
        headline=resume.headline,
        skills=", ".join(resume.skills),
        experience=experience_text or "No experience provided",
        education=education_text or "No education provided",
        job_description=jd_text or "Not provided",
    )

    output: SummaryAIOutput = client.generate_structured(
        prompt, SummaryAIOutput, system=GENERATE_SUMMARY_SYSTEM
    )
    return SummaryResult(summary=output.summary)
