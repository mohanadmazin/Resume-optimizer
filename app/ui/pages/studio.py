"""ResumeStudioPage — persistent 3-panel Resume Studio."""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.exports.exporter import to_markdown
from app.ui.components.resume_insights_panel import ResumeInsightsPanel
from app.ui.components.resume_preview import ResumePreview
from app.ui.components.section_editor import SectionEditor
from app.ui.components.section_navigator import SectionNavigator
from app.ui.view_models.studio_vm import SECTION_NAMES, ResumeStudioViewModel

from app.services.ats_engine import analyze


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
        self._nav = SectionNavigator(SECTIONS)
        self._nav.section_selected.connect(self._on_section_selected)
        splitter.addWidget(self._nav)

        # ── Center: editor + preview tabs ────────────────────────────
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._editor = SectionEditor()
        self._editor.section_edited.connect(self._on_section_edited)

        self._preview = ResumePreview()

        self._tabs.addTab(self._editor, "Editor")
        self._tabs.addTab(self._preview, "Preview")
        center_layout.addWidget(self._tabs)

        splitter.addWidget(center)

        # ── Right: insights ──────────────────────────────────────────
        self._insights = ResumeInsightsPanel()
        splitter.addWidget(self._insights)

        splitter.setSizes([180, 600, 280])
        root.addWidget(splitter)

        # ── Bottom bar: undo/redo ────────────────────────────────────
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

        root.addLayout(bar)

        # ── Debounce timer for recalculation ─────────────────────────
        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(350)
        self._analysis_timer.timeout.connect(self._recalculate)

        # ── ViewModel signal wiring ──────────────────────────────────
        self._vm.resume_changed.connect(self._on_resume_changed)
        self._vm.section_changed.connect(self._on_section_changed)
        self._vm.ats_changed.connect(self._on_ats_changed)
        self._vm.undoStateChanged.connect(self._on_undo_state_changed)

    # ── Public lifecycle ─────────────────────────────────────────────

    def on_show(self) -> None:
        """Called by MainWindow when this page becomes visible."""
        if self.window.state.resume is not None and self._vm.resume is None:
            self._vm.resume = copy.deepcopy(self.window.state.resume)
            self._nav.select_section("Contact")
            self._on_section_selected("Contact")
            self._recalculate()

    # ── Navigation ───────────────────────────────────────────────────

    def _on_section_selected(self, name: str) -> None:
        self._vm.select_section(name)
        value = self._vm.get_section_value(name)
        self._editor.load(name, copy.deepcopy(value))

    def _on_section_changed(self, name: str) -> None:
        self._nav.select_section(name)
        value = self._vm.get_section_value(name)
        self._editor.load(name, copy.deepcopy(value))

    # ── Editing ──────────────────────────────────────────────────────

    def _on_section_edited(self, section: str, old_value, new_value) -> None:
        self._vm.update_section(section, old_value, new_value)
        self._analysis_timer.start()

    # ── Undo / redo ──────────────────────────────────────────────────

    def _on_undo(self) -> None:
        self._vm.undo()
        self._analysis_timer.start()

    def _on_redo(self) -> None:
        self._vm.redo()
        self._analysis_timer.start()

    def _on_undo_state_changed(self) -> None:
        self._undo_btn.setEnabled(self._vm.can_undo)
        self._redo_btn.setEnabled(self._vm.can_redo)

    # ── Preview ──────────────────────────────────────────────────────

    def _on_resume_changed(self) -> None:
        resume = self._vm.resume
        if resume is not None:
            self._preview.set_markdown(to_markdown(resume))
        else:
            self._preview.clear()

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
        except Exception as exc:
            self._insights.clear()

    def _on_ats_changed(self) -> None:
        self._insights.update_from_ats(self._vm.ats)
