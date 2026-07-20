"""Agent domain models — tool definitions and action types."""
from enum import Enum

from pydantic import BaseModel, Field


class AgentTool(str, Enum):
    """Tools the agent can invoke against a resume."""

    SCORE = "score"
    TARGET = "target"
    SUGGEST_BULLETS = "suggest_bullets"
    REWRITE_SUMMARY = "rewrite_summary"
    EXPLAIN_ISSUES = "explain_issues"
    OPTIMIZE = "optimize"
    CHECK_FACTS = "check_facts"


class AgentAction(BaseModel):
    """A single proposed action from the agent."""

    tool: AgentTool
    description: str = ""
    section: str = ""
    original: str = ""
    proposed: str = ""
    experience_index: int | None = None
    bullet_index: int | None = None
    accepted: bool | None = None


class AgentProposal(BaseModel):
    """A set of actions proposed in response to a single agent turn."""

    tool: AgentTool
    summary: str = ""
    actions: list[AgentAction] = Field(default_factory=list)

    @property
    def has_actions(self) -> bool:
        return len(self.actions) > 0

    @property
    def all_reviewed(self) -> bool:
        return all(a.accepted is not None for a in self.actions)
