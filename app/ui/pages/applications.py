"""Applications page — track job application status."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
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

from app.database.repositories.application_repository import (
    ApplicationRepository,
    VALID_STATUSES,
)
from app.database.session import get_session

logger = logging.getLogger(__name__)


class _ApplicationDialog(QDialog):
    """Dialog for adding/editing an application."""

    def __init__(self, parent=None, resume_id=0, job_id=0, notes="", status="draft"):
        super().__init__(parent)
        self.setWindowTitle("Application Details")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Status:"))
        self._status_combo = QComboBox()
        self._status_combo.addItems(list(VALID_STATUSES))
        self._status_combo.setCurrentText(status)
        layout.addWidget(self._status_combo)

        layout.addWidget(QLabel("Notes:"))
        self._notes = QTextEdit()
        self._notes.setPlainText(notes)
        self._notes.setMaximumHeight(120)
        layout.addWidget(self._notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, str]:
        return self._status_combo.currentText(), self._notes.toPlainText()


class ApplicationsPage(QWidget):
    """Job application tracker with status workflow."""

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Application Tracker")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel("Track your job applications through the hiring pipeline.")
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Application")
        self._add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(self._add_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        stats_row = QHBoxLayout()
        self._stat_total = self._stat_card("Total", "0")
        self._stat_applied = self._stat_card("Applied", "0")
        self._stat_interview = self._stat_card("Interviews", "0")
        self._stat_offers = self._stat_card("Offers", "0")
        self._stat_rejected = self._stat_card("Rejected", "0")
        stats_row.addWidget(self._stat_total)
        stats_row.addWidget(self._stat_applied)
        stats_row.addWidget(self._stat_interview)
        stats_row.addWidget(self._stat_offers)
        stats_row.addWidget(self._stat_rejected)
        layout.addLayout(stats_row)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Resume", "Job", "Status", "Applied", "Notes"]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self._table, stretch=1)

        action_row = QHBoxLayout()
        self._status_btn = QPushButton("Advance Status")
        self._status_btn.clicked.connect(self._on_advance)
        action_row.addWidget(self._status_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete)
        action_row.addWidget(self._delete_btn)

        action_row.addStretch()
        layout.addLayout(action_row)

        self._applications: list = []

    def on_show(self) -> None:
        self._refresh()

    def _stat_card(self, label: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        val_label = QLabel(value)
        val_label.setObjectName("scoreValue")
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(label.upper())
        lbl.setStyleSheet("font-size: 10px; color: #6B7280; font-weight: bold;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(val_label)
        layout.addWidget(lbl)
        return frame

    def _refresh(self) -> None:
        try:
            with get_session() as session:
                repo = ApplicationRepository(session)
                self._applications = repo.list_all()
        except Exception:
            logger.exception("Failed to load applications")
            self._applications = []

        self._table.setRowCount(len(self._applications))
        for i, app in enumerate(self._applications):
            self._table.setItem(i, 0, QTableWidgetItem(str(app.id)))
            self._table.setItem(i, 1, QTableWidgetItem(f"Resume #{app.resume_id}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"Job #{app.job_id}"))
            self._table.setItem(i, 3, QTableWidgetItem(app.status))
            applied = app.applied_at.strftime("%Y-%m-%d") if app.applied_at else "-"
            self._table.setItem(i, 4, QTableWidgetItem(applied))
            self._table.setItem(i, 5, QTableWidgetItem(app.notes[:80] if app.notes else ""))

        from app.database.repositories.application_repository import VALID_STATUSES
        counts = {s: 0 for s in VALID_STATUSES}
        for app in self._applications:
            if app.status in counts:
                counts[app.status] += 1

        def _update_stat(card: QFrame, value: str) -> None:
            val_label = card.findChild(QLabel)
            if val_label:
                val_label.setText(value)

        _update_stat(self._stat_total, str(len(self._applications)))
        _update_stat(self._stat_applied, str(counts.get("applied", 0)))
        _update_stat(self._stat_interview, str(counts.get("interview", 0)))
        _update_stat(self._stat_offers, str(counts.get("offer", 0)))
        _update_stat(self._stat_rejected, str(counts.get("rejected", 0)))

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        return int(self._table.item(row, 0).text())

    def _on_add(self) -> None:
        resume_id = self.window.state.resume_id or 0
        job_id = self.window.state.job_id or 0
        dlg = _ApplicationDialog(self, resume_id=resume_id, job_id=job_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            status, notes = dlg.get_data()
            try:
                with get_session() as session:
                    repo = ApplicationRepository(session)
                    repo.create(resume_id, job_id, status=status, notes=notes)
                self._refresh()
            except Exception:
                logger.exception("Failed to create application")

    def _on_edit(self) -> None:
        app_id = self._selected_id()
        if app_id is None:
            return
        app = next((a for a in self._applications if a.id == app_id), None)
        if app is None:
            return
        dlg = _ApplicationDialog(
            self,
            resume_id=app.resume_id,
            job_id=app.job_id,
            notes=app.notes or "",
            status=app.status,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            status, notes = dlg.get_data()
            try:
                with get_session() as session:
                    repo = ApplicationRepository(session)
                    repo.update_status(app_id, status)
                    repo.update_notes(app_id, notes)
                self._refresh()
            except Exception:
                logger.exception("Failed to update application")

    def _on_advance(self) -> None:
        app_id = self._selected_id()
        if app_id is None:
            return
        app = next((a for a in self._applications if a.id == app_id), None)
        if app is None:
            return
        idx = VALID_STATUSES.index(app.status) if app.status in VALID_STATUSES else 0
        if idx < len(VALID_STATUSES) - 1:
            next_status = VALID_STATUSES[idx + 1]
            try:
                with get_session() as session:
                    repo = ApplicationRepository(session)
                    repo.update_status(app_id, next_status)
                self._refresh()
            except Exception:
                logger.exception("Failed to advance status")

    def _on_delete(self) -> None:
        app_id = self._selected_id()
        if app_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete Application",
            "Are you sure you want to delete this application?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with get_session() as session:
                    repo = ApplicationRepository(session)
                    repo.delete(app_id)
                self._refresh()
            except Exception:
                logger.exception("Failed to delete application")
