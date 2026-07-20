"""Cover Letter Library page — browse, search, and reuse saved cover letters."""
from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import db
from app.database.repositories.cover_letter_repository import CoverLetterRepository

logger = logging.getLogger(__name__)


class CoverLetterLibraryPage(QWidget):
    """Library for browsing and managing saved cover letters."""

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Cover Letter Library")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel("Browse, search, and reuse previously generated cover letters.")
        layout.addWidget(desc)

        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search by content...")
        self._search_input.returnPressed.connect(self._on_search)
        search_row.addWidget(self._search_input)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._on_search)
        search_row.addWidget(search_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._on_clear_search)
        search_row.addWidget(clear_btn)
        layout.addLayout(search_row)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Resume", "Job", "Created", "Preview"]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._on_view)
        layout.addWidget(self._table, stretch=1)

        action_row = QHBoxLayout()
        self._view_btn = QPushButton("View Full")
        self._view_btn.clicked.connect(self._on_view)
        action_row.addWidget(self._view_btn)

        self._copy_btn = QPushButton("Copy to Clipboard")
        self._copy_btn.clicked.connect(self._on_copy)
        action_row.addWidget(self._copy_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete)
        action_row.addWidget(self._delete_btn)

        action_row.addStretch()
        layout.addLayout(action_row)

        self._letters: list = []

    def on_show(self) -> None:
        self._refresh()

    def _refresh(self, letters: list | None = None) -> None:
        if letters is None:
            try:
                with db.session_scope() as session:
                    repo = CoverLetterRepository(session)
                    self._letters = repo.list_all()
            except Exception:
                logger.exception("Failed to load cover letters")
                self._letters = []
        else:
            self._letters = letters

        self._table.setRowCount(len(self._letters))
        for i, cl in enumerate(self._letters):
            self._table.setItem(i, 0, QTableWidgetItem(str(cl.id)))
            self._table.setItem(i, 1, QTableWidgetItem(f"Resume #{cl.resume_id}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"Job #{cl.job_id}"))
            created = cl.created_at.strftime("%Y-%m-%d %H:%M") if cl.created_at else "-"
            self._table.setItem(i, 3, QTableWidgetItem(created))
            preview = (cl.content[:120] + "...") if len(cl.content) > 120 else cl.content
            self._table.setItem(i, 4, QTableWidgetItem(preview))

    def _selected_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        return int(self._table.item(row, 0).text())

    def _on_search(self) -> None:
        query = self._search_input.text().strip()
        try:
            with db.session_scope() as session:
                repo = CoverLetterRepository(session)
                results = repo.search(query=query)
            self._refresh(results)
        except Exception:
            logger.exception("Failed to search cover letters")

    def _on_clear_search(self) -> None:
        self._search_input.clear()
        self._refresh()

    def _on_view(self) -> None:
        cl_id = self._selected_id()
        if cl_id is None:
            return
        cl = next((c for c in self._letters if c.id == cl_id), None)
        if cl is None:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Cover Letter #{cl.id}")
        dlg.setMinimumSize(500, 400)
        dlg_layout = QVBoxLayout(dlg)

        info = QLabel(f"Resume #{cl.resume_id} | Job #{cl.job_id} | {cl.created_at.strftime('%Y-%m-%d') if cl.created_at else ''}")
        info.setStyleSheet("color: #6B7280; font-size: 12px;")
        dlg_layout.addWidget(info)

        text = QTextEdit()
        text.setPlainText(cl.content)
        text.setReadOnly(True)
        dlg_layout.addWidget(text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(cl.content))
        btn_row.addWidget(copy_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.close)
        btn_row.addWidget(close_btn)
        dlg_layout.addLayout(btn_row)

        dlg.exec()

    def _on_copy(self) -> None:
        cl_id = self._selected_id()
        if cl_id is None:
            return
        cl = next((c for c in self._letters if c.id == cl_id), None)
        if cl is not None:
            QApplication.clipboard().setText(cl.content)
            self.window.notify("Cover letter copied to clipboard.")

    def _on_delete(self) -> None:
        cl_id = self._selected_id()
        if cl_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete Cover Letter",
            "Are you sure you want to delete this cover letter?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with db.session_scope() as session:
                    repo = CoverLetterRepository(session)
                    repo.delete(cl_id)
                self._refresh()
            except Exception:
                logger.exception("Failed to delete cover letter")
