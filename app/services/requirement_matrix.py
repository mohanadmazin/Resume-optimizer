"""Requirement Evidence Matrix — deterministic matching of JD requirements to vault evidence."""
from __future__ import annotations

import logging
import re
from typing import Sequence

from app.domain.evidence import CareerFact
from app.domain.job_requirements import JobRequirements
from app.domain.requirement_matrix import (
    CoverageLevel,
    MatrixExportFormat,
    RequirementItem,
    RequirementMatrix,
    RequirementType,
)
from app.domain.skill_lexicon import extract_skills

logger = logging.getLogger(__name__)

# Weights for importance by requirement type
_TYPE_WEIGHTS: dict[RequirementType, float] = {
    RequirementType.REQUIRED: 1.0,
    RequirementType.PREFERRED: 0.7,
    RequirementType.RESPONSIBILITY: 0.8,
    RequirementType.DOMAIN: 0.9,
    RequirementType.TOOL: 0.8,
    RequirementType.EDUCATION: 0.6,
    RequirementType.CERTIFICATION: 0.7,
    RequirementType.LOCATION: 0.4,
    RequirementType.AUTHORIZATION: 0.5,
    RequirementType.TRAVEL: 0.3,
    RequirementType.SOFT_SKILL: 0.5,
}

# Coverage score for each level
_COVERAGE_SCORES: dict[CoverageLevel, float] = {
    CoverageLevel.DIRECT_EVIDENCE: 1.0,
    CoverageLevel.RELATED_EVIDENCE: 0.6,
    CoverageLevel.KEYWORD_ONLY: 0.3,
    CoverageLevel.USER_CONFIRMED: 0.9,
    CoverageLevel.MISSING: 0.0,
    CoverageLevel.CONTRADICTORY: -0.5,
    CoverageLevel.UNKNOWN: 0.0,
}


def classify_requirement(text: str) -> RequirementType:
    """Classify a requirement sentence by type using keyword heuristics."""
    lower = text.lower()

    if any(w in lower for w in ("certification", "certified", "certificate", "license")):
        return RequirementType.CERTIFICATION
    if any(w in lower for w in ("degree", "bachelor", "master", "phd", "education", "diploma")):
        return RequirementType.EDUCATION
    if any(w in lower for w in ("location", "relocate", "on-site", "onsite", "hybrid", "remote")):
        return RequirementType.LOCATION
    if any(w in lower for w in ("clearance", "authorized", "authorization", "citizenship", "visa")):
        return RequirementType.AUTHORIZATION
    if any(w in lower for w in ("travel", "traveling")):
        return RequirementType.TRAVEL
    if any(w in lower for w in ("must have", "required", "essential", "mandatory", "necessary")):
        return RequirementType.REQUIRED
    if any(w in lower for w in ("preferred", "nice to have", "plus", "bonus", "desirable")):
        return RequirementType.PREFERRED
    if any(w in lower for w in ("responsible for", "responsibilities", "duties", "will be")):
        return RequirementType.RESPONSIBILITY
    if any(w in lower for w in (
        "experience in", "experience with", "knowledge of", "understanding of",
        "familiarity with", "background in",
    )):
        return RequirementType.DOMAIN
    if any(w in lower for w in (
        "tool", "software", "platform", "framework", "language",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    )):
        return RequirementType.TOOL
    if any(w in lower for w in (
        "communication", "leadership", "teamwork", "collaboration",
        "problem-solving", "analytical", "creative", "self-motivated",
    )):
        return RequirementType.SOFT_SKILL

    return RequirementType.REQUIRED


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def _find_exact_phrase(requirement_text: str, fact_text: str) -> bool:
    """Check if requirement keywords appear verbatim in fact text."""
    req_words = set(_normalize(requirement_text).split())
    fact_words = set(_normalize(fact_text).split())
    # Require at least one meaningful word (len >= 3) to match
    meaningful = {w for w in req_words if len(w) >= 3}
    if not meaningful:
        return False
    overlap = meaningful & fact_words
    return len(overlap) >= max(1, len(meaningful) // 3)


def _find_related_evidence(requirement_text: str, fact_text: str) -> bool:
    """Check if the fact mentions skills related to the requirement via aliases."""
    req_skills = extract_skills(requirement_text)
    fact_skills = extract_skills(fact_text)
    if req_skills and fact_skills:
        return bool(req_skills & fact_skills)
    return _find_exact_phrase(requirement_text, fact_text)


def _score_requirement(
    requirement: RequirementItem,
    facts: Sequence[CareerFact],
) -> RequirementItem:
    """Score a single requirement against all vault facts."""
    best_level = CoverageLevel.MISSING
    best_score = 0.0
    matched_ids: list[int] = []
    matched_texts: list[str] = []

    for fact in facts:
        if _find_exact_phrase(requirement.text, fact.statement):
            matched_ids.append(fact.id)
            matched_texts.append(fact.statement)
            if best_level != CoverageLevel.DIRECT_EVIDENCE:
                best_level = CoverageLevel.DIRECT_EVIDENCE
                best_score = _COVERAGE_SCORES[CoverageLevel.DIRECT_EVIDENCE]
        elif _find_related_evidence(requirement.text, fact.statement):
            matched_ids.append(fact.id)
            matched_texts.append(fact.statement)
            if best_score < _COVERAGE_SCORES[CoverageLevel.RELATED_EVIDENCE]:
                best_level = CoverageLevel.RELATED_EVIDENCE
                best_score = _COVERAGE_SCORES[CoverageLevel.RELATED_EVIDENCE]

    requirement.coverage = best_level
    requirement.coverage_score = best_score * requirement.importance
    requirement.evidence_fact_ids = matched_ids
    requirement.candidate_evidence_text = matched_texts[:5]

    if best_level == CoverageLevel.MISSING:
        requirement.action_needed = f"No evidence found for: {requirement.text}"
    elif best_level == CoverageLevel.RELATED_EVIDENCE:
        requirement.action_needed = (
            f"Consider adding direct evidence for: {requirement.text}"
        )
    else:
        requirement.action_needed = ""

    return requirement


def build_matrix(
    job: JobRequirements,
    facts: Sequence[CareerFact],
) -> RequirementMatrix:
    """Build a requirement-evidence matrix.

    Pure deterministic matching: no AI, no Ollama calls.
    """
    items: list[RequirementItem] = []

    for req in job.required_skills:
        items.append(RequirementItem(
            text=req.name,
            requirement_type=RequirementType.REQUIRED,
            importance=1.0,
        ))

    for req in job.preferred_skills:
        items.append(RequirementItem(
            text=req.name,
            requirement_type=RequirementType.PREFERRED,
            importance=0.7,
        ))

    for resp in job.responsibilities:
        items.append(RequirementItem(
            text=resp,
            requirement_type=RequirementType.RESPONSIBILITY,
            importance=0.8,
        ))

    for edu in job.education_requirements:
        items.append(RequirementItem(
            text=edu,
            requirement_type=RequirementType.EDUCATION,
            importance=0.6,
        ))

    # Score each requirement
    items = [_score_requirement(item, facts) for item in items]

    # Compute overall score
    if items:
        total_weight = sum(item.importance for item in items)
        weighted_score = sum(item.coverage_score for item in items)
        overall = weighted_score / total_weight if total_weight > 0 else 0.0
    else:
        overall = 0.0

    gaps = [item.action_needed for item in items if item.action_needed]
    strengths = [item.text for item in items if item.coverage == CoverageLevel.DIRECT_EVIDENCE]

    covered = sum(1 for i in items if i.coverage not in (CoverageLevel.MISSING, CoverageLevel.UNKNOWN))

    return RequirementMatrix(
        requirements=items,
        overall_score=max(0.0, overall),
        gaps=gaps,
        strengths=strengths,
        total_requirements=len(items),
        covered_count=covered,
        gap_count=len(items) - covered,
    )


# ── Export ────────────────────────────────────────────────────────────

_COVERAGE_BADGE: dict[CoverageLevel, str] = {
    CoverageLevel.DIRECT_EVIDENCE: "YES",
    CoverageLevel.RELATED_EVIDENCE: "~YES",
    CoverageLevel.KEYWORD_ONLY: "PARTIAL",
    CoverageLevel.USER_CONFIRMED: "YES",
    CoverageLevel.MISSING: "NO",
    CoverageLevel.CONTRADICTORY: "CONTRA",
    CoverageLevel.UNKNOWN: "?",
}


def export_matrix(matrix: RequirementMatrix, fmt: MatrixExportFormat) -> str:
    """Export the matrix as markdown table or CSV."""
    if fmt == MatrixExportFormat.MARKDOWN:
        return _export_markdown(matrix)
    return _export_csv(matrix)


def _export_markdown(matrix: RequirementMatrix) -> str:
    lines = [
        "# Requirement Evidence Matrix",
        "",
        f"**Overall score:** {matrix.overall_score:.0%} "
        f"({matrix.covered_count}/{matrix.total_requirements} covered, "
        f"{matrix.gap_count} gaps)",
        "",
        "| Requirement | Type | Importance | Coverage | Evidence | Action |",
        "|---|---|---|---|---|---|",
    ]
    for item in matrix.requirements:
        badge = _COVERAGE_BADGE.get(item.coverage, "?")
        n_facts = len(item.evidence_fact_ids)
        action = item.action_needed or "-"
        lines.append(
            f"| {item.text[:60]} | {item.requirement_type.value} "
            f"| {item.importance:.0%} | {badge} "
            f"| {n_facts} | {action[:50]} |"
        )
    return "\n".join(lines)


def _export_csv(matrix: RequirementMatrix) -> str:
    header = "Requirement,Type,Importance,Coverage,EvidenceCount,ActionNeeded"
    rows = [header]
    for item in matrix.requirements:
        badge = _COVERAGE_BADGE.get(item.coverage, "?")
        n_facts = len(item.evidence_fact_ids)
        text = item.text.replace('"', '""')
        action = item.action_needed.replace('"', '""') or "-"
        rows.append(
            f'"{text}",{item.requirement_type.value},{item.importance:.0%},'
            f"{badge},{n_facts},\"{action}\""
        )
    return "\n".join(rows)
