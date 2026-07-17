"""Pipeline result data model."""
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.analysis import ATSResult
from app.domain.fact_guard import FactGuardResult
from app.schemas import ResumeData


@dataclass
class PipelineResult:
    """Holds all outputs from a full pipeline run."""

    ats_before: ATSResult
    optimized: ResumeData
    cover_letter: str
    cover_letter_warnings: list[str] = field(default_factory=list)
    fact_guard: FactGuardResult | None = None
    ats_after_score: int = 0
    duration_seconds: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)
    requires_review: bool = False
