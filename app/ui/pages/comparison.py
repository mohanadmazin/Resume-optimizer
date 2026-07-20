"""Resume comparison page — side-by-side diff view."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.session import get_session
from app.database.repositories.resume_repository import ResumeRepository
from app.schemas import ResumeData
from app.services.resume_comparison import compare_resumes

logger = logging.getLogger(__name__)


_HIGHLIGHT_RED = "background-color: #3b1515; border-radius: 4px;"
_HIGHLIGHT_GREEN = "background-color: #153b15; border-radius: 4px;"
_CHANGED_STYLE = "color: #f87171;"
_ADDED_STYLE = "color: #4ade80;"
_REMOVED_STYLE = "color: #9ca3af; text-decoration: line-through;"


class ComparisonPage(QWidget):
    """Side-by-side resume comparison view."""

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self._resume_a: ResumeData | None = None
        self._resume_b: ResumeData | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Resume Comparison")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel("Select two resumes to see a side-by-side diff of all changes.")
        layout.addWidget(desc)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Resume A (Original):"))
        self._combo_a = QComboBox()
        self._combo_a.setMinimumWidth(200)
        selector_row.addWidget(self._combo_a)

        selector_row.addSpacing(20)

        selector_row.addWidget(QLabel("Resume B (Modified):"))
        self._combo_b = QComboBox()
        self._combo_b.setMinimumWidth(200)
        selector_row.addWidget(self._combo_b)

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.clicked.connect(self._on_compare)
        selector_row.addWidget(self._compare_btn)
        selector_row.addStretch()
        layout.addLayout(selector_row)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self._summary_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Original"))
        self._text_a = QTextEdit()
        self._text_a.setReadOnly(True)
        left_layout.addWidget(self._text_a)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Modified"))
        self._text_b = QTextEdit()
        self._text_b.setReadOnly(True)
        right_layout.addWidget(self._text_b)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 500])

        layout.addWidget(splitter, stretch=1)

    def on_show(self) -> None:
        self._load_resumes()

    def _load_resumes(self) -> None:
        try:
            with get_session() as session:
                repo = ResumeRepository(session)
                resumes = repo.get_all()
        except Exception:
            logger.exception("Failed to load resumes")
            resumes = []

        self._combo_a.clear()
        self._combo_b.clear()
        self._resume_map: dict[str, tuple[int, str]] = {}

        for r in resumes:
            display = f"{r['name'] or 'Untitled'} (#{r['id']})"
            key = display
            self._combo_a.addItem(display)
            self._combo_b.addItem(display)
            self._resume_map[key] = (r["id"], r["name"] or "Untitled")

        if len(resumes) >= 2:
            self._combo_b.setCurrentIndex(1)

    def _on_compare(self) -> None:
        key_a = self._combo_a.currentText()
        key_b = self._combo_b.currentText()

        if not key_a or not key_b:
            QMessageBox.information(self, "Select Resumes", "Please select two resumes to compare.")
            return

        if key_a == key_b:
            QMessageBox.information(self, "Same Resume", "Please select two different resumes.")
            return

        resume_a = self._load_resume_data(key_a)
        resume_b = self._load_resume_data(key_b)

        if resume_a is None or resume_b is None:
            QMessageBox.warning(self, "Error", "Could not load one or both resumes.")
            return

        comparison = compare_resumes(resume_a, resume_b)

        self._render_comparison(comparison)

    def _load_resume_data(self, key: str) -> ResumeData | None:
        info = self._resume_map.get(key)
        if not info:
            return None
        try:
            with get_session() as session:
                repo = ResumeRepository(session)
                row = repo.get_by_id(info[0])
                if row and row.data_json:
                    return ResumeData.model_validate_json(row.data_json)
        except Exception:
            logger.exception("Failed to load resume %d", info[0])
        return None

    def _render_comparison(self, comp) -> None:
        if comp.total_changes == 0:
            self._summary_label.setText("No differences found.")
            self._text_a.setPlainText("Identical resumes.")
            self._text_b.setPlainText("Identical resumes.")
            return

        self._summary_label.setText(
            f"{comp.total_changes} change(s) found across {len(comp.experience)} experience entries."
        )

        self._text_a.clear()
        self._text_b.clear()

        self._append_field(comp.name, "Name")
        self._append_field(comp.headline, "Headline")
        self._append_field(comp.summary, "Summary")

        if comp.skills_changed:
            self._text_a.append("\n--- Skills ---")
            self._text_b.append("\n--- Skills ---")
            self._text_a.append(", ".join(comp.skills_old) or "(none)")
            self._text_b.append(", ".join(comp.skills_new) or "(none)")

        for exp in comp.experience:
            header = f"\n--- Experience #{exp.index + 1} ---"
            self._text_a.append(header)
            self._text_b.append(header)

            self._append_field(exp.title, "Title")
            self._append_field(exp.company, "Company")
            self._append_field(exp.start_date, "Start")
            self._append_field(exp.end_date, "End")

            for bd in exp.bullets:
                bullet_label = f"  Bullet #{bd.index + 1}:"
                self._text_a.append(bullet_label)
                self._text_b.append(bullet_label)
                self._append_line(bd.old_text, bd.new_text, bd.changed)

    def _append_field(self, field_diff, label: str) -> None:
        prefix = f"{label}: "
        if field_diff.changed:
            self._text_a.append(
                f"<span style='{_CHANGED_STYLE}'>{prefix}{self._esc(field_diff.old_value)}</span>"
            )
            self._text_b.append(
                f"<span style='{_ADDED_STYLE}'>{prefix}{self._esc(field_diff.new_value)}</span>"
            )
        else:
            text = f"{prefix}{self._esc(field_diff.old_value)}"
            self._text_a.append(text)
            self._text_b.append(text)

    def _append_line(self, old: str, new: str, changed: bool) -> None:
        if changed:
            self._text_a.append(
                f"  <span style='{_CHANGED_STYLE}'>{self._esc(old) or '(empty)'}</span>"
            )
            self._text_b.append(
                f"  <span style='{_ADDED_STYLE}'>{self._esc(new) or '(empty)'}</span>"
            )
        else:
            text = f"  {self._esc(old)}"
            self._text_a.append(text)
            self._text_b.append(text)

    @staticmethod
    def _esc(text: str) -> str:
        from html import escape
        return escape(text)
