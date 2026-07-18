"""Dashboard: one-click pipeline, latest scores and recent analyses."""
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import db


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


class DashboardPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._pipeline_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ── Pipeline section ──────────────────────────────────────────────
        pipeline_group = QGroupBox("One-Click Optimization Pipeline")
        pipeline_layout = QVBoxLayout(pipeline_group)
        pipeline_layout.setSpacing(12)

        desc = QLabel(
            "Run ATS analysis, AI resume optimization, and cover letter "
            "generation in a single click."
        )
        desc.setObjectName("pipelineDesc")
        desc.setWordWrap(True)
        pipeline_layout.addWidget(desc)

        btn_row = QHBoxLayout()
        self.pipeline_btn = QPushButton("Run Full Pipeline")
        self.pipeline_btn.setObjectName("pipelineBtn")
        self.pipeline_btn.setMinimumHeight(48)
        self.pipeline_btn.clicked.connect(self._run_pipeline)
        btn_row.addWidget(self.pipeline_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.setMinimumHeight(48)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_pipeline)
        btn_row.addWidget(self.cancel_btn)
        pipeline_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(8)
        pipeline_layout.addWidget(self.progress_bar)

        self.step_label = QLabel("")
        self.step_label.setObjectName("stepLabel")
        self.step_label.setVisible(False)
        pipeline_layout.addWidget(self.step_label)

        layout.addWidget(pipeline_group)

        # ── Score cards ───────────────────────────────────────────────────
        cards = QHBoxLayout()
        card1, self.score_value = _card("ATS Score")
        card2, self.keyword_value = _card("Keyword Match")
        card3, self.skills_value = _card("Skills Match")
        for card in (card1, card2, card3):
            cards.addWidget(card)
        layout.addLayout(cards)

        # ── Recent analyses table ─────────────────────────────────────────
        layout.addWidget(QLabel("Recent Analyses"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Resume", "Job", "ATS Score", "Keyword %", "Skills %"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

    # ── Pipeline control ──────────────────────────────────────────────────

    def _run_pipeline(self) -> None:
        state = self.window.state

        if state.resume is None:
            self._prompt_import_resume()
            return

        if not state.job_text.strip():
            self._prompt_job_description()
            return

        # Disable controls
        self.pipeline_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.step_label.setVisible(True)
        self.step_label.setText("Starting pipeline...")
        state.pipeline_running = True

        from app.ui.workers import PipelineWorker

        self._pipeline_worker = PipelineWorker(
            resume=state.resume,
            job_text=state.job_text,
            job_title=state.job_title,
            job_id=state.job_id,
            resume_id=state.resume_id,
            parent=self,
        )
        self._pipeline_worker.progress.connect(self._on_pipeline_progress)
        self._pipeline_worker.result.connect(self._on_pipeline_done)
        self._pipeline_worker.error.connect(self._on_pipeline_error)
        self._pipeline_worker.start()

    # ── Resume import prompt ─────────────────────────────────────────────

    def _prompt_import_resume(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Resume", "", "Documents (*.pdf *.docx *.txt)"
        )
        if not path:
            return

        self._pending_resume_path = path
        self.pipeline_btn.setEnabled(False)

        from app.services.document_reader import extract_text
        from app.ui.workers import Worker
        self._overlay_label = "Extracting text..."
        self._extract_worker = Worker(extract_text, path)
        self._extract_worker.result.connect(self._on_resume_text_extracted)
        self._extract_worker.error.connect(self._on_resume_import_error)
        self._extract_worker.start()

    def _on_resume_text_extracted(self, text: str) -> None:
        if not text.strip():
            self.pipeline_btn.setEnabled(True)
            QMessageBox.warning(self, "Empty document", "No text could be extracted from the file.")
            return

        self._raw_text = text
        from app.services.resume_parser import parse_resume
        from app.ui.workers import Worker
        self._parse_worker = Worker(parse_resume, text)
        self._parse_worker.result.connect(self._on_resume_parsed)
        self._parse_worker.error.connect(self._on_resume_import_error)
        self._parse_worker.start()

    def _on_resume_parsed(self, resume) -> None:
        self.pipeline_btn.setEnabled(True)
        resume.raw_text = self._raw_text

        state = self.window.state
        resume_id = db.save_resume(
            resume.contact.name or "Resume",
            resume.model_dump_json(),
            self._raw_text,
            source_type="import",
            source_filename=getattr(self, "_pending_resume_path", ""),
        )
        state.resume = resume
        state.resume_id = resume_id
        self.window.notify(f"Resume imported — {resume.contact.name or 'Resume'}")
        self._run_pipeline()

    def _on_resume_import_error(self, message: str) -> None:
        self.pipeline_btn.setEnabled(True)
        QMessageBox.critical(self, "Import failed", message)

    # ── Job description prompt ───────────────────────────────────────────

    def _prompt_job_description(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Job Description")
        dialog.setMinimumWidth(520)
        dialog.setMinimumHeight(400)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setSpacing(10)

        dlg_layout.addWidget(QLabel("Paste the job description text, or enter a URL to fetch it:"))

        url_row = QHBoxLayout()
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("https://linkedin.com/jobs/view/...")
        url_row.addWidget(url_edit, 1)
        fetch_btn = QPushButton("Fetch")
        url_row.addWidget(fetch_btn)
        dlg_layout.addLayout(url_row)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Paste the full job description here...")
        dlg_layout.addWidget(text_edit, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dlg_layout.addWidget(buttons)

        def _fetch():
            url = url_edit.text().strip()
            if not url:
                QMessageBox.warning(dialog, "Missing URL", "Enter a URL first.")
                return
            fetch_btn.setEnabled(False)
            fetch_btn.setText("Fetching...")

            class _FetchThread(QThread):
                done = Signal(object)
                def run(self):
                    from app.services.job_fetcher import fetch_job
                    self.done.emit(fetch_job(url))

            thread = _FetchThread(dialog)
            thread.done.connect(lambda result: _on_fetched(result, thread))
            thread.start()

        def _on_fetched(result, thread):
            fetch_btn.setEnabled(True)
            fetch_btn.setText("Fetch")
            if result.requires_manual_input:
                QMessageBox.information(
                    dialog, "Could not fetch",
                    "Could not fetch the job description. Please paste it manually.",
                )
            else:
                text_edit.setPlainText(result.text)

        fetch_btn.clicked.connect(_fetch)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        text = text_edit.toPlainText().strip()
        if not text:
            return

        state = self.window.state
        title = url_edit.text().strip() or "Job from Pipeline"
        job_id = db.save_job(title, text)
        state.job_text = text
        state.job_title = title
        state.job_id = job_id
        self.window.notify(f"Job description added — {title}")
        self._run_pipeline()

    def _cancel_pipeline(self) -> None:
        if self._pipeline_worker and self._pipeline_worker.isRunning():
            self._pipeline_worker.cancel()
            self._pipeline_worker.wait(3000)
        self._reset_pipeline_ui()
        self.window.notify("Pipeline cancelled.")

    def _reset_pipeline_ui(self) -> None:
        self.pipeline_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.step_label.setVisible(False)
        self.window.state.pipeline_running = False
        self._pipeline_worker = None

    def _on_pipeline_progress(self, step: str, percent: int) -> None:
        self.progress_bar.setValue(percent)
        self.step_label.setText(step)

    def _on_pipeline_done(self, result) -> None:
        state = self.window.state
        state.ats = result.ats_before
        state.optimized = result.optimized
        state.cover_letter_text = result.cover_letter
        state.fact_guard = result.fact_guard
        state.pipeline_result = result
        state.pipeline_running = False

        self._reset_pipeline_ui()

        improvement = result.ats_after_score - result.ats_before.ats_score
        sign = "+" if improvement >= 0 else ""
        self.window.notify(
            f"Pipeline complete in {result.duration_seconds}s | "
            f"ATS: {result.ats_before.ats_score} → {result.ats_after_score} "
            f"({sign}{improvement})"
        )

        # Update score cards
        self.score_value.setText(str(result.ats_after_score))
        self.keyword_value.setText(
            f"{result.ats_before.keyword_match_pct:.0f}%"
        )
        self.skills_value.setText(
            f"{result.ats_before.skills_match_pct:.0f}%"
        )

        # Navigate to the optimization page to show results
        self.window.nav.setCurrentRow(4)

    def _on_pipeline_error(self, message: str) -> None:
        self._reset_pipeline_ui()
        QMessageBox.critical(self, "Pipeline Failed", message)

    # ── Page lifecycle ────────────────────────────────────────────────────

    def on_show(self) -> None:
        rows = db.recent_analyses(10)
        self.table.setRowCount(len(rows))
        keys = (
            "created_at", "resume_name", "job_title",
            "ats_score", "keyword_match", "skills_match",
        )
        for row_idx, row in enumerate(rows):
            for col_idx, key in enumerate(keys):
                self.table.setItem(
                    row_idx, col_idx, QTableWidgetItem(str(row[key]))
                )
        if rows:
            self.score_value.setText(str(rows[0]["ats_score"]))
            self.keyword_value.setText(f"{rows[0]['keyword_match']}%")
            self.skills_value.setText(f"{rows[0]['skills_match']}%")
