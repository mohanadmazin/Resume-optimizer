# app/ui/components/rezi/top_nav.py
"""Top navigation bar with resume dropdown, section tabs, and action buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from app.ui.components.rezi.section_tabs import SectionTabBar
from app.ui.theme import REZI_COLORS


REZI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class ReziTopNav(QWidget):
    """Top navigation bar containing resume dropdown, section tabs, and action buttons."""

    section_changed = Signal(str)
    action_clicked = Signal(str)  # "finish_preview" or "ai_cover_letter"
    resume_dropdown_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(75)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(75, 10, 75, 0)
        layout.setSpacing(12)

        # ── Resume dropdown button ──
        self._resume_btn = QPushButton("MOHANAD RESUME 2026  ▾")
        self._resume_btn.setFixedSize(250, 44)
        self._resume_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._resume_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {REZI_COLORS['window_bg']};"
            f"  border: 1px solid {REZI_COLORS['border']};"
            f"  border-radius: 10px;"
            f"  color: {REZI_COLORS['text_primary']};"
            f"  font-family: {REZI_FONT_FAMILY};"
            f"  font-size: 13px;"
            f"  font-weight: 700;"
            f"  padding-left: 16px;"
            f"  padding-right: 12px;"
            f"  text-align: left;"
            f"}}"
            f"QPushButton:hover {{"
            f"  border-color: {REZI_COLORS['primary']};"
            f"}}"
        )
        self._resume_btn.clicked.connect(self.resume_dropdown_clicked.emit)
        layout.addWidget(self._resume_btn)

        # ── Section tabs ──
        self._tab_bar = SectionTabBar()
        self._tab_bar.tab_selected.connect(self.section_changed.emit)
        layout.addWidget(self._tab_bar, 1)

        layout.addSpacing(8)

        # ── Action buttons ──
        self._finish_btn = self._make_action_button("FINISH UP & PREVIEW")
        self._finish_btn.clicked.connect(lambda: self.action_clicked.emit("finish_preview"))
        layout.addWidget(self._finish_btn)

        self._cover_btn = self._make_action_button("AI COVER LETTER")
        self._cover_btn.clicked.connect(lambda: self.action_clicked.emit("ai_cover_letter"))
        layout.addWidget(self._cover_btn)

    @property
    def tab_bar(self) -> SectionTabBar:
        return self._tab_bar

    @property
    def resume_button(self) -> QPushButton:
        return self._resume_btn

    def _make_action_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(38)
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  border: 1px solid {REZI_COLORS['border']};"
            f"  border-radius: 8px;"
            f"  color: {REZI_COLORS['text_secondary']};"
            f"  font-family: {REZI_FONT_FAMILY};"
            f"  font-size: 11px;"
            f"  font-weight: 700;"
            f"  padding: 0 14px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  border-color: {REZI_COLORS['primary']};"
            f"  color: {REZI_COLORS['text_primary']};"
            f"}}"
        )
        return btn
