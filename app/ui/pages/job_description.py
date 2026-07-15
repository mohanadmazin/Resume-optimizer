"""Job Description page: paste, upload, or fetch the target job posting from a URL."""
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
from app.services.job_scraper import fetch_job_from_url
from app.ui.workers import Worker


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

        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste a LinkedIn (or other) job posting URL...")
        self.url_edit.returnPressed.connect(self._fetch_url)
        url_row.addWidget(self.url_edit, 1)
        self.fetch_btn = QPushButton("Fetch from URL")
        self.fetch_btn.clicked.connect(self._fetch_url)
        url_row.addWidget(self.fetch_btn)
        layout.addLayout(url_row)

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

    def _fetch_url(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Paste a job posting URL first.")
            return
        self.fetch_btn.setEnabled(False)
        self.window.notify("Fetching job posting...")
        self._fetch_worker = Worker(fetch_job_from_url, url)
        self._fetch_worker.result.connect(self._on_fetch_done)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.start()

    def _on_fetch_done(self, job: dict) -> None:
        self.fetch_btn.setEnabled(True)
        self.content.setPlainText(job["description"])
        if job.get("title"):
            self.title_edit.setText(job["title"])
        if job.get("company"):
            self.company_edit.setText(job["company"])
        self.window.notify("Job description fetched from URL.")

    def _on_fetch_error(self, message: str) -> None:
        self.fetch_btn.setEnabled(True)
        QMessageBox.critical(self, "Fetch failed", message)

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
        state.job_id = job_id
        state.ats = None
        self.window.notify(f"Job description '{title}' saved.")
