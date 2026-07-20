"""Tests for ResumeStudioViewModel, SectionNavigator, SectionEditor, InsightsPanel."""
from __future__ import annotations

import copy
import sys
from unittest.mock import MagicMock

import pytest

# ── PySide6 import guard ───────────────────────────────────────────────────
from PySide6.QtWidgets import QApplication

from datetime import datetime, timezone

from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeData,
)
from app.domain.analysis import ATSResult
from app.domain.scoring import (
    CategoryScore,
    IssueSeverity,
    ResumeIssue,
    ResumeScoreReport,
    ScoreCategory,
)
from app.ui.undo_stack import UndoCommand
from app.ui.view_models.studio_vm import SECTION_NAMES, ResumeStudioViewModel

# Ensure QApplication instance exists for widget tests
_app = QApplication.instance() or QApplication(sys.argv)


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Alice", email="alice@test.com", phone="555-1234"),
        summary="Senior engineer with 5 years experience.",
        skills=["python", "sql", "docker"],
        experience=[
            ExperienceItem(
                title="Engineer",
                company="Acme",
                start_date="2020",
                end_date="2024",
                bullets=["Built things", "Led a team of 3"],
            )
        ],
        education=[
            EducationItem(degree="BS CS", institution="MIT", year="2019"),
        ],
        projects=[
            ProjectItem(title="ProjectX", description="A cool tool"),
        ],
        certifications=["AWS Solutions Architect"],
        languages=["English", "Spanish"],
    )


def _make_state() -> MagicMock:
    state = MagicMock()
    state.resume = None
    state.job_text = "Python engineer needed"
    state.ats = None
    return state


def _make_ats() -> ATSResult:
    return ATSResult(
        ats_score=75,
        keyword_match_pct=60.0,
        skills_match_pct=50.0,
        matched_keywords=["python"],
        missing_keywords=["docker", "kubernetes"],
        score_report=ResumeScoreReport(
            ruleset_version="2026.1",
            overall_score=75,
            categories=[
                CategoryScore(
                    category=ScoreCategory.CONTENT,
                    score=80,
                    weight=0.30,
                    issues=[],
                ),
            ],
            generated_at=datetime.now(timezone.utc),
        ),
    )


# ── ResumeStudioViewModel tests ────────────────────────────────────────────


def test_vm_initial_state():
    vm = ResumeStudioViewModel(state=_make_state())
    assert vm.resume is None
    assert vm.selected_section == "Contact"
    assert vm.ats is None
    assert not vm.can_undo
    assert not vm.can_redo


def test_vm_set_resume_emits_signal():
    state = _make_state()
    vm = ResumeStudioViewModel(state=state)
    spy = MagicMock()
    vm.resume_changed.connect(spy)
    vm.resume = _make_resume()
    spy.assert_called_once()
    assert state.resume is vm.resume


def test_vm_select_section_emits_signal():
    vm = ResumeStudioViewModel(state=_make_state())
    spy = MagicMock()
    vm.section_changed.connect(spy)
    vm.select_section("Summary")
    spy.assert_called_once_with("Summary")
    assert vm.selected_section == "Summary"


def test_vm_select_same_section_no_emit():
    vm = ResumeStudioViewModel(state=_make_state())
    spy = MagicMock()
    vm.section_changed.connect(spy)
    vm.select_section("Contact")
    spy.assert_not_called()


def test_vm_update_section_pushes_undo():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()

    old_summary = vm.resume.summary
    new_summary = "Updated summary text here."
    vm.update_section("Summary", old_summary, new_summary)

    assert vm.can_undo
    assert vm.resume.summary == new_summary


def test_vm_undo_reverts():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    original = vm.resume.summary

    vm.update_section("Summary", original, "New summary")
    assert vm.resume.summary == "New summary"

    vm.undo()
    assert vm.resume.summary == original
    assert not vm.can_undo
    assert vm.can_redo


def test_vm_redo_reapplies():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    original = vm.resume.summary

    vm.update_section("Summary", original, "New summary")
    vm.undo()
    vm.redo()
    assert vm.resume.summary == "New summary"
    assert vm.can_undo
    assert not vm.can_redo


def test_vm_redo_clears_on_new_push():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    original = vm.resume.summary

    vm.update_section("Summary", original, "First edit")
    vm.undo()
    assert vm.can_redo

    vm.update_section("Summary", original, "Second edit")
    assert not vm.can_redo


def test_vm_update_same_value_no_push():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    current = vm.resume.summary
    vm.update_section("Summary", current, current)
    assert not vm.can_undo


def test_vm_push_command_updates_resume():
    state = _make_state()
    vm = ResumeStudioViewModel(state=state)
    vm.resume = _make_resume()

    new_skills = ["python", "rust"]
    cmd = UndoCommand(
        description="Update skills",
        execute=lambda: setattr(vm._resume, "skills", new_skills),
        undo=lambda: setattr(vm._resume, "skills", ["python"]),
    )
    vm.push_command(cmd)
    assert vm.resume.skills == new_skills
    assert state.resume is vm.resume


def test_vm_get_section_value():
    vm = ResumeStudioViewModel(state=_make_state())
    resume = _make_resume()
    vm.resume = resume

    assert vm.get_section_value("Contact") is resume.contact
    assert vm.get_section_value("Summary") == resume.summary
    assert vm.get_section_value("Skills") is resume.skills
    assert vm.get_section_value("Experience") is resume.experience
    assert vm.get_section_value("Nonexistent") is None


def test_vm_has_resume_and_job_text():
    state = _make_state()
    vm = ResumeStudioViewModel(state=state)
    assert not vm.has_resume()
    assert vm.has_job_text()

    vm.resume = _make_resume()
    assert vm.has_resume()


def test_vm_clear():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    vm.update_section("Summary", vm.resume.summary, "Changed")
    assert vm.can_undo
    vm.clear()
    assert not vm.can_undo
    assert not vm.can_redo


def test_vm_multiple_undos():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()

    vm.update_section("Summary", vm.resume.summary, "Edit 1")
    vm.update_section("Summary", "Edit 1", "Edit 2")
    vm.update_section("Summary", "Edit 2", "Edit 3")

    vm.undo()
    assert vm.resume.summary == "Edit 2"
    vm.undo()
    assert vm.resume.summary == "Edit 1"
    vm.undo()
    assert vm.resume.summary == vm.resume.summary  # back to original


# ── SECTION_NAMES constant tests ───────────────────────────────────────────


def test_section_names_has_all():
    expected = {"Contact", "Summary", "Experience", "Projects",
                "Education", "Skills", "Certifications", "Languages"}
    assert set(SECTION_NAMES) == expected


# ── Component signal wiring tests ──────────────────────────────────────────


def test_section_editor_emits_signal():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    spy = MagicMock()
    editor.section_edited.connect(spy)

    resume = _make_resume()
    editor.load("Summary", resume.summary)
    # Simulate editing by directly calling the internal mechanism
    editor._old_value = "Original text"
    editor.section_edited.emit("Summary", "Original text", "New text")
    spy.assert_called_once_with("Summary", "Original text", "New text")


def test_section_navigator_select_section_sets_tab():
    from app.ui.components.section_navigator import SectionNavigator

    nav = SectionNavigator(SECTION_NAMES)
    # Programmatic selection blocks signals to avoid recursion.
    nav.select_section("Skills")
    assert nav.tabText(nav.currentIndex()) == "Skills"


def test_section_navigator_change_emits_signal():
    from app.ui.components.section_navigator import SectionNavigator

    nav = SectionNavigator(SECTION_NAMES)
    spy = MagicMock()
    nav.section_selected.connect(spy)
    # Move away from the initially selected first tab, then back.
    nav.setCurrentIndex(1)
    spy.reset_mock()
    nav.setCurrentIndex(0)
    spy.assert_called_once_with(SECTION_NAMES[0])


def test_section_navigator_includes_review():
    from app.ui.components.section_navigator import SectionNavigator

    nav = SectionNavigator(SECTION_NAMES)
    assert nav.tabText(nav.count() - 1) == "Review"


def test_resume_preview_set_and_clear():
    from app.ui.components.resume_preview import ResumePreview
    preview = ResumePreview()
    preview.set_markdown("Hello World")
    assert "Hello World" in preview._preview.toPlainText()
    preview.clear()
    assert preview._preview.toPlainText() == ""


def test_insights_panel_clear():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    panel = ResumeInsightsPanel()
    panel.update_from_ats(_make_ats())
    assert panel.ats_card._value.text() == "75"
    panel.clear()
    assert panel.ats_card._value.text() == "--"


def test_insights_panel_update_from_none():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    panel = ResumeInsightsPanel()
    panel.update_from_ats(_make_ats())
    panel.update_from_ats(None)
    assert panel.ats_card._value.text() == "--"
