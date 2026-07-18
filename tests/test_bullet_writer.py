"""Tests for bullet writer domain models, service, and undo stack."""
import pytest
from unittest.mock import MagicMock, patch

from app.domain.bullet_writer import (
    BulletEvidence,
    BulletSuggestion,
    BulletSuggestionResult,
)
from app.services.bullet_writer import _validate_suggestion
from app.ui.undo_stack import UndoCommand, UndoStack


# ── BulletEvidence ─────────────────────────────────────────────────────────


def test_evidence_minimal():
    e = BulletEvidence(
        experience_index=0,
        role="Developer",
        company="Acme",
        responsibility="Build APIs",
        action="Designed REST endpoints",
    )
    assert e.tools == []
    assert e.outcome is None
    assert e.metric is None
    assert e.target_keywords == []


def test_evidence_full():
    e = BulletEvidence(
        experience_index=1,
        role="Lead Engineer",
        company="TechCorp",
        responsibility="Lead team",
        action="Managed 5 engineers",
        tools=["Python", "Django", "PostgreSQL"],
        outcome="Shipped 3 major features",
        metric="40% faster deployments",
        target_keywords=["leadership", "python"],
    )
    assert len(e.tools) == 3
    assert e.metric == "40% faster deployments"


def test_evidence_rejects_negative_index():
    with pytest.raises(Exception):
        BulletEvidence(
            experience_index=-1,
            role="X",
            company="X",
            responsibility="X",
            action="X",
        )


# ── BulletSuggestion ──────────────────────────────────────────────────────


def test_suggestion_valid():
    s = BulletSuggestion(
        text="Built REST APIs serving 1M users",
        style="achievement",
        used_keywords=["rest", "apis"],
        evidence_fields=["action", "tools"],
        requires_review=True,
    )
    assert s.requires_review is True
    assert s.style == "achievement"


def test_suggestion_valid_styles():
    for style in ("concise", "achievement", "technical"):
        s = BulletSuggestion(text="Test", style=style)
        assert s.style == style


def test_suggestion_rejects_empty_text():
    with pytest.raises(Exception):
        BulletSuggestion(text="", style="concise")


def test_suggestion_rejects_invalid_style():
    with pytest.raises(Exception):
        BulletSuggestion(text="Test", style="invalid")


# ── BulletSuggestionResult ────────────────────────────────────────────────


def test_result_requires_exactly_three():
    s = BulletSuggestion(text="Test", style="concise")
    with pytest.raises(Exception):
        BulletSuggestionResult(suggestions=[s, s])


def test_result_accepts_three():
    s = BulletSuggestion(text="Test", style="concise")
    result = BulletSuggestionResult(suggestions=[s, s, s])
    assert len(result.suggestions) == 3


# ── _validate_suggestion ──────────────────────────────────────────────────


def test_validate_marks_requires_review():
    evidence = BulletEvidence(
        experience_index=0,
        role="Dev",
        company="X",
        responsibility="Build",
        action="Built APIs",
        metric="100 users",
    )
    s = BulletSuggestion(
        text="Built APIs for 100 users",
        style="achievement",
        evidence_fields=["action", "metric"],
    )
    _validate_suggestion(s, evidence)
    assert s.requires_review is True


def test_validate_flags_invented_numbers():
    evidence = BulletEvidence(
        experience_index=0,
        role="Dev",
        company="X",
        responsibility="Build",
        action="Built APIs",
        metric="100 users",
    )
    s = BulletSuggestion(
        text="Increased revenue by 500% with new APIs",
        style="achievement",
        evidence_fields=["action"],
    )
    _validate_suggestion(s, evidence)
    assert s.requires_review is True


def test_validate_flags_empty_evidence_fields():
    evidence = BulletEvidence(
        experience_index=0,
        role="Dev",
        company="X",
        responsibility="Build",
        action="Built APIs",
    )
    s = BulletSuggestion(
        text="Something vague",
        style="concise",
        evidence_fields=[],
    )
    _validate_suggestion(s, evidence)
    assert s.requires_review is True


# ── UndoStack ──────────────────────────────────────────────────────────────


def test_undo_stack_push_and_undo():
    state = {"value": 0}
    stack = UndoStack()

    cmd = UndoCommand(
        description="set to 1",
        execute=lambda: state.__setitem__("value", 1),
        undo=lambda: state.__setitem__("value", 0),
    )
    stack.push(cmd)
    assert state["value"] == 1
    assert stack.can_undo is True
    assert stack.can_redo is False

    desc = stack.undo()
    assert desc == "set to 1"
    assert state["value"] == 0
    assert stack.can_undo is False
    assert stack.can_redo is True


def test_undo_stack_redo():
    state = {"value": 0}
    stack = UndoStack()

    cmd = UndoCommand(
        description="set to 1",
        execute=lambda: state.__setitem__("value", 1),
        undo=lambda: state.__setitem__("value", 0),
    )
    stack.push(cmd)
    stack.undo()
    desc = stack.redo()
    assert desc == "set to 1"
    assert state["value"] == 1


def test_undo_stack_push_clears_redo():
    state = {"value": 0}
    stack = UndoStack()

    cmd1 = UndoCommand(
        description="set to 1",
        execute=lambda: state.__setitem__("value", 1),
        undo=lambda: state.__setitem__("value", 0),
    )
    cmd2 = UndoCommand(
        description="set to 2",
        execute=lambda: state.__setitem__("value", 2),
        undo=lambda: state.__setitem__("value", 1),
    )
    stack.push(cmd1)
    stack.undo()
    assert stack.can_redo is True

    stack.push(cmd2)
    assert stack.can_redo is False
    assert state["value"] == 2


def test_undo_stack_empty_returns_none():
    stack = UndoStack()
    assert stack.undo() is None
    assert stack.redo() is None


def test_undo_stack_clear():
    state = {"value": 0}
    stack = UndoStack()
    cmd = UndoCommand(
        description="set to 1",
        execute=lambda: state.__setitem__("value", 1),
        undo=lambda: state.__setitem__("value", 0),
    )
    stack.push(cmd)
    stack.clear()
    assert stack.can_undo is False
    assert stack.can_redo is False
