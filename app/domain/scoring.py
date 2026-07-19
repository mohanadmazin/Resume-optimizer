"""Scoring domain models — versioned rule engine with individual findings."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ScoreCategory(str, Enum):
    CONTENT = "content"
    FORMAT = "format"
    OPTIMIZATION = "optimization"
    BEST_PRACTICES = "best_practices"
    APPLICATION_READY = "application_ready"


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ResumeIssue(BaseModel):
    code: str
    category: ScoreCategory
    severity: IssueSeverity
    path: str
    message: str
    recommendation: str
    penalty: float = Field(ge=0)
    autofix_action: str | None = None


class CategoryScore(BaseModel):
    category: ScoreCategory
    score: int = Field(ge=0, le=100)
    weight: float
    issues: list[ResumeIssue]


class ResumeScoreReport(BaseModel):
    ruleset_version: str
    overall_score: int = Field(ge=0, le=100)
    categories: list[CategoryScore]
    generated_at: datetime


class LayoutMetrics(BaseModel):
    word_count: int = 0
    page_count: int = 1
    has_bullets: bool = False
    has_tables: bool = False
    line_count: int = 0


CATEGORY_WEIGHTS = {
    ScoreCategory.CONTENT: 0.30,
    ScoreCategory.FORMAT: 0.20,
    ScoreCategory.OPTIMIZATION: 0.25,
    ScoreCategory.BEST_PRACTICES: 0.15,
    ScoreCategory.APPLICATION_READY: 0.10,
}
