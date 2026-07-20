"""Profile compiler — deterministic evidence ranking and resume generation."""
from __future__ import annotations

import logging
import re
from datetime import datetime

from app.domain.evidence import CareerFact, FactConfidence, FactType
from app.domain.job_requirements import JobRequirements
from app.domain.master_profile import (
    CareerEntry,
    CompiledExclusion,
    CompiledItem,
    CompiledResume,
    CompiledSection,
    EmphasisType,
    MasterCareerProfile,
    ResumeCompilerConfig,
)
from app.domain.skill_lexicon import extract_skills

logger = logging.getLogger(__name__)

# ── Scoring constants ───────────────────────────────────────────────────────

EXACT_KEYWORD_SCORE = 10.0
RELATED_SKILL_SCORE = 5.0
RECENCY_BONUS = 3.0
SENIORITY_BONUS = 2.0
FACT_TYPE_BONUS: dict[FactType, float] = {
    FactType.ACHIEVEMENT: 3.0,
    FactType.METRIC: 3.0,
    FactType.PROJECT: 2.0,
    FactType.TEAM: 1.5,
    FactType.TECHNOLOGY: 1.0,
    FactType.RESPONSIBILITY: 0.5,
}

CONFIDENCE_MULTIPLIER: dict[FactConfidence, float] = {
    FactConfidence.VERIFIED: 1.0,
    FactConfidence.USER_CONFIRMED: 0.95,
    FactConfidence.REASONABLE_PARAPHRASE: 0.8,
    FactConfidence.USER_ESTIMATE: 0.6,
    FactConfidence.UNSUPPORTED: 0.2,
    FactConfidence.CONTRADICTORY: 0.0,
}

SENIORITY_KEYWORDS = {
    "senior": 3,
    "lead": 3,
    "principal": 4,
    "staff": 4,
    "director": 5,
    "vp": 5,
    "head": 4,
    "architect": 4,
    "manager": 3,
    "chief": 5,
}

# ── Section budget allocation ───────────────────────────────────────────────

SECTION_BUDGETS: dict[EmphasisType, dict[str, float]] = {
    EmphasisType.BALANCED: {
        "summary": 0.10,
        "experience": 0.40,
        "skills": 0.20,
        "education": 0.15,
        "certifications": 0.10,
        "projects": 0.05,
    },
    EmphasisType.EXPERIENCE: {
        "summary": 0.08,
        "experience": 0.55,
        "skills": 0.12,
        "education": 0.10,
        "certifications": 0.08,
        "projects": 0.07,
    },
    EmphasisType.SKILLS: {
        "summary": 0.08,
        "experience": 0.30,
        "skills": 0.35,
        "education": 0.10,
        "certifications": 0.10,
        "projects": 0.07,
    },
    EmphasisType.EDUCATION: {
        "summary": 0.08,
        "experience": 0.30,
        "skills": 0.15,
        "education": 0.30,
        "certifications": 0.10,
        "projects": 0.07,
    },
}


# ── Text helpers ─────────────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    cleaned = re.sub(r"[^a-z0-9#+]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _tokenize(text: str) -> set[str]:
    """Extract word tokens from text."""
    return set(re.findall(r"[a-z0-9+#]+", text.lower()))


def _parse_year(date_str: str) -> int | None:
    """Extract a 4-digit year from a date string like '2020-01' or '2024'."""
    m = re.search(r"(20\d{2}|19\d{2})", date_str)
    return int(m.group(1)) if m else None


def _seniority_level(text: str) -> int:
    """Estimate seniority from job title text (0-5 scale)."""
    lower = text.lower()
    for keyword, level in SENIORITY_KEYWORDS.items():
        if keyword in lower:
            return level
    return 1


# ── Evidence ranking ─────────────────────────────────────────────────────────


def rank_facts(
    facts: list[CareerFact],
    job_requirements: JobRequirements,
    reference_year: int | None = None,
) -> list[tuple[CareerFact, float]]:
    """Score each fact against job requirements.

    Returns facts sorted by descending relevance score.

    Scoring:
    - Exact keyword match: +10
    - Related skill match (via aliases): +5
    - Recency bonus: +3 if within 2 years
    - Seniority alignment: +2
    - Fact type bonus: varies by type
    - Confidence multiplier: scales total
    """
    if reference_year is None:
        reference_year = datetime.now().year

    required_tokens = set()
    for req in job_requirements.required_skills:
        required_tokens.update(_tokenize(req.name))
        for alias in getattr(req, "aliases", []):
            required_tokens.update(_tokenize(alias))

    preferred_tokens = set()
    for req in job_requirements.preferred_skills:
        preferred_tokens.update(_tokenize(req.name))

    all_job_tokens = required_tokens | preferred_tokens

    required_skills_canonical = {
        _normalize(req.name) for req in job_requirements.required_skills
    }
    preferred_skills_canonical = {
        _normalize(req.name) for req in job_requirements.preferred_skills
    }

    results: list[tuple[CareerFact, float]] = []
    for fact in facts:
        score = 0.0
        fact_tokens = _tokenize(fact.statement)
        fact_text_norm = _normalize(fact.statement)

        # Exact keyword match
        exact_matches = fact_tokens & all_job_tokens
        score += len(exact_matches) * EXACT_KEYWORD_SCORE

        # Related skill match via canonical aliases
        fact_skills = extract_skills(fact.statement)
        for skill in fact_skills:
            if skill in required_skills_canonical:
                score += RELATED_SKILL_SCORE * 1.5
            elif skill in preferred_skills_canonical:
                score += RELATED_SKILL_SCORE

        # Partial token overlap for non-skill keywords
        partial = sum(
            1 for t in all_job_tokens
            if len(t) >= 3 and (t in fact_text_norm or any(
                w.startswith(t) or t.startswith(w)
                for w in fact_tokens if len(w) >= 3
            ))
        )
        score += partial * 1.0

        # Recency bonus
        year = _parse_year(fact.date_to) or _parse_year(fact.date_from)
        if year and (reference_year - year) <= 2:
            score += RECENCY_BONUS

        # Fact type bonus
        score += FACT_TYPE_BONUS.get(fact.fact_type, 0.0)

        # Confidence multiplier
        multiplier = CONFIDENCE_MULTIPLIER.get(fact.confidence, 0.5)
        score *= multiplier

        results.append((fact, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


# ── Resume compilation ──────────────────────────────────────────────────────


def compile_resume(
    profile: MasterCareerProfile,
    job_requirements: JobRequirements,
    config: ResumeCompilerConfig | None = None,
) -> CompiledResume:
    """Compile a targeted resume from the master profile.

    Selects and arranges evidence based on relevance to the job,
    enforces page budget, and generates rationale for each item.
    """
    if config is None:
        config = ResumeCompilerConfig()

    budgets = SECTION_BUDGETS.get(config.emphasis, SECTION_BUDGETS[EmphasisType.BALANCED])

    # Collect all facts from the profile
    all_facts = _profile_to_facts(profile)
    ranked = rank_facts(all_facts, job_requirements)
    score_map = {f.id: s for f, s in ranked if f.id is not None}

    # Build ranked entries (filter excluded roles)
    active_entries = [
        e for e in profile.entries
        if e.role not in config.exclude_roles
    ]
    ranked_entries = _rank_entries(active_entries, job_requirements, score_map)

    sections: list[CompiledSection] = []
    exclusions: list[CompiledExclusion] = []
    total_items = 0

    # Experience section
    max_exp_items = _budget_item_count(budgets["experience"], config.max_pages)
    exp_items, exp_exclusions = _compile_experience(
        ranked_entries, max_exp_items, config.min_relevance_score,
    )
    sections.append(CompiledSection(
        section_name="Experience",
        items=exp_items,
        rationale=f"Selected top {len(exp_items)} items by relevance",
        budget_pct=budgets["experience"],
    ))
    exclusions.extend(exp_exclusions)
    total_items += len(exp_items)

    # Skills section
    max_skill_items = _budget_item_count(budgets["skills"], config.max_pages)
    skill_items, skill_exclusions = _compile_skills(
        profile.skills, job_requirements, max_skill_items,
    )
    sections.append(CompiledSection(
        section_name="Skills",
        items=skill_items,
        rationale=f"Selected {len(skill_items)} skills matching job requirements",
        budget_pct=budgets["skills"],
    ))
    exclusions.extend(skill_exclusions)
    total_items += len(skill_items)

    # Education section
    edu_items = [
        CompiledItem(
            text=f"{edu.degree} — {edu.institution} ({edu.year})",
            relevance_score=1.0,
            rationale="Education entry",
        )
        for edu in profile.education
    ]
    sections.append(CompiledSection(
        section_name="Education",
        items=edu_items,
        rationale=f"Included all {len(edu_items)} education entries",
        budget_pct=budgets["education"],
    ))
    total_items += len(edu_items)

    # Certifications section
    cert_items = [
        CompiledItem(text=cert, relevance_score=1.0, rationale="Certification")
        for cert in profile.certifications
    ]
    sections.append(CompiledSection(
        section_name="Certifications",
        items=cert_items,
        rationale=f"Included all {len(cert_items)} certifications",
        budget_pct=budgets["certifications"],
    ))
    total_items += len(cert_items)

    # Summary section
    summary_items = []
    if profile.summary:
        summary_items.append(CompiledItem(
            text=profile.summary,
            relevance_score=1.0,
            rationale="Professional summary",
        ))
    sections.append(CompiledSection(
        section_name="Summary",
        items=summary_items,
        budget_pct=budgets["summary"],
    ))
    total_items += len(summary_items)

    return CompiledResume(
        sections=sections,
        exclusions=exclusions,
        rationale=(
            f"Compiled from master profile with {len(profile.entries)} entries "
            f"using {config.emphasis.value} emphasis"
        ),
        total_items=total_items,
        config_used=config,
    )


# ── Private helpers ──────────────────────────────────────────────────────────


def _profile_to_facts(profile: MasterCareerProfile) -> list[CareerFact]:
    """Convert profile entries to CareerFact objects for ranking."""
    from app.domain.evidence import FactType as FT

    facts: list[CareerFact] = []
    for entry in profile.entries:
        for bullet in entry.bullets:
            facts.append(CareerFact(
                id=None,
                statement=bullet,
                fact_type=FT.RESPONSIBILITY,
                employer=entry.company,
                date_from=entry.date_from,
                date_to=entry.date_to,
                tags=entry.tags,
            ))
    for skill in profile.skills:
        facts.append(CareerFact(
            id=None,
            statement=f"Skilled in {skill}",
            fact_type=FT.TECHNOLOGY,
        ))
    return facts


def _rank_entries(
    entries: list[CareerEntry],
    job_req: JobRequirements,
    score_map: dict[int, float],
) -> list[tuple[CareerEntry, float]]:
    """Rank career entries by their best bullet score."""
    scored: list[tuple[CareerEntry, float]] = []
    for entry in entries:
        bullet_scores = [
            score_map[fid] for fid in entry.fact_ids if fid in score_map
        ]
        best = max(bullet_scores, default=0.0)
        # Recency boost for entries
        year = _parse_year(entry.date_to) or _parse_year(entry.date_from)
        if year and (datetime.now().year - year) <= 2:
            best += RECENCY_BONUS
        scored.append((entry, best))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _budget_item_count(budget_pct: float, max_pages: int) -> int:
    """Estimate how many items fit within a section's budget."""
    words_per_page = 400
    total_words = max_pages * words_per_page
    section_words = int(total_words * budget_pct)
    avg_words_per_bullet = 20
    return max(1, section_words // avg_words_per_bullet)


def _compile_experience(
    ranked_entries: list[tuple[CareerEntry, float]],
    max_items: int,
    min_score: float,
) -> tuple[list[CompiledItem], list[CompiledExclusion]]:
    """Select top bullets from ranked entries."""
    items: list[CompiledItem] = []
    exclusions: list[CompiledExclusion] = []

    for entry, entry_score in ranked_entries:
        for bullet in entry.bullets:
            if len(items) >= max_items:
                exclusions.append(CompiledExclusion(
                    text=bullet,
                    reason="Exceeded page budget",
                    relevance_score=entry_score,
                ))
                continue
            if entry_score < min_score and min_score > 0:
                exclusions.append(CompiledExclusion(
                    text=bullet,
                    reason=f"Below relevance threshold ({entry_score:.1f} < {min_score:.1f})",
                    relevance_score=entry_score,
                ))
                continue
            items.append(CompiledItem(
                text=bullet,
                source_entry_id=entry.id,
                relevance_score=entry_score,
                rationale=f"From {entry.role or 'role'} at {entry.company}",
            ))

    return items, exclusions


def _compile_skills(
    skills: list[str],
    job_req: JobRequirements,
    max_items: int,
) -> tuple[list[CompiledItem], list[CompiledExclusion]]:
    """Select and prioritize skills matching the job."""
    required = {_normalize(r.name) for r in job_req.required_skills}
    preferred = {_normalize(r.name) for r in job_req.preferred_skills}
    all_job = required | preferred

    scored_skills: list[tuple[str, float]] = []
    for skill in skills:
        norm = _normalize(skill)
        if norm in required:
            scored_skills.append((skill, 10.0))
        elif norm in preferred:
            scored_skills.append((skill, 7.0))
        elif any(norm in j or j in norm for j in all_job if len(j) >= 3):
            scored_skills.append((skill, 4.0))
        else:
            scored_skills.append((skill, 1.0))

    scored_skills.sort(key=lambda x: x[1], reverse=True)

    items: list[CompiledItem] = []
    exclusions: list[CompiledExclusion] = []
    for skill, score in scored_skills:
        if len(items) >= max_items:
            exclusions.append(CompiledExclusion(
                text=skill,
                reason="Exceeded skill budget",
                relevance_score=score,
            ))
            continue
        rationale = "Required" if _normalize(skill) in required else (
            "Preferred" if _normalize(skill) in preferred else "Additional"
        )
        items.append(CompiledItem(
            text=skill,
            relevance_score=score,
            rationale=rationale,
        ))

    return items, exclusions
