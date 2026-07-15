"""Dashboard: latest scores and recent analyses."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        cards = QHBoxLayout()
        card1, self.score_value = _card("ATS Score")
        card2, self.keyword_value = _card("Keyword Match")
        card3, self.skills_value = _card("Skills Match")
        for card in (card1, card2, card3):
            cards.addWidget(card)
        layout.addLayout(cards)

        layout.addWidget(QLabel("Recent Analyses"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Resume", "Job", "ATS Score", "Keyword %", "Skills %"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

    def on_show(self) -> None:
        rows = db.recent_analyses(10)
        self.table.setRowCount(len(rows))
        keys = ("created_at", "resume_name", "job_title", "ats_score", "keyword_match", "skills_match")
        for row_idx, row in enumerate(rows):
            for col_idx, key in enumerate(keys):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(row[key])))
        if rows:
            self.score_value.setText(str(rows[0]["ats_score"]))
            self.keyword_value.setText(f"{rows[0]['keyword_match']}%")
            self.skills_value.setText(f"{rows[0]['skills_match']}%")
