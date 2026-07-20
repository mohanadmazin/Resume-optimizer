# app/ui/components/resumeai/card.py
"""Rounded card container widget."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from app.ui.theme import RESUMEAI_COLORS


class ResumeAiCard(QFrame):
    """A dark rounded card container for form content."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {RESUMEAI_COLORS['card_bg']};"
            f"  border: 1px solid {RESUMEAI_COLORS['border']};"
            f"  border-radius: 11px;"
            f"}}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(30, 32, 30, 32)
        self._layout.setSpacing(0)

    @property
    def card_layout(self) -> QVBoxLayout:
        return self._layout
