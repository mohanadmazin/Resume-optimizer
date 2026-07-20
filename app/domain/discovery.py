"""Achievement Discovery Interview — Pydantic schemas for guided achievement extraction."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MetricStatus(str, Enum):
    VERIFIED = "verified"
    ESTIMATE = "estimate"
    UNAVAILABLE = "unavailable"


class QuestionCategory(str, Enum):
    ROLE = "role"
    ACHIEVEMENT = "achievement"
    METRIC = "metric"
    TOOL = "tool"
    CHALLENGE = "challenge"
    SCALE = "scale"
    IMPACT = "impact"


class InterviewQuestion(BaseModel):
    """A question posed during the discovery interview."""
    question_text: str
    context: str = ""
    follow_ups: list[str] = Field(default_factory=list)
    category: QuestionCategory = QuestionCategory.ACHIEVEMENT
    question_id: str = ""


class InterviewAnswer(BaseModel):
    """User's answer to an interview question."""
    answer_text: str
    extracted_metrics: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    fact_links: list[int] = Field(default_factory=list)


class AchievementResult(BaseModel):
    """A discovered achievement with quantified metrics."""
    statement: str
    metrics: dict[str, str] = Field(default_factory=dict)
    previous_value: str = ""
    current_value: str = ""
    metric_status: MetricStatus = MetricStatus.UNAVAILABLE
    tools_used: list[str] = Field(default_factory=list)
    category: QuestionCategory = QuestionCategory.ACHIEVEMENT


class DiscoverySession(BaseModel):
    """State of an in-progress discovery interview."""
    role: str = ""
    questions_asked: list[InterviewQuestion] = Field(default_factory=list)
    answers: list[InterviewAnswer] = Field(default_factory=list)
    achievements_discovered: list[AchievementResult] = Field(default_factory=list)
    current_question_index: int = 0
    max_questions: int = 10
    is_complete: bool = False
