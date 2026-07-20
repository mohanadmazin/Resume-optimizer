"""Requirement Matrix page — interactive requirement-evidence mapping."""
from __future__ import annotations

import logging
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.requirement_matrix import (
    CoverageLevel,
    MatrixExportFormat,
    RequirementMatrix,
)

logger = logging.getLogger(__name__)

_COVERAGE_COLORS: dict[CoverageLevel, str] = {
    CoverageLevel.DIRECT_EVIDENCE: "#d4edda",
    CoverageLevel.RELATED_EVIDENCE: "#fff3cd",
    CoverageLevel.KEYWORD_ONLY: "#ffeeba",
    CoverageLevel.USER_CONFIRMED: "#cce5ff",
    CoverageLevel.MISSING: "#f8d7da",
    CoverageLevel.CONTRADICTORY: "#f5c6cb",
    CoverageLevel.UNKNOWN: "#e2e3e5",
}

_COVERAGE_LABELS: dict[CoverageLevel, str] = {
    CoverageLevel.DIRECT_EVIDENCE: "Direct",
    CoverageLevel.RELATED_EVIDENCE: "Related",
    CoverageLevel.KEYWORD_ONLY: "Keyword",
    CoverageLevel.USER_CONFIRMED: "Confirmed",
    CoverageLevel.MISSING: "Missing",
    CoverageLevel.CONTRADICTORY: "Contradictory",
    CoverageLevel.UNKNOWN: "Unknown",
}


class RequirementMatrixPage(QWidget):
    """Interactive matrix view: job requirements mapped to vault evidence."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._matrix: RequirementMatrix | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel("Requirement Evidence Matrix")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(header)

        # Job selector row
        job_row = QHBoxLayout()
        job_row.addWidget(QLabel("Job:"))
        self._job_combo = QComboBox()
        self._job_combo.setMinimumWidth(250)
        job_row.addWidget(self._job_combo)

        job_row.addWidget(QLabel("Filter:"))
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All", "Gaps Only", "Covered Only"])
        job_row.addWidget(self._filter_combo)

        job_row.addStretch()

        self._build_btn = QPushButton("Build Matrix")
        self._build_btn.clicked.connect(self._on_build)
        job_row.addWidget(self._build_btn)

        self._export_md_btn = QPushButton("Export Markdown")
        self._export_md_btn.clicked.connect(lambda: self._on_export(MatrixExportFormat.MARKDOWN))
        job_row.addWidget(self._export_md_btn)

        self._export_csv_btn = QPushButton("Export CSV")
        self._export_csv_btn.clicked.connect(lambda: self._on_export(MatrixExportFormat.CSV))
        job_row.addWidget(self._export_csv_btn)

        layout.addLayout(job_row)

        # Score bar
        self._score_label = QLabel("Overall coverage: —")
        self._score_label.setStyleSheet("font-size: 14px; margin: 4px 0;")
        layout.addWidget(self._score_label)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Requirement", "Type", "Importance", "Coverage",
            "Evidence #", "Score", "Action Needed",
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self._table)

        # Evidence detail panel
        detail_group = QGroupBox("Evidence Detail")
        detail_layout = QVBoxLayout(detail_group)
        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setMaximumHeight(120)
        detail_layout.addWidget(self._detail_text)
        layout.addWidget(detail_group)

        self._filter_combo.currentIndexChanged.connect(self._apply_filter)

    def refresh(self) -> None:
        """Reload job list."""
        self._job_combo.clear()
        try:
            from app.database.repositories.job_repository import JobRepository
            repo = JobRepository()
            jobs = repo.get_all()
            for job in jobs:
                title = job.get("title", "") if isinstance(job, dict) else getattr(job, "title", "")
                jid = job.get("id", 0) if isinstance(job, dict) else getattr(job, "id", 0)
                self._job_combo.addItem(title, jid)
        except Exception:
            logger.debug("No jobs available")

    def _on_build(self) -> None:
        """Build the matrix in a background thread."""
        idx = self._job_combo.currentIndex()
        if idx < 0:
            QMessageBox.information(self, "No Job", "Select a job description first.")
            return

        job_id = self._job_combo.currentData()

        self._build_btn.setEnabled(False)
        self._build_btn.setText("Building…")

        thread = threading.Thread(
            target=self._build_worker, args=(job_id,), daemon=True
        )
        thread.start()

    def _build_worker(self, job_id: int) -> None:
        try:
            from app.database.repositories.job_repository import JobRepository
            from app.domain.evidence import CareerFact
            from app.domain.job_requirements import JobRequirements
            from app.services.evidence_vault import EvidenceVault
            from app.services.requirement_matrix import build_matrix

            job_repo = JobRepository()
            orm_job = job_repo.get_by_id(job_id)
            if orm_job is None:
                self._finish_build("Job not found")
                return

            # Parse job requirements from raw_text or title
            job_text = getattr(orm_job, "raw_text", "") or getattr(orm_job, "title", "")
            words = [w.strip() for w in job_text.split() if len(w.strip()) >= 3][:30]
            job_req = JobRequirements(
                required_skills=[
                    __import__(
                        "app.domain.job_requirements", fromlist=["Requirement"]
                    ).Requirement(name=w)
                    for w in words
                ],
            )

            vault = EvidenceVault()
            facts = vault.list_facts()
            career_facts: list[CareerFact] = []
            for f in facts:
                if isinstance(f, CareerFact):
                    career_facts.append(f)
                elif isinstance(f, dict):
                    career_facts.append(CareerFact(**f))

            matrix = build_matrix(job_req, career_facts)
            self._matrix = matrix
            self._apply_filter()
            self._update_score()
        except Exception as exc:
            logger.exception("Matrix build failed")
            self._finish_build(str(exc))

        self._finish_build("")

    def _finish_build(self, error: str) -> None:
        from PySide6.QtCore import QMetaObject, Qt as QtEnum

        def _update():
            self._build_btn.setEnabled(True)
            self._build_btn.setText("Build Matrix")
            if error:
                QMessageBox.warning(self, "Build Failed", error)

        QMetaObject.invokeMethod(self, _update, QtEnum.QueuedConnection)

    def _apply_filter(self) -> None:
        if self._matrix is None:
            return
        filter_text = self._filter_combo.currentText()
        items = self._matrix.requirements
        if filter_text == "Gaps Only":
            items = [r for r in items if r.coverage in (CoverageLevel.MISSING, CoverageLevel.UNKNOWN)]
        elif filter_text == "Covered Only":
            items = [r for r in items if r.coverage in (
                CoverageLevel.DIRECT_EVIDENCE, CoverageLevel.RELATED_EVIDENCE,
                CoverageLevel.USER_CONFIRMED,
            )]
        self._populate_table(items)

    def _populate_table(self, items) -> None:
        self._table.setRowCount(len(items))
        for row, item in enumerate(items):
            self._table.setItem(row, 0, QTableWidgetItem(item.text[:80]))
            self._table.setItem(row, 1, QTableWidgetItem(item.requirement_type.value))
            self._table.setItem(row, 2, QTableWidgetItem(f"{item.importance:.0%}"))

            cov_item = QTableWidgetItem(_COVERAGE_LABELS.get(item.coverage, "?"))
            bg = _COVERAGE_COLORS.get(item.coverage, "#ffffff")
            cov_item.setBackground(Qt.GlobalColor.white)
            cov_item.setData(Qt.ItemDataRole.BackgroundRole, bg)
            self._table.setItem(row, 3, cov_item)

            self._table.setItem(row, 4, QTableWidgetItem(str(len(item.evidence_fact_ids))))
            self._table.setItem(row, 5, QTableWidgetItem(f"{item.coverage_score:.2f}"))
            self._table.setItem(row, 6, QTableWidgetItem(item.action_needed[:60]))

    def _update_score(self) -> None:
        if self._matrix is None:
            return
        m = self._matrix
        self._score_label.setText(
            f"Overall coverage: {m.overall_score:.0%}  "
            f"({m.covered_count}/{m.total_requirements} covered, {m.gap_count} gaps)"
        )

    def _on_row_clicked(self, row: int, _col: int) -> None:
        if self._matrix is None:
            return
        filter_text = self._filter_combo.currentText()
        items = self._matrix.requirements
        if filter_text == "Gaps Only":
            items = [r for r in items if r.coverage in (CoverageLevel.MISSING, CoverageLevel.UNKNOWN)]
        elif filter_text == "Covered Only":
            items = [r for r in items if r.coverage in (
                CoverageLevel.DIRECT_EVIDENCE, CoverageLevel.RELATED_EVIDENCE,
                CoverageLevel.USER_CONFIRMED,
            )]
        if row < len(items):
            item = items[row]
            lines = [
                f"Requirement: {item.text}",
                f"Type: {item.requirement_type.value}",
                f"Coverage: {_COVERAGE_LABELS.get(item.coverage, '?')}",
                f"Evidence IDs: {item.evidence_fact_ids or 'none'}",
                "",
                "Matched evidence:",
            ]
            for txt in item.candidate_evidence_text:
                lines.append(f"  - {txt}")
            if item.action_needed:
                lines.append(f"\nAction: {item.action_needed}")
            self._detail_text.setPlainText("\n".join(lines))

    def _on_export(self, fmt: MatrixExportFormat) -> None:
        if self._matrix is None:
            QMessageBox.information(self, "No Matrix", "Build a matrix first.")
            return
        from app.services.requirement_matrix import export_matrix
        text = export_matrix(self._matrix, fmt)
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(text)
        QMessageBox.information(
            self, "Exported",
            f"{fmt.value.upper()} copied to clipboard.\n\n{text[:500]}",
        )
