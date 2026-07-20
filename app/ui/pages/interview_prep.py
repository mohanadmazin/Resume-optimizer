"""Interview Prep page — generate interview questions with STAR outlines."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.database import db
from app.database.models import InterviewSession
from app.services.interview_prep import InterviewPrepService, InterviewQuestionsResult
from app.ui.components.loading_overlay import LoadingOverlayManager
from app.ui.workers import Worker

logger = logging.getLogger(__name__)


class _QuestionCard(QFrame):
    """Card displaying a single interview question with STAR outline."""

    def __init__(self, question, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        cat_label = QLabel(question.category.upper())
        colors = {
            "behavioral": ("#7C3AED", "white"),
            "technical": ("#D97706", "white"),
            "situational": ("#059669", "white"),
        }
        bg, fg = colors.get(question.category, ("#6B7280", "white"))
        cat_label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; padding: 2px 8px; "
            f"border-radius: 4px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(cat_label)
        header.addStretch()
        layout.addLayout(header)

        q_label = QLabel(question.question)
        q_label.setWordWrap(True)
        q_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(q_label)

        star = question.star
        if star.situation:
            layout.addWidget(self._star_label("Situation", star.situation))
        if star.task:
            layout.addWidget(self._star_label("Task", star.task))
        if star.action:
            layout.addWidget(self._star_label("Action", star.action))
        if star.result:
            layout.addWidget(self._star_label("Result", star.result))

    def _star_label(self, heading: str, text: str) -> QLabel:
        label = QLabel(f"<b>{heading}:</b> {text}")
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 12px; color: #374151;")
        return label


class InterviewPrepPage(QWidget):
    """Interview preparation page with question generation and STAR outlines."""

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self._worker: Worker | None = None
        self._overlay = LoadingOverlayManager()
        self._result: InterviewQuestionsResult | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Interview Preparation")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Generate role-specific interview questions with STAR response outlines "
            "based on your resume and target job."
        )
        layout.addWidget(desc)

        form = QHBoxLayout()

        form.addWidget(QLabel("Role:"))
        self._role_input = QLineEdit()
        self._role_input.setPlaceholderText("e.g. Senior Software Engineer")
        form.addWidget(self._role_input)

        form.addWidget(QLabel("Company:"))
        self._company_input = QLineEdit()
        self._company_input.setPlaceholderText("e.g. Google")
        form.addWidget(self._company_input)

        self._generate_btn = QPushButton("Generate Questions")
        self._generate_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 6px 20px; "
            "border-radius: 4px; font-weight: bold;"
        )
        self._generate_btn.clicked.connect(self._on_generate)
        form.addWidget(self._generate_btn)

        layout.addLayout(form)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll, stretch=1)

        action_row = QHBoxLayout()
        self._export_btn = QPushButton("Export to Markdown")
        self._export_btn.clicked.connect(self._on_export)
        self._export_btn.setEnabled(False)
        action_row.addWidget(self._export_btn)

        self._save_btn = QPushButton("Save to Session")
        self._save_btn.clicked.connect(self._on_save)
        self._save_btn.setEnabled(False)
        action_row.addWidget(self._save_btn)

        action_row.addStretch()
        layout.addLayout(action_row)

    def on_show(self) -> None:
        pass

    def _on_generate(self) -> None:
        role = self._role_input.text().strip()
        company = self._company_input.text().strip()

        if not role:
            QMessageBox.warning(self, "Missing Role", "Please enter a target role.")
            return

        resume = self.window.state.resume
        if resume is None:
            QMessageBox.warning(self, "No Resume", "Please upload a resume first.")
            return

        self._generate_btn.setEnabled(False)
        self._overlay.show(self)

        def _do_generate():
            svc = InterviewPrepService()
            return svc.generate_questions(resume, role, company)

        self._worker = Worker(_do_generate, timeout_seconds=300)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, result: InterviewQuestionsResult) -> None:
        self._overlay.hide()
        self._generate_btn.setEnabled(True)

        self._result = result
        self._clear_cards()

        if not result.questions:
            self._cards_layout.insertWidget(
                self._cards_layout.count() - 1,
                QLabel("No questions generated. Try again."),
            )
            return

        for q in result.questions:
            card = _QuestionCard(q)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        self._export_btn.setEnabled(True)
        self._save_btn.setEnabled(True)

    def _on_error(self, msg: str) -> None:
        self._overlay.hide()
        self._generate_btn.setEnabled(True)
        QMessageBox.warning(self, "Error", f"Failed to generate questions: {msg}")

    def _on_export(self) -> None:
        if self._result is None:
            return
        svc = InterviewPrepService()
        md = svc.to_markdown(self._result)
        QApplication.clipboard().setText(md)
        self.window.notify("Interview prep copied to clipboard as markdown.")

    def _on_save(self) -> None:
        if self._result is None:
            return
        role = self._role_input.text().strip()
        company = self._company_input.text().strip()
        resume_id = self.window.state.resume_id
        job_id = self.window.state.job_id

        if resume_id is None:
            QMessageBox.warning(self, "No Resume", "No active resume to link.")
            return

        try:
            svc = InterviewPrepService()
            md = svc.to_markdown(self._result)
            with db.session_scope() as session:
                row = InterviewSession(
                    resume_id=resume_id,
                    job_id=job_id,
                    company=company,
                    role=role,
                    notes=md,
                )
                session.add(row)
            self.window.notify("Interview prep saved.")
        except Exception:
            logger.exception("Failed to save interview session")

    def _clear_cards(self) -> None:
        while self._cards_layout.count():
            child = self._cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._cards_layout.addStretch()
