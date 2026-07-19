"""Standalone headline generation from resume data."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel

from app.ai.prompts import GENERATE_HEADLINE_PROMPT, GENERATE_HEADLINE_SYSTEM
from app.domain.resume import ResumeData

logger = logging.getLogger(__name__)


class HeadlineAIOutput(BaseModel):
    headline: str


@dataclass
class HeadlineResult:
    headline: str


def generate_headline(
    resume: ResumeData,
    jd_text: str = "",
    client: object | None = None,
) -> HeadlineResult:
    """Generate a professional headline from resume data.

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
        f"{e.title} at {e.company}" for e in resume.experience
    )

    prompt = GENERATE_HEADLINE_PROMPT.format(
        candidate_name=resume.contact.name,
        current_headline=resume.headline,
        skills=", ".join(resume.skills),
        experience=experience_text or "No experience provided",
        job_description=jd_text or "Not provided",
    )

    output: HeadlineAIOutput = client.generate_structured(
        prompt, HeadlineAIOutput, system=GENERATE_HEADLINE_SYSTEM
    )
    return HeadlineResult(headline=output.headline)
