"""Agent service — proposal pipeline with fact guard integration."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import (
    AGENT_CHECK_FACTS_PROMPT,
    AGENT_EXPLAIN_ISSUES_PROMPT,
    AGENT_OPTIMIZE_PROMPT,
    AGENT_REWRITE_SUMMARY_PROMPT,
    AGENT_SCORE_PROMPT,
    AGENT_SUGGEST_BULLETS_PROMPT,
    AGENT_SYSTEM,
    AGENT_TARGET_PROMPT,
)
from app.domain.agent import AgentAction, AgentProposal, AgentTool
from app.domain.fact_guard import ChangeType, ProposedChange
from app.domain.resume import ResumeData
from app.engines import diff_highlight
from app.engines.fact_guard import FactGuard, _source_tech_vocab, _source_vocabulary

logger = logging.getLogger(__name__)

_TOOL_PROMPTS: dict[AgentTool, str] = {
    AgentTool.SCORE: AGENT_SCORE_PROMPT,
    AgentTool.TARGET: AGENT_TARGET_PROMPT,
    AgentTool.SUGGEST_BULLETS: AGENT_SUGGEST_BULLETS_PROMPT,
    AgentTool.REWRITE_SUMMARY: AGENT_REWRITE_SUMMARY_PROMPT,
    AgentTool.EXPLAIN_ISSUES: AGENT_EXPLAIN_ISSUES_PROMPT,
    AgentTool.OPTIMIZE: AGENT_OPTIMIZE_PROMPT,
    AgentTool.CHECK_FACTS: AGENT_CHECK_FACTS_PROMPT,
}

_TOOL_TO_CHANGE_TYPE: dict[AgentTool, ChangeType] = {
    AgentTool.SCORE: ChangeType.GRAMMAR,
    AgentTool.TARGET: ChangeType.SKILL_ADD,
    AgentTool.SUGGEST_BULLETS: ChangeType.BULLET,
    AgentTool.REWRITE_SUMMARY: ChangeType.SUMMARY,
    AgentTool.EXPLAIN_ISSUES: ChangeType.GRAMMAR,
    AgentTool.OPTIMIZE: ChangeType.REWRITE,
    AgentTool.CHECK_FACTS: ChangeType.GRAMMAR,
}


def _resume_to_text(resume: ResumeData) -> str:
    """Convert a ResumeData model to a readable text block for prompts."""
    parts: list[str] = []

    if resume.contact:
        c = resume.contact
        parts.append(f"Name: {c.name or ''}")
        if c.email:
            parts.append(f"Email: {c.email}")
        if c.phone:
            parts.append(f"Phone: {c.phone}")
        if c.location:
            parts.append(f"Location: {c.location}")

    if resume.headline:
        parts.append(f"Headline: {resume.headline}")

    if resume.summary:
        parts.append(f"\nSummary: {resume.summary}")

    if resume.skills:
        parts.append(f"\nSkills: {', '.join(resume.skills)}")

    if resume.experience:
        parts.append("\nExperience:")
        for i, exp in enumerate(resume.experience):
            parts.append(f"  [{i}] {exp.title or ''} at {exp.company or ''} ({exp.start_date or ''} - {exp.end_date or 'Present'})")
            for j, bullet in enumerate(exp.bullets):
                parts.append(f"    - [{j}] {bullet}")

    if resume.education:
        parts.append("\nEducation:")
        for edu in resume.education:
            parts.append(f"  {edu.degree or ''} - {edu.institution or ''} ({edu.year or ''})")

    if resume.certifications:
        parts.append(f"\nCertifications: {', '.join(resume.certifications)}")

    return "\n".join(parts)


def _parse_agent_actions(raw: dict[str, Any], tool: AgentTool) -> AgentProposal:
    """Parse raw JSON output into an AgentProposal."""
    actions: list[AgentAction] = []
    for item in raw.get("actions", []):
        actions.append(
            AgentAction(
                tool=AgentTool(item.get("tool", tool.value)),
                description=item.get("description", ""),
                section=item.get("section", ""),
                original=item.get("original", ""),
                proposed=item.get("proposed", ""),
                experience_index=item.get("experience_index"),
                bullet_index=item.get("bullet_index"),
            )
        )

    return AgentProposal(
        tool=tool,
        summary=raw.get("summary", ""),
        actions=actions,
    )


def _build_proposed_change(
    action: AgentAction,
) -> ProposedChange:
    """Convert an AgentAction to a ProposedChange for fact guard validation."""
    change_type = _TOOL_TO_CHANGE_TYPE.get(action.tool, ChangeType.GRAMMAR)
    return ProposedChange(
        change_type=change_type,
        section=action.section,
        original=action.original,
        rewritten=action.proposed,
        experience_index=action.experience_index,
        bullet_index=action.bullet_index,
    )


class AgentService:
    """Orchestrates the agent proposal pipeline."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient()
        self._fact_guard = FactGuard()

    def propose(
        self,
        resume: ResumeData,
        jd_text: str,
        tool: AgentTool,
        extra_context: str = "",
    ) -> AgentProposal:
        """Generate a proposal of changes for the given tool.

        Returns an AgentProposal with actions validated through FactGuard.
        """
        resume_text = _resume_to_text(resume)
        prompt_template = _TOOL_PROMPTS[tool]

        format_kwargs: dict[str, str] = {
            "resume_text": resume_text,
            "job_description": jd_text,
        }

        if tool == AgentTool.SUGGEST_BULLETS:
            idx = 0
            if resume.experience:
                idx = len(resume.experience) - 1
            format_kwargs["experience_index"] = str(idx)
        elif tool == AgentTool.REWRITE_SUMMARY:
            format_kwargs["current_summary"] = resume.summary or ""
            format_kwargs["resume_text"] = resume_text
        elif tool == AgentTool.EXPLAIN_ISSUES:
            format_kwargs["issues_text"] = extra_context or "No specific issues provided."
        elif tool == AgentTool.CHECK_FACTS:
            format_kwargs["original_text"] = resume_text
            format_kwargs["proposed_text"] = extra_context
            format_kwargs.pop("resume_text", None)

        prompt = prompt_template.format(**format_kwargs)

        raw_text = self._client.generate(
            prompt=prompt,
            system=AGENT_SYSTEM,
            json_mode=True,
        )

        try:
            raw_json = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("Agent returned invalid JSON, wrapping as text proposal")
            return AgentProposal(
                tool=tool,
                summary=raw_text[:500],
                actions=[],
            )

        proposal = _parse_agent_actions(raw_json, tool)

        source_vocab = _source_vocabulary(resume)
        source_tech = _source_tech_vocab(resume)

        for action in proposal.actions:
            change = _build_proposed_change(action)
            validated = self._fact_guard._check_text_change(
                change.change_type,
                change.section,
                change.original,
                change.rewritten,
                source_vocab,
                source_tech,
                experience_index=change.experience_index,
                bullet_index=change.bullet_index,
            )
            action.accepted = not validated.requires_review

        return proposal

    def get_diff_html(
        self,
        original: ResumeData,
        optimized: ResumeData,
    ) -> str:
        """Generate an HTML diff between original and optimized resumes."""
        return diff_highlight.resume_diff_html(original, optimized)

    def create_conversation_title(self, tool: AgentTool, jd_text: str) -> str:
        """Generate a short title for a new conversation."""
        role_hint = jd_text[:60].strip().replace("\n", " ") if jd_text else "General"
        return f"{tool.value.replace('_', ' ').title()} — {role_hint}"
