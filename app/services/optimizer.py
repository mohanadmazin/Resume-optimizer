"""AI resume optimization via Ollama. Facts are always preserved:
only the summary and experience bullets are rewritten."""
import json

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import OPTIMIZE_PROMPT, OPTIMIZE_SYSTEM
from app.schemas import ResumeData
from app.services.ats_engine import ATSResult


def optimize_resume(resume: ResumeData, jd_text: str, ats: ATSResult, client: OllamaClient) -> ResumeData:
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
    return optimized