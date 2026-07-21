"""Regression tests for top-section editing, review, and approved export."""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
from app.domain.resume import ContactInfo, ProjectItem, ResumeData
from app.ui.components.resumeai.section_tabs import SectionTabBar
from app.ui.components.section_editor import SectionEditor
from app.ui.pages.studio import ResumeStudioPage
from app.ui.view_models.studio_vm import ResumeStudioViewModel

_app = QApplication.instance() or QApplication(sys.argv)


def _state() -> MagicMock:
    state = MagicMock()
    state.resume = None
    state.optimized = None
    state.ats = None
    state.job_text = ""
    state.active_resume_id = None
    state.fact_guard = None
    return state


def _resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Alice", email="alice@example.com"),
        summary="Engineer",
        skills=["Python"],
    )


def _window() -> MagicMock:
    window = MagicMock()
    window.state = _state()
    window.notify = MagicMock()
    return window


def test_top_tabs_are_real_editable_destinations() -> None:
    tab_bar = SectionTabBar()
    assert tab_bar.DEFAULT_SECTIONS == [
        "CONTACT",
        "SUMMARY",
        "EXPERIENCE",
        "PROJECTS",
        "EDUCATION",
        "SKILLS",
        "CERTIFICATIONS",
        "LANGUAGES",
        "REVIEW",
    ]


def test_programmatic_tab_selection_can_avoid_signal_loop() -> None:
    tab_bar = SectionTabBar()
    spy = MagicMock()
    tab_bar.tab_selected.connect(spy)

    tab_bar.select_tab("SKILLS", emit_signal=False)

    assert tab_bar.selected_section == "SKILLS"
    spy.assert_not_called()


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


def test_undo_invalidates_approved_export_snapshot() -> None:
    vm = ResumeStudioViewModel(_state())
    vm.resume = _resume()
    vm.update_section("Summary", "Engineer", "Senior Engineer")
    vm.approve_for_export()

    vm.undo()

    assert not vm.is_approved_for_export


def test_approved_resume_is_a_defensive_copy() -> None:
    vm = ResumeStudioViewModel(_state())
    vm.resume = _resume()
    vm.approve_for_export()

    exported = vm.approved_resume
    exported.summary = "Changed outside the view model"

    assert vm.approved_resume.summary == "Engineer"


def test_studio_ats_does_not_overwrite_original_baseline() -> None:
    state = _state()
    original_ats = object()
    state.ats = original_ats
    vm = ResumeStudioViewModel(state)

    vm.ats = MagicMock()

    assert state.ats is original_ats


def test_pending_fact_guard_change_blocks_review() -> None:
    window = _window()
    window.state.resume = _resume()
    window.state.fact_guard = FactGuardResult(
        flagged_changes=[
            ProposedChange(
                change_type=ChangeType.REWRITE,
                original="old",
                rewritten="new",
                accepted=None,
            )
        ]
    )
    page = ResumeStudioPage(window)
    page.load_from_state()

    blockers = page._review_blockers()

    assert any("pending AI-generated" in blocker for blocker in blockers)


def test_export_is_disabled_until_approved() -> None:
    window = _window()
    window.state.resume = _resume()
    page = ResumeStudioPage(window)
    page.load_from_state()

    assert not page._export_btn.isEnabled()
    page._vm.approve_for_export()
    assert page._export_btn.isEnabled()


def test_section_editor_replaces_widget_tree_immediately():
    """Rapid tab changes must detach the previous editor before the next draws."""
    from app.ui.components.section_editor import SectionEditor

    editor = SectionEditor()
    editor.resize(900, 600)
    editor.show()

    editor.load(
        "Projects",
        [ProjectItem(title="Old project", description="Old description")],
    )
    old_container = editor._container

    # Deliberately do not process Qt events between loads.  This reproduces the
    # original overlap, where deleteLater() left the old controls visible.
    editor.load("Skills", ["Python", "SQL"])

    assert editor._container is not old_container
    assert old_container is not None
    assert old_container.parent() is None
    assert not old_container.isVisible()
    assert editor._title.text() == "Skills"

    editor.close()


def test_show_destination_loads_changed_section_once():
    """The view-model signal and public navigation must not both rebuild UI."""
    from app.ui.pages.studio import ResumeStudioPage

    window = MagicMock()
    window.state = _state()
    window.state.resume = _resume()
    window.state.active_resume_id = None
    window.state.fact_guard = None

    page = ResumeStudioPage(window)
    page._vm.resume = _resume()
    page._editor.load = MagicMock()

    page.show_destination("Projects")

    page._editor.load.assert_called_once()
    assert page._editor.load.call_args.args[0] == "Projects"

    page.close()
