"""Optimization domain models — structured AI output for resume optimization."""
from pydantic import BaseModel, Field


class BulletRewrite(BaseModel):
    """A single indexed bullet rewrite from the AI optimizer.

    Uses immutable coordinates (experience_index, bullet_index) instead of
    text matching, so reordering or duplicate titles/bullets cannot cause
    wrong assignments.
    """
    experience_index: int = Field(ge=0)
    bullet_index: int = Field(ge=0)
    rewritten: str = Field(min_length=1, max_length=2_000)


class OptimizationAIOutput(BaseModel):
    """Structured output from the AI resume optimizer.

    Matches the JSON schema specified in OPTIMIZE_PROMPT. Using Pydantic
    validation ensures the AI response conforms to the expected structure
    before any business logic processes it.
    """
    headline: str = ""
    summary: str = ""
    bullet_rewrites: list[BulletRewrite] = Field(default_factory=list)
