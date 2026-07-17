"""Job requirements domain model — structured extraction from JD text."""
from typing import List

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """A single skill or requirement extracted from a job description."""
    name: str = ""
    evidence: str = ""


class JobRequirements(BaseModel):
    """Structured representation of a job description's requirements."""
    required_skills: List[Requirement] = Field(default_factory=list)
    preferred_skills: List[Requirement] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    minimum_experience_years: float | None = None
    education_requirements: List[str] = Field(default_factory=list)
