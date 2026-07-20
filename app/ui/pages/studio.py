"""ResumeStudioPage — persistent 3-panel Resume Studio."""
from __future__ import annotations

import copy
import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.database.session import get_session
from app.database.repositories.resume_repository import ResumeRepository
from app.database.repositories.versioning_repository import VersioningRepository
from app.exports.exporter import to_markdown
from app.ui.components.resume_insights_panel import ResumeInsightsPanel
from app.ui.components.resume_preview import ResumePreview
from app.ui.components.section_editor import SectionEditor
from app.ui.components.section_navigator import SectionNavigator
from app.ui.view_models.studio_vm import SECTION_NAMES, ResumeStudioViewModel

from app.services.ats_engine import analyze

logger = logging.getLogger(__name__)

_AUTO_SAVE_INTERVAL_MS = 2000


class ResumeStudioPage(QWidget):
    """Rezi-style persistent resume editor with live insights.

    ┌──────────────┬────────────────────────────┬──────────────────┐
    │ Section nav  │ Editor / preview tabs      │ Score & insights │
    └──────────────┴────────────────────────────┴──────────────────┘
    """

    def __init__(self, window: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window

        self._vm = ResumeStudioViewModel(state=window.state, parent=self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: section navigator ──────────────────────────────────
        self._nav = SectionNavigator(SECTION_NAMES)
        self._nav.section_selected.connect(self._on_section_selected)
        self._nav.section_reorder.connect(self._on_section_reorder)
        self._nav.section_renamed.connect(self._on_section_renamed)
        splitter.addWidget(self._nav)

        # ── Center: editor + preview tabs ────────────────────────────
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._editor = SectionEditor()
        self._editor.section_edited.connect(self._on_section_edited)
        self._editor.text_changed.connect(self._on_text_changed)
        self._editor.generate_summary_requested.connect(self._on_generate_summary)
        self._editor.generate_headline_requested.connect(self._on_generate_headline)
        self._editor.set_reload_callback(self._on_editor_reload)

        self._preview = ResumePreview()

        self._tabs.addTab(self._editor, "Editor")
        self._tabs.addTab(self._preview, "Preview")
        center_layout.addWidget(self._tabs)

        splitter.addWidget(center)

        # ── Right: insights ──────────────────────────────────────────
        self._insights = ResumeInsightsPanel()
        self._insights.issue_selected.connect(self._on_issue_selected)
        self._insights.suggestion_accepted.connect(self._on_suggestion_accepted)
        splitter.addWidget(self._insights)

        splitter.setSizes([180, 600, 280])
        root.addWidget(splitter)

        # ── Bottom bar: undo/redo/duplicate/version ──────────────────
        bar = QHBoxLayout()
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

        # ── Export controls ──────────────────────────────────────────
        bar.addWidget(QLabel("Format:"))
        self._export_format = QComboBox()
        self._export_format.addItems(["PDF", "DOCX", "Markdown"])
        bar.addWidget(self._export_format)

        bar.addWidget(QLabel("Template:"))
        self._export_template = QComboBox()
        self._export_template.addItems(["Classic", "Modern", "Compact"])
        bar.addWidget(self._export_template)

        self._export_btn = QPushButton("Export")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        bar.addWidget(self._export_btn)

        root.addLayout(bar)

        # ── Auto-save timer ──────────────────────────────────────────
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(_AUTO_SAVE_INTERVAL_MS)
        self._auto_save_timer.timeout.connect(self._auto_save)

        # ── Debounce timer for recalculation ─────────────────────────
        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(350)
        self._analysis_timer.timeout.connect(self._recalculate)

        # ── Debounce timer for live preview ──────────────────────────
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._update_preview)

        # ── ViewModel signal wiring ──────────────────────────────────
        self._vm.resume_changed.connect(self._on_resume_changed)
        self._vm.section_changed.connect(self._on_section_changed)
        self._vm.ats_changed.connect(self._on_ats_changed)
        self._vm.undoStateChanged.connect(self._on_undo_state_changed)
        self._vm.section_order_changed.connect(self._on_section_order_changed)
        self._vm.custom_headings_changed.connect(self._on_custom_headings_changed)

    # ── Public lifecycle ─────────────────────────────────────────────

    def on_show(self) -> None:
        """Called by MainWindow when this page becomes visible."""
        if self.window.state.resume is not None and self._vm.resume is None:
            self._vm.resume = copy.deepcopy(self.window.state.resume)
            self._nav.select_section("Contact")
            self._on_section_selected("Contact")
            self._recalculate()
        has = self._vm.has_resume()
        self._dup_btn.setEnabled(has)
        self._export_btn.setEnabled(has)
        self._save_version_btn.setEnabled(
            has and self.window.state.active_resume_id is not None
        )

    # ── Navigation ───────────────────────────────────────────────────

    def _on_section_selected(self, name: str) -> None:
        internal = self._vm.get_internal_name(name)
        self._vm.select_section(internal)
        value = self._vm.get_section_value(internal)
        self._editor.load(internal, copy.deepcopy(value))

    def _on_section_changed(self, name: str) -> None:
        display = self._vm.get_display_name(name)
        self._nav.select_section(display)
        value = self._vm.get_section_value(name)
        self._editor.load(name, copy.deepcopy(value))

    # ── Editing ──────────────────────────────────────────────────────

    def _on_section_edited(self, section: str, old_value, new_value) -> None:
        self._vm.update_section(section, old_value, new_value)
        self._analysis_timer.start()
        self._auto_save_timer.start()
        self._update_preview()

    def _on_text_changed(self, section: str, old_value, new_value) -> None:
        """Handle live text changes for preview update (debounced)."""
        self._preview_timer.start()

    def _on_editor_reload(self) -> None:
        """Reload the editor after structural changes (add/delete entries)."""
        section = self._vm.selected_section
        value = self._vm.get_section_value(section)
        self._editor.load(section, copy.deepcopy(value))
        self._update_preview()

    # ── Undo / redo ──────────────────────────────────────────────────

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

    # ── Duplicate ──────────────────────────────────────────────────

    def _on_duplicate(self) -> None:
        dup = self._vm.duplicate_resume()
        if dup is None:
            return
        self._vm.clear()
        self._vm.resume = dup
        self._nav.select_section("Contact")
        self._on_section_selected("Contact")
        self._recalculate()
        self._auto_save_timer.start()

    # ── Version save ──────────────────────────────────────────────

    def _on_save_version(self) -> None:
        resume = self._vm.resume
        resume_id = self.window.state.active_resume_id
        if resume is None or resume_id is None:
            return
        try:
            with get_session() as session:
                VersioningRepository(session).create_version(
                    resume_id, resume.model_dump_json()
                )
        except Exception:
            logger.exception("Failed to save resume version")

    # ── Issue navigation ──────────────────────────────────────────

    def _on_issue_selected(self, section: str) -> None:
        internal = self._vm.get_internal_name(section)
        display = self._vm.get_display_name(internal)
        self._nav.select_section(display)
        self._vm.select_section(internal)
        value = self._vm.get_section_value(internal)
        self._editor.load(internal, copy.deepcopy(value))
        self._editor.scroll_to_field(internal)

    # ── Skill suggestion accept ──────────────────────────────────

    def _on_suggestion_accepted(self, keyword: str) -> None:
        resume = self._vm.resume
        if resume is None:
            return
        old_skills = list(resume.skills)
        if keyword.lower() not in [s.lower() for s in old_skills]:
            new_skills = old_skills + [keyword]
            self._vm.update_section("Skills", old_skills, new_skills)
            self._analysis_timer.start()
            self._auto_save_timer.start()

    # ── Section reorder ──────────────────────────────────────────

    def _on_section_reorder(self, section: str, direction: int) -> None:
        self._vm.move_section(section, direction)

    # ── Section rename ───────────────────────────────────────────

    def _on_section_renamed(self, old_name: str, new_name: str) -> None:
        self._vm.set_custom_heading(old_name, new_name)
        self._nav.set_sections(
            [self._vm.get_display_name(s) for s in self._vm.section_order]
        )
        self._nav.select_section(new_name)

    # ── Section order changed (from ViewModel) ───────────────────

    def _on_section_order_changed(self) -> None:
        self._nav.set_sections(
            [self._vm.get_display_name(s) for s in self._vm.section_order]
        )

    def _on_custom_headings_changed(self) -> None:
        self._nav.set_sections(
            [self._vm.get_display_name(s) for s in self._vm.section_order]
        )

    # ── Preview ──────────────────────────────────────────────────────

    def _on_resume_changed(self) -> None:
        resume = self._vm.resume
        if resume is not None:
            self._preview.set_markdown(to_markdown(resume))
        else:
            self._preview.clear()

    def _update_preview(self) -> None:
        """Update the preview tab with the current resume state."""
        resume = self._vm.resume
        if resume is not None:
            self._preview.set_markdown(to_markdown(resume))

    # ── ATS recalculation ────────────────────────────────────────────

    def _recalculate(self) -> None:
        resume = self._vm.resume
        job_text = self._vm.job_text()
        if resume is None or not job_text.strip():
            self._insights.clear()
            return

        try:
            ats = analyze(resume, job_text)
            self._vm.ats = ats
        except Exception:
            self._insights.clear()

    def _on_ats_changed(self) -> None:
        self._insights.update_from_ats(self._vm.ats)

    # ── Auto-save ─────────────────────────────────────────────────

    def _auto_save(self) -> None:
        resume = self._vm.resume
        resume_id = self.window.state.active_resume_id
        if resume is None or resume_id is None:
            return
        try:
            with get_session() as session:
                ResumeRepository(session).update(
                    resume_id, resume.model_dump_json()
                )
        except Exception:
            logger.exception("Auto-save failed")

    # ── AI generation (summary / headline) ───────────────────────

    def _on_generate_summary(self) -> None:
        resume = self._vm.resume
        if resume is None:
            return
        old_summary = resume.summary
        jd_text = self._vm.job_text()

        def _do_generate():
            from app.services.summary_generator import generate_summary
            result = generate_summary(resume, jd_text)
            return result.summary

        def _on_generated(new_summary):
            self._vm.update_section("Summary", old_summary, new_summary)
            self._editor.load("Summary", new_summary)
            self._analysis_timer.start()
            self._auto_save_timer.start()

        from app.ui.workers import Worker
        self._gen_worker = Worker(_do_generate)
        self._gen_worker.result.connect(_on_generated)
        self._gen_worker.error.connect(
            lambda e: logger.warning("Summary generation failed: %s", e)
        )
        self._gen_worker.start()

    def _on_generate_headline(self) -> None:
        resume = self._vm.resume
        if resume is None:
            return
        old_headline = resume.headline
        jd_text = self._vm.job_text()

        def _do_generate():
            from app.services.headline_generator import generate_headline
            result = generate_headline(resume, jd_text)
            return result.headline

        def _on_generated(new_headline):
            self._vm.update_section("Headline", old_headline, new_headline)
            self._recalculate()
            self._analysis_timer.start()
            self._auto_save_timer.start()

        from app.ui.workers import Worker
        self._gen_worker = Worker(_do_generate)
        self._gen_worker.result.connect(_on_generated)
        self._gen_worker.error.connect(
            lambda e: logger.warning("Headline generation failed: %s", e)
        )
        self._gen_worker.start()

    # ── Export ──────────────────────────────────────────────────────

    def _on_export(self) -> None:
        """Export resume to chosen format and template."""
        resume = self._vm.resume
        if resume is None:
            return

        fmt = self._export_format.currentText()
        template_name = self._export_template.currentText()

        ext_map = {"PDF": "pdf", "DOCX": "docx", "Markdown": "md"}
        ext = ext_map.get(fmt, "pdf")

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        default_name = (resume.contact.name or "resume").replace(" ", "_").lower()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Resume", f"{default_name}.{ext}",
            f"{fmt} Files (*.{ext})"
        )
        if not path:
            return

        try:
            from app.exports.exporter import export_pdf, export_docx, export_markdown, get_template
            theme = get_template(template_name)

            if fmt == "PDF":
                export_pdf(resume, path, theme=theme)
            elif fmt == "DOCX":
                export_docx(resume, path, theme=theme)
            else:
                export_markdown(resume, path)

            QMessageBox.information(self, "Export Complete", f"Resume exported to:\n{path}")
        except Exception as e:
            logger.exception("Export failed")
            QMessageBox.critical(self, "Export Failed", str(e))
