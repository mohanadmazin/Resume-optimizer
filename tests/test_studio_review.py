"""Regression tests for Resume Studio editing, review, and export gating."""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.resume import ContactInfo, ResumeData
from app.ui.components.section_editor import SectionEditor
from app.ui.components.section_navigator import SectionNavigator
from app.ui.view_models.studio_vm import SECTION_NAMES, ResumeStudioViewModel

_app = QApplication.instance() or QApplication(sys.argv)


def _state() -> MagicMock:
    state = MagicMock()
    state.resume = None
    state.optimized = None
    state.ats = None
    state.job_text = ""
    return state


def _resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Alice", email="alice@example.com"),
        summary="Engineer",
        skills=["Python"],
    )


def test_top_navigator_contains_edit_sections_and_review() -> None:
    navigator = SectionNavigator(SECTION_NAMES)
    assert [navigator.tabText(i) for i in range(navigator.count())] == [
        *SECTION_NAMES,
        "Review",
    ]


def test_select_destination_uses_existing_tab() -> None:
    navigator = SectionNavigator(SECTION_NAMES)
    navigator.select_destination("Skills")
    assert navigator.tabText(navigator.currentIndex()) == "Skills"


def test_second_contact_edit_uses_first_edit_as_undo_baseline() -> None:
    editor = SectionEditor()
    spy = MagicMock()
    editor.section_edited.connect(spy)
    editor.load("Contact", _resume().contact)

    editor._line_edits["name"].setText("Bob")
    editor._on_contact_field("name")
    editor._line_edits["email"].setText("bob@example.com")
    editor._on_contact_field("email")

    first_old, first_new = spy.call_args_list[0].args[1:]
    second_old, second_new = spy.call_args_list[1].args[1:]
    assert first_old.name == "Alice"
    assert first_new.name == "Bob"
    assert second_old.name == "Bob"
    assert second_new.email == "bob@example.com"


def test_list_edit_is_committed() -> None:
    editor = SectionEditor()
    spy = MagicMock()
    editor.section_edited.connect(spy)
    editor.load("Skills", ["Python"])

    editor._list_widget.item(0).setText("Python 3")

    assert spy.call_count == 1
    assert spy.call_args.args == ("Skills", ["Python"], ["Python 3"])


def test_edit_invalidates_approved_export_snapshot() -> None:
    vm = ResumeStudioViewModel(_state())
    vm.resume = _resume()
    vm.approve_for_export()
    assert vm.is_approved_for_export
    assert vm.approved_resume.summary == "Engineer"

    vm.update_section("Summary", "Engineer", "Senior Engineer")

    assert not vm.is_approved_for_export
    assert vm.approved_resume is None


def test_approved_resume_is_a_defensive_copy() -> None:
    vm = ResumeStudioViewModel(_state())
    vm.resume = _resume()
    vm.approve_for_export()

    exported = vm.approved_resume
    exported.summary = "Changed outside the view model"

    assert vm.approved_resume.summary == "Engineer"
