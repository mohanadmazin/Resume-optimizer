"""Benchmark-driven salary estimation with deterministic arithmetic.

The language model is used only for role classification and evidence-based
adjustments. Benchmark retrieval, currency, weighting validation, range
calculation, rounding, and annual conversion are application-controlled.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Iterable, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.ai.ollama_client import OllamaCancelledError, OllamaClient
from app.ai.prompts import SALARY_PROMPT, SALARY_SYSTEM
from app.data.salary_benchmarks import (
    MARKETS_BY_COUNTRY_CODE,
    RoleBenchmark,
    SalaryMarket,
)
from app.schemas import ResumeData, SalaryEstimate
from app.domain.salary import (
    SalaryAdjustment,
    SalaryBenchmarkSelection,
    SalaryConfidence,
    SalaryLocation,
)

logger = logging.getLogger(__name__)

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_DATE_RE = re.compile(
    r"^(?:(?P<month>[A-Za-z]{3,9})\.?\s+)?(?P<year>\d{4})$",
    re.I,
)
_YEAR_RE = re.compile(r"(?P<year>\d{4})")
_TOKEN_RE = re.compile(r"[a-z0-9+#.-]+")

_COUNTRY_ALIASES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "MY": ("Malaysia", "MYR", ("malaysia", "kuala lumpur", "selangor", "penang", "johor", "putrajaya", "cyberjaya")),
    "SG": ("Singapore", "SGD", ("singapore",)),
    "ID": ("Indonesia", "IDR", ("indonesia", "jakarta", "surabaya", "bandung")),
    "PH": ("Philippines", "PHP", ("philippines", "manila", "makati", "cebu")),
    "TH": ("Thailand", "THB", ("thailand", "bangkok", "chiang mai")),
    "VN": ("Vietnam", "VND", ("vietnam", "ho chi minh", "hanoi", "da nang")),
    "US": ("United States", "USD", ("united states", "usa", "u.s.", "new york", "san francisco", "seattle")),
    "GB": ("United Kingdom", "GBP", ("united kingdom", "uk", "london", "manchester")),
    "AU": ("Australia", "AUD", ("australia", "sydney", "melbourne", "brisbane")),
}

_GENERIC_ROLE_TOKENS = {
    "engineer",
    "engineering",
    "senior",
    "junior",
    "lead",
    "specialist",
    "technical",
    "technology",
    "it",
    "the",
    "and",
    "of",
}

_ALLOWED_ADJUSTMENTS: dict[str, tuple[Decimal, Decimal]] = {
    "location": (Decimal("0.90"), Decimal("1.10")),
    "industry": (Decimal("0.95"), Decimal("1.10")),
    "scope": (Decimal("0.95"), Decimal("1.15")),
    "scarce_skills": (Decimal("1.00"), Decimal("1.10")),
    "certifications": (Decimal("1.00"), Decimal("1.05")),
    "education": (Decimal("0.98"), Decimal("1.03")),
}


@dataclass
class ExperienceEstimate:
    """Numeric experience estimate with date-aware calculation."""

    minimum_years: float = 0.0
    maximum_years: float = 0.0
    confidence: str = "low"
    missing_dates: list[str] = field(default_factory=list)
    future_start: bool = False


class _AISelectedBenchmark(BaseModel):
    role_key: str
    weight: Decimal = Decimal("0")

    @field_validator("weight", mode="before")
    @classmethod
    def _coerce_weight(cls, value):
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")


class _AIAdjustment(BaseModel):
    factor: str
    multiplier: Decimal = Decimal("1")
    reason: str = ""

    @field_validator("multiplier", mode="before")
    @classmethod
    def _coerce_multiplier(cls, value):
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("1")


class _AIConfidence(BaseModel):
    score: Decimal = Decimal("0")
    reasons: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)


class _SalaryAIAnalysis(BaseModel):
    normalized_role: str = ""
    role_family: str = ""
    specialization: str = ""
    career_track: Literal["individual_contributor", "management"] = (
        "individual_contributor"
    )
    relevant_experience_years: Decimal = Decimal("0")
    specialization_experience_years: Decimal = Decimal("0")
    management_experience_years: Decimal = Decimal("0")
    seniority: str = "unknown"
    selected_benchmarks: list[_AISelectedBenchmark] = Field(default_factory=list)
    adjustments: list[_AIAdjustment] = Field(default_factory=list)
    confidence: _AIConfidence = Field(default_factory=_AIConfidence)
    factors: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    additional_compensation_notes: str = ""
    notes: str = ""


@dataclass(frozen=True)
class _RoleCandidate:
    benchmark: RoleBenchmark
    score: float


def _parse_date(text: str) -> date | None:
    """Parse ``Mar 2021``, ``2021`` or ``Present`` into a month-level date."""
    normalized = (text or "").strip().lower().replace(",", "")
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized in {"present", "current", "now", "ongoing"}:
        return date.today()

    match = _DATE_RE.match(normalized)
    if match:
        year = int(match.group("year"))
        month_name = (match.group("month") or "").rstrip(".").lower()
        month = _MONTHS.get(month_name, 1)
        try:
            return date(year, month, 1)
        except ValueError:
            return None

    # Graceful fallback for text such as "Sep 2020 - contract".
    year_match = _YEAR_RE.search(normalized)
    if not year_match:
        return None
    year = int(year_match.group("year"))
    prefix = normalized[: year_match.start()].strip(" .-/")
    month = 1
    if prefix:
        month_token = prefix.split()[-1].rstrip(".")
        month = _MONTHS.get(month_token, 1)
    try:
        return date(year, month, 1)
    except ValueError:
        return None


def _months_between(start: date, end: date) -> float:
    """Return whole month distance between two month-level dates."""
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def _merge_intervals(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Merge overlapping or adjacent employment intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda item: item[0])
    merged = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return merged


def _experience_intervals(
    resume: ResumeData,
    include: Callable[[object], bool] | None = None,
) -> tuple[list[tuple[date, date]], list[str], bool]:
    today = date.today().replace(day=1)
    records: list[tuple[date, date | None, str, object]] = []
    unresolved: list[str] = []
    future_start = False

    for experience in resume.experience:
        if include is not None and not include(experience):
            continue

        start = _parse_date(experience.start_date)
        end = _parse_date(experience.end_date)
        label = experience.company or experience.title or "Unknown role"

        if start is None:
            unresolved.append(label)
            continue
        if start > today:
            unresolved.append(label)
            future_start = True
            continue
        if end is not None:
            end = min(end, today)
            if end < start:
                unresolved.append(label)
                continue

        records.append((start, end, label, experience))

    records.sort(key=lambda item: item[0])
    intervals: list[tuple[date, date]] = []
    for index, (start, end, label, _experience) in enumerate(records):
        if end is None:
            if index == len(records) - 1:
                end = today
            else:
                end = min(records[index + 1][0], today)
            unresolved.append(label)
        if end >= start:
            intervals.append((start, end))

    return _merge_intervals(intervals), list(dict.fromkeys(unresolved)), future_start


def estimate_experience(resume: ResumeData) -> ExperienceEstimate:
    """Calculate non-overlapping total professional experience."""
    intervals, unresolved, future_start = _experience_intervals(resume)
    total_months = sum(_months_between(start, end) for start, end in intervals)
    years = round(total_months / 12, 1)

    total_entries = len(resume.experience)
    parsed_entries = max(0, total_entries - len(unresolved))
    if total_entries == 0:
        confidence = "low"
    elif not unresolved and parsed_entries >= 2:
        confidence = "high"
    elif parsed_entries >= 1:
        confidence = "medium"
    else:
        confidence = "low"

    return ExperienceEstimate(
        minimum_years=years,
        maximum_years=years,
        confidence=confidence,
        missing_dates=unresolved,
        future_start=future_start,
    )


def _normalize_text(value: str) -> str:
    value = (value or "").casefold().replace("–", "-").replace("—", "-")
    value = re.sub(r"[^a-z0-9+#./-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(_normalize_text(value))
        if token not in _GENERIC_ROLE_TOKENS and len(token) > 1
    }


def _normalize_location(location: str) -> SalaryLocation:
    normalized = _normalize_text(location)
    country_code = ""
    country = ""
    currency = ""

    for code, (country_name, currency_code, aliases) in _COUNTRY_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            country_code = code
            country = country_name
            currency = currency_code
            break

    parts = [part.strip() for part in re.split(r"[,|]", location or "") if part.strip()]
    city = parts[0] if parts else ""
    region = parts[1] if len(parts) > 2 else ""

    # A country-only location should not repeat the country as the city.
    if _normalize_text(city) in {_normalize_text(country), country_code.casefold()}:
        city = ""

    return SalaryLocation(
        city=city,
        region=region,
        country=country,
        country_code=country_code,
        currency=currency,
    )


def _resume_context(resume: ResumeData) -> str:
    experience = " ".join(
        " ".join([item.title, item.company, item.location, *item.bullets])
        for item in resume.experience
    )
    projects = " ".join(
        " ".join([project.title, project.meta, project.description, *project.bullets])
        for project in resume.projects
    )
    return " ".join(
        [
            resume.headline,
            resume.summary,
            " ".join(resume.skills),
            experience,
            projects,
            " ".join(resume.certifications),
        ]
    )


def _has_management_evidence(role: str, resume: ResumeData) -> bool:
    title_text = _normalize_text(
        " ".join([role, resume.headline, *(item.title for item in resume.experience)])
    )
    if re.search(r"\b(manager|director|head of|vice president|vp)\b", title_text):
        return True

    evidence = _normalize_text(_resume_context(resume))
    patterns = (
        "direct reports",
        "hiring",
        "hired",
        "budget ownership",
        "owned budget",
        "portfolio ownership",
        "department ownership",
        "performance reviews",
        "people management",
    )
    return any(pattern in evidence for pattern in patterns)


def _score_role_candidates(
    market: SalaryMarket,
    role: str,
    resume: ResumeData,
) -> list[_RoleCandidate]:
    role_text = _normalize_text(role)
    context = _normalize_text(" ".join([role, _resume_context(resume)]))
    role_tokens = _tokens(role)
    management_evidence = _has_management_evidence(role, resume)
    candidates: list[_RoleCandidate] = []

    for benchmark in market.roles.values():
        score = 0.0
        for alias in benchmark.aliases:
            alias_text = _normalize_text(alias)
            alias_tokens = _tokens(alias)
            if role_text == alias_text:
                score += 20.0
            elif alias_text and alias_text in role_text:
                score += 14.0
            elif alias_text and alias_text in context:
                score += 7.0

            if alias_tokens:
                overlap = len(role_tokens & alias_tokens) / len(alias_tokens)
                score += overlap * 6.0

        for keyword in benchmark.keywords:
            keyword_text = _normalize_text(keyword)
            if keyword_text in role_text:
                score += 4.0
            elif keyword_text in context:
                score += 1.25

        if benchmark.career_track == "management" and not management_evidence:
            score *= 0.45

        if score > 0:
            candidates.append(_RoleCandidate(benchmark=benchmark, score=score))

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:6]


def _candidate_weights(candidates: list[_RoleCandidate]) -> list[tuple[str, Decimal]]:
    if not candidates:
        return []

    top_score = candidates[0].score
    selected = [candidate for candidate in candidates[:3] if candidate.score >= top_score * 0.48]
    if not selected:
        selected = candidates[:1]

    raw = [max(candidate.score, 0.01) ** 1.35 for candidate in selected]
    total = sum(raw)
    weights = [Decimal(str(value / total)) for value in raw]
    return [(candidate.benchmark.key, weight) for candidate, weight in zip(selected, weights)]


def _experience_matches_benchmarks(experience, benchmarks: Iterable[RoleBenchmark]) -> bool:
    text = _normalize_text(
        " ".join([experience.title, experience.company, experience.location, *experience.bullets])
    )
    text_tokens = _tokens(text)
    for benchmark in benchmarks:
        if any(_normalize_text(alias) in text for alias in benchmark.aliases):
            return True
        keyword_hits = sum(_normalize_text(keyword) in text for keyword in benchmark.keywords)
        benchmark_tokens = set().union(*(_tokens(alias) for alias in benchmark.aliases))
        token_hits = len(text_tokens & benchmark_tokens)
        if keyword_hits >= 1 or token_hits >= 1:
            return True
    return False


def _estimate_relevant_experience(
    resume: ResumeData,
    benchmarks: list[RoleBenchmark],
) -> ExperienceEstimate:
    intervals, unresolved, future_start = _experience_intervals(
        resume,
        include=lambda experience: _experience_matches_benchmarks(experience, benchmarks),
    )
    months = sum(_months_between(start, end) for start, end in intervals)
    years = round(months / 12, 1)
    if not intervals:
        confidence = "low"
    elif not unresolved:
        confidence = "high"
    else:
        confidence = "medium"
    return ExperienceEstimate(
        minimum_years=years,
        maximum_years=years,
        confidence=confidence,
        missing_dates=unresolved,
        future_start=future_start,
    )


def _format_experience(estimate: ExperienceEstimate) -> str:
    years = estimate.minimum_years
    value = f"{int(years)}" if years == int(years) else f"{years:.1f}"
    return f"{value} years ({estimate.confidence} date confidence)"


def _education_text(resume: ResumeData) -> str:
    rows = []
    for education in resume.education:
        details = [education.degree, education.institution, education.location, education.cgpa, education.year]
        rows.append(" | ".join(value for value in details if value))
    return "; ".join(rows) if rows else "Not provided"


def _experience_text(resume: ResumeData) -> str:
    rows = []
    for item in resume.experience:
        header = " | ".join(
            value for value in (item.title, item.company, item.location, item.start_date, item.end_date) if value
        )
        bullets = "; ".join(item.bullets)
        rows.append(f"{header}: {bullets}" if bullets else header)
    return "\n".join(rows) if rows else "Not provided"


def _scope_text(resume: ResumeData) -> str:
    project_rows = []
    for project in resume.projects:
        project_rows.append(
            " | ".join(
                value
                for value in (
                    project.title,
                    project.meta,
                    project.start_date,
                    project.end_date,
                    project.description,
                    "; ".join(project.bullets),
                )
                if value
            )
        )
    experience_bullets = " ".join(
        bullet for experience in resume.experience for bullet in experience.bullets
    )
    return "\n".join(project_rows + [experience_bullets]) or "Not provided"


def _benchmark_context(market: SalaryMarket) -> str:
    return json.dumps(
        {
            "market": market.country,
            "country_code": market.country_code,
            "currency": market.currency,
            "benchmark_year": market.benchmark_year,
            "compensation_basis": market.compensation_basis,
            "source_name": market.source_name,
            "macro_reference": market.macro_reference,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _candidate_context(candidates: list[_RoleCandidate]) -> str:
    return json.dumps(
        [
            {
                "role_key": candidate.benchmark.key,
                "role": candidate.benchmark.label,
                "family": candidate.benchmark.family,
                "career_track": candidate.benchmark.career_track,
                "monthly_low": int(candidate.benchmark.low),
                "monthly_median": int(candidate.benchmark.median),
                "monthly_high": int(candidate.benchmark.high),
                "deterministic_match_score": round(candidate.score, 2),
            }
            for candidate in candidates
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _safe_ai_analysis(client: OllamaClient, prompt: str) -> _SalaryAIAnalysis | None:
    try:
        raw = client.generate_json(prompt, system=SALARY_SYSTEM)
        return _SalaryAIAnalysis.model_validate(raw)
    except OllamaCancelledError:
        raise
    except (ValidationError, Exception) as exc:  # deterministic fallback is intentional
        logger.warning("Salary AI classification failed; using deterministic fallback: %s", exc)
        return None


def _validated_selection(
    market: SalaryMarket,
    candidates: list[_RoleCandidate],
    analysis: _SalaryAIAnalysis | None,
) -> list[tuple[RoleBenchmark, Decimal]]:
    allowed = {candidate.benchmark.key: candidate.benchmark for candidate in candidates}
    selected: list[tuple[RoleBenchmark, Decimal]] = []

    if analysis is not None:
        for item in analysis.selected_benchmarks[:3]:
            benchmark = allowed.get(item.role_key)
            if benchmark is None or item.weight <= 0:
                continue
            selected.append((benchmark, item.weight))

    if not selected:
        selected = [
            (market.roles[key], weight)
            for key, weight in _candidate_weights(candidates)
            if key in market.roles
        ]

    total = sum((weight for _benchmark, weight in selected), Decimal("0"))
    if total <= 0:
        return []
    return [(benchmark, weight / total) for benchmark, weight in selected]


def _deterministic_adjustments(
    resume: ResumeData,
    selected: list[tuple[RoleBenchmark, Decimal]],
) -> list[SalaryAdjustment]:
    context = _normalize_text(_resume_context(resume))
    skill_text = _normalize_text(" ".join(resume.skills))
    adjustments: list[SalaryAdjustment] = []

    scope_markers = (
        "end-to-end",
        "architecture",
        "designed",
        "led",
        "cutover",
        "handover",
        "multi-site",
        "enterprise",
    )
    metric_count = len(re.findall(r"\b\d+(?:\.\d+)?(?:%|\+)?\b", context))
    scope_hits = sum(marker in context for marker in scope_markers)
    if scope_hits >= 3 or metric_count >= 5:
        adjustments.append(
            SalaryAdjustment(
                factor="scope",
                multiplier=Decimal("1.05"),
                reason="Evidence shows broad delivery scope and quantified operational impact.",
            )
        )

    relevant_keywords = {
        _normalize_text(keyword)
        for benchmark, _weight in selected
        for keyword in benchmark.keywords
    }
    skill_hits = sum(keyword in skill_text for keyword in relevant_keywords if keyword)
    if skill_hits >= 6:
        multiplier = Decimal("1.06")
    elif skill_hits >= 3:
        multiplier = Decimal("1.03")
    else:
        multiplier = Decimal("1.00")
    if multiplier > 1:
        adjustments.append(
            SalaryAdjustment(
                factor="scarce_skills",
                multiplier=multiplier,
                reason=f"Candidate shows {skill_hits} benchmark-relevant specialist skill signals.",
            )
        )

    certification_text = _normalize_text(" ".join(resume.certifications))
    certification_hits = sum(
        token in certification_text
        for token in ("cisco", "ccnp", "palo alto", "cato", "security", "firewall", "mikrotik")
    )
    if certification_hits >= 2:
        adjustments.append(
            SalaryAdjustment(
                factor="certifications",
                multiplier=Decimal("1.02"),
                reason="Multiple role-relevant technical certifications are listed.",
            )
        )

    education_text = _normalize_text(_education_text(resume))
    if "master" in education_text and any(
        token in education_text for token in ("network", "computer", "security", "information technology")
    ):
        adjustments.append(
            SalaryAdjustment(
                factor="education",
                multiplier=Decimal("1.02"),
                reason="A role-relevant master's qualification is listed.",
            )
        )

    return adjustments


def _validated_adjustments(
    analysis: _SalaryAIAnalysis | None,
    deterministic: list[SalaryAdjustment],
) -> list[SalaryAdjustment]:
    if analysis is None or not analysis.adjustments:
        return deterministic

    accepted: dict[str, SalaryAdjustment] = {item.factor: item for item in deterministic}
    for item in analysis.adjustments:
        factor = item.factor.strip().casefold()
        bounds = _ALLOWED_ADJUSTMENTS.get(factor)
        if bounds is None or not item.reason.strip():
            continue
        minimum, maximum = bounds
        multiplier = max(minimum, min(maximum, item.multiplier))
        accepted[factor] = SalaryAdjustment(
            factor=factor,
            multiplier=multiplier,
            reason=item.reason.strip(),
        )
    return list(accepted.values())


def _combined_multiplier(adjustments: list[SalaryAdjustment]) -> Decimal:
    result = Decimal("1")
    for adjustment in adjustments:
        result *= adjustment.multiplier
    return max(Decimal("0.80"), min(Decimal("1.25"), result))


def _blend_benchmarks(
    selected: list[tuple[RoleBenchmark, Decimal]],
) -> tuple[Decimal, Decimal, Decimal]:
    low = sum((benchmark.low * weight for benchmark, weight in selected), Decimal("0"))
    median = sum((benchmark.median * weight for benchmark, weight in selected), Decimal("0"))
    high = sum((benchmark.high * weight for benchmark, weight in selected), Decimal("0"))
    return low, median, high


def _seniority_for_years(years: Decimal, management: bool) -> str:
    if management and years >= 5:
        return "manager"
    if years < 2:
        return "entry"
    if years < 5:
        return "mid"
    if years < 9:
        return "senior"
    return "lead"


def _position_in_benchmark(
    low: Decimal,
    median: Decimal,
    high: Decimal,
    relevant_years: Decimal,
) -> Decimal:
    years = max(Decimal("0"), relevant_years)
    if years < 2:
        ratio = Decimal("0.15") + years / Decimal("2") * Decimal("0.20")
        return low + (median - low) * ratio
    if years < 5:
        ratio = Decimal("0.45") + (years - 2) / Decimal("3") * Decimal("0.35")
        return low + (median - low) * ratio
    if years < 9:
        ratio = Decimal("0.15") + (years - 5) / Decimal("4") * Decimal("0.45")
        return median + (high - median) * ratio
    ratio = min(Decimal("0.82"), Decimal("0.60") + (years - 9) * Decimal("0.035"))
    return median + (high - median) * ratio


def _round_money(value: Decimal, currency: str) -> Decimal:
    increments = {
        "MYR": Decimal("100"),
        "SGD": Decimal("100"),
        "USD": Decimal("100"),
        "GBP": Decimal("100"),
        "AUD": Decimal("100"),
        "THB": Decimal("500"),
        "PHP": Decimal("1000"),
        "IDR": Decimal("100000"),
        "VND": Decimal("100000"),
    }
    increment = increments.get(currency, Decimal("100"))
    return (value / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * increment


def _build_range(
    low: Decimal,
    median: Decimal,
    high: Decimal,
    relevant_years: Decimal,
    multiplier: Decimal,
    currency: str,
) -> tuple[Decimal, Decimal, Decimal]:
    target = _position_in_benchmark(low, median, high, relevant_years) * multiplier
    minimum = target * Decimal("0.88")
    maximum = target * Decimal("1.12")

    # Stay close to the published benchmark envelope while allowing a modest
    # evidence-based premium or discount.
    minimum = max(low * Decimal("0.90"), minimum)
    maximum = min(high * Decimal("1.08"), maximum)
    midpoint = max(minimum, min(maximum, target))

    if minimum > 0 and maximum / minimum > Decimal("1.60"):
        maximum = minimum * Decimal("1.60")
        midpoint = min(midpoint, maximum)

    rounded = tuple(_round_money(value, currency) for value in (minimum, midpoint, maximum))
    return rounded  # type: ignore[return-value]


def _confidence_details(
    location: SalaryLocation,
    candidates: list[_RoleCandidate],
    total_experience: ExperienceEstimate,
    relevant_experience: ExperienceEstimate,
    analysis: _SalaryAIAnalysis | None,
    responsibilities: str,
) -> SalaryConfidence:
    score = Decimal("0.20")
    reasons: list[str] = []
    missing: list[str] = []

    if location.country_code:
        score += Decimal("0.15")
        reasons.append("Country and currency were normalized.")
    else:
        missing.append("Recognizable country")

    if location.city:
        score += Decimal("0.08")
    else:
        missing.append("City")

    if candidates:
        top = candidates[0].score
        score += Decimal("0.22") if top >= 16 else Decimal("0.14") if top >= 8 else Decimal("0.07")
        reasons.append("Role was matched to versioned benchmark records.")
    else:
        missing.append("Close role benchmark")

    if total_experience.confidence == "high":
        score += Decimal("0.16")
        reasons.append("Employment dates support a high-confidence experience estimate.")
    elif total_experience.confidence == "medium":
        score += Decimal("0.10")
    else:
        missing.append("Complete employment dates")

    if relevant_experience.minimum_years > 0:
        score += Decimal("0.10")
    else:
        missing.append("Clearly role-relevant employment history")

    if responsibilities.strip():
        score += Decimal("0.05")
    else:
        missing.append("Target-job responsibilities")

    if analysis is not None:
        ai_score = max(Decimal("0"), min(Decimal("1"), analysis.confidence.score))
        score = score * Decimal("0.80") + ai_score * Decimal("0.20")
        reasons.extend(reason for reason in analysis.confidence.reasons if reason)
        missing.extend(item for item in analysis.confidence.missing_inputs if item)

    score = max(Decimal("0"), min(Decimal("1"), score))
    if score >= Decimal("0.80"):
        level = "high"
    elif score >= Decimal("0.55"):
        level = "medium"
    else:
        level = "low"

    return SalaryConfidence(
        score=score.quantize(Decimal("0.01")),
        level=level,
        reasons=list(dict.fromkeys(reasons)),
        missing_inputs=list(dict.fromkeys(missing)),
    )


def _insufficient_estimate(
    role: str,
    location_text: str,
    location: SalaryLocation,
    notes: str,
) -> SalaryEstimate:
    confidence = SalaryConfidence(
        score=Decimal("0.15"),
        level="low",
        reasons=["No supported versioned benchmark market was available."],
        missing_inputs=["Supported local benchmark dataset"],
    )
    return SalaryEstimate(
        status="insufficient_data",
        role=role,
        normalized_role=role,
        location=location_text,
        location_details=location,
        currency=location.currency,
        salary_source="No supported benchmark dataset",
        confidence="low",
        confidence_details=confidence,
        notes=notes,
        assumptions=["No salary amount was generated without a supported local benchmark."],
    )


def estimate_salary(
    resume: ResumeData,
    role: str,
    location: str,
    client: OllamaClient | None = None,
    *,
    responsibilities: str = "",
    industry: str = "",
    company_context: str = "",
) -> SalaryEstimate:
    """Estimate base salary from versioned benchmarks and validated evidence.

    Only Malaysia is bundled with a reviewed local benchmark dataset. Other
    countries return ``insufficient_data`` rather than converting or inventing
    salaries from another market.
    """
    normalized_location = _normalize_location(location)
    market = MARKETS_BY_COUNTRY_CODE.get(normalized_location.country_code)
    if market is None:
        return _insufficient_estimate(
            role,
            location,
            normalized_location,
            "A local benchmark dataset is not bundled for this country. Add a versioned market dataset before estimating salary.",
        )

    candidates = _score_role_candidates(market, role, resume)
    if not candidates:
        return _insufficient_estimate(
            role,
            location,
            normalized_location,
            "No sufficiently related benchmark role was found for the requested title and resume evidence.",
        )

    deterministic_selection = _candidate_weights(candidates)
    deterministic_benchmarks = [
        market.roles[key] for key, _weight in deterministic_selection if key in market.roles
    ]
    total_experience = estimate_experience(resume)
    relevant_experience = _estimate_relevant_experience(resume, deterministic_benchmarks)

    if client is None:
        client = OllamaClient()

    prompt = SALARY_PROMPT.format(
        benchmark_context=_benchmark_context(market),
        role_candidates=_candidate_context(candidates),
        role=role,
        location=json.dumps(normalized_location.model_dump(), ensure_ascii=False),
        responsibilities=responsibilities or "Not provided",
        industry=industry or "Not provided",
        company_context=company_context or "Not provided",
        profile_summary="\n".join(value for value in (resume.headline, resume.summary) if value) or "Not provided",
        skills=", ".join(resume.skills) if resume.skills else "Not provided",
        experience_history=_experience_text(resume),
        experience_years=_format_experience(total_experience),
        relevant_experience=_format_experience(relevant_experience),
        scope=_scope_text(resume),
        education=_education_text(resume),
        certifications="; ".join(resume.certifications) if resume.certifications else "Not provided",
    )

    logger.info("Estimating salary using %s for role=%s location=%s", market.source_name, role, location)
    analysis = _safe_ai_analysis(client, prompt)
    selected = _validated_selection(market, candidates, analysis)
    if not selected:
        return _insufficient_estimate(
            role,
            location,
            normalized_location,
            "The role could not be mapped to a valid benchmark selection.",
        )

    management_evidence = _has_management_evidence(role, resume)
    if analysis is not None and analysis.career_track == "management" and not management_evidence:
        career_track = "individual_contributor"
    elif analysis is not None:
        career_track = analysis.career_track
    else:
        career_track = "management" if management_evidence else "individual_contributor"

    deterministic_relevant = Decimal(str(relevant_experience.minimum_years))
    total_years = Decimal(str(total_experience.minimum_years))
    if analysis is not None:
        ai_relevant = max(Decimal("0"), min(total_years, analysis.relevant_experience_years))
        # Blend the model interpretation with date-derived evidence rather than
        # allowing either source to dominate completely.
        relevant_years = (
            deterministic_relevant * Decimal("0.70") + ai_relevant * Decimal("0.30")
        )
    else:
        relevant_years = deterministic_relevant
    relevant_years = relevant_years.quantize(Decimal("0.1"))

    specialization_years = (
        max(Decimal("0"), min(total_years, analysis.specialization_experience_years))
        if analysis is not None
        else relevant_years
    )
    management_years = (
        max(Decimal("0"), min(total_years, analysis.management_experience_years))
        if analysis is not None and management_evidence
        else Decimal("0")
    )

    deterministic_adjustments = _deterministic_adjustments(resume, selected)
    adjustments = _validated_adjustments(analysis, deterministic_adjustments)
    multiplier = _combined_multiplier(adjustments)

    blended_low, blended_median, blended_high = _blend_benchmarks(selected)
    monthly_min, monthly_mid, monthly_max = _build_range(
        blended_low,
        blended_median,
        blended_high,
        relevant_years,
        multiplier,
        market.currency,
    )

    confidence = _confidence_details(
        normalized_location,
        candidates,
        total_experience,
        relevant_experience,
        analysis,
        responsibilities,
    )

    normalized_role = (
        analysis.normalized_role.strip()
        if analysis is not None and analysis.normalized_role.strip()
        else selected[0][0].label
    )
    role_family = (
        analysis.role_family.strip()
        if analysis is not None and analysis.role_family.strip()
        else selected[0][0].family
    )
    specialization = analysis.specialization.strip() if analysis is not None else ""
    seniority = (
        analysis.seniority.strip().casefold()
        if analysis is not None and analysis.seniority.strip()
        else _seniority_for_years(relevant_years, career_track == "management")
    )
    allowed_seniority = {"entry", "mid", "senior", "lead", "manager", "director", "unknown"}
    if seniority not in allowed_seniority:
        seniority = _seniority_for_years(relevant_years, career_track == "management")

    selected_models = [
        SalaryBenchmarkSelection(
            role_key=benchmark.key,
            role=benchmark.label,
            weight=weight.quantize(Decimal("0.001")),
            low=benchmark.low,
            median=benchmark.median,
            high=benchmark.high,
        )
        for benchmark, weight in selected
    ]

    factors = [
        f"{benchmark.label}: {weight * Decimal('100'):.0f}% benchmark weight"
        for benchmark, weight in selected
    ]
    factors.extend(
        f"{adjustment.factor.replace('_', ' ').title()}: x{adjustment.multiplier} — {adjustment.reason}"
        for adjustment in adjustments
    )
    if analysis is not None:
        factors.extend(item for item in analysis.factors if item)

    assumptions = [
        "Estimate represents basic monthly base salary for a permanent role.",
        "Annual salary is monthly base salary multiplied by 12.",
        "Bonus, AWS, commission, allowances, equity, and benefits are excluded.",
    ]
    if not responsibilities.strip():
        assumptions.append("No target-job responsibilities were supplied; role matching used the title and resume evidence.")
    if analysis is not None:
        assumptions.extend(item for item in analysis.assumptions if item)

    experience_label = f"{relevant_years} relevant / {total_years} total years"
    salary_range = f"{market.currency} {monthly_min:,.0f} - {monthly_max:,.0f} monthly"

    return SalaryEstimate(
        status="ok",
        role=role,
        normalized_role=normalized_role,
        role_family=role_family,
        specialization=specialization,
        career_track=career_track,
        location=location,
        location_details=normalized_location,
        experience_years=experience_label,
        total_experience_years=total_years,
        relevant_experience_years=relevant_years,
        specialization_experience_years=specialization_years,
        management_experience_years=management_years,
        seniority=seniority,
        salary_range=salary_range,
        salary_min=monthly_min * Decimal("12"),
        salary_max=monthly_max * Decimal("12"),
        salary_monthly_min=monthly_min,
        salary_monthly_mid=monthly_mid,
        salary_monthly_max=monthly_max,
        salary_annual_min=monthly_min * Decimal("12"),
        salary_annual_mid=monthly_mid * Decimal("12"),
        salary_annual_max=monthly_max * Decimal("12"),
        currency=market.currency,
        salary_source=market.source_name,
        source_date=str(market.benchmark_year),
        compensation_basis=market.compensation_basis,
        confidence=confidence.level,
        confidence_details=confidence,
        selected_benchmarks=selected_models,
        adjustments=adjustments,
        combined_multiplier=multiplier.quantize(Decimal("0.001")),
        factors=list(dict.fromkeys(factors)),
        assumptions=list(dict.fromkeys(assumptions)),
        additional_compensation_notes=(
            analysis.additional_compensation_notes if analysis is not None else ""
        ),
        notes=(
            analysis.notes.strip()
            if analysis is not None and analysis.notes.strip()
            else "Benchmark-driven estimate; use as a negotiation range, not a guaranteed offer."
        ),
    )
