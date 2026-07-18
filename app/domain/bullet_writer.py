"""Bullet writer domain models — Rezi-style 3-alternative generation from evidence."""
from typing import Literal

from pydantic import BaseModel, Field


class BulletEvidence(BaseModel):
    """Structured evidence extracted from the user's actual experience.

    The AI must use ONLY these fields — nothing else may be invented.
    """
    experience_index: int = Field(ge=0)
    role: str
    company: str
    responsibility: str
    action: str
    tools: list[str] = Field(default_factory=list)
    outcome: str | None = None
    metric: str | None = None
    target_keywords: list[str] = Field(default_factory=list)


class BulletSuggestion(BaseModel):
    """A single generated bullet alternative."""
    text: str = Field(min_length=1, max_length=500)
    style: Literal["concise", "achievement", "technical"]
    used_keywords: list[str] = Field(default_factory=list)
    evidence_fields: list[str] = Field(default_factory=list)
    requires_review: bool = True


class BulletSuggestionResult(BaseModel):
    """All three suggestions returned by the AI, with validation metadata."""
    suggestions: list[BulletSuggestion] = Field(min_length=3, max_length=3)
