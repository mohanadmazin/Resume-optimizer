"""Pipeline result data model."""
from dataclasses import dataclass, field
from datetime import datetime

from app.services.ats_engine import ATSResult
from app.schemas import ResumeData


@dataclass
class PipelineResult:
    """Holds all outputs from a full pipeline run."""

    ats_before: ATSResult
    optimized: ResumeData
    cover_letter: str
    ats_after_score: int = 0
    duration_seconds: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)
