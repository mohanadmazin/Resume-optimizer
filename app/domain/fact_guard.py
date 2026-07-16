"""Fact guard domain models — deterministic validation of AI-generated changes."""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    SUMMARY = "summary"
    HEADLINE = "headline"
    BULLET = "bullet"


class ProposedChange(BaseModel):
    """A single proposed change from the AI optimizer."""

    change_type: ChangeType
    section: str = ""
    original: str = ""
    rewritten: str = ""
    # Deterministic guard results
    has_new_numbers: bool = False
    has_new_entities: bool = False
    has_new_skills: bool = False
    accepted: bool = False


class FactGuardResult(BaseModel):
    """Deterministic validation of all AI-generated changes."""

    safe_changes: List[ProposedChange] = Field(default_factory=list)
    flagged_changes: List[ProposedChange] = Field(default_factory=list)
    unsupported_numbers: List[str] = Field(default_factory=list)
    unsupported_entities: List[str] = Field(default_factory=list)
    unsupported_skills: List[str] = Field(default_factory=list)

    @property
    def all_changes(self) -> List[ProposedChange]:
        return self.safe_changes + self.flagged_changes

    @property
    def accepted_count(self) -> int:
        return sum(1 for c in self.all_changes if c.accepted)

    @property
    def flagged_count(self) -> int:
        return len(self.flagged_changes)
