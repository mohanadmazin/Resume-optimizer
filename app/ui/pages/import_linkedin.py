"""LinkedIn Import page — import resume data from LinkedIn data export."""
from __future__ import annotations

import logging
from pathlib import Path

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
from app.database.repositories.resume_repository import ResumeRepository
from app.domain.resume import ResumeData
from app.services.linkedin_import import import_linkedin
from app.ui.workers import Worker

logger = logging.getLogger(__name__)


class LinkedInImportPage(QWidget):
    """Import resume data from a LinkedIn data export file (JSON or CSV)."""

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self._worker: Worker | None = None
        self._imported: ResumeData | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("LinkedIn Import")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Import resume data from a LinkedIn data export file. "
            "Download your data from LinkedIn Settings > Data Privacy > Get a copy of your data."
        )
        layout.addWidget(desc)

        file_row = QHBoxLayout()
        self._file_path = QLineEdit()
        self._file_path.setPlaceholderText("Select a LinkedIn export file (.json or .csv)...")
        self._file_path.setReadOnly(True)
        file_row.addWidget(self._file_path)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        self._import_btn = QPushButton("Import Data")
        self._import_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 6px 20px; "
            "border-radius: 4px; font-weight: bold;"
        )
        self._import_btn.clicked.connect(self._on_import)
        self._import_btn.setEnabled(False)
        layout.addWidget(self._import_btn)

        layout.addWidget(QLabel("Preview:"))

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("Imported data will appear here...")
        layout.addWidget(self._preview, stretch=1)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Resume Name:"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("My LinkedIn Resume")
        name_row.addWidget(self._name_input)
        layout.addLayout(name_row)

        self._save_btn = QPushButton("Save as Resume")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        layout.addWidget(self._save_btn)

    def on_show(self) -> None:
        pass

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select LinkedIn Export",
            "",
            "LinkedIn Export (*.json *.csv);;All Files (*)",
        )
        if path:
            self._file_path.setText(path)
            self._import_btn.setEnabled(True)

    def _on_import(self) -> None:
        path_str = self._file_path.text().strip()
        if not path_str:
            return

        path = Path(path_str)
        if not path.exists():
            QMessageBox.warning(self, "File Not Found", "The selected file does not exist.")
            return

        try:
            result = import_linkedin(path)
            self._imported = result
            self._show_preview(result)
            self._save_btn.setEnabled(True)
        except Exception as exc:
            QMessageBox.warning(self, "Import Error", f"Failed to import: {exc}")

    def _show_preview(self, data: ResumeData) -> None:
        lines: list[str] = []

        if data.contact:
            c = data.contact
            if c.name:
                lines.append(f"Name: {c.name}")
            if c.email:
                lines.append(f"Email: {c.email}")
            if c.phone:
                lines.append(f"Phone: {c.phone}")
            if c.location:
                lines.append(f"Location: {c.location}")

        if data.headline:
            lines.append(f"\nHeadline: {data.headline}")

        if data.summary:
            lines.append(f"\nSummary: {data.summary[:200]}...")

        if data.skills:
            lines.append(f"\nSkills ({len(data.skills)}): {', '.join(data.skills[:10])}")

        if data.experience:
            lines.append(f"\nExperience ({len(data.experience)} entries):")
            for exp in data.experience:
                lines.append(f"  - {exp.title} at {exp.company} ({exp.start_date} - {exp.end_date})")
                for b in exp.bullets[:3]:
                    lines.append(f"    * {b}")

        if data.education:
            lines.append(f"\nEducation ({len(data.education)} entries):")
            for edu in data.education:
                lines.append(f"  - {edu.degree} at {edu.institution} ({edu.year})")

        self._preview.setPlainText("\n".join(lines))

    def _on_save(self) -> None:
        if self._imported is None:
            return

        name = self._name_input.text().strip() or "LinkedIn Import"

        try:
            with db.session_scope() as session:
                repo = ResumeRepository(session)
                resume_id = repo.save(
                    name=name,
                    data_json=self._imported.model_dump_json(),
                    raw_text="",
                    source_type="linkedin",
                    source_filename=self._file_path.text(),
                )
            self.window.state.resume_id = resume_id
            self.window.notify(f"Resume saved as '{name}' (ID: {resume_id}).")
            QMessageBox.information(
                self,
                "Saved",
                f"Resume '{name}' saved successfully.\n"
                "Go to Resume Upload to view and edit it.",
            )
        except Exception:
            logger.exception("Failed to save imported resume")
            QMessageBox.warning(self, "Save Error", "Failed to save the imported resume.")
