"""Salary estimation service — uses Ollama to estimate compensation."""
import logging

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import SALARY_PROMPT, SALARY_SYSTEM
from app.schemas import ResumeData, SalaryEstimate

logger = logging.getLogger(__name__)


def _estimate_years(resume: ResumeData) -> str:
    count = len(resume.experience)
    if count == 0:
        return "Entry level (0-1 years)"
    if count <= 2:
        return "Junior (1-3 years)"
    if count <= 4:
        return "Mid-level (3-6 years)"
    return "Senior (6+ years)"


def _education_text(resume: ResumeData) -> str:
    parts = [f"{edu.degree} from {edu.institution}" for edu in resume.education]
    return "; ".join(parts) if parts else "Not specified"


def estimate_salary(
    resume: ResumeData,
    role: str,
    location: str,
) -> SalaryEstimate:
    """Use Ollama to estimate salary range based on skills and experience."""
    client = OllamaClient()

    skills = ", ".join(resume.skills) if resume.skills else "Not specified"
    years = _estimate_years(resume)
    education = _education_text(resume)

    prompt = SALARY_PROMPT.format(
        role=role,
        location=location,
        skills=skills,
        experience_years=years,
        education=education,
    )

    logger.info("Estimating salary for role=%s location=%s", role, location)
    data = client.generate_json(prompt, system=SALARY_SYSTEM)

    def _dec(val: str | int | float | None, default: str = "0") -> str:
        if val is None or val == "":
            return default
        return str(val)

    result = SalaryEstimate(
        role=data.get("role", role),
        location=data.get("location", location),
        experience_years=data.get("experience_years", years),
        salary_range=data.get("salary_range", ""),
        salary_min=_dec(data.get("salary_min")),
        salary_max=_dec(data.get("salary_max")),
        salary_monthly_min=_dec(data.get("salary_monthly_min")),
        salary_monthly_max=_dec(data.get("salary_monthly_max")),
        salary_annual_min=_dec(data.get("salary_annual_min")),
        salary_annual_max=_dec(data.get("salary_annual_max")),
        currency=data.get("currency", ""),
        factors=data.get("factors", []),
        notes=data.get("notes", ""),
    )

    logger.info("Salary estimate: %s %s", result.salary_range, result.currency)
    return result
