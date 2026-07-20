# app/ui/pages/resumeai_placeholder.py
"""Placeholder pages for resume sections not yet fully implemented."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.components.resumeai.card import ResumeAiCard
from app.ui.theme import RESUMEAI_COLORS


RESUMEAI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class ResumeAiPlaceholderPage(QWidget):
    """A placeholder page for sections not yet implemented."""

    def __init__(self, section_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(75, 25, 75, 25)

        card = ResumeAiCard()
        lbl = QLabel(f"{section_name.upper()}\n\nComing soon...")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: {RESUMEAI_COLORS['text_muted']};"
            f" font-size: 18px; font-weight: 600;"
            f" font-family: {RESUMEAI_FONT_FAMILY};"
            f" border: none; background: transparent;"
        )
        card.card_layout.addWidget(lbl)
        layout.addWidget(card)
        layout.addStretch()
