"""Resume Upload page: import PDF/DOCX, parse and save."""
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
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

from app.ai.ollama_client import OllamaClient
from app.database import db
from app.services.document_reader import extract_text
from app.services.resume_parser import parse_resume, parse_resume_ai
from app.ui.components.loading_overlay import LoadingOverlayManager
from app.ui.workers import Worker


class ResumeUploadPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._parsed = None
        self._raw_text = ""
        self._source_filename = ""
        self._worker = None
        self._overlay = LoadingOverlayManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Resume Upload")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        self.import_btn = QPushButton("Import Resume (PDF / DOCX)")
        self.import_btn.clicked.connect(self._import)
        self.ai_check = QCheckBox("Use AI parsing (Ollama)")
        row.addWidget(self.import_btn)
        row.addWidget(self.ai_check)
        row.addStretch()
        layout.addLayout(row)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Resume name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Parsed resume (structured JSON):"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)

        self.save_btn = QPushButton("Save to Database")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Resume", "", "Documents (*.pdf *.docx *.txt)"
        )
        if not path:
            return
        try:
            text = extract_text(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        if not text.strip():
            QMessageBox.warning(self, "Empty document", "No text could be extracted from the file.")
            return
        self._raw_text = text
        self._source_filename = Path(path).name
        if not self.name_edit.text():
            self.name_edit.setText(Path(path).stem)
        if self.ai_check.isChecked():
            self.window.notify("Parsing resume with AI - this may take a moment...")
            self.import_btn.setEnabled(False)
            self._overlay.show(self, "Parsing resume with AI...")
            self._worker = Worker(parse_resume_ai, text, OllamaClient())
            self._worker.result.connect(self._on_parsed)
            self._worker.error.connect(self._on_error)
            self._worker.start()
        else:
            self._on_parsed(parse_resume(text))

    def _on_parsed(self, resume) -> None:
        self._overlay.hide(self)
        resume.raw_text = self._raw_text
        self._parsed = resume
        data = resume.model_dump()
        data.pop("raw_text", None)
        self.preview.setPlainText(json.dumps(data, indent=2))
        self.save_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.window.notify("Resume parsed. Review the JSON, then save it.")

    def _on_error(self, message: str) -> None:
        self._overlay.hide(self)
        self.import_btn.setEnabled(True)
        QMessageBox.critical(self, "AI parsing failed", message)

    def _save(self) -> None:
        if self._parsed is None:
            return
        name = self.name_edit.text().strip() or self._parsed.contact.name or "Resume"
        resume_id = db.save_resume(
            name,
            self._parsed.model_dump_json(),
            self._raw_text,
            source_type="import",
            source_filename=self._source_filename,
        )
        state = self.window.state
        state.resume = self._parsed
        state.resume_id = resume_id
        state.ats = None
        state.optimized = None
        self.window.notify(f"Resume '{name}' saved.")
