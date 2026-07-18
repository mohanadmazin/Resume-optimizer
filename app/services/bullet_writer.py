"""Bullet writer service — generates 3 alternatives from structured evidence."""
import logging
import re

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import BULLET_WRITER_PROMPT, BULLET_WRITER_SYSTEM
from app.domain.bullet_writer import (
    BulletEvidence,
    BulletSuggestion,
    BulletSuggestionResult,
)

logger = logging.getLogger(__name__)


def generate_bullet_suggestions(
    evidence: BulletEvidence,
    client: OllamaClient,
) -> BulletSuggestionResult:
    """Generate three bullet alternatives from structured evidence.

    The AI must use ONLY the supplied evidence. After generation,
    the suggestions are validated and returned for user review.
    """
    tools_str = ", ".join(evidence.tools) if evidence.tools else "None specified"
    keywords_str = ", ".join(evidence.target_keywords) if evidence.target_keywords else "None"
    outcome_str = evidence.outcome or "Not specified"
    metric_str = evidence.metric or "Not specified"

    prompt = BULLET_WRITER_PROMPT.format(
        role=evidence.role,
        company=evidence.company,
        responsibility=evidence.responsibility,
        action=evidence.action,
        tools=tools_str,
        outcome=outcome_str,
        metric=metric_str,
        keywords=keywords_str,
    )

    logger.info(
        "Generating bullet suggestions for role=%s company=%s",
        evidence.role, evidence.company,
    )

    data = client.generate_json(prompt, system=BULLET_WRITER_SYSTEM)

    suggestions_raw = data.get("suggestions", [])
    if not isinstance(suggestions_raw, list) or len(suggestions_raw) != 3:
        raise ValueError(
            f"AI returned {len(suggestions_raw)} suggestions, expected exactly 3"
        )

    suggestions: list[BulletSuggestion] = []
    for raw in suggestions_raw:
        if not isinstance(raw, dict):
            raise ValueError("Each suggestion must be a JSON object")
        suggestion = BulletSuggestion(
            text=raw.get("text", ""),
            style=raw.get("style", "achievement"),
            used_keywords=raw.get("used_keywords", []),
            evidence_fields=raw.get("evidence_fields", []),
            requires_review=True,
        )
        _validate_suggestion(suggestion, evidence)
        suggestions.append(suggestion)

    return BulletSuggestionResult(suggestions=suggestions)


def _validate_suggestion(
    suggestion: BulletSuggestion,
    evidence: BulletEvidence,
) -> None:
    """Post-hoc validation: ensure suggestion doesn't invent facts."""
    text_lower = suggestion.text.lower()

    # Check for invented numbers not in evidence
    evidence_numbers = set()
    for field_val in (evidence.metric, evidence.outcome):
        if field_val:
            evidence_numbers.update(re.findall(r"\d+", field_val))

    suggestion_numbers = set(re.findall(r"\d+", suggestion.text))
    invented_numbers = suggestion_numbers - evidence_numbers
    if invented_numbers:
        logger.warning(
            "Suggestion contains numbers not in evidence: %s",
            invented_numbers,
        )
        suggestion.requires_review = True

    # Check that suggestion uses at least one evidence field
    if not suggestion.evidence_fields:
        suggestion.requires_review = True

    # All suggestions always require review
    suggestion.requires_review = True
