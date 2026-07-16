# app/ui/pages/job_description.py

"""Job Description page: paste, upload, or fetch from URL."""

from PySide6.QtCore import QThread, Signal
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
from app.services.job_fetcher import JobFetcher, JobFetcherError


class _FetchWorker(QThread):
    """Background thread for fetching job descriptions from URLs."""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            text = JobFetcher.fetch_from_url(self.url)
            self.finished.emit(text)
        except JobFetcherError as exc:
            self.error.emit(str(exc))


class JobDescriptionPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._fetch_worker = None

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

        # URL fetch row
        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter job posting URL (e.g. https://linkedin.com/jobs/...)")
        url_row.addWidget(self.url_edit, 1)
        self.fetch_btn = QPushButton("Fetch from URL")
        self.fetch_btn.clicked.connect(self._fetch_from_url)
        url_row.addWidget(self.fetch_btn)
        layout.addLayout(url_row)

        # Upload button row
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

    def _fetch_from_url(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Enter a job posting URL first.")
            return

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Fetching...")
        self.window.notify("Fetching job description from URL...")

        self._fetch_worker = _FetchWorker(url)
        self._fetch_worker.finished.connect(self._on_fetch_done)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.start()

    def _on_fetch_done(self, text: str) -> None:
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch from URL")
        self.content.setPlainText(text)
        self.window.notify("Job description fetched successfully.")

    def _on_fetch_error(self, message: str) -> None:
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch from URL")
        QMessageBox.critical(self, "Fetch failed", message)

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

        skill_gap_page = self.window.get_page("Skill Gap")
        if skill_gap_page and state.job_title:
            skill_gap_page.role_input.setText(state.job_title)

        salary_page = self.window.get_page("Salary Estimate")
        if salary_page:
            if state.job_title:
                salary_page.role_input.setText(state.job_title)
            if state.job_location:
                salary_page.location_input.setText(state.job_location)

        ats_page = self.window.get_page("ATS Analysis")
        if ats_page:
            ats_page.run_analysis(silent=True)

        if skill_gap_page:
            skill_gap_page.run_analysis(silent=True)

        if salary_page:
            salary_page.run_analysis(silent=True)
