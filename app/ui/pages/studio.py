"""Persistent, feature-rich Resume Studio with review-gated export."""
from __future__ import annotations

import copy
import logging
import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.resume_repository import ResumeRepository
from app.database.repositories.versioning_repository import VersioningRepository
from app.database.session import get_session
from app.domain.salary import SalaryEstimate
from app.exports.exporter import to_markdown
from app.engines.ats_engine import analyze
from app.services.salary_estimator import estimate_salary
from app.ui.components.resume_insights_panel import ResumeInsightsPanel
from app.ui.components.resume_preview import ResumePreview
from app.ui.components.resume_review_panel import ResumeReviewPanel
from app.ui.components.section_editor import SectionEditor
from app.ui.components.section_navigator import SectionNavigator
from app.ui.view_models.studio_vm import SECTION_NAMES, ResumeStudioViewModel

logger = logging.getLogger(__name__)

_AUTO_SAVE_INTERVAL_MS = 2000


class ResumeStudioPage(QWidget):
    """Edit, analyze, review, approve, and export one working resume."""

    destination_changed = Signal(str)

    def __init__(self, window: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._vm = ResumeStudioViewModel(state=window.state, parent=self)
        self._pending_preview_resume = None
        self._loaded_resume_id: int | None = None
        self._review_tab_index = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # The main window's top bar is the primary section navigation.  This
        # existing navigator remains available on demand for reorder/rename.
        self._nav = SectionNavigator(SECTION_NAMES)
        self._nav.section_selected.connect(self._on_section_selected)
        self._nav.section_reorder.connect(self._on_section_reorder)
        self._nav.section_renamed.connect(self._on_section_renamed)
        self._nav.setVisible(False)
        splitter.addWidget(self._nav)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._editor = SectionEditor()
        self._editor.section_edited.connect(self._on_section_edited)
        self._editor.text_changed.connect(self._on_text_changed)
        self._editor.generate_summary_requested.connect(self._on_generate_summary)
        self._editor.generate_headline_requested.connect(self._on_generate_headline)
        self._editor.generate_salary_requested.connect(self._on_generate_salary)
        self._editor.set_reload_callback(self._on_editor_reload)

        self._preview = ResumePreview()
        self._review = ResumeReviewPanel()
        self._review.approved.connect(self._approve_review)
        self._review.export_docx_requested.connect(lambda: self._export_as("DOCX"))
        self._review.export_pdf_requested.connect(lambda: self._export_as("PDF"))

        self._tabs.addTab(self._editor, "Editor")
        self._tabs.addTab(self._preview, "Preview")
        self._review_tab_index = self._tabs.addTab(self._review, "Review")
        self._tabs.currentChanged.connect(self._on_content_tab_changed)
        center_layout.addWidget(self._tabs)
        splitter.addWidget(center)

        self._insights = ResumeInsightsPanel()
        self._insights.issue_selected.connect(self._on_issue_selected)
        self._insights.suggestion_accepted.connect(self._on_suggestion_accepted)
        splitter.addWidget(self._insights)

        splitter.setSizes([0, 760, 300])
        root.addWidget(splitter, 1)
        self._splitter = splitter

        bar = QHBoxLayout()

        self._manage_sections_btn = QPushButton("Manage Sections")
        self._manage_sections_btn.setCheckable(True)
        self._manage_sections_btn.toggled.connect(self._toggle_section_manager)
        bar.addWidget(self._manage_sections_btn)

        bar.addStretch()

        self._undo_btn = QPushButton("Undo")
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(self._on_undo)
        bar.addWidget(self._undo_btn)

        self._redo_btn = QPushButton("Redo")
        self._redo_btn.setEnabled(False)
        self._redo_btn.clicked.connect(self._on_redo)
        bar.addWidget(self._redo_btn)

        self._dup_btn = QPushButton("Duplicate")
        self._dup_btn.setEnabled(False)
        self._dup_btn.clicked.connect(self._on_duplicate)
        bar.addWidget(self._dup_btn)

        self._save_version_btn = QPushButton("Save Version")
        self._save_version_btn.setEnabled(False)
        self._save_version_btn.clicked.connect(self._on_save_version)
        bar.addWidget(self._save_version_btn)

        bar.addSpacing(20)
        bar.addWidget(QLabel("Format:"))
        self._export_format = QComboBox()
        self._export_format.addItems(["PDF", "DOCX", "Markdown"])
        bar.addWidget(self._export_format)

        bar.addWidget(QLabel("Template:"))
        self._export_template = QComboBox()
        self._export_template.addItems(["Classic", "Modern", "Compact"])
        bar.addWidget(self._export_template)

        self._export_btn = QPushButton("Export Approved Resume")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        bar.addWidget(self._export_btn)
        root.addLayout(bar)

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(_AUTO_SAVE_INTERVAL_MS)
        self._auto_save_timer.timeout.connect(self._auto_save)

        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(350)
        self._analysis_timer.timeout.connect(self._recalculate)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)
        self._preview_timer.timeout.connect(self._update_preview)

        self._vm.resume_changed.connect(self._on_resume_changed)
        self._vm.section_changed.connect(self._on_section_changed)
        self._vm.ats_changed.connect(self._on_ats_changed)
        self._vm.undoStateChanged.connect(self._on_undo_state_changed)
        self._vm.section_order_changed.connect(self._on_section_order_changed)
        self._vm.custom_headings_changed.connect(self._on_custom_headings_changed)
        self._vm.reviewStateChanged.connect(self._on_review_state_changed)

    # ── Public lifecycle/navigation ─────────────────────────────────

    def force_reload(self) -> None:
        """Reset the loaded ID so the next on_show() always triggers a reload."""
        self._loaded_resume_id = None

    def on_show(self) -> None:
        state_resume = self.window.state.resume
        if state_resume is not None and (
            self._vm.resume is None
            or self._vm.resume != state_resume
            or self._loaded_resume_id != self.window.state.active_resume_id
        ):
            self.load_from_state()
        self._update_controls()

    def load_from_state(self) -> None:
        """Load the current global resume into the working Studio draft."""
        state_resume = self.window.state.resume
        if state_resume is None:
            return

        self._vm.resume = state_resume.model_copy(deep=True)
        self._loaded_resume_id = self.window.state.active_resume_id
        self.show_destination("Contact")
        self._recalculate()
        self._update_controls()

    def show_destination(self, destination: str) -> None:
        """Open one editable section or the final Review destination."""
        self._editor.save_pending_list()

        if destination == "Review":
            self._show_review()
            self.destination_changed.emit("Review")
            return

        if destination not in SECTION_NAMES:
            return

        self._tabs.setCurrentWidget(self._editor)

        # ``select_section`` emits ``section_changed`` synchronously. Let that
        # signal perform the load when the destination changes; loading here as
        # well created two widget trees during the same event-loop turn.
        if destination != self._vm.selected_section:
            self._vm.select_section(destination)
            return

        self._load_editor_section(destination)

    def force_save(self) -> None:
        """Commit pending editor content and persist the current draft."""
        self._editor.save_pending_list()
        self._auto_save()

    def export(self) -> None:
        """Public entry point used by Ctrl+E."""
        self._on_export()

    # ── Navigation ──────────────────────────────────────────────────

    def _on_section_selected(self, name: str) -> None:
        internal = self._vm.get_internal_name(name)
        self.show_destination(internal)

    def _load_editor_section(self, name: str) -> None:
        self._tabs.setCurrentWidget(self._editor)
        display = self._vm.get_display_name(name)
        self._nav.select_section(display)
        if name == "Salary":
            # Salary estimate comes from state; also pass job info for defaults
            value = {
                "estimate": copy.deepcopy(self.window.state.salary_estimate),
                "job_title": self.window.state.job_title or "",
                "job_location": self.window.state.job_location or "",
            }
        else:
            value = self._vm.get_section_value(name)
        self._editor.load(name, copy.deepcopy(value) if value is not None else None)
        self.destination_changed.emit(name)

    def _on_section_changed(self, name: str) -> None:
        self._load_editor_section(name)

    def _on_content_tab_changed(self, index: int) -> None:
        if index == self._review_tab_index:
            self._show_review()
            self.destination_changed.emit("Review")

    def _toggle_section_manager(self, visible: bool) -> None:
        self._nav.setVisible(visible)
        self._splitter.setSizes([180 if visible else 0, 700, 300])

    # ── Editing / preview ───────────────────────────────────────────

    def _on_section_edited(self, section: str, old_value, new_value) -> None:
        self._vm.update_section(section, old_value, new_value)
        self._pending_preview_resume = None
        self._analysis_timer.start()
        self._auto_save_timer.start()

    def _on_text_changed(self, section: str, _old_value, new_value) -> None:
        resume = self._vm.resume
        if resume is None:
            return

        draft = resume.model_copy(deep=True)
        if section == "Contact":
            draft.contact = copy.deepcopy(new_value)
        elif section == "Summary":
            draft.summary = str(new_value)
        else:
            return
        self._pending_preview_resume = draft
        self._preview_timer.start()

    def _on_editor_reload(self) -> None:
        section = self._vm.selected_section
        if section == "Salary":
            value = {
                "estimate": copy.deepcopy(self.window.state.salary_estimate),
                "job_title": self.window.state.job_title or "",
                "job_location": self.window.state.job_location or "",
            }
        else:
            value = self._vm.get_section_value(section)
        self._editor.load(section, copy.deepcopy(value) if value is not None else None)
        self._update_preview()

    def _on_resume_changed(self) -> None:
        self._pending_preview_resume = None
        self._update_preview()
        self._refresh_review_panel()
        self._update_controls()

    def _update_preview(self) -> None:
        resume = self._pending_preview_resume or self._vm.resume
        if resume is None:
            self._preview.clear()
            return
        self._preview.set_markdown(to_markdown(resume))

    # ── Undo / redo ─────────────────────────────────────────────────

    def _on_undo(self) -> None:
        self._vm.undo()
        self._analysis_timer.start()
        self._auto_save_timer.start()

    def _on_redo(self) -> None:
        self._vm.redo()
        self._analysis_timer.start()
        self._auto_save_timer.start()

    def _on_undo_state_changed(self) -> None:
        self._undo_btn.setEnabled(self._vm.can_undo)
        self._redo_btn.setEnabled(self._vm.can_redo)

    # ── Duplicate/versioning ────────────────────────────────────────

    def _on_duplicate(self) -> None:
        duplicate = self._vm.duplicate_resume()
        if duplicate is None:
            return
        self.window.state.active_resume_id = None
        self._loaded_resume_id = None
        self._vm.resume = duplicate
        self.show_destination("Contact")
        self._recalculate()
        self.window.notify("Created an unsaved resume copy.")

    def _on_save_version(self) -> None:
        resume = self._vm.resume
        resume_id = self.window.state.active_resume_id
        if resume is None or resume_id is None:
            return
        try:
            with get_session() as session:
                VersioningRepository(session).create_version(
                    resume_id,
                    resume.model_dump_json(),
                )
            self.window.notify("Resume version saved.")
        except Exception as exc:
            logger.exception("Failed to save resume version")
            QMessageBox.critical(self, "Save Version Failed", str(exc))

    # ── Insights / section management ───────────────────────────────

    def _on_issue_selected(self, section: str) -> None:
        internal = self._vm.get_internal_name(section)
        if internal in SECTION_NAMES:
            self.show_destination(internal)
            self._editor.scroll_to_field(internal)

    def _on_suggestion_accepted(self, keyword: str) -> None:
        resume = self._vm.resume
        if resume is None:
            return
        old_skills = list(resume.skills)
        if keyword.casefold() in {skill.casefold() for skill in old_skills}:
            return
        self._vm.update_section("Skills", old_skills, old_skills + [keyword])
        self._analysis_timer.start()
        self._auto_save_timer.start()

    def _on_section_reorder(self, section: str, direction: int) -> None:
        self._vm.move_section(section, direction)

    def _on_section_renamed(self, old_name: str, new_name: str) -> None:
        self._vm.set_custom_heading(old_name, new_name)
        self._refresh_section_manager()
        self._nav.select_section(new_name)

    def _on_section_order_changed(self) -> None:
        self._refresh_section_manager()

    def _on_custom_headings_changed(self) -> None:
        self._refresh_section_manager()

    def _refresh_section_manager(self) -> None:
        self._nav.set_sections(
            [self._vm.get_display_name(section) for section in self._vm.section_order]
        )

    # ── Analysis ────────────────────────────────────────────────────

    def _recalculate(self) -> None:
        resume = self._vm.resume
        if resume is None:
            self._insights.clear()
            self._vm.ats = None
            return

        job_text = self._vm.job_text()

        try:
            from app.engines.content_checker import check_content

            self._insights.update_from_content_check(check_content(resume))
        except Exception:
            logger.debug("Content check failed", exc_info=True)

        try:
            from app.engines.resume_scorer import calculate_resume_score

            self._insights.update_from_resume_score(
                calculate_resume_score(resume, job_text)
            )
        except Exception:
            logger.debug("Resume scoring failed", exc_info=True)

        if not job_text.strip():
            self._vm.ats = None
            return

        try:
            self._vm.ats = analyze(resume, job_text)
        except Exception:
            logger.debug("ATS analysis failed", exc_info=True)
            self._vm.ats = None

    def _on_ats_changed(self) -> None:
        self._insights.update_from_ats(self._vm.ats)

    # ── Auto-save ───────────────────────────────────────────────────

    def _auto_save(self) -> None:
        resume = self._vm.resume
        resume_id = self.window.state.active_resume_id
        if resume is None or resume_id is None:
            return
        try:
            with get_session() as session:
                ResumeRepository(session).update(
                    resume_id,
                    resume.model_dump_json(),
                )
        except Exception:
            logger.exception("Auto-save failed")

    # ── Salary estimation ────────────────────────────────────────────

    def _on_generate_salary(self, role: str, location: str) -> None:
        """Run salary estimation in a background worker."""
        resume = self._vm.resume
        if resume is None:
            self.window.notify("Load a resume first.")
            return

        self.window.notify(f"Estimating salary for {role} in {location}...")

        def _estimate():
            return estimate_salary(resume, role, location)

        def _on_result(result: SalaryEstimate) -> None:
            self.window.state.salary_estimate = result
            self.window.notify(f"Salary estimate: {result.salary_range} {result.currency}/year")
            # Reload the editor to show results
            self._on_editor_reload()

        def _on_error(message: str) -> None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Salary Estimation Failed", message)

        self._start_generation_worker(_estimate, _on_result, "Salary Estimation")

    # ── AI generation ───────────────────────────────────────────────

    def _start_generation_worker(self, function, on_result, label: str) -> None:
        from app.ui.workers import Worker

        current = getattr(self, "_gen_worker", None)
        if current is not None and current.isRunning():
            self.window.notify("An AI generation task is already running.")
            return

        worker = Worker(function, parent=self)
        self._gen_worker = worker
        worker.result.connect(on_result)
        worker.error.connect(
            lambda message: QMessageBox.warning(
                self,
                f"{label} Failed",
                message,
            )
        )
        worker.finished.connect(self._cleanup_generation_worker)
        worker.start()

    def _cleanup_generation_worker(self) -> None:
        worker = getattr(self, "_gen_worker", None)
        self._gen_worker = None
        if worker is not None:
            worker.deleteLater()

    def _on_generate_summary(self) -> None:
        resume = self._vm.resume
        if resume is None:
            return
        old_summary = resume.summary
        job_text = self._vm.job_text()

        def _generate():
            from app.services.summary_generator import generate_summary

            return generate_summary(resume, job_text).summary

        def _apply(new_summary: str) -> None:
            self._vm.update_section("Summary", old_summary, new_summary)
            self.show_destination("Summary")
            self._analysis_timer.start()
            self._auto_save_timer.start()

        self._start_generation_worker(_generate, _apply, "Summary Generation")

    def _on_generate_headline(self) -> None:
        resume = self._vm.resume
        if resume is None:
            return
        old_headline = resume.headline
        job_text = self._vm.job_text()

        def _generate():
            from app.services.headline_generator import generate_headline

            return generate_headline(resume, job_text).headline

        def _apply(new_headline: str) -> None:
            if old_headline == new_headline:
                return
            self._vm.update_section("Headline", old_headline, new_headline)
            self.window.notify("AI headline generated.")
            self._analysis_timer.start()
            self._auto_save_timer.start()

        self._start_generation_worker(_generate, _apply, "Headline Generation")

    # ── Review and export ───────────────────────────────────────────

    def _show_review(self) -> None:
        self._editor.save_pending_list()
        self._refresh_review_panel()
        if self._tabs.currentIndex() != self._review_tab_index:
            self._tabs.blockSignals(True)
            self._tabs.setCurrentIndex(self._review_tab_index)
            self._tabs.blockSignals(False)

    def _review_blockers(self) -> list[str]:
        resume = self._vm.resume
        if resume is None:
            return ["No resume is loaded."]

        blockers: list[str] = []
        if not resume.contact.name.strip():
            blockers.append("Candidate name is required.")
        if not resume.contact.email.strip():
            blockers.append("Email address is required.")

        fact_guard = self.window.state.fact_guard
        flagged_changes = getattr(fact_guard, "flagged_changes", []) if fact_guard else []
        pending = [
            change
            for change in flagged_changes
            if getattr(change, "accepted", None) is None
        ]
        if pending:
            blockers.append(
                f"Review {len(pending)} pending AI-generated change(s) in Optimization."
            )
        return blockers

    def _refresh_review_panel(self) -> None:
        resume = self._vm.resume
        blockers = self._review_blockers()
        self._review.set_resume(resume)
        self._review.set_review_issues(blockers=blockers)
        self._review.set_export_enabled(
            self._vm.is_approved_for_export and not blockers
        )

    def _approve_review(self) -> None:
        self._editor.save_pending_list()
        blockers = self._review_blockers()
        if blockers:
            QMessageBox.warning(
                self,
                "Resume Cannot Be Approved",
                "\n".join(f"• {message}" for message in blockers),
            )
            self._refresh_review_panel()
            return

        self._vm.approve_for_export()
        self.window.notify("Current resume revision approved for export.")

    def _on_review_state_changed(self) -> None:
        self._refresh_review_panel()
        self._update_controls()

    def _update_controls(self) -> None:
        has_resume = self._vm.has_resume()
        self._dup_btn.setEnabled(has_resume)
        self._save_version_btn.setEnabled(
            has_resume and self.window.state.active_resume_id is not None
        )
        self._export_btn.setEnabled(
            self._vm.is_approved_for_export and not self._review_blockers()
        )

    @staticmethod
    def _safe_export_name(name: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", name)
        return cleaned.strip(" ._") or "Resume"

    def _export_as(self, format_name: str) -> None:
        self._export_format.setCurrentText(format_name)
        self._on_export()

    def _on_export(self) -> None:
        self._editor.save_pending_list()
        blockers = self._review_blockers()
        resume = self._vm.approved_resume
        if blockers:
            QMessageBox.warning(
                self,
                "Review Required",
                "Resolve the following before exporting:\n"
                + "\n".join(f"• {message}" for message in blockers),
            )
            return
        if resume is None:
            QMessageBox.warning(
                self,
                "Review Required",
                "Open Review and approve the current resume revision before exporting.",
            )
            return

        format_name = self._export_format.currentText()
        template_name = self._export_template.currentText()
        extension = {"PDF": "pdf", "DOCX": "docx", "Markdown": "md"}.get(
            format_name,
            "pdf",
        )
        default_name = f"{self._safe_export_name(resume.contact.name)}_Resume.{extension}"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Approved Resume",
            default_name,
            f"{format_name} Files (*.{extension})",
        )
        if not path:
            return
        if not path.lower().endswith(f".{extension}"):
            path += f".{extension}"

        try:
            from app.exports.exporter import (
                export_docx,
                export_markdown,
                export_pdf,
                get_template,
            )

            theme = get_template(template_name)
            if format_name == "PDF":
                export_pdf(resume, path, theme=theme)
            elif format_name == "DOCX":
                export_docx(resume, path, theme=theme)
            else:
                export_markdown(resume, path)

            QMessageBox.information(
                self,
                "Export Complete",
                f"Approved resume exported to:\n{Path(path)}",
            )
        except Exception as exc:
            logger.exception("Export failed")
            QMessageBox.critical(self, "Export Failed", str(exc))
