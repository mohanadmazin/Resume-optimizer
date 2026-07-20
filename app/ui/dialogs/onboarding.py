"""First-launch onboarding wizard."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import settings_service

logger = logging.getLogger(__name__)


class OnboardingWizard(QDialog):
    """Three-step first-launch wizard."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to Resume Optimizer")
        self.setMinimumSize(520, 380)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        root = QVBoxLayout(self)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._welcome_page())
        self._stack.addWidget(self._ai_page())
        self._stack.addWidget(self._appearance_page())

        self._prev_btn = QPushButton("Back")
        self._prev_btn.clicked.connect(self._go_prev)
        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._go_next)
        self._finish_btn = QPushButton("Finish")
        self._finish_btn.clicked.connect(self._finish)
        self._finish_btn.hide()

        row = QHBoxLayout()
        row.addWidget(self._prev_btn)
        row.addStretch()
        row.addWidget(self._next_btn)
        row.addWidget(self._finish_btn)
        root.addLayout(row)

        self._prev_btn.setEnabled(False)

    def _welcome_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("Welcome!")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        desc = QLabel(
            "This wizard will help you get started with Resume Optimizer.\n\n"
            "We'll configure your AI model and choose a theme."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addStretch()
        return w

    def _ai_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("AI Configuration")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("Enter your Ollama server URL (leave blank for localhost:11434):")
        layout.addWidget(desc)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("http://localhost:11434")
        layout.addWidget(self._url_input)

        layout.addStretch()
        return w

    def _appearance_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("Choose Your Theme")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("Select a color theme for the interface:")
        layout.addWidget(desc)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark", "Light"])
        self._theme_combo.setCurrentText("Dark")
        layout.addWidget(self._theme_combo)

        layout.addStretch()
        return w

    def _go_next(self) -> None:
        idx = self._stack.currentIndex()
        if idx < self._stack.count() - 1:
            self._stack.setCurrentIndex(idx + 1)
            self._prev_btn.setEnabled(True)
            if idx + 1 == self._stack.count() - 1:
                self._next_btn.hide()
                self._finish_btn.show()

    def _go_prev(self) -> None:
        idx = self._stack.currentIndex()
        if idx > 0:
            self._stack.setCurrentIndex(idx - 1)
            self._prev_btn.setEnabled(idx - 1 > 0)
            if self._next_btn.isHidden():
                self._next_btn.show()
                self._finish_btn.hide()

    def _finish(self) -> None:
        url = self._url_input.text().strip()
        theme = self._theme_combo.currentText().lower()

        settings = settings_service.settings.model_copy(deep=True)
        if url:
            settings.ai.ollama_url = url
        settings.appearance.theme = theme  # type: ignore[assignment]
        settings.onboarding_completed = True
        settings_service.save(settings)

        self.accept()
