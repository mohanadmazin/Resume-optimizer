"""Job Match — Pydantic schemas for scoring a job against the Master Profile."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MatchCategory(str, Enum):
    """The dimensions over which a job is scored against the Master Profile."""

    SKILLS = "skills"
    EXPERIENCE = "experience"
    RESPONSIBILITIES = "responsibilities"
    EVIDENCE = "evidence"
    SENIORITY = "seniority"
    SALARY = "salary"


class MatchStrength(str, Enum):
    """Interpretation of an overall or per-category match score."""

    STRONG = "strong"
    GOOD = "good"
    MODERATE = "moderate"
    WEAK = "weak"


class CategoryScore(BaseModel):
    """A single category's match result."""

    category: MatchCategory
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    detail: str = ""
    weight: float = Field(default=0.0, ge=0.0, le=1.0)


class SkillMatch(BaseModel):
    """Whether a single JD skill is present or missing in the profile."""

    skill: str
    matched: bool
    evidence: str = ""


class JobMatch(BaseModel):
    """The complete job-to-Master-Profile match result."""

    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    categories: list[CategoryScore] = Field(default_factory=list)
    strengths: list[SkillMatch] = Field(default_factory=list)
    gaps: list[SkillMatch] = Field(default_factory=list)
    recommendation: str = ""
    strength: MatchStrength = MatchStrength.WEAK
    job_title: str = ""