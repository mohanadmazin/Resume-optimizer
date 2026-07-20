"""Requirement Evidence Matrix — Pydantic schemas for requirement-evidence mapping."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RequirementType(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    RESPONSIBILITY = "responsibility"
    DOMAIN = "domain"
    TOOL = "tool"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    LOCATION = "location"
    AUTHORIZATION = "authorization"
    TRAVEL = "travel"
    SOFT_SKILL = "soft_skill"


class CoverageLevel(str, Enum):
    DIRECT_EVIDENCE = "direct_evidence"
    RELATED_EVIDENCE = "related_evidence"
    KEYWORD_ONLY = "keyword_only"
    USER_CONFIRMED = "user_confirmed"
    MISSING = "missing"
    CONTRADICTORY = "contradictory"
    UNKNOWN = "unknown"


class RequirementItem(BaseModel):
    """A single requirement mapped against vault evidence."""
    text: str
    requirement_type: RequirementType = RequirementType.REQUIRED
    importance: float = Field(default=1.0, ge=0.0, le=1.0)
    coverage: CoverageLevel = CoverageLevel.UNKNOWN
    evidence_fact_ids: list[int] = Field(default_factory=list)
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    action_needed: str = ""
    candidate_evidence_text: list[str] = Field(default_factory=list)


class RequirementMatrix(BaseModel):
    """Complete mapping of job requirements to career evidence."""
    requirements: list[RequirementItem] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    gaps: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    total_requirements: int = 0
    covered_count: int = 0
    gap_count: int = 0


class MatrixExportFormat(str, Enum):
    MARKDOWN = "markdown"
    CSV = "csv"
