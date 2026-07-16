"""Job Description page: paste or upload the target job posting."""
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import db
from app.services.document_reader import extract_text


class JobDescriptionPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Job Description")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Job title (e.g. Senior Python Developer)")
        layout.addWidget(self.title_edit)

        self.company_edit = QLineEdit()
        self.company_edit.setPlaceholderText("Company (e.g. Acme Corp)")
        layout.addWidget(self.company_edit)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Location (e.g. Kuala Lumpur, Malaysia)")
        layout.addWidget(self.location_edit)

        row = QHBoxLayout()
        upload_btn = QPushButton("Upload PDF / DOCX")
        upload_btn.clicked.connect(self._upload)
        row.addWidget(upload_btn)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(QLabel("Paste or edit the job description below:"))
        self.content = QTextEdit()
        self.content.setPlaceholderText("Paste the job description here...")
        layout.addWidget(self.content, 1)

        save_btn = QPushButton("Use This Job Description")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Upload Job Description", "", "Documents (*.pdf *.docx *.txt)"
        )
        if not path:
            return
        try:
            self.content.setPlainText(extract_text(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Upload failed", str(exc))

    def _save(self) -> None:
        text = self.content.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Missing text", "Paste or upload a job description first.")
            return
        title = self.title_edit.text().strip() or "Untitled Job"
        job_id = db.save_job(title, text)
        state = self.window.state
        state.job_text = text
        state.job_title = title
        state.job_company = self.company_edit.text().strip()
        state.job_location = self.location_edit.text().strip()
        state.job_id = job_id
        state.ats = None
        self.window.notify(f"Job description '{title}' saved — running analyses...")
        self._trigger_analyses()

    def _trigger_analyses(self) -> None:
        """Auto-fill role/location and run ATS, Skill Gap, and Salary analyses."""
        state = self.window.state

        # Auto-fill Skill Gap role input
        skill_gap_page = self.window.get_page("Skill Gap")
        if skill_gap_page and state.job_title:
            skill_gap_page.role_input.setText(state.job_title)

        # Auto-fill Salary Estimate inputs
        salary_page = self.window.get_page("Salary Estimate")
        if salary_page:
            if state.job_title:
                salary_page.role_input.setText(state.job_title)
            if state.job_location:
                salary_page.location_input.setText(state.job_location)

        # Run ATS analysis (synchronous, fast)
        ats_page = self.window.get_page("ATS Analysis")
        if ats_page:
            ats_page.run_analysis(silent=True)

        # Run Skill Gap analysis (async, Ollama)
        if skill_gap_page:
            skill_gap_page.run_analysis(silent=True)

        # Run Salary Estimate (async, Ollama)
        if salary_page:
            salary_page.run_analysis(silent=True)
