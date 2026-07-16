"""Salary estimation service — uses Ollama to estimate compensation."""
import logging
import re
from dataclasses import dataclass, field
from datetime import date

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import SALARY_PROMPT, SALARY_SYSTEM
from app.schemas import ResumeData, SalaryEstimate

logger = logging.getLogger(__name__)

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

_DATE_RE = re.compile(
    r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+)?(\d{4})",
    re.I,
)


@dataclass
class ExperienceEstimate:
    """Numeric experience estimate with date-aware calculation."""

    minimum_years: float = 0.0
    maximum_years: float = 0.0
    confidence: str = "low"
    missing_dates: list[str] = field(default_factory=list)


def _parse_date(text: str) -> date | None:
    """Parse a date string like 'Jan 2020', '2020', 'January 2019' into a date."""
    text = text.strip().lower().replace(".", "")
    if text in ("present", "current", "now"):
        return date.today()

    m = _DATE_RE.search(text)
    if not m:
        return None

    year = int(m.group(1))
    month = 1

    # Try to find a month name before the year
    prefix = text[: m.start()].strip()
    if prefix:
        for name, num in _MONTHS.items():
            if prefix.startswith(name):
                month = num
                break

    return date(year, month, 1)


def _months_between(start: date, end: date) -> float:
    """Return the number of months between two dates as a float."""
    return (end.year - start.year) * 12 + (end.month - start.month)


def _merge_intervals(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Merge overlapping or adjacent date intervals."""
    if not intervals:
        return []
    sorted_ivs = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_ivs[0]]
    for start, end in sorted_ivs[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def estimate_experience(resume: ResumeData) -> ExperienceEstimate:
    """Calculate actual years of experience from date intervals.

    Merges overlapping periods and handles missing dates by assuming
    the position continues to the present (for the most recent entry).
    Returns a min/max range to account for uncertainty.
    """
    today = date.today()
    intervals: list[tuple[date, date]] = []
    missing: list[str] = []

    for exp in resume.experience:
        start = _parse_date(exp.start_date) if exp.start_date else None
        end = _parse_date(exp.end_date) if exp.end_date else None

        if start is None:
            # Cannot use this entry at all
            if exp.company:
                missing.append(exp.company)
            continue

        if end is None:
            # Missing end date — assume still employed (use today)
            # Track as missing only if it's not the most recent-looking entry
            end = today
            if exp.company:
                missing.append(exp.company)

        intervals.append((start, end))

    merged = _merge_intervals(intervals)

    total_months = sum(_months_between(s, e) for s, e in merged)
    min_years = round(total_months / 12, 1)

    # Maximum: if there are missing dates, add a buffer of 1 year per missing entry
    max_years = min_years + len(missing) * 1.0

    # Confidence assessment
    total_entries = len(resume.experience)
    parsed_entries = total_entries - len(missing)
    if total_entries == 0:
        confidence = "low"
    elif len(missing) == 0 and total_entries >= 2:
        confidence = "high"
    elif parsed_entries >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    # At least 0.5 years if there's any experience at all
    if min_years < 0.5 and intervals:
        min_years = 0.5

    return ExperienceEstimate(
        minimum_years=min_years,
        maximum_years=round(max_years, 1),
        confidence=confidence,
        missing_dates=missing,
    )


def _format_experience(est: ExperienceEstimate) -> str:
    """Format the experience estimate for the salary prompt."""
    if est.minimum_years == est.maximum_years:
        years_str = f"{est.minimum_years:.0f} years"
    else:
        years_str = f"{est.minimum_years:.1f} to {est.maximum_years:.1f} years"

    parts = [f"{years_str} of professional experience"]
    if est.confidence == "low":
        parts.append("(some dates missing)")
    elif est.confidence == "medium":
        parts.append("(most dates available)")
    return ", ".join(parts)


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
    exp = estimate_experience(resume)
    years = _format_experience(exp)
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
        experience_years=years,
        salary_range=data.get("salary_range", ""),
        salary_min=_dec(data.get("salary_min")),
        salary_max=_dec(data.get("salary_max")),
        salary_monthly_min=_dec(data.get("salary_monthly_min")),
        salary_monthly_max=_dec(data.get("salary_monthly_max")),
        salary_annual_min=_dec(data.get("salary_annual_min")),
        salary_annual_max=_dec(data.get("salary_annual_max")),
        currency=data.get("currency", ""),
        confidence=exp.confidence,
        factors=data.get("factors", []),
        notes=data.get("notes", ""),
    )

    logger.info("Salary estimate: %s %s", result.salary_range, result.currency)
    return result
