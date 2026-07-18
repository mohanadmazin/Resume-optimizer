"""Optimization domain models — structured AI output for resume optimization."""
from typing import List

from pydantic import BaseModel, Field


class OptimizedExperience(BaseModel):
    """Single experience entry as returned by the AI optimizer.

    The AI rewrites bullets while preserving metadata (title, company, dates).
    """
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: List[str] = Field(default_factory=list)


class OptimizationAIOutput(BaseModel):
    """Structured output from the AI resume optimizer.

    Matches the JSON schema specified in OPTIMIZE_PROMPT. Using Pydantic
    validation ensures the AI response conforms to the expected structure
    before any business logic processes it.
    """
    headline: str = ""
    summary: str = ""
    experience: List[OptimizedExperience] = Field(default_factory=list)
