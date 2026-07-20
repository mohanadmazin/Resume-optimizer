"""Master Career Profile — domain models for comprehensive career history."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CareerEntry(BaseModel):
    """A single role/position in career history."""

    id: int | None = None
    role: str = ""
    company: str = ""
    location: str = ""
    date_from: str = ""
    date_to: str = ""
    bullets: list[str] = Field(default_factory=list)
    fact_ids: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class MasterCareerProfile(BaseModel):
    """The comprehensive master profile containing all career history."""

    id: int | None = None
    name: str = ""
    entries: list[CareerEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    summary: str = ""
    headline: str = ""
    total_fact_count: int = 0
    created_at: str = ""
    updated_at: str = ""


class EducationEntry(BaseModel):
    """Education item in the master profile."""

    degree: str = ""
    institution: str = ""
    year: str = ""
    notes: str = ""


# ── Resume Compiler Config ──────────────────────────────────────────────────


class EmphasisType(str, Enum):
    """What to emphasize in the compiled resume."""

    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    BALANCED = "balanced"


class ResumeCompilerConfig(BaseModel):
    """Configuration for compiling a targeted resume from the master profile."""

    max_pages: int = 1
    emphasis: EmphasisType = EmphasisType.BALANCED
    exclude_roles: list[str] = Field(default_factory=list)
    include_sections: list[str] = Field(default_factory=list)
    min_relevance_score: float = 0.0
    target_role: str = ""


# ── Compiled Resume Output ──────────────────────────────────────────────────


class CompiledItem(BaseModel):
    """A single item (bullet, skill, education) selected for the compiled resume."""

    text: str = ""
    source_fact_id: int | None = None
    source_entry_id: int | None = None
    relevance_score: float = 0.0
    rationale: str = ""


class CompiledSection(BaseModel):
    """A section of the compiled resume with its items and budget allocation."""

    section_name: str = ""
    items: list[CompiledItem] = Field(default_factory=list)
    rationale: str = ""
    budget_pct: float = 0.0


class CompiledResume(BaseModel):
    """The full output of the resume compiler."""

    sections: list[CompiledSection] = Field(default_factory=list)
    exclusions: list[CompiledExclusion] = Field(default_factory=list)
    rationale: str = ""
    total_items: int = 0
    config_used: ResumeCompilerConfig = Field(default_factory=ResumeCompilerConfig)


class CompiledExclusion(BaseModel):
    """An item that was excluded from the compiled resume with reasoning."""

    text: str = ""
    source_fact_id: int | None = None
    reason: str = ""
    relevance_score: float = 0.0
