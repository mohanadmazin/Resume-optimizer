# app/ui/pages/rezi_placeholder.py
"""Placeholder pages for resume sections not yet fully implemented."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.components.rezi.card import ReziCard
from app.ui.theme import REZI_COLORS


REZI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class ReziPlaceholderPage(QWidget):
    """A placeholder page for sections not yet implemented."""

    def __init__(self, section_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(75, 25, 75, 25)

        card = ReziCard()
        lbl = QLabel(f"{section_name.upper()}\n\nComing soon...")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: {REZI_COLORS['text_muted']};"
            f" font-size: 18px; font-weight: 600;"
            f" font-family: {REZI_FONT_FAMILY};"
            f" border: none; background: transparent;"
        )
        card.card_layout.addWidget(lbl)
        layout.addWidget(card)
        layout.addStretch()
