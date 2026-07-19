# app/ui/pages/optimization.py

"""Optimization page: AI-powered resume optimization with fact guard review."""

import re
from dataclasses import replace

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import settings_service
from app.ai.ollama_client import OllamaClient
from app.database import db
from app.domain.fact_guard import FactGuardResult, ProposedChange
from app.exports.exporter import export_docx, export_markdown, export_pdf, to_markdown
from app.services.ats_engine import analyze
from app.services.diff_highlight import resume_diff_html
from app.services.document_reader import extract_text
from app.services.job_fetcher import fetch_job
from app.services.optimizer import apply_accepted_changes, optimize_resume
from app.services.resume_parser import parse_resume
from app.ui.components.loading_overlay import LoadingOverlayManager
from app.ui.workers import Worker


class OptimizationPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._worker = None
        self._overlay = LoadingOverlayManager()
        self._change_cards: dict[int, tuple[ProposedChange, QFrame]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Optimization")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.run_btn = QPushButton("Optimize with AI")
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        # ATS Score Comparison
        score_row = QHBoxLayout()
        score_row.setSpacing(24)

        self.before_score_label = QLabel("Original ATS Score: -- / 100")
        self.before_score_label.setObjectName("scoreLabel")
        self.before_score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_row.addWidget(self.before_score_label)

        self.after_score_label = QLabel("Optimized ATS Score: -- / 100")
        self.after_score_label.setObjectName("scoreLabel")
        self.after_score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_row.addWidget(self.after_score_label)

        layout.addLayout(score_row)

        # Fact Guard banner (hidden by default)
        self.fact_banner = QLabel("")
        self.fact_banner.setObjectName("factBanner")
        self.fact_banner.setWordWrap(True)
        self.fact_banner.setVisible(False)
        layout.addWidget(self.fact_banner)

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

        # Fact Guard review panel (hidden by default) — wrapped in a scroll area
        self.review_scroll = QScrollArea()
        self.review_scroll.setWidgetResizable(True)
        self.review_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.review_scroll.setMaximumHeight(350)
        self.review_scroll.setVisible(False)

        self.review_panel = QWidget()
        self.review_panel.setObjectName("reviewPanel")
        self.review_layout = QVBoxLayout(self.review_panel)
        self.review_layout.setContentsMargins(0, 0, 0, 0)
        self.review_layout.setSpacing(8)
        self.review_scroll.setWidget(self.review_panel)
        layout.addWidget(self.review_scroll)

        # Apply button for accepted flagged changes
        self.apply_btn = QPushButton("Apply Accepted Changes")
        self.apply_btn.clicked.connect(self._apply_accepted)
        self.apply_btn.setVisible(False)
        layout.addWidget(self.apply_btn)

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
        if state.optimized is not None and state.resume is not None:
            self.before.setPlainText(to_markdown(state.resume))
            self.after.setHtml(resume_diff_html(state.resume, state.optimized))
            self._update_score_display()
        if state.fact_guard is not None:
            self._show_fact_guard(state.fact_guard)

    def _run(self) -> None:
        state = self.window.state

        # Prompt for resume if not loaded
        if state.resume is None:
            self._prompt_import_resume()
            return

        # Prompt for job description if not loaded
        if not state.job_text.strip():
            self._prompt_job_description()
            return

        # Calculate before score if not already available
        if state.ats is None:
            state.ats = analyze(state.resume, state.job_text)
            state.selected_keywords = list(state.ats.missing_keywords)

        before_score = state.ats.ats_score

        ats_for_optimizer = state.ats
        if state.selected_keywords is not None:
            allowed = set(state.selected_keywords)
            ats_for_optimizer = replace(
                state.ats,
                missing_keywords=[k for k in state.ats.missing_keywords if k in allowed],
            )

        # Update UI with before score
        self.before_score_label.setText(f"Original ATS Score: {before_score} / 100")
        self._style_before_score(before_score)

        self.before.setPlainText(to_markdown(state.resume))
        self.run_btn.setEnabled(False)
        self.fact_banner.setVisible(False)
        self.review_scroll.setVisible(False)
        model = settings_service.model
        self.window.notify(f"Optimizing with {model} - this may take a minute...")
        self._overlay.show(self, f"Optimizing resume with {model}...")
        # Use the current optimized resume as source if re-running after accepting changes
        # so FactGuard doesn't re-flag already-accepted changes
        source_resume = state.optimized if state.optimized is not None else state.resume
        self._worker = Worker(
            optimize_resume, source_resume, state.job_text, ats_for_optimizer, OllamaClient()
        )
        self._worker.result.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # ── Resume import prompt ─────────────────────────────────────────────

    def _prompt_import_resume(self) -> None:
        """Open a file dialog to import a resume, then re-run optimization."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Resume", "", "Documents (*.pdf *.docx *.txt)"
        )
        if not path:
            return

        self._pending_resume_path = path
        self.run_btn.setEnabled(False)
        self._overlay.show(self, "Extracting text from document...")
        self._extract_worker = Worker(extract_text, path)
        self._extract_worker.result.connect(self._on_resume_text_extracted)
        self._extract_worker.error.connect(self._on_resume_import_error)
        self._extract_worker.start()

    def _on_resume_text_extracted(self, text: str) -> None:
        self._overlay.hide(self)
        if not text.strip():
            self.run_btn.setEnabled(True)
            QMessageBox.warning(self, "Empty document", "No text could be extracted from the file.")
            return
        self._raw_text = text
        self._overlay.show(self, "Parsing resume...")
        self._parse_worker = Worker(parse_resume, text)
        self._parse_worker.result.connect(self._on_resume_parsed)
        self._parse_worker.error.connect(self._on_resume_import_error)
        self._parse_worker.start()

    def _on_resume_parsed(self, resume) -> None:
        self._overlay.hide(self)
        self.run_btn.setEnabled(True)
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
        state.ats = None
        self.window.notify(f"Resume imported — {resume.contact.name or 'Resume'}")

        # Continue with optimization
        self._run()

    def _on_resume_import_error(self, message: str) -> None:
        self._overlay.hide(self)
        self.run_btn.setEnabled(True)
        QMessageBox.critical(self, "Import failed", message)

    # ── Job description prompt ───────────────────────────────────────────

    def _prompt_job_description(self) -> None:
        """Open a dialog to paste job description text or a URL."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Job Description")
        dialog.setMinimumWidth(520)
        dialog.setMinimumHeight(400)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setSpacing(10)

        dlg_layout.addWidget(QLabel("Paste the job description text, or enter a URL to fetch it:"))

        # URL row
        url_row = QHBoxLayout()
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("https://linkedin.com/jobs/view/...")
        url_row.addWidget(url_edit, 1)
        fetch_btn = QPushButton("Fetch")
        url_row.addWidget(fetch_btn)
        dlg_layout.addLayout(url_row)

        # Text area
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Paste the full job description here...")
        dlg_layout.addWidget(text_edit, 1)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dlg_layout.addWidget(buttons)

        # Wire up fetch button
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
        title = url_edit.text().strip() or "Job from Optimizer"
        job_id = db.save_job(title, text)
        state.job_text = text
        state.job_title = title
        state.job_id = job_id
        state.ats = None
        self.window.notify(f"Job description added — {title}")

        # Continue with optimization
        self._run()

    def _on_done(self, result) -> None:
        self._overlay.hide(self)
        state = self.window.state

        # Unpack tuple (optimized, fact_guard_result)
        optimized, fact_result = result
        state.optimized = optimized
        state.fact_guard = fact_result

        self.after.setHtml(resume_diff_html(state.resume, optimized))
        self.run_btn.setEnabled(True)

        # Calculate after score
        new_result = analyze(optimized, state.job_text)

        # Only save to database when there are no flagged changes
        if fact_result.flagged_count == 0:
            if state.resume_id is not None and state.job_id is not None:
                db.save_optimization(
                    state.resume_id, state.job_id, settings_service.model, optimized.model_dump_json()
                )

        # Update score display
        old_score = state.ats.ats_score if state.ats else 0
        self.after_score_label.setText(f"Optimized ATS Score: {new_result.ats_score} / 100")
        self._style_after_score(old_score, new_result.ats_score)

        # Show fact guard results
        self._show_fact_guard(fact_result)

        flagged = fact_result.flagged_count
        if flagged:
            self.window.notify(
                f"Optimization complete — {flagged} change(s) require review "
                f"(new numbers, entities, or skills detected). "
                f"Review and accept/reject below, then click 'Apply Accepted Changes'."
            )
        else:
            self.window.notify(
                f"Optimization complete — all changes passed fact guard "
                f"(ATS {new_result.ats_score}/100, was {old_score})."
            )

    def _on_error(self, message: str) -> None:
        self._overlay.hide(self)
        self.run_btn.setEnabled(True)
        QMessageBox.critical(self, "Optimization failed", message)

    # ── Fact Guard UI ─────────────────────────────────────────────────────

    def _show_fact_guard(self, result: FactGuardResult) -> None:
        """Display the fact guard banner and flagged changes panel."""
        flagged = result.flagged_count
        total = len(result.all_changes)

        # Clear old change cards
        self._change_cards.clear()

        if total == 0:
            self.fact_banner.setVisible(False)
            self.review_scroll.setVisible(False)
            self.apply_btn.setVisible(False)
            return

        # Banner
        if flagged:
            warnings = []
            if result.unsupported_numbers:
                warnings.append(f"{len(result.unsupported_numbers)} new number(s)")
            if result.unsupported_entities:
                warnings.append(f"{len(result.unsupported_entities)} new entity/entities")
            if result.unsupported_skills:
                warnings.append(f"{len(result.unsupported_skills)} new skill(s)")

            self.fact_banner.setText(
                f"AI suggestions require review — {flagged}/{total} change(s) "
                f"contain unsupported details: {', '.join(warnings)}. "
                f"Accept or reject each change below, then click 'Apply Accepted Changes'."
            )
            self.fact_banner.setStyleSheet(
                "background-color: rgba(234, 179, 8, 0.15); color: #EAB308; "
                "padding: 10px; border-radius: 6px; font-weight: bold;"
            )
        else:
            self.fact_banner.setText(
                f"All {total} AI change(s) passed fact guard — no unsupported "
                f"numbers, entities, or skills detected."
            )
            self.fact_banner.setStyleSheet(
                "background-color: rgba(34, 197, 94, 0.15); color: #22C55E; "
                "padding: 10px; border-radius: 6px; font-weight: bold;"
            )
        self.fact_banner.setVisible(True)

        # Review panel — every proposal is a user decision. Fact safety is
        # metadata and never acts as approval.
        # Clear old content
        while self.review_layout.count():
            child = self.review_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        header = QLabel("Proposed Changes — Accept or Reject Each:")
        header.setObjectName("reviewHeader")
        self.review_layout.addWidget(header)

        for idx, change in enumerate(result.all_changes):
            self._add_change_card(idx, change)

        self.review_scroll.setVisible(True)
        self.apply_btn.setVisible(True)

    def _add_change_card(self, idx: int, change: ProposedChange) -> None:
        """Add a single change card to the review panel with Accept/Reject."""
        card = QFrame()
        card.setObjectName("changeCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(4)

        # Section + type label
        type_labels = {"summary": "Summary", "headline": "Headline", "bullet": "Bullet"}
        badges = []
        if change.has_new_numbers:
            badges.append("NEW NUMBERS")
        if change.has_new_entities:
            badges.append("NEW ENTITIES")
        if change.has_new_skills:
            badges.append("NEW SKILLS")

        header_row = QHBoxLayout()
        section_label = QLabel(f"{type_labels.get(change.change_type, '?')} — {change.section}")
        section_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_row.addWidget(section_label)

        for badge in badges:
            badge_label = QLabel(badge)
            badge_label.setStyleSheet(
                "background-color: #EF4444; color: white; padding: 2px 6px; "
                "border-radius: 4px; font-size: 10px; font-weight: bold;"
            )
            header_row.addWidget(badge_label)

        header_row.addStretch()
        card_layout.addLayout(header_row)

        # Original text
        orig_text = change.original[:200] if change.original else "(new content)"
        orig_label = QLabel(f"Original: {orig_text}")
        orig_label.setWordWrap(True)
        orig_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        card_layout.addWidget(orig_label)

        # Rewritten text
        rewrite_label = QLabel(f"AI wrote: {change.rewritten[:200]}")
        rewrite_label.setWordWrap(True)
        rewrite_label.setStyleSheet("color: #F59E0B; font-size: 12px;")
        card_layout.addWidget(rewrite_label)

        # Accept / Reject buttons
        btn_row = QHBoxLayout()
        accept_btn = QPushButton("Accept")
        reject_btn = QPushButton("Reject")
        status_label = QLabel("Pending review")
        status_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")

        if change.accepted is True:
            status_label.setText("Accepted")
            status_label.setStyleSheet(
                "color: #22C55E; font-size: 11px; font-weight: bold;"
            )
        elif change.accepted is False:
            status_label.setText("Rejected")
            status_label.setStyleSheet(
                "color: #EF4444; font-size: 11px; font-weight: bold;"
            )

        def _on_accept(_checked: bool = False, proposal=change, sl=status_label):
            proposal.accepted = True
            sl.setText("Accepted")
            sl.setStyleSheet("color: #22C55E; font-size: 11px; font-weight: bold;")

        def _on_reject(_checked: bool = False, proposal=change, sl=status_label):
            proposal.accepted = False
            sl.setText("Rejected")
            sl.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold;")

        accept_btn.clicked.connect(_on_accept)
        reject_btn.clicked.connect(_on_reject)
        btn_row.addWidget(accept_btn)
        btn_row.addWidget(reject_btn)
        btn_row.addWidget(status_label)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        self._change_cards[idx] = (change, card)
        self.review_layout.addWidget(card)

    def _apply_accepted(self) -> None:
        """Collect accepted keywords and re-run optimization with them."""
        state = self.window.state
        if state.fact_guard is None or state.resume is None:
            return

        if not state.fact_guard.review_complete:
            QMessageBox.warning(
                self,
                "Changes pending",
                "Please accept or reject every proposed change before applying.",
            )
            return

        accepted_count = state.fact_guard.accepted_count
        state.optimized = apply_accepted_changes(state.resume, state.fact_guard)
        self.after.setHtml(resume_diff_html(state.resume, state.optimized))
        self._update_score_display()

        # Clear fact guard state before re-running
        state.fact_guard = None
        self.review_scroll.setVisible(False)
        self.apply_btn.setVisible(False)
        self.fact_banner.setVisible(False)

        self.window.notify(f"Applied {accepted_count} accepted change(s).")

    # ── Score styling ──────────────────────────────────────────────────────

    def _update_score_display(self) -> None:
        """Update score labels when page is shown with existing optimization."""
        state = self.window.state
        if state.ats is not None:
            self.before_score_label.setText(f"Original ATS Score: {state.ats.ats_score} / 100")
            self._style_before_score(state.ats.ats_score)

        if state.optimized is not None and state.ats is not None:
            after_result = analyze(state.optimized, state.job_text)
            self.after_score_label.setText(f"Optimized ATS Score: {after_result.ats_score} / 100")
            self._style_after_score(state.ats.ats_score, after_result.ats_score)

    def _style_before_score(self, score: int) -> None:
        if score >= 80:
            color = "#22C55E"
        elif score >= 60:
            color = "#EAB308"
        else:
            color = "#EF4444"

        self.before_score_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {color}; padding: 8px; "
            f"background-color: rgba({self._hex_to_rgb(color)}, 0.1); border-radius: 6px;"
        )

    def _style_after_score(self, before: int, after: int) -> None:
        if after > before:
            color = "#22C55E"
            improvement = after - before
            text = f"Optimized ATS Score: {after} / 100 (+{improvement})"
        elif after < before:
            color = "#EF4444"
            change = before - after
            text = f"Optimized ATS Score: {after} / 100 (-{change})"
        else:
            color = "#EAB308"
            text = f"Optimized ATS Score: {after} / 100 (no change)"

        self.after_score_label.setText(text)
        self.after_score_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {color}; padding: 8px; "
            f"background-color: rgba({self._hex_to_rgb(color)}, 0.1); border-radius: 6px;"
        )

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"

    @staticmethod
    def _clean_filename_part(text: str) -> str:
        """Return an underscore-safe filename fragment."""
        tokens = re.findall(r"[A-Za-z0-9]+", text or "")
        return "_".join(tokens)

    def _default_filename(self, fmt: str) -> str:
        """Use the targeted-resume naming convention shown in the template."""
        state = self.window.state
        resume = state.optimized or state.resume

        name = resume.contact.name if resume is not None else "Resume"
        name_tokens = re.findall(r"[A-Za-z0-9]+", name)
        candidate = "_".join(name_tokens[:2]) or "Resume"

        headline_role = ""
        if resume is not None and resume.headline.strip():
            headline_role = resume.headline.split("|", 1)[0].strip()
        role = headline_role or state.job_title.strip() or "Resume"
        role_fragment = self._clean_filename_part(role) or "Resume"
        return f"{candidate}_Targeted_{role_fragment}.{fmt}"

    def _export(self, fmt: str) -> None:
        state = self.window.state
        resume = state.optimized or state.resume
        if resume is None:
            QMessageBox.warning(self, "Nothing to export", "Import or optimize a resume first.")
            return

        # Warn if there are still pending flagged changes
        if state.fact_guard and state.fact_guard.flagged_count > 0:
            pending = sum(
                1 for c in state.fact_guard.flagged_changes
                if not c.accepted and (c.has_new_numbers or c.has_new_entities or c.has_new_skills)
            )
            if pending > 0:
                reply = QMessageBox.question(
                    self,
                    "Pending review",
                    f"There are {pending} flagged change(s) that haven't been reviewed yet. "
                    f"Exporting now will only include safe changes. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
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
