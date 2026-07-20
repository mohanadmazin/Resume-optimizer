# app/ui/pages/ats_analysis.py

"""ATS Analysis page with keyword heatmap visualization."""

import re
import threading

from PySide6.QtCore import Qt, QMetaObject
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import db
from app.schemas import ResumeData
from app.services.ats_engine import analyze


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


def _highlight_keywords(text: str, matched: list[str], missing: list[str]) -> str:
    """Convert text to HTML with highlighted keywords.

    Uses a token-based approach to avoid matching inside HTML tags or
    previously generated highlight spans.
    """
    # First escape HTML entities in the original text
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = escaped.split("\n")

    # Build a combined regex for all keywords (matched + missing) — longest first
    # to avoid partial matches
    all_keywords = sorted(set(matched + missing), key=len, reverse=True)
    if not all_keywords:
        return f"<div style='font-family: Segoe UI; font-size: 13px; line-height: 1.6;'>{'<br>'.join(lines)}</div>"

    # Create keyword lookup sets for fast membership testing
    matched_set = {k.lower() for k in matched}
    missing_set = {k.lower() for k in missing}

    # Tokenize each line and highlight matched tokens
    result_lines = []
    for line in lines:
        # Split on word boundaries while preserving the delimiters
        tokens = re.split(r'(\b\w+\b)', line)
        highlighted_parts = []
        for token in tokens:
            lower = token.lower()
            if lower in matched_set:
                highlighted_parts.append(
                    f'<span style="background-color: #22C55E; color: white; '
                    f'font-weight: bold; padding: 2px 4px; border-radius: 3px;">{token}</span>'
                )
            elif lower in missing_set:
                highlighted_parts.append(
                    f'<span style="background-color: #EF4444; color: white; '
                    f'font-weight: bold; padding: 2px 4px; border-radius: 3px;">{token}</span>'
                )
            else:
                highlighted_parts.append(token)
        result_lines.append("".join(highlighted_parts))

    return f"<div style='font-family: Segoe UI; font-size: 13px; line-height: 1.6;'>{'<br>'.join(result_lines)}</div>"


class ATSAnalysisPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("ATS Analysis")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        run_btn = QPushButton("Run ATS Analysis")
        run_btn.clicked.connect(self._run)
        layout.addWidget(run_btn)

        # Score cards
        cards = QHBoxLayout()

        card1, self.score_value = _card("ATS Score")
        card2, self.keyword_value = _card("Keyword Match")
        card3, self.skills_value = _card("Skills Match")

        for card in (card1, card2, card3):
            cards.addWidget(card)

        layout.addLayout(cards)

        # Main columns
        columns = QHBoxLayout()

        # Keywords side
        left = QVBoxLayout()

        left.addWidget(QLabel("Missing keywords:"))

        self.select_all_checkbox = QCheckBox(
            "Select / Unselect All ATS Words"
        )
        self.select_all_checkbox.stateChanged.connect(
            self._toggle_all_keywords
        )

        left.addWidget(self.select_all_checkbox)

        self.keywords_list = QListWidget()
        self.keywords_list.itemChanged.connect(
            self._update_select_all_checkbox
        )
        self.keywords_list.itemChanged.connect(
            lambda _: self._sync_selected_keywords()
        )

        left.addWidget(self.keywords_list)

        # Suggestions side
        right = QVBoxLayout()

        right.addWidget(QLabel("Improvement suggestions:"))

        self.suggestions = QTextEdit()
        self.suggestions.setReadOnly(True)

        right.addWidget(self.suggestions)

        columns.addLayout(left, 1)
        columns.addLayout(right, 1)

        layout.addLayout(columns, 1)

        # Keyword Heatmap section
        heatmap_label = QLabel("Keyword Heatmap (Green = Matched, Red = Missing)")
        heatmap_label.setStyleSheet("font-weight: bold; margin-top: 12px;")
        layout.addWidget(heatmap_label)

        heatmap_columns = QHBoxLayout()

        # Resume side
        resume_col = QVBoxLayout()
        resume_col.addWidget(QLabel("Your Resume:"))
        self.resume_heatmap = QTextEdit()
        self.resume_heatmap.setReadOnly(True)
        resume_col.addWidget(self.resume_heatmap)
        heatmap_columns.addLayout(resume_col, 1)

        # Job description side
        jd_col = QVBoxLayout()
        jd_col.addWidget(QLabel("Job Description:"))
        self.jd_heatmap = QTextEdit()
        self.jd_heatmap.setReadOnly(True)
        jd_col.addWidget(self.jd_heatmap)
        heatmap_columns.addLayout(jd_col, 1)

        layout.addLayout(heatmap_columns, 1)

        # ── Requirement Matrix section ─────────────────────────────
        matrix_group = QFrame()
        matrix_group.setObjectName("card")
        matrix_layout = QVBoxLayout(matrix_group)

        matrix_header = QHBoxLayout()
        matrix_header.addWidget(QLabel("REQUIREMENT EVIDENCE MATRIX"))
        matrix_header.addStretch()
        self._matrix_build_btn = QPushButton("Build Matrix")
        self._matrix_build_btn.clicked.connect(self._on_build_matrix)
        matrix_header.addWidget(self._matrix_build_btn)
        matrix_layout.addLayout(matrix_header)

        self._matrix_score_label = QLabel("Coverage: —")
        self._matrix_score_label.setStyleSheet("font-size: 13px; margin: 4px 0;")
        matrix_layout.addWidget(self._matrix_score_label)

        matrix_cols = QHBoxLayout()

        gaps_col = QVBoxLayout()
        gaps_col.addWidget(QLabel("Gaps:"))
        self._matrix_gaps = QTextEdit()
        self._matrix_gaps.setReadOnly(True)
        self._matrix_gaps.setMaximumHeight(100)
        gaps_col.addWidget(self._matrix_gaps)
        matrix_cols.addLayout(gaps_col, 1)

        strengths_col = QVBoxLayout()
        strengths_col.addWidget(QLabel("Strengths:"))
        self._matrix_strengths = QTextEdit()
        self._matrix_strengths.setReadOnly(True)
        self._matrix_strengths.setMaximumHeight(100)
        strengths_col.addWidget(self._matrix_strengths)
        matrix_cols.addLayout(strengths_col, 1)

        matrix_layout.addLayout(matrix_cols)
        layout.addWidget(matrix_group)

    def _update_select_all_checkbox(self):
        if self.keywords_list.count() == 0:
            return

        all_checked = all(
            self.keywords_list.item(i).checkState()
            == Qt.CheckState.Checked
            for i in range(self.keywords_list.count())
        )

        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(all_checked)
        self.select_all_checkbox.blockSignals(False)

    def _toggle_all_keywords(self, state):
        checked = (
            state == Qt.CheckState.Checked.value
        )

        self.keywords_list.blockSignals(True)

        for i in range(self.keywords_list.count()):
            item = self.keywords_list.item(i)

            item.setCheckState(
                Qt.CheckState.Checked
                if checked
                else Qt.CheckState.Unchecked
            )

        self.keywords_list.blockSignals(False)
        self._sync_selected_keywords()

    def _sync_selected_keywords(self) -> None:
        """Synchronize checked keyword items with application state."""
        state = self.window.state
        selected = []
        for i in range(self.keywords_list.count()):
            item = self.keywords_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        state.selected_keywords = selected

    def _load_fallbacks(self) -> None:
        state = self.window.state

        if state.resume is None:
            row = db.latest_resume()

            if row:
                state.resume = ResumeData.model_validate_json(
                    row["data_json"]
                )
                state.resume_id = row["id"]

        if not state.job_text:
            row = db.latest_job()

            if row:
                state.job_text = row["content"]
                state.job_title = row["title"]
                state.job_id = row["id"]

    def on_show(self):
        """Load resume and job when page is shown."""
        self._load_fallbacks()
        self._update_heatmaps()

    def _run(self) -> None:
        self.run_analysis()

    def run_analysis(self, silent: bool = False) -> None:
        """Run ATS analysis — can be called internally or from another page."""
        state = self.window.state

        self._load_fallbacks()

        if state.resume is None or not state.job_text.strip():
            if not silent:
                QMessageBox.warning(
                    self,
                    "Missing input",
                    "Import a resume and add a job description first."
                )
            return

        result = analyze(
            state.resume,
            state.job_text
        )

        state.ats = result

        # Update scores
        self.score_value.setText(
            str(result.ats_score)
        )

        self.keyword_value.setText(
            f"{result.keyword_match_pct}%"
        )

        self.skills_value.setText(
            f"{result.skills_match_pct}%"
        )

        # Load keywords
        self.keywords_list.blockSignals(True)

        self.keywords_list.clear()

        for keyword in result.missing_keywords:

            item = QListWidgetItem(keyword)

            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
            )

            # Default selected
            item.setCheckState(
                Qt.CheckState.Checked
            )

            self.keywords_list.addItem(item)

        self.keywords_list.blockSignals(False)

        # Sync checked keywords to state
        self._sync_selected_keywords()

        # Master checkbox selected
        self.select_all_checkbox.blockSignals(True)

        self.select_all_checkbox.setChecked(True)

        self.select_all_checkbox.blockSignals(False)

        # Show suggestions
        self.suggestions.clear()

        if result.suggestions:

            self.suggestions.setPlainText(
                "\n".join(
                    f"• {s}"
                    for s in result.suggestions
                )
            )

        else:

            self.suggestions.setPlainText(
                "No improvement suggestions available."
            )

        # Update keyword heatmaps
        self._update_heatmaps()

        # Save analysis
        if state.resume_id is None:

            state.resume_id = db.save_resume(
                state.resume.contact.name
                or "Resume",

                state.resume.model_dump_json(),

                state.resume.raw_text,
            )

        if state.job_id is None:

            state.job_id = db.save_job(
                state.job_title
                or "Untitled Job",

                state.job_text,
            )

        db.save_analysis(
            state.resume_id,
            state.job_id,
            result.to_dict()
        )

        self.window.notify(
            f"ATS analysis complete - score {result.ats_score}/100."
        )

    def _update_heatmaps(self) -> None:
        """Update the keyword heatmap displays with current analysis results."""
        state = self.window.state
        if state.ats is None or not state.resume or not state.job_text:
            self.resume_heatmap.clear()
            self.jd_heatmap.clear()
            return

        matched = state.ats.matched_keywords
        missing = state.ats.missing_keywords

        # Resume heatmap
        from app.exports.exporter import to_markdown
        resume_text = to_markdown(state.resume)
        self.resume_heatmap.setHtml(
            _highlight_keywords(resume_text, matched, missing)
        )

        # Job description heatmap
        self.jd_heatmap.setHtml(
            _highlight_keywords(state.job_text, matched, missing)
        )

    # ── Requirement Matrix ──────────────────────────────────────────

    def _on_build_matrix(self) -> None:
        """Build the requirement matrix in background."""
        state = self.window.state
        if not state.job_text.strip():
            QMessageBox.warning(self, "No Job", "Add a job description first.")
            return

        self._matrix_build_btn.setEnabled(False)
        self._matrix_build_btn.setText("Building…")
        thread = threading.Thread(target=self._build_matrix_worker, daemon=True)
        thread.start()

    def _build_matrix_worker(self) -> None:
        try:
            from app.domain.evidence import CareerFact
            from app.domain.job_requirements import JobRequirements, Requirement
            from app.services.evidence_vault import EvidenceVault
            from app.services.requirement_matrix import build_matrix

            state = self.window.state
            words = [w.strip() for w in state.job_text.split() if len(w.strip()) >= 3][:30]
            job_req = JobRequirements(
                required_skills=[Requirement(name=w) for w in words],
            )

            vault = EvidenceVault()
            facts = vault.list_facts()
            career_facts = [
                f if isinstance(f, CareerFact) else CareerFact(**f)
                for f in facts
            ]

            matrix = build_matrix(job_req, career_facts)
            self._update_matrix_ui(matrix)
        except Exception:
            self._finish_matrix_build("Matrix build failed")

        self._finish_matrix_build("")

    def _update_matrix_ui(self, matrix) -> None:
        def _update():
            self._matrix_score_label.setText(
                f"Coverage: {matrix.overall_score:.0%} "
                f"({matrix.covered_count}/{matrix.total_requirements} covered, "
                f"{matrix.gap_count} gaps)"
            )
            self._matrix_gaps.setPlainText(
                "\n".join(f"• {g}" for g in matrix.gaps) or "No gaps found"
            )
            self._matrix_strengths.setPlainText(
                "\n".join(f"• {s}" for s in matrix.strengths) or "No strengths identified"
            )
        QMetaObject.invokeMethod(self, _update, Qt.QueuedConnection)

    def _finish_matrix_build(self, error: str) -> None:
        def _update():
            self._matrix_build_btn.setEnabled(True)
            self._matrix_build_btn.setText("Build Matrix")
            if error:
                QMessageBox.warning(self, "Matrix Build Failed", error)
        QMetaObject.invokeMethod(self, _update, Qt.QueuedConnection)
