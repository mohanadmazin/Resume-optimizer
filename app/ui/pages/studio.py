"""Resume Studio: section editing, final review, and approved export."""
from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.exports.exporter import export_docx, export_pdf, to_markdown
from app.services.ats_engine import analyze
from app.ui.components.resume_insights_panel import ResumeInsightsPanel
from app.ui.components.resume_preview import ResumePreview
from app.ui.components.resume_review_panel import ResumeReviewPanel
from app.ui.components.section_editor import SectionEditor
from app.ui.components.section_navigator import SectionNavigator
from app.ui.view_models.studio_vm import SECTION_NAMES, ResumeStudioViewModel


class ResumeStudioPage(QWidget):
    """Edit one working resume and export only its approved snapshot."""

    def __init__(self, window: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._loaded_target: str | None = None
        self._vm = ResumeStudioViewModel(state=window.state, parent=self)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Resume sections live at the top and reuse one shared editor.
        self._nav = SectionNavigator(SECTION_NAMES, self)
        self._nav.destination_selected.connect(self._on_destination_selected)
        root.addWidget(self._nav)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._content_stack = QStackedWidget()
        self._editor = SectionEditor()
        self._editor.section_edited.connect(self._on_section_edited)
        self._content_stack.addWidget(self._editor)

        self._review = ResumeReviewPanel()
        self._review.approved.connect(self._approve_review)
        self._review.export_docx_requested.connect(lambda: self._export("docx"))
        self._review.export_pdf_requested.connect(lambda: self._export("pdf"))
        self._content_stack.addWidget(self._review)
        splitter.addWidget(self._content_stack)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        preview_label = QLabel("Live Preview")
        preview_label.setObjectName("sectionLabel")
        right_layout.addWidget(preview_label)
        self._preview = ResumePreview()
        right_layout.addWidget(self._preview, 2)

        self._insights = ResumeInsightsPanel()
        right_layout.addWidget(self._insights, 1)
        splitter.addWidget(right)
        splitter.setSizes([700, 420])
        root.addWidget(splitter, 1)

        controls = QHBoxLayout()
        self._undo_btn = QPushButton("Undo")
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(self._on_undo)
        controls.addWidget(self._undo_btn)

        self._redo_btn = QPushButton("Redo")
        self._redo_btn.setEnabled(False)
        self._redo_btn.clicked.connect(self._on_redo)
        controls.addWidget(self._redo_btn)
        controls.addStretch()

        self._review_status = QLabel("Not approved for export")
        self._review_status.setObjectName("reviewApprovalStatus")
        controls.addWidget(self._review_status)
        root.addLayout(controls)

        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(350)
        self._analysis_timer.timeout.connect(self._recalculate)

        self._vm.resume_changed.connect(self._on_resume_changed)
        self._vm.section_changed.connect(self._on_section_changed)
        self._vm.ats_changed.connect(self._on_ats_changed)
        self._vm.undoStateChanged.connect(self._on_undo_state_changed)
        self._vm.reviewStateChanged.connect(self._update_review_state)

    def on_show(self) -> None:
        """Load the optimized resume when present, otherwise the imported one."""
        state = self.window.state
        if state.optimized is not None:
            source = state.optimized
            target = "optimized"
        else:
            source = state.resume
            target = "resume"

        if source is None:
            self._preview.clear()
            self._review.set_resume(None)
            self._insights.clear()
            return

        if (
            self._vm.resume is None
            or self._loaded_target != target
            or self._vm.resume != source
        ):
            self._loaded_target = target
            self._vm.load_resume(copy.deepcopy(source), target=target)

        self._nav.select_destination(self._vm.selected_section)
        self._show_section(self._vm.selected_section)
        self._recalculate()

    # Navigation --------------------------------------------------------

    def _on_destination_selected(self, destination: str) -> None:
        self._commit_pending_editor()
        if destination == SectionNavigator.REVIEW_TAB:
            self._show_review()
            return

        if destination == self._vm.selected_section:
            self._show_section(destination)
        else:
            self._vm.select_section(destination)

    def _on_section_changed(self, section: str) -> None:
        self._nav.select_destination(section)
        self._show_section(section)

    def _show_section(self, section: str) -> None:
        self._content_stack.setCurrentWidget(self._editor)
        self._editor.load(
            section,
            copy.deepcopy(self._vm.get_section_value(section)),
        )

    def _show_review(self) -> None:
        self._commit_pending_editor()
        self._review.set_resume(self._vm.resume)
        self._review.set_export_enabled(self._vm.is_approved_for_export)
        self._content_stack.setCurrentWidget(self._review)

    def _commit_pending_editor(self) -> None:
        self._editor.save_pending_list()

    # Editing and history ----------------------------------------------

    def _on_section_edited(self, section: str, old_value, new_value) -> None:
        self._vm.update_section(section, old_value, new_value)
        self._analysis_timer.start()

    def _on_undo(self) -> None:
        self._commit_pending_editor()
        self._vm.undo()
        self._analysis_timer.start()

    def _on_redo(self) -> None:
        self._commit_pending_editor()
        self._vm.redo()
        self._analysis_timer.start()

    def _on_undo_state_changed(self) -> None:
        self._undo_btn.setEnabled(self._vm.can_undo)
        self._redo_btn.setEnabled(self._vm.can_redo)

    # Preview, ATS, and review -----------------------------------------

    def _on_resume_changed(self) -> None:
        resume = self._vm.resume
        if resume is None:
            self._preview.clear()
            self._review.set_resume(None)
            return

        self._preview.set_markdown(to_markdown(resume))
        if self._content_stack.currentWidget() is self._review:
            self._review.set_resume(resume)
        self._update_review_state()

    def _recalculate(self) -> None:
        resume = self._vm.resume
        job_text = self._vm.job_text()
        if resume is None or not job_text.strip():
            self._insights.clear()
            return
        try:
            self._vm.ats = analyze(resume, job_text)
        except Exception:
            self._insights.clear()

    def _on_ats_changed(self) -> None:
        self._insights.update_from_ats(self._vm.ats)

    def _approve_review(self) -> None:
        self._commit_pending_editor()
        resume = self._vm.resume
        if resume is None:
            QMessageBox.warning(self, "No resume", "Load a resume before review.")
            return

        warnings = ResumeReviewPanel.validation_warnings(resume)
        if warnings:
            answer = QMessageBox.question(
                self,
                "Approve with warnings?",
                "The resume has the following review warnings:\n\n"
                + "\n".join(f"• {warning}" for warning in warnings)
                + "\n\nApprove this exact version anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self._vm.approve_for_export()
        self.window.notify("Resume approved for DOCX/PDF export.")

    def _update_review_state(self) -> None:
        approved = self._vm.is_approved_for_export
        self._review.set_export_enabled(approved)
        self._review_status.setText(
            "Approved for export" if approved else "Not approved for export"
        )

    # Export ------------------------------------------------------------

    def _export(self, file_type: str) -> None:
        self._commit_pending_editor()
        approved_resume = self._vm.approved_resume
        if approved_resume is None:
            QMessageBox.warning(
                self,
                "Review required",
                "Open Review and approve the current resume before exporting.",
            )
            return

        safe_name = approved_resume.contact.name.strip().replace(" ", "_") or "Resume"
        if file_type == "docx":
            extension = ".docx"
            file_filter = "Word Document (*.docx)"
            exporter = export_docx
        elif file_type == "pdf":
            extension = ".pdf"
            file_filter = "PDF Document (*.pdf)"
            exporter = export_pdf
        else:
            raise ValueError(f"Unsupported export type: {file_type}")

        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Export {file_type.upper()}",
            safe_name + extension,
            file_filter,
        )
        if not path:
            return
        if not path.lower().endswith(extension):
            path += extension

        try:
            exporter(approved_resume, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return

        self.window.notify(f"Exported {Path(path).name}")
