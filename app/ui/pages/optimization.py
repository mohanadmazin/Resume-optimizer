# app/ui/pages/optimization.py
import re
from datetime import date

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

from app import config
from app.ai.ollama_client import OllamaClient
from app.database import db
from app.exports.exporter import export_docx, export_markdown, export_pdf, to_markdown
from app.services.ats_engine import analyze
from app.ui.workers import Worker


class OptimizationPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Optimization")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.run_btn = QPushButton("Optimize with AI")
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn, 1)

        # Resume Display
        columns = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Original resume:"))
        self.before = QTextEdit()
        self.before.setReadOnly(True)
        left.addWidget(self.before)
        right = QVBoxLayout()
        after_header = QHBoxLayout()
        after_header.addWidget(QLabel("Optimized resume:"))
        legend = QLabel("Red = AI added/changed")
        legend.setStyleSheet("color:#ff5c5c;")
        after_header.addWidget(legend)
        after_header.addStretch()
        right.addLayout(after_header)
        self.after = QTextEdit()
        self.after.setReadOnly(True)
        right.addWidget(self.after)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        layout.addLayout(columns, 1)

        # Exports
        exports = QHBoxLayout()
        for label, fmt in (("Export DOCX", "docx"), ("Export PDF", "pdf"), ("Export Markdown", "md")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, f=fmt: self._export(f))
            exports.addWidget(btn)
        exports.addStretch()
        layout.addLayout(exports)

    def on_show(self) -> None:
        state = self.window.state
        if state.resume is not None:
            self.before.setPlainText(to_markdown(state.resume))
        if state.optimized is not None and state.resume is not None:
            self.after.setHtml(resume_diff_html(state.resume, state.optimized))

    def _run(self) -> None:
        state = self.window.state
        if state.resume is None or not state.job_text.strip():
            QMessageBox.warning(
                self,
                "Missing input",
                "Import a resume and add a job description first (then run an ATS analysis).",
            )
            return
        if state.ats is None:
            state.ats = analyze(state.resume, state.job_text)
            state.selected_keywords = list(state.ats.missing_keywords)

        ats_for_optimizer = state.ats
        if state.selected_keywords is not None:
            allowed = set(state.selected_keywords)
            ats_for_optimizer = replace(
                state.ats,
                missing_keywords=[k for k in state.ats.missing_keywords if k in allowed],
            )

        self.before.setPlainText(to_markdown(state.resume))
        self.run_btn.setEnabled(False)
        model = config.load_config()["model"]
        self.window.notify(f"Optimizing with {model} - this may take a minute...")
        self._worker = Worker(
            optimize_resume, state.resume, state.job_text, ats_for_optimizer, OllamaClient()
        )
        self._worker.result.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, optimized) -> None:
        state = self.window.state
        state.optimized = optimized
        self.after.setHtml(resume_diff_html(state.resume, optimized))
        self.run_btn.setEnabled(True)
        new_result = analyze(optimized, state.job_text)
        if state.resume_id is not None and state.job_id is not None:
            db.save_optimization(
                state.resume_id, state.job_id, config.load_config()["model"], optimized.model_dump_json()
            )
        old_score = state.ats.ats_score if state.ats else "?"
        self.window.notify(
            f"Optimization complete - new ATS score {new_result.ats_score}/100 (was {old_score})."
        )

    def _on_error(self, message: str) -> None:
        self.run_btn.setEnabled(True)
        QMessageBox.critical(self, "Optimization failed", message)

    @staticmethod
    def _clean_filename_part(text: str) -> str:
        text = re.sub(r'[\\/:*?"<>|]+', "", text).strip()
        return re.sub(r"\s+", " ", text)

    def _default_filename(self, fmt: str) -> str:
        state = self.window.state
        parts = ["Resume"]
        if state.job_company.strip():
            parts.append(self._clean_filename_part(state.job_company))
        if state.job_title.strip():
            parts.append(self._clean_filename_part(state.job_title))
        parts.append(date.today().isoformat())
        return " - ".join(parts) + f".{fmt}"

    def _export(self, fmt: str) -> None:
        state = self.window.state
        resume = state.optimized or state.resume
        if resume is None:
            QMessageBox.warning(self, "Nothing to export", "Import or optimize a resume first.")
            return
        filters = {
            "docx": "Word Document (*.docx)",
            "pdf": "PDF Document (*.pdf)",
            "md": "Markdown (*.md)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Resume", self._default_filename(fmt), filters[fmt]
        )
        if not path:
            return
        try:
            if fmt == "docx":
                export_docx(resume, path)
            elif fmt == "pdf":
                export_pdf(resume, path)
            else:
                export_markdown(resume, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.window.notify(f"Exported to {path}")