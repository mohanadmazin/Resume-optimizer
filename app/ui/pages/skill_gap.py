"""Skill Gap Analysis page — compare skills vs job description requirements."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.schemas import ResumeData, SkillGapResult
from app.services.skill_gap import analyze_skill_gap
from app.ui.components.loading_overlay import LoadingOverlayManager
from app.ui.workers import Worker


def _card(title: str) -> tuple[QFrame, QLabel]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    label = QLabel(title.upper())
    label.setObjectName("cardTitle")
    value = QLabel("--")
    value.setObjectName("scoreValue")
    value.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    layout.addWidget(value)
    return frame, value


class SkillGapPage(QWidget):

    def __init__(self, window):
        super().__init__()
        self.window = window
        self._worker = None
        self._result = None
        self._overlay = LoadingOverlayManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Skill Gap Analysis")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Compare your resume skills against the requirements "
            "in your loaded job description."
        )
        layout.addWidget(desc)

        disclaimer = QLabel(
            "Note: Required skills are extracted from the job description text. "
            "The AI interprets the posting — always verify against the original."
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("color: #9CA3AF; font-size: 11px; font-style: italic;")
        layout.addWidget(disclaimer)

        input_row = QHBoxLayout()
        self.role_input = QLineEdit()
        self.role_input.setPlaceholderText("e.g. Senior Software Engineer")
        input_row.addWidget(self.role_input, 1)

        self.analyze_btn = QPushButton("Analyze Skill Gap")
        self.analyze_btn.clicked.connect(self._run)
        input_row.addWidget(self.analyze_btn)
        layout.addLayout(input_row)

        cards = QHBoxLayout()
        card1, self.matched_value = _card("Matched Skills")
        card2, self.missing_value = _card("Missing Skills")
        card3, self.total_value = _card("Required Skills")
        for c in (card1, card2, card3):
            cards.addWidget(c)
        layout.addLayout(cards)

        columns = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel("Missing skills:"))
        self.missing_table = QTableWidget()
        self.missing_table.setColumnCount(3)
        self.missing_table.setHorizontalHeaderLabels(
            ["Skill", "Importance", "Recommendation"]
        )
        self.missing_table.horizontalHeader().setStretchLastSection(True)
        self.missing_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        left.addWidget(self.missing_table)
        columns.addLayout(left, 2)

        right = QVBoxLayout()
        right.addWidget(QLabel("Analysis summary:"))
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        right.addWidget(self.summary)
        columns.addLayout(right, 1)

        layout.addLayout(columns, 1)

    def on_show(self):
        """Auto-populate role from the current job description and load resume."""
        state = self.window.state
        if state.job_title and not self.role_input.text().strip():
            self.role_input.setText(state.job_title)
        self._load_resume()

    def _load_resume(self) -> ResumeData | None:
        from app.database import db

        state = self.window.state
        if state.resume is None:
            row = db.latest_resume()
            if row:
                state.resume = ResumeData.model_validate_json(row["data_json"])
                state.resume_id = row["id"]
        return state.resume

    def _run(self) -> None:
        self.run_analysis()

    def run_analysis(self, silent: bool = False) -> None:
        """Run skill gap analysis — can be called internally or from another page."""
        state = self.window.state
        resume = self._load_resume()

        if resume is None:
            if not silent:
                QMessageBox.warning(
                    self,
                    "Missing input",
                    "Import a resume first.",
                )
            return

        role = self.role_input.text().strip()
        if not role:
            if not silent:
                QMessageBox.warning(
                    self,
                    "Missing input",
                    "Enter a target role.",
                )
            return

        if not state.job_text.strip():
            if not silent:
                QMessageBox.warning(
                    self,
                    "Missing input",
                    "Load a job description first.",
                )
            return

        self.analyze_btn.setEnabled(False)
        self.window.notify("Analyzing skill gap — this may take a minute...")
        self._overlay.show(self, "Analyzing skill gap...")
        self._worker = Worker(analyze_skill_gap, resume, state.job_text, role)
        self._worker.result.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result: SkillGapResult) -> None:
        self._overlay.hide(self)
        self._result = result
        self.analyze_btn.setEnabled(True)

        self.matched_value.setText(str(len(result.matched)))
        self.missing_value.setText(str(len(result.missing)))
        self.total_value.setText(str(len(result.market_skills)))

        self.missing_table.setRowCount(len(result.missing))
        for i, item in enumerate(result.missing):
            self.missing_table.setItem(i, 0, QTableWidgetItem(item.skill))
            imp_item = QTableWidgetItem(item.importance)
            if item.importance.lower() == "high":
                imp_item.setForeground(Qt.GlobalColor.red)
            elif item.importance.lower() == "medium":
                imp_item.setForeground(Qt.GlobalColor.darkYellow)
            self.missing_table.setItem(i, 1, imp_item)
            self.missing_table.setItem(i, 2, QTableWidgetItem(item.recommendation))

        self.summary.setPlainText(result.summary or "No summary available.")
        self.window.notify(
            f"Skill gap analysis complete — {len(result.matched)} matched, "
            f"{len(result.missing)} missing."
        )

    def _on_error(self, message: str) -> None:
        self._overlay.hide(self)
        self.analyze_btn.setEnabled(True)
        QMessageBox.critical(self, "Analysis failed", message)
