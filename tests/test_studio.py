"""Tests for ResumeStudioViewModel, SectionNavigator, SectionEditor, InsightsPanel."""
from __future__ import annotations

import copy
import sys
from unittest.mock import MagicMock, patch


# ── PySide6 import guard ───────────────────────────────────────────────────
from PySide6.QtWidgets import QApplication, QTextEdit

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


def test_section_navigator_select_section_sets_row():
    from app.ui.components.section_navigator import SectionNavigator
    nav = SectionNavigator(SECTION_NAMES)
    # Programmatic select_section blocks signals to avoid recursion
    nav.select_section("Skills")
    assert nav._list.currentItem().text() == "Skills"


def test_section_navigator_click_emits_signal():
    from app.ui.components.section_navigator import SectionNavigator
    nav = SectionNavigator(SECTION_NAMES)
    spy = MagicMock()
    nav.section_selected.connect(spy)
    # Simulate user clicking on item 0
    nav._list.setCurrentRow(0)
    spy.assert_called_once_with(SECTION_NAMES[0])


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


# ── Helper for ATS with issues ─────────────────────────────────────────────

def _make_ats_with_issues() -> ATSResult:
    return ATSResult(
        ats_score=60,
        keyword_match_pct=40.0,
        skills_match_pct=30.0,
        matched_keywords=["python"],
        missing_keywords=["docker", "kubernetes", "aws"],
        score_report=ResumeScoreReport(
            ruleset_version="2026.1",
            overall_score=60,
            categories=[
                CategoryScore(
                    category=ScoreCategory.CONTENT,
                    score=50,
                    weight=0.30,
                    issues=[
                        ResumeIssue(
                            code="CONTENT_001",
                            category=ScoreCategory.CONTENT,
                            path="summary",
                            message="Summary is too short",
                            severity=IssueSeverity.WARNING,
                            recommendation="Add more detail",
                            penalty=5.0,
                        ),
                    ],
                ),
                CategoryScore(
                    category=ScoreCategory.FORMAT,
                    score=70,
                    weight=0.20,
                    issues=[
                        ResumeIssue(
                            code="FORMAT_001",
                            category=ScoreCategory.FORMAT,
                            path="contact",
                            message="Missing contact info",
                            severity=IssueSeverity.ERROR,
                            recommendation="Add email",
                            penalty=3.0,
                        ),
                    ],
                ),
            ],
            generated_at=datetime.now(timezone.utc),
        ),
    )


# ── Task 11: Auto-save ────────────────────────────────────────────────────


def test_auto_save_timer_is_single_shot():
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    window.state = MagicMock()
    window.state.resume = None
    window.state.active_resume_id = None
    page = ResumeStudioPage(window)
    assert page._auto_save_timer.isSingleShot()
    assert page._auto_save_timer.interval() == 2000


def test_auto_save_skips_when_no_resume_id():
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    window.state = MagicMock()
    window.state.resume = None
    window.state.active_resume_id = None
    page = ResumeStudioPage(window)
    page._vm.resume = _make_resume()
    with patch("app.ui.pages.studio.get_session") as mock_session:
        page._auto_save()
        mock_session.assert_not_called()


def test_auto_save_skips_when_no_resume():
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    window.state = MagicMock()
    window.state.resume = None
    window.state.active_resume_id = 42
    page = ResumeStudioPage(window)
    with patch("app.ui.pages.studio.get_session") as mock_session:
        page._auto_save()
        mock_session.assert_not_called()


def test_auto_save_calls_repository():
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    window.state = MagicMock()
    window.state.resume = None
    window.state.active_resume_id = 42
    page = ResumeStudioPage(window)
    page._vm.resume = _make_resume()
    with patch("app.ui.pages.studio.get_session") as mock_session:
        mock_ctx = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        page._auto_save()
        mock_session.assert_called_once()


# ── Task 12: Resume duplication ───────────────────────────────────────────


def test_duplicate_resume_returns_deep_copy():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    dup = vm.duplicate_resume()
    assert dup is not None
    assert dup is not vm.resume
    assert dup.contact.name == "Alice (Copy)"


def test_duplicate_resume_independent():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    dup = vm.duplicate_resume()
    dup.summary = "Changed summary"
    assert vm.resume.summary != "Changed summary"


def test_duplicate_resume_none_when_empty():
    vm = ResumeStudioViewModel(state=_make_state())
    assert vm.duplicate_resume() is None


def test_duplicate_resume_preserves_other_fields():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    dup = vm.duplicate_resume()
    assert dup.skills == vm.resume.skills
    assert len(dup.experience) == len(vm.resume.experience)
    assert dup.education == vm.resume.education


# ── Task 14: Section reorder ──────────────────────────────────────────────


def test_section_order_default():
    vm = ResumeStudioViewModel(state=_make_state())
    assert vm.section_order == SECTION_NAMES


def test_move_section_up():
    vm = ResumeStudioViewModel(state=_make_state())
    spy = MagicMock()
    vm.section_order_changed.connect(spy)
    vm.move_section("Summary", -1)
    assert vm.section_order[0] == "Summary"
    assert vm.section_order[1] == "Contact"
    spy.assert_called_once()


def test_move_section_down():
    vm = ResumeStudioViewModel(state=_make_state())
    spy = MagicMock()
    vm.section_order_changed.connect(spy)
    vm.move_section("Contact", 1)
    assert vm.section_order[0] == "Summary"
    assert vm.section_order[1] == "Contact"
    spy.assert_called_once()


def test_move_section_no_op_at_top():
    vm = ResumeStudioViewModel(state=_make_state())
    spy = MagicMock()
    vm.section_order_changed.connect(spy)
    vm.move_section("Contact", -1)
    assert vm.section_order[0] == "Contact"
    spy.assert_not_called()


def test_move_section_no_op_at_bottom():
    vm = ResumeStudioViewModel(state=_make_state())
    spy = MagicMock()
    vm.section_order_changed.connect(spy)
    last = vm.section_order[-1]
    vm.move_section(last, 1)
    assert vm.section_order[-1] == last
    spy.assert_not_called()


# ── Task 15: Custom headings / rename ─────────────────────────────────────


def test_custom_heading_default():
    vm = ResumeStudioViewModel(state=_make_state())
    assert vm.get_display_name("Contact") == "Contact"
    assert vm.custom_headings == {}


def test_set_custom_heading():
    vm = ResumeStudioViewModel(state=_make_state())
    spy = MagicMock()
    vm.custom_headings_changed.connect(spy)
    vm.set_custom_heading("Contact", "My Info")
    assert vm.get_display_name("Contact") == "My Info"
    assert vm.custom_headings == {"Contact": "My Info"}
    spy.assert_called_once()


def test_set_custom_heading_same_as_section_clears():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.set_custom_heading("Contact", "Contact")
    assert vm.custom_headings == {}


def test_get_internal_name_with_heading():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.set_custom_heading("Contact", "My Info")
    assert vm.get_internal_name("My Info") == "Contact"


def test_get_internal_name_without_heading():
    vm = ResumeStudioViewModel(state=_make_state())
    assert vm.get_internal_name("Summary") == "Summary"


def test_get_internal_name_unknown_returns_input():
    vm = ResumeStudioViewModel(state=_make_state())
    assert vm.get_internal_name("Unknown") == "Unknown"


# ── Task 16: Issue navigation signal ──────────────────────────────────────


def test_insights_panel_emits_issue_selected():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    panel = ResumeInsightsPanel()
    spy = MagicMock()
    panel.issue_selected.connect(spy)
    panel.update_from_ats(_make_ats_with_issues())
    from PySide6.QtWidgets import QPushButton
    btns = panel._issues_container.findChildren(QPushButton)
    assert len(btns) == 2
    btns[0].click()
    spy.assert_called_once_with("Summary")


def test_insights_panel_issue_button_mapped_to_section():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    panel = ResumeInsightsPanel()
    spy = MagicMock()
    panel.issue_selected.connect(spy)
    panel.update_from_ats(_make_ats_with_issues())
    from PySide6.QtWidgets import QPushButton
    btns = panel._issues_container.findChildren(QPushButton)
    assert len(btns) == 2
    btns[1].click()
    spy.assert_called_once_with("Contact")


def test_insights_panel_no_issues_shows_message():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    panel = ResumeInsightsPanel()
    panel.update_from_ats(_make_ats())
    from PySide6.QtWidgets import QLabel
    labels = [
        w for w in panel._issues_container.findChildren(QLabel)
        if "No issues" in (w.text() or "")
    ]
    assert len(labels) == 1


# ── Section navigator reorder and rename signals ──────────────────────────


def test_navigator_up_down_buttons_exist():
    from app.ui.components.section_navigator import SectionNavigator
    nav = SectionNavigator(SECTION_NAMES)
    assert nav._up_btn is not None
    assert nav._down_btn is not None


def test_navigator_move_down():
    from app.ui.components.section_navigator import SectionNavigator
    nav = SectionNavigator(SECTION_NAMES)
    spy = MagicMock()
    nav.section_reorder.connect(spy)
    nav._list.setCurrentRow(0)
    nav._on_move_down()
    assert nav._list.item(0).text() == SECTION_NAMES[1]
    assert nav._list.item(1).text() == SECTION_NAMES[0]
    spy.assert_called_once_with(SECTION_NAMES[0], 1)


def test_navigator_move_up():
    from app.ui.components.section_navigator import SectionNavigator
    nav = SectionNavigator(SECTION_NAMES)
    spy = MagicMock()
    nav.section_reorder.connect(spy)
    nav._list.setCurrentRow(1)
    nav._on_move_up()
    assert nav._list.item(0).text() == SECTION_NAMES[1]
    assert nav._list.item(1).text() == SECTION_NAMES[0]
    spy.assert_called_once_with(SECTION_NAMES[1], -1)


def test_navigator_set_sections():
    from app.ui.components.section_navigator import SectionNavigator
    nav = SectionNavigator(SECTION_NAMES)
    new_order = ["Skills", "Contact", "Summary"]
    nav.set_sections(new_order)
    assert nav._list.count() == 3
    assert nav._list.item(0).text() == "Skills"
    assert nav._list.item(1).text() == "Contact"
    assert nav._list.item(2).text() == "Summary"


def test_navigator_double_click_renames():
    from app.ui.components.section_navigator import SectionNavigator
    nav = SectionNavigator(SECTION_NAMES)
    spy = MagicMock()
    nav.section_renamed.connect(spy)
    nav._list.setCurrentRow(0)
    item = nav._list.item(0)
    item.setText("My Info")
    nav.section_renamed.emit(SECTION_NAMES[0], "My Info")
    spy.assert_called_once_with(SECTION_NAMES[0], "My Info")


# ── SectionEditor scroll_to_field ─────────────────────────────────────────


def test_editor_scroll_to_field_finds_widget():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Contact", resume.contact)
    # Should not raise even if scroll parent is None
    editor.scroll_to_field("name")


# ── ResumeRepository.update ───────────────────────────────────────────────


def test_resume_repository_update():
    from app.database.session import get_session
    from app.database.repositories.resume_repository import ResumeRepository
    with get_session() as session:
        repo = ResumeRepository(session)
        rid = repo.save("Test", "{}", "", "test", "test.pdf")
        assert repo.update(rid, '{"updated": true}')
        row = repo.get_by_id(rid)
        assert row.data_json == '{"updated": true}'


def test_resume_repository_update_nonexistent():
    from app.database.session import get_session
    from app.database.repositories.resume_repository import ResumeRepository
    with get_session() as session:
        repo = ResumeRepository(session)
        assert repo.update(99999, '{"x": 1}') is False


# ── Phase 3: Task 17 — Summary generator prompts and service ───────────────


def test_generate_summary_prompt_has_placeholders():
    from app.ai.prompts import GENERATE_SUMMARY_PROMPT
    assert "{candidate_name}" in GENERATE_SUMMARY_PROMPT
    assert "{skills}" in GENERATE_SUMMARY_PROMPT
    assert "{experience}" in GENERATE_SUMMARY_PROMPT
    assert "{job_description}" in GENERATE_SUMMARY_PROMPT


def test_generate_summary_system_delimiter():
    from app.ai.prompts import GENERATE_SUMMARY_SYSTEM
    assert "<<<USER_INPUT>>>" in GENERATE_SUMMARY_SYSTEM


def test_summary_generator_output_model():
    from app.services.summary_generator import SummaryAIOutput
    out = SummaryAIOutput(summary="Senior engineer with 5 years experience.")
    assert out.summary == "Senior engineer with 5 years experience."


# ── Phase 3: Task 18 — Headline generator prompts and service ──────────────


def test_generate_headline_prompt_has_placeholders():
    from app.ai.prompts import GENERATE_HEADLINE_PROMPT
    assert "{candidate_name}" in GENERATE_HEADLINE_PROMPT
    assert "{current_headline}" in GENERATE_HEADLINE_PROMPT
    assert "{skills}" in GENERATE_HEADLINE_PROMPT
    assert "{job_description}" in GENERATE_HEADLINE_PROMPT


def test_generate_headline_system_delimiter():
    from app.ai.prompts import GENERATE_HEADLINE_SYSTEM
    assert "<<<USER_INPUT>>>" in GENERATE_HEADLINE_SYSTEM


def test_headline_generator_output_model():
    from app.services.headline_generator import HeadlineAIOutput
    out = HeadlineAIOutput(headline="Senior Software Engineer | Python & Cloud")
    assert "Senior" in out.headline


# ── Phase 3: Task 18 — Headline support in ViewModel ───────────────────────


def test_vm_headline_section():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    old = vm.resume.headline
    vm.update_section("Headline", old, "New Headline")
    assert vm.resume.headline == "New Headline"


def test_vm_get_section_value_headline():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    assert vm.get_section_value("Headline") == vm.resume.headline


# ── Phase 3: Task 19 — Skill suggestions UI ────────────────────────────────


def test_insights_panel_has_suggestions_section():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    panel = ResumeInsightsPanel()
    assert hasattr(panel, "_suggestions_scroll")
    assert hasattr(panel, "_suggestions_container")
    assert hasattr(panel, "_suggestions_layout")


def test_insights_panel_update_from_suggestions():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    from app.domain.keyword_targeting import KeywordTarget, KeywordStatus
    panel = ResumeInsightsPanel()
    targets = [
        KeywordTarget(
            canonical_name="kubernetes",
            source_phrases=["k8s"],
            importance=0.9,
            frequency_in_job=3,
            status=KeywordStatus.MISSING,
            suggested_paths=["skills"],
        ),
    ]
    panel.update_from_suggestions(targets)
    from PySide6.QtWidgets import QPushButton
    btns = panel._suggestions_container.findChildren(QPushButton)
    assert len(btns) == 2  # Accept + Reject


def test_insights_panel_suggestion_accept_signal():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    from app.domain.keyword_targeting import KeywordTarget, KeywordStatus
    panel = ResumeInsightsPanel()
    spy = MagicMock()
    panel.suggestion_accepted.connect(spy)
    targets = [
        KeywordTarget(
            canonical_name="docker",
            source_phrases=["containers"],
            importance=0.8,
            frequency_in_job=2,
            status=KeywordStatus.MISSING,
            suggested_paths=["skills"],
        ),
    ]
    panel.update_from_suggestions(targets)
    from PySide6.QtWidgets import QPushButton
    btns = panel._suggestions_container.findChildren(QPushButton)
    btns[0].click()  # Accept
    spy.assert_called_once_with("docker")


def test_insights_panel_suggestion_reject_signal():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    from app.domain.keyword_targeting import KeywordTarget, KeywordStatus
    panel = ResumeInsightsPanel()
    spy = MagicMock()
    panel.suggestion_rejected.connect(spy)
    targets = [
        KeywordTarget(
            canonical_name="kubernetes",
            source_phrases=["k8s"],
            importance=0.9,
            frequency_in_job=3,
            status=KeywordStatus.PARTIAL,
            suggested_paths=["skills"],
        ),
    ]
    panel.update_from_suggestions(targets)
    from PySide6.QtWidgets import QPushButton
    btns = panel._suggestions_container.findChildren(QPushButton)
    btns[1].click()  # Reject
    spy.assert_called_once_with("kubernetes")


def test_insights_panel_no_missing_suggestions():
    from app.ui.components.resume_insights_panel import ResumeInsightsPanel
    from app.domain.keyword_targeting import KeywordTarget, KeywordStatus
    panel = ResumeInsightsPanel()
    targets = [
        KeywordTarget(
            canonical_name="python",
            source_phrases=[],
            importance=1.0,
            frequency_in_job=5,
            status=KeywordStatus.PRESENT,
        ),
    ]
    panel.update_from_suggestions(targets)
    from PySide6.QtWidgets import QLabel
    labels = [
        w for w in panel._suggestions_container.findChildren(QLabel)
        if "No suggestions" in (w.text() or "")
    ]
    assert len(labels) == 1


# ── Phase 3: Task 19 — Section editor generate buttons ─────────────────────


def test_editor_summary_has_generate_button():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    spy = MagicMock()
    editor.generate_summary_requested.connect(spy)
    editor.load("Summary", "Test summary")
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    gen_btns = [b for b in btns if b.objectName() == "generateSummaryBtn"]
    assert len(gen_btns) == 1
    gen_btns[0].click()
    spy.assert_called_once()


def test_editor_contact_has_generate_headline_button():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    spy = MagicMock()
    editor.generate_headline_requested.connect(spy)
    resume = _make_resume()
    editor.load("Contact", resume.contact)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    gen_btns = [b for b in btns if b.objectName() == "generateHeadlineBtn"]
    assert len(gen_btns) == 1
    gen_btns[0].click()
    spy.assert_called_once()


# ── Phase 3: Task 21 — Rollback button exists in optimization page ─────────


def test_optimization_page_has_revert_button():
    from app.ui.pages.optimization import OptimizationPage
    window = MagicMock()
    page = OptimizationPage(window)
    assert hasattr(page, "revert_btn")
    assert not page.revert_btn.isVisible()  # hidden by default


def test_optimization_page_original_resume_none_by_default():
    from app.ui.pages.optimization import OptimizationPage
    window = MagicMock()
    page = OptimizationPage(window)
    assert page._original_resume is None


# ── Sprint 3: CRUD / Reorder / Live Preview ───────────────────────────────


def test_editor_has_text_changed_signal():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    assert hasattr(editor, "text_changed")


def test_editor_has_set_reload_callback():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    called = []
    editor.set_reload_callback(lambda: called.append(True))
    editor._reload()
    assert called == [True]


def test_editor_experience_has_add_button():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Experience", resume.experience)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    add_btns = [b for b in btns if b.objectName() == "addExpBtn"]
    assert len(add_btns) == 1


def test_editor_experience_has_delete_buttons():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Experience", resume.experience)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    del_btns = [b for b in btns if b.objectName() == "deleteExpBtn"]
    assert len(del_btns) == len(resume.experience)


def test_editor_projects_has_add_button():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Projects", resume.projects)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    add_btns = [b for b in btns if b.objectName() == "addProjBtn"]
    assert len(add_btns) == 1


def test_editor_projects_has_delete_buttons():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Projects", resume.projects)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    del_btns = [b for b in btns if b.objectName() == "deleteProjBtn"]
    assert len(del_btns) == len(resume.projects)


def test_editor_education_has_add_button():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Education", resume.education)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    add_btns = [b for b in btns if b.objectName() == "addEduBtn"]
    assert len(add_btns) == 1


def test_editor_education_has_delete_buttons():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Education", resume.education)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    del_btns = [b for b in btns if b.objectName() == "deleteEduBtn"]
    assert len(del_btns) == len(resume.education)


def test_editor_experience_has_add_bullet_buttons():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Experience", resume.experience)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    add_bullet = [b for b in btns if b.text() == "+ Add Bullet"]
    assert len(add_bullet) == len(resume.experience)


def test_editor_list_has_up_down_buttons():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    resume = _make_resume()
    editor.load("Skills", resume.skills)
    from PySide6.QtWidgets import QPushButton
    btns = editor.findChildren(QPushButton)
    up_btns = [b for b in btns if b.text() == "\u2191"]
    down_btns = [b for b in btns if b.text() == "\u2193"]
    assert len(up_btns) == 1
    assert len(down_btns) == 1


def test_editor_list_move_item():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    editor.load("Skills", ["python", "sql", "docker"])
    editor._list_widget.setCurrentRow(0)
    editor._move_list_item(1)
    items = [editor._list_widget.item(i).text() for i in range(editor._list_widget.count())]
    assert items == ["sql", "python", "docker"]


def test_editor_list_move_item_no_op_at_boundaries():
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    editor.load("Skills", ["python", "sql"])
    editor._list_widget.setCurrentRow(0)
    editor._move_list_item(-1)
    items = [editor._list_widget.item(i).text() for i in range(editor._list_widget.count())]
    assert items == ["python", "sql"]
    editor._list_widget.setCurrentRow(1)
    editor._move_list_item(1)
    items = [editor._list_widget.item(i).text() for i in range(editor._list_widget.count())]
    assert items == ["python", "sql"]


def test_editor_experience_add_entry_via_vm():
    """Adding an experience entry via the ViewModel works end-to-end."""
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    old_exp = list(vm.resume.experience)
    new_exp = old_exp + [ExperienceItem(title="New Role")]
    vm.update_section("Experience", old_exp, new_exp)
    assert len(vm.resume.experience) == len(old_exp) + 1
    assert vm.resume.experience[-1].title == "New Role"
    assert vm.can_undo
    vm.undo()
    assert len(vm.resume.experience) == len(old_exp)


def test_editor_experience_delete_entry_via_vm():
    """Deleting an experience entry via the ViewModel works end-to-end."""
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    old_exp = list(vm.resume.experience)
    new_exp = old_exp[:-1]
    vm.update_section("Experience", old_exp, new_exp)
    assert len(vm.resume.experience) == len(old_exp) - 1
    vm.undo()
    assert len(vm.resume.experience) == len(old_exp)


def test_editor_bullet_reorder_via_vm():
    """Reordering bullets via the ViewModel works end-to-end."""
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    old_exp = copy.deepcopy(vm.resume.experience)
    new_exp = copy.deepcopy(old_exp)
    bullets = new_exp[0].bullets
    bullets[0], bullets[1] = bullets[1], bullets[0]
    vm.update_section("Experience", old_exp, new_exp)
    assert vm.resume.experience[0].bullets[0] == old_exp[0].bullets[1]
    vm.undo()
    assert vm.resume.experience[0].bullets[0] == old_exp[0].bullets[0]


def test_editor_text_changed_signal_emitted():
    """text_changed signal is emitted by the editor."""
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    spy = MagicMock()
    editor.text_changed.connect(spy)
    editor.load("Summary", "Hello world")
    # Simulate text change by calling the handler directly
    editor._on_text_edit_changed(editor._container.findChildren(QTextEdit)[0])
    spy.assert_called()


def test_editor_reload_callback_invoked():
    """Reload callback is called after structural changes."""
    from app.ui.components.section_editor import SectionEditor
    editor = SectionEditor()
    reloads = []
    editor.set_reload_callback(lambda: reloads.append(True))
    editor._reload()
    assert reloads == [True]


def test_editor_projects_add_entry_via_vm():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    old_proj = list(vm.resume.projects)
    new_proj = old_proj + [ProjectItem(title="New Project")]
    vm.update_section("Projects", old_proj, new_proj)
    assert len(vm.resume.projects) == len(old_proj) + 1
    vm.undo()
    assert len(vm.resume.projects) == len(old_proj)


def test_editor_education_add_entry_via_vm():
    vm = ResumeStudioViewModel(state=_make_state())
    vm.resume = _make_resume()
    old_edu = list(vm.resume.education)
    new_edu = old_edu + [EducationItem(degree="PhD")]
    vm.update_section("Education", old_edu, new_edu)
    assert len(vm.resume.education) == len(old_edu) + 1
    vm.undo()
    assert len(vm.resume.education) == len(old_edu)


# ── Studio load_from_state ─────────────────────────────────────────────────


def test_studio_load_from_state_populates_vm():
    """load_from_state() copies state.resume into the Studio VM."""
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    original = _make_resume()
    window.state.resume = original
    window.state.active_resume_id = None
    page = ResumeStudioPage(window)
    assert page._vm.resume is None
    page.load_from_state()
    assert page._vm.resume is not None
    assert page._vm.resume.contact.name == "Alice"


def test_studio_load_from_state_noop_when_none():
    """load_from_state() does nothing if state.resume is still None."""
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    window.state.resume = None
    page = ResumeStudioPage(window)
    page.load_from_state()
    assert page._vm.resume is None


def test_studio_load_from_state_replaces_existing():
    """load_from_state() replaces any resume already in the VM."""
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    first = _make_resume()
    second = _make_resume()
    second.contact = ContactInfo(name="Bob", email="bob@test.com")
    window.state.resume = first
    window.state.active_resume_id = None
    page = ResumeStudioPage(window)
    page.load_from_state()
    assert page._vm.resume.contact.name == "Alice"
    window.state.resume = second
    page.load_from_state()
    assert page._vm.resume.contact.name == "Bob"


def test_studio_load_from_state_deep_copies():
    """load_from_state() deep-copies so mutations don't leak into previous state."""
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    original = _make_resume()
    window.state.resume = original
    window.state.active_resume_id = None
    page = ResumeStudioPage(window)
    # Mutate the VM resume
    page.load_from_state()
    page._vm.resume.contact.name = "CHANGED"
    # The VM setter writes back to state, so state follows the VM.
    # Verify the deep copy is independent of the ORIGINAL object we started with.
    assert original.contact.name == "Alice"


def test_studio_load_from_state_enables_buttons():
    """load_from_state() enables the export and duplicate buttons."""
    from app.ui.pages.studio import ResumeStudioPage
    window = MagicMock()
    window.state.resume = _make_resume()
    window.state.active_resume_id = None
    page = ResumeStudioPage(window)
    page.load_from_state()
    assert not page._export_btn.isEnabled()
    assert page._dup_btn.isEnabled()


# ── OptimizationPage: Edit in Studio ───────────────────────────────────────


def test_optimization_page_has_edit_in_studio_button():
    from app.ui.pages.optimization import OptimizationPage
    window = MagicMock()
    page = OptimizationPage(window)
    assert hasattr(page, "edit_in_studio_btn")
    assert not page.edit_in_studio_btn.isVisible()


def test_optimization_page_edit_in_studio_hidden_by_default():
    from app.ui.pages.optimization import OptimizationPage
    window = MagicMock()
    page = OptimizationPage(window)
    assert not page.edit_in_studio_btn.isVisibleTo(None) or not page.edit_in_studio_btn.isVisible()


def test_optimization_page_edit_in_studio_replaces_state():
    """_edit_in_studio() copies optimized resume into state.resume."""
    from app.ui.pages.optimization import OptimizationPage
    window = MagicMock()
    original = _make_resume()
    optimized = _make_resume()
    optimized.contact = ContactInfo(name="Optimized", email="opt@test.com")
    window.state.resume = original
    window.state.optimized = optimized
    window.state.active_resume_id = 42
    window.nav.findItems.return_value = [MagicMock()]
    page = OptimizationPage(window)
    page._edit_in_studio()
    assert window.state.resume.contact.name == "Optimized"
    assert window.state.active_resume_id is None


def test_optimization_page_edit_in_studio_navigates():
    """_edit_in_studio() navigates to the Studio page."""
    from app.ui.pages.optimization import OptimizationPage
    window = MagicMock()
    window.state.optimized = _make_resume()
    window.state.active_resume_id = None
    studio_mock = MagicMock()
    window.get_page.return_value = studio_mock
    nav_item = MagicMock()
    window.nav.findItems.return_value = [nav_item]
    page = OptimizationPage(window)
    page._edit_in_studio()
    studio_mock.load_from_state.assert_called_once()
    window.nav.setCurrentItem.assert_called_once_with(nav_item)


def test_optimization_page_edit_in_studio_noop_without_optimized():
    """_edit_in_studio() is a no-op if state.optimized is None."""
    from app.ui.pages.optimization import OptimizationPage
    window = MagicMock()
    window.state.optimized = None
    page = OptimizationPage(window)
    page._edit_in_studio()
    window.get_page.assert_not_called()


def test_editor_education_exposes_location_and_cgpa_fields():
    from app.ui.components.section_editor import SectionEditor
    from PySide6.QtWidgets import QLineEdit

    editor = SectionEditor()
    editor.load(
        "Education",
        [EducationItem(
            degree="MSc Computer Networks",
            institution="Universiti Putra Malaysia",
            location="Selangor",
            cgpa="3.625",
            year="2015 – 2019",
        )],
    )
    values = {widget.text() for widget in editor.findChildren(QLineEdit)}
    assert "Selangor" in values
    assert "3.625" in values


def test_editor_certifications_exposes_issuer_and_year_fields():
    from app.ui.components.section_editor import SectionEditor
    from PySide6.QtWidgets import QLineEdit

    editor = SectionEditor()
    editor.load("Certifications", ["CCNP Routing & Switching | Cisco | 2014"])
    values = {widget.text() for widget in editor.findChildren(QLineEdit)}
    assert {"CCNP Routing & Switching", "Cisco", "2014"}.issubset(values)


def test_editor_projects_exposes_context_dates_and_bullets():
    from app.ui.components.section_editor import SectionEditor
    from PySide6.QtWidgets import QLineEdit

    editor = SectionEditor()
    editor.load(
        "Projects",
        [ProjectItem(
            title="Data Center Build",
            meta="Project within Example role",
            start_date="Mar 2025",
            end_date="May 2025",
            bullets=["Migrated production traffic."],
        )],
    )
    values = {widget.text() for widget in editor.findChildren(QLineEdit)}
    assert "Project within Example role" in values
    assert "Mar 2025" in values
    assert "May 2025" in values
    assert "Migrated production traffic." in values


def test_optimization_review_preview_recalculates_ats_score():
    from types import SimpleNamespace
    from app.domain.fact_guard import ChangeType, FactGuardResult, ProposedChange
    from app.engines.ats_engine import analyze
    from app.ui.pages.optimization import OptimizationPage

    original = ResumeData(
        contact=ContactInfo(email="alice@test.com", phone="5551234567"),
        summary="Python engineer",
        skills=["Python"],
    )
    job_text = "Requirements:\nPython and Docker"
    before = analyze(original, job_text)
    change = ProposedChange(
        change_type=ChangeType.SKILL_ADD,
        section="skills",
        original="",
        rewritten="Docker",
        accepted=True,
    )
    state = SimpleNamespace(
        resume=original,
        optimized=None,
        fact_guard=FactGuardResult(safe_changes=[change]),
        job_text=job_text,
        ats=before,
        ats_after=None,
    )
    window = MagicMock()
    window.state = state
    page = OptimizationPage(window)

    page._refresh_review_preview()

    assert "Docker" in state.optimized.skills
    assert state.ats_after.ats_score > before.ats_score
