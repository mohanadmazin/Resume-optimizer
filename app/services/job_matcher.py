"""Job matcher — deterministic scoring of a job against the Master Profile.

Pure, local-first matching: no AI, no Ollama, no server. Reuses existing
domains (skill lexicon, ATS keyword extraction, requirement matrix, master
profile) to produce an explainable per-category match score.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Sequence

from app.domain.evidence import CareerFact
from app.domain.job_match import (
    CategoryScore,
    JobMatch,
    MatchCategory,
    MatchStrength,
    SkillMatch,
)
from app.domain.job_requirements import JobRequirements, Requirement
from app.domain.master_profile import MasterCareerProfile
from app.domain.requirement_matrix import RequirementType
from app.domain.skill_lexicon import SKILL_ALIASES, extract_skills
from app.services.ats_engine import extract_required_skills
from app.services.profile_compiler import SENIORITY_KEYWORDS
from app.services.requirement_matrix import build_matrix

# ── Category weights ─────────────────────────────────────────────────────────

_CATEGORY_WEIGHTS: dict[MatchCategory, float] = {
    MatchCategory.SKILLS: 0.25,
    MatchCategory.EXPERIENCE: 0.20,
    MatchCategory.RESPONSIBILITIES: 0.20,
    MatchCategory.EVIDENCE: 0.15,
    MatchCategory.SENIORITY: 0.10,
    MatchCategory.SALARY: 0.10,
}


def _strength_for(score: float) -> MatchStrength:
    if score >= 0.80:
        return MatchStrength.STRONG
    if score >= 0.65:
        return MatchStrength.GOOD
    if score >= 0.45:
        return MatchStrength.MODERATE
    return MatchStrength.WEAK


def _recommendation(strength: MatchStrength) -> str:
    labels = {
        MatchStrength.STRONG: "Strong match",
        MatchStrength.GOOD: "Good match",
        MatchStrength.MODERATE: "Moderate match",
        MatchStrength.WEAK: "Weak match",
    }
    return labels[strength]


# ── Skills category ──────────────────────────────────────────────────────────


def _profile_skill_set(profile: MasterCareerProfile) -> set[str]:
    """Canonical skill names present anywhere in the profile."""
    texts = list(profile.skills)
    texts.extend(bullet for entry in profile.entries for bullet in entry.bullets)
    skills = set()
    for text in texts:
        skills.update(extract_skills(text))
        skills.update(skill.casefold() for skill in profile.skills)
    return skills


def _jd_skill_canonical(skill_name: str) -> set[str]:
    """Canonical forms for a JD skill name (handles aliases and short forms)."""
    found = extract_skills(skill_name)
    if found:
        return found
    lowered = skill_name.casefold()
    for canonical, aliases in SKILL_ALIASES.items():
        if lowered == canonical or lowered in aliases:
            return {canonical}
    return {lowered}


_RESPONSIBILITY_MARKERS = (
    "responsible for",
    "responsibilities",
    "duties",
    "will",
    "manage",
    "lead",
    "develop",
    "build",
    "design",
    "implement",
    "maintain",
    "oversee",
    "collaborate",
)


def _job_requirements_from_text(job_text: str, title: str = "") -> JobRequirements:
    """Build a JobRequirements object from raw JD text."""
    job_text = job_text or title
    required = extract_required_skills(job_text)
    responsibilities = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", job_text)
        if any(marker in sentence.lower() for marker in _RESPONSIBILITY_MARKERS)
    ][:8]
    return JobRequirements(
        required_skills=[Requirement(name=skill) for skill in required],
        responsibilities=responsibilities,
    )


# ── Experience category ──────────────────────────────────────────────────────


def _parse_year(text: str) -> int | None:
    m = re.search(r"(20\d{2}|19\d{2})", text)
    return int(m.group(1)) if m else None


def _profile_experience_years(profile: MasterCareerProfile) -> float:
    """Estimate total (overlap-merged) years from profile career entries."""
    today = date.today()
    intervals: list[tuple[date, date]] = []
    for entry in profile.entries:
        start = _parse_year(entry.date_from)
        end = _parse_year(entry.date_to)
        if start is None:
            continue
        start_d = date(start, 1, 1)
        end_d = date(end, 12, 31) if end is not None else today
        if end_d < start_d:
            continue
        intervals.append((start_d, end_d))
    intervals.sort(key=lambda pair: pair[0])
    merged: list[tuple[date, date]] = []
    for start_d, end_d in intervals:
        if merged and start_d <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end_d))
        else:
            merged.append((start_d, end_d))
    total_days = sum((end_d - start_d).days for start_d, end_d in merged)
    return round(total_days / 365.25, 1)


# ── Seniority category ───────────────────────────────────────────────────────


def _seniority_level(text: str) -> int:
    lower = text.lower()
    for keyword, level in SENIORITY_KEYWORDS.items():
        if keyword in lower:
            return level
    return 1


# ── Main entry point ─────────────────────────────────────────────────────────


def match_job(
    *,
    job_text: str,
    job_title: str,
    profile: MasterCareerProfile,
    facts: Sequence[CareerFact] | None = None,
    job_salary_text: str = "",
) -> JobMatch:
    """Score a job against the Master Profile across six categories.

    ``facts`` are optional Evidence Vault ``CareerFact`` objects used to boost
    the evidence and responsibilities categories.
    """
    requirements = _job_requirements_from_text(job_text, job_title)
    skill_set = _profile_skill_set(profile)

    # Skills
    matched: list[SkillMatch] = []
    gaps: list[SkillMatch] = []
    for req in requirements.required_skills:
        present = bool(_jd_skill_canonical(req.name) & skill_set)
        match = SkillMatch(skill=req.name, matched=present)
        if present:
            matched.append(match)
        else:
            gaps.append(match)
    total_skills = len(matched) + len(gaps)
    skills_score = round(len(matched) / total_skills, 2) if total_skills else 0.5

    # Experience
    profile_years = _profile_experience_years(profile)
    required_years = 0.0
    years_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:\+|to|–|-)?\s*(?:years?|yrs?)", job_text, re.IGNORECASE
    )
    if years_match:
        required_years = float(years_match.group(1))
    if required_years and profile_years >= required_years:
        experience_score = 1.0
    elif required_years:
        experience_score = max(0.0, round(profile_years / required_years, 2))
    else:
        experience_score = 0.8 if profile_years >= 1 else 0.4

    # Responsibilities + Evidence (via requirement matrix)
    responsibility_score = 0.0
    evidence_score = 0.0
    if facts:
        matrix = build_matrix(requirements, facts)
        resp_items = [
            item for item in matrix.requirements
            if item.requirement_type == RequirementType.RESPONSIBILITY
        ]
        if resp_items:
            resp_weight = sum(item.importance for item in resp_items) or 1.0
            responsibility_score = round(
                sum(item.coverage_score for item in resp_items) / resp_weight,
                2,
            )
        else:
            responsibility_score = 0.4
        evidence_score = round(
            matrix.covered_count / matrix.total_requirements, 2
        ) if matrix.total_requirements else 0.4
    else:
        responsibility_score = 0.4
        evidence_score = 0.4

    # Seniority
    job_level = _seniority_level(job_title)
    profile_roles = " ".join(entry.role for entry in profile.entries)
    profile_level = _seniority_level(profile_roles)
    seniority_score = min(1.0, round(job_level / max(profile_level, 1), 2))

    # Salary
    salary_score = 0.6 if job_salary_text.strip() else 0.5

    categories = [
        CategoryScore(
            category=MatchCategory.SKILLS,
            score=skills_score,
            weight=_CATEGORY_WEIGHTS[MatchCategory.SKILLS],
            detail=f"{len(matched)}/{total_skills} required skills present",
        ),
        CategoryScore(
            category=MatchCategory.EXPERIENCE,
            score=experience_score,
            weight=_CATEGORY_WEIGHTS[MatchCategory.EXPERIENCE],
            detail=f"{profile_years} yrs profile vs {required_years or 'unknown'} yrs required",
        ),
        CategoryScore(
            category=MatchCategory.RESPONSIBILITIES,
            score=responsibility_score,
            weight=_CATEGORY_WEIGHTS[MatchCategory.RESPONSIBILITIES],
            detail="responsibility coverage via evidence",
        ),
        CategoryScore(
            category=MatchCategory.EVIDENCE,
            score=evidence_score,
            weight=_CATEGORY_WEIGHTS[MatchCategory.EVIDENCE],
            detail="evidence-backed requirement coverage",
        ),
        CategoryScore(
            category=MatchCategory.SENIORITY,
            score=seniority_score,
            weight=_CATEGORY_WEIGHTS[MatchCategory.SENIORITY],
            detail=f"job level {job_level} vs profile level {profile_level}",
        ),
        CategoryScore(
            category=MatchCategory.SALARY,
            score=salary_score,
            weight=_CATEGORY_WEIGHTS[MatchCategory.SALARY],
            detail="salary transparency present" if job_salary_text.strip() else "no salary provided",
        ),
    ]

    overall = round(sum(cat.score * cat.weight for cat in categories), 2)
    strength = _strength_for(overall)
    # Keep only meaningful strengths/gaps (top few) to avoid a noisy card.
    top_matches = matched[:6]
    top_gaps = gaps[:6]

    return JobMatch(
        overall_score=overall,
        categories=categories,
        strengths=top_matches,
        gaps=top_gaps,
        recommendation=_recommendation(strength),
        strength=strength,
        job_title=job_title,
    )