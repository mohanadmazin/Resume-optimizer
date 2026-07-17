"""Pydantic models — backward-compatible re-exports from domain modules.

New code should import from:
  - app.domain.resume
  - app.domain.skill_gap
  - app.domain.salary
"""
from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ParseWarning,
    ProjectItem,
    ResumeData,
)
from app.domain.skill_gap import SkillGapItem, SkillGapResult
from app.domain.salary import SalaryEstimate

__all__ = [
    "ContactInfo",
    "EducationItem",
    "ExperienceItem",
    "ParseWarning",
    "ProjectItem",
    "ResumeData",
    "SkillGapItem",
    "SkillGapResult",
    "SalaryEstimate",
]
