"""Salary Estimation page — estimate salary range via Ollama."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.schemas import ResumeData, SalaryEstimate
from app.services.salary_estimator import estimate_salary
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


class SalaryEstimatePage(QWidget):

    analysis_finished = Signal()

    def __init__(self, window):
        super().__init__()
        self.window = window
        self._worker = None
        self._result = None
        self._overlay = LoadingOverlayManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Salary Estimation")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Estimate your expected salary range based on your skills, "
            "experience, and target location."
        )
        layout.addWidget(desc)

        disclaimer = QLabel(
            "Benchmark-based estimate: salary arithmetic is calculated from a "
            "versioned local market dataset. AI is used only to classify the role "
            "and interpret candidate evidence. It is not a guaranteed offer and "
            "does not include bonus, AWS, commission, allowances, equity, or benefits."
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("color: #F59E0B; font-size: 11px; font-style: italic; "
                                 "background-color: rgba(245, 158, 11, 0.1); "
                                 "padding: 6px; border-radius: 4px;")
        layout.addWidget(disclaimer)

        input_row = QHBoxLayout()
        self.role_input = QLineEdit()
        self.role_input.setPlaceholderText("Target role (e.g. Software Engineer)")
        input_row.addWidget(self.role_input, 1)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Location (e.g. Kuala Lumpur, Malaysia)")
        input_row.addWidget(self.location_input, 1)

        self.estimate_btn = QPushButton("Estimate Salary")
        self.estimate_btn.clicked.connect(self._run)
        input_row.addWidget(self.estimate_btn)
        layout.addLayout(input_row)

        cards = QHBoxLayout()
        card1, self.monthly_value = _card("Monthly Range")
        card2, self.annual_value = _card("Annual Range")
        card3, self.currency_value = _card("Currency")
        card4, self.exp_value = _card("Experience Level")
        for c in (card1, card2, card3, card4):
            cards.addWidget(c)
        layout.addLayout(cards)

        columns = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel("Factors affecting estimate:"))
        self.factors = QTextEdit()
        self.factors.setReadOnly(True)
        left.addWidget(self.factors)
        columns.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Notes:"))
        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        right.addWidget(self.notes)
        columns.addLayout(right, 1)

        layout.addLayout(columns, 1)

    def on_show(self):
        """Auto-populate role and location from the current job description and load resume."""
        state = self.window.state
        if state.job_title and not self.role_input.text().strip():
            self.role_input.setText(state.job_title)
        if state.job_location and not self.location_input.text().strip():
            self.location_input.setText(state.job_location)
        self._load_resume()
        if state.salary_estimate is not None and self._result is None:
            self._on_done(state.salary_estimate)

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

    def run_analysis(self, silent: bool = False) -> bool:
        """Run salary estimation — can be called internally or from another page."""
        resume = self._load_resume()

        if resume is None:
            if not silent:
                QMessageBox.warning(
                    self,
                    "Missing input",
                    "Import a resume first.",
                )
            return False

        role = self.role_input.text().strip()
        location = self.location_input.text().strip()

        if not role or not location:
            if not silent:
                QMessageBox.warning(
                    self,
                    "Missing input",
                    "Enter both a target role and location.",
                )
            return False

        self.estimate_btn.setEnabled(False)
        self.window.notify("Estimating salary — this may take a minute...")
        self._overlay.show(self, "Estimating salary...")
        self._worker = Worker(estimate_salary, resume, role, location)
        self._worker.result.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        return True

    def _on_done(self, result: SalaryEstimate) -> None:
        self._overlay.hide(self)
        self._result = result
        self.estimate_btn.setEnabled(True)

        def _fmt(value):
            if value is None:
                return "N/A"
            return f"{value:,.0f}"

        if result.status != "ok":
            self.monthly_value.setText("Insufficient data")
            self.annual_value.setText("Insufficient data")
            self.currency_value.setText(result.currency or "N/A")
            self.exp_value.setText("Low confidence")
            self.factors.setPlainText(
                "A supported, versioned local benchmark dataset is required."
            )
            self.notes.setPlainText(result.notes or "No defensible estimate is available.")
            self.window.notify("Salary estimate unavailable for this market or role.")
            self.analysis_finished.emit()
            return

        monthly = (
            f"{_fmt(result.salary_monthly_min)} - "
            f"{_fmt(result.salary_monthly_mid)} - "
            f"{_fmt(result.salary_monthly_max)}"
        )
        annual = (
            f"{_fmt(result.salary_annual_min)} - "
            f"{_fmt(result.salary_annual_mid)} - "
            f"{_fmt(result.salary_annual_max)}"
        )

        self.monthly_value.setText(monthly)
        self.monthly_value.setToolTip("Minimum - midpoint - maximum")
        self.annual_value.setText(annual)
        self.annual_value.setToolTip("Minimum - midpoint - maximum")
        self.currency_value.setText(result.currency or "N/A")
        self.exp_value.setText(
            f"{result.seniority.title()} | {result.experience_years}"
        )

        factor_rows = [f"• {factor}" for factor in result.factors]
        factor_rows.append(
            f"• Confidence: {result.confidence_details.level.title()} "
            f"({result.confidence_details.score:.0%})"
        )
        factor_rows.extend(
            f"• Missing input: {item}"
            for item in result.confidence_details.missing_inputs
        )
        self.factors.setPlainText("\n".join(factor_rows))

        note_rows = [
            result.notes or "No additional notes.",
            "",
            f"Source: {result.salary_source} ({result.source_date})",
            f"Basis: {result.compensation_basis}",
        ]
        if result.additional_compensation_notes:
            note_rows.extend(["", result.additional_compensation_notes])
        if result.assumptions:
            note_rows.extend(["", "Assumptions:"])
            note_rows.extend(f"• {item}" for item in result.assumptions)
        self.notes.setPlainText("\n".join(note_rows))

        self.window.notify(
            f"Salary estimate: {annual} {result.currency}/year"
        )
        self.analysis_finished.emit()

    def _on_error(self, message: str) -> None:
        self._overlay.hide(self)
        self.estimate_btn.setEnabled(True)
        QMessageBox.critical(
            self,
            "Estimation failed",
            f"{message}\n\nTip: Check that your model in Settings is installed and supports text generation.",
        )
        self.analysis_finished.emit()
