"""Skill gap domain models — market demand vs candidate skills."""
from typing import List

from pydantic import BaseModel, Field


class SkillGapItem(BaseModel):
    skill: str = ""
    importance: str = ""
    recommendation: str = ""


class SkillGapResult(BaseModel):
    target_role: str = ""
    market_skills: List[str] = Field(default_factory=list)
    your_skills: List[str] = Field(default_factory=list)
    matched: List[str] = Field(default_factory=list)
    missing: List[SkillGapItem] = Field(default_factory=list)
    summary: str = ""
    data_source: str = "AI-generated (no external market data)"
