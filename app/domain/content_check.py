"""Content quality check domain models."""
from enum import Enum

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    WEAK_WORD = "weak_word"
    PASSIVE_VOICE = "passive_voice"
    SHORT_BULLET = "short_bullet"
    NO_METRICS = "no_metrics"
    SUMMARY_TOO_SHORT = "summary_too_short"
    SUMMARY_TOO_LONG = "summary_too_long"
    BULLET_NO_ACTION = "bullet_no_action"
    CONTACT_INCOMPLETE = "contact_incomplete"


class ContentIssue(BaseModel):
    issue_type: IssueType
    severity: str = "warning"
    path: str
    message: str
    suggestion: str = ""


class ContentCheckResult(BaseModel):
    issues: list[ContentIssue] = Field(default_factory=list)
    score: int = Field(ge=0, le=100, default=100)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0
