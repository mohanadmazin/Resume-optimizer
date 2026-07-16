"""Cover letter generation via Ollama."""
import json
import logging
import re

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import COVER_LETTER_PROMPT, COVER_LETTER_SYSTEM
from app.schemas import ResumeData

logger = logging.getLogger(__name__)


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

    return letter
