"""Discovery Interview page — chat-style guided achievement extraction."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.discovery import AchievementResult, DiscoverySession

logger = logging.getLogger(__name__)


class _ChatBubble(QFrame):
    """Styled chat bubble for AI questions and user answers."""

    def __init__(self, text: str, is_ai: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("chatBubble")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_ai:
            label.setStyleSheet(
                "background-color: #e3f2fd; padding: 8px; border-radius: 8px; "
                "font-size: 13px;"
            )
        else:
            label.setStyleSheet(
                "background-color: #c8e6c9; padding: 8px; border-radius: 8px; "
                "font-size: 13px;"
            )
        layout.addWidget(label)


class _AchievementCard(QFrame):
    """Card displaying a discovered achievement with save button."""

    def __init__(self, achievement: AchievementResult, parent=None):
        super().__init__(parent)
        self.achievement = achievement
        self.setObjectName("achievementCard")
        self.setStyleSheet(
            "QFrame { border: 1px solid #90caf9; border-radius: 6px; "
            "padding: 8px; margin: 4px 0; background-color: #fafafa; }"
        )
        layout = QVBoxLayout(self)

        title = QLabel("Achievement Discovered")
        title.setStyleSheet("font-weight: bold; color: #1565c0; font-size: 13px;")
        layout.addWidget(title)

        stmt = QLabel(achievement.statement)
        stmt.setWordWrap(True)
        stmt.setStyleSheet("font-size: 12px;")
        layout.addWidget(stmt)

        if achievement.metrics:
            metrics_text = " | ".join(
                f"{k}: {v}" for k, v in achievement.metrics.items()
            )
            ml = QLabel(f"Metrics: {metrics_text}")
            ml.setStyleSheet("font-size: 11px; color: #666;")
            layout.addWidget(ml)

        if achievement.tools_used:
            tl = QLabel(f"Tools: {', '.join(achievement.tools_used)}")
            tl.setStyleSheet("font-size: 11px; color: #666;")
            layout.addWidget(tl)

        self.save_btn = QPushButton("Save to Vault")
        self.save_btn.setFixedWidth(120)
        layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignRight)


class DiscoveryPage(QWidget):
    """Chat-style discovery interview page."""

    MAX_DISPLAY_BUBBLES = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session: DiscoverySession | None = None
        self._achievements: list[AchievementResult] = []
        self._bubble_count = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel("Achievement Discovery Interview")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(header)

        # Role + controls
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Role:"))
        self._role_input = QLineEdit()
        self._role_input.setPlaceholderText("e.g. Senior Backend Engineer")
        ctrl_row.addWidget(self._role_input)

        self._start_btn = QPushButton("Start Interview")
        self._start_btn.clicked.connect(self._on_start)
        ctrl_row.addWidget(self._start_btn)

        self._progress_label = QLabel("Question 0/10")
        ctrl_row.addWidget(self._progress_label)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Chat area + achievements panel
        columns = QHBoxLayout()

        # Chat scroll
        chat_frame = QFrame()
        chat_frame.setObjectName("chatFrame")
        self._chat_layout = QVBoxLayout(chat_frame)
        self._chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        from PySide6.QtWidgets import QScrollArea
        self._chat_scroll = QScrollArea()
        self._chat_scroll.setWidget(chat_frame)
        self._chat_scroll.setWidgetResizable(True)
        columns.addWidget(self._chat_scroll, 2)

        # Achievements panel
        ach_frame = QVBoxLayout()
        ach_label = QLabel("Discovered Achievements")
        ach_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        ach_frame.addWidget(ach_label)

        self._ach_list = QListWidget()
        self._ach_list.currentRowChanged.connect(self._on_ach_selected)
        ach_frame.addWidget(self._ach_list)

        self._save_all_btn = QPushButton("Save All to Vault")
        self._save_all_btn.clicked.connect(self._on_save_all)
        ach_frame.addWidget(self._save_all_btn)

        columns.addLayout(ach_frame, 1)
        layout.addLayout(columns, 1)

        # Input row
        input_row = QHBoxLayout()
        self._answer_input = QLineEdit()
        self._answer_input.setPlaceholderText("Type your answer...")
        self._answer_input.returnPressed.connect(self._on_submit_answer)
        input_row.addWidget(self._answer_input)

        self._submit_btn = QPushButton("Send")
        self._submit_btn.clicked.connect(self._on_submit_answer)
        input_row.addWidget(self._submit_btn)
        layout.addLayout(input_row)

    def refresh(self) -> None:
        pass

    def _on_start(self) -> None:
        role = self._role_input.text().strip()
        from app.services.discovery import start_interview
        self._session = start_interview(role)
        self._achievements.clear()
        self._ach_list.clear()
        self._bubble_count = 0

        # Clear chat
        while self._chat_layout.count():
            item = self._chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Show first question
        q = self._session.questions_asked[0] if self._session.questions_asked else None
        if q:
            self._add_bubble(q.question_text, is_ai=True)
            self._update_progress()

    def _on_submit_answer(self) -> None:
        text = self._answer_input.text().strip()
        if not text or self._session is None:
            return

        from app.services.discovery import answer_question, get_next_question, extract_achievements

        self._add_bubble(text, is_ai=False)
        self._answer_input.clear()

        answer_question(self._session, text)

        # Extract achievements after each answer
        self._achievements = extract_achievements(self._session)
        self._refresh_ach_list()

        # Next question
        q = get_next_question(self._session)
        if q:
            self._add_bubble(q.question_text, is_ai=True)
        else:
            self._add_bubble(
                "Interview complete! Review and save your achievements.",
                is_ai=True,
            )
        self._update_progress()

    def _add_bubble(self, text: str, is_ai: bool = True) -> None:
        bubble = _ChatBubble(text, is_ai)
        self._chat_layout.addWidget(bubble)
        self._bubble_count += 1
        if self._bubble_count > self.MAX_DISPLAY_BUBBLES:
            first = self._chat_layout.takeAt(0)
            if first and first.widget():
                first.widget().deleteLater()

    def _update_progress(self) -> None:
        if self._session:
            n = len(self._session.questions_asked)
            total = self._session.max_questions
            self._progress_label.setText(f"Question {n}/{total}")

    def _refresh_ach_list(self) -> None:
        self._ach_list.clear()
        for i, ach in enumerate(self._achievements):
            item = QListWidgetItem(f"{i+1}. {ach.statement[:60]}...")
            self._ach_list.addItem(item)

    def _on_ach_selected(self, row: int) -> None:
        pass

    def _on_save_all(self) -> None:
        if not self._achievements:
            QMessageBox.information(self, "No Achievements", "Complete the interview first.")
            return
        from app.services.discovery import store_achievements
        try:
            ids = store_achievements(self._achievements)
            QMessageBox.information(
                self, "Saved",
                f"Saved {len(ids)} achievements to the evidence vault.",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Save Failed", str(exc))
