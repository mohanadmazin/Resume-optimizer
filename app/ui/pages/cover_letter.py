"""Cover Letter page: generate a tailored letter from resume + job."""
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ai.ollama_client import OllamaClient
from app.exports.exporter import export_text_docx
from app.services.cover_letter import generate_cover_letter
from app.ui.workers import Worker


class CoverLetterPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Cover Letter")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Cover Letter")
        self.generate_btn.clicked.connect(self._run)
        self.save_btn = QPushButton("Save As...")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        row.addWidget(self.generate_btn)
        row.addWidget(self.save_btn)
        row.addStretch()
        layout.addLayout(row)

        self.output = QTextEdit()
        self.output.setPlaceholderText(
            "The generated cover letter appears here. You can edit it before saving."
        )
        layout.addWidget(self.output, 1)

    def _run(self) -> None:
        state = self.window.state
        resume = state.optimized or state.resume
        if resume is None or not state.job_text.strip():
            QMessageBox.warning(
                self, "Missing input", "Import a resume and add a job description first."
            )
            return
        self.generate_btn.setEnabled(False)
        self.window.notify("Generating cover letter - this may take a minute...")
        self._worker = Worker(generate_cover_letter, resume, state.job_text, OllamaClient())
        self._worker.result.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, text: str) -> None:
        self.output.setPlainText(text)
        self.generate_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.window.notify("Cover letter generated.")

    def _on_error(self, message: str) -> None:
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Generation failed", message)

    def _save(self) -> None:
        text = self.output.toPlainText().strip()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Cover Letter",
            "cover_letter.txt",
            "Text (*.txt);;Markdown (*.md);;Word Document (*.docx)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".docx"):
                export_text_docx(text, path)
            else:
                Path(path).write_text(text, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self.window.notify(f"Cover letter saved to {path}")
