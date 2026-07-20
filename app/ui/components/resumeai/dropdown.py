# app/ui/components/resumeai/dropdown.py
"""Styled dropdown button with popup list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import RESUMEAI_COLORS


RESUMEAI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class ResumeAiDropdown(QWidget):
    """A dropdown control that shows a styled popup list when clicked."""

    selected = Signal(str)

    def __init__(
        self,
        label: str = "",
        value: str = "",
        items: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._items = items or []
        self._value = value
        self._open = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Label
        if label:
            lbl = QLabel(label.upper())
            lbl.setStyleSheet(
                f"color: {RESUMEAI_COLORS['text_primary']};"
                f" font-size: 13px; font-weight: 800;"
                f" font-family: {RESUMEAI_FONT_FAMILY};"
                f" border: none; background: transparent;"
            )
            layout.addWidget(lbl)

        # Button
        self._btn = QPushButton(f"{value}  ▾")
        self._btn.setFixedHeight(52)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {RESUMEAI_COLORS['input_bg']};"
            f"  border: 2px solid {RESUMEAI_COLORS['input_border']};"
            f"  border-radius: 5px;"
            f"  color: {RESUMEAI_COLORS['text_primary']};"
            f"  font-family: {RESUMEAI_FONT_FAMILY};"
            f"  font-size: 15px;"
            f"  font-weight: 600;"
            f"  padding-left: 18px;"
            f"  text-align: left;"
            f"}}"
            f"QPushButton:hover {{"
            f"  border-color: {RESUMEAI_COLORS['input_border_focus']};"
            f"}}"
        )
        self._btn.clicked.connect(self._toggle_list)
        layout.addWidget(self._btn)

        # Popup list (initially hidden)
        self._list = QListWidget()
        self._list.setMaximumHeight(200)
        self._list.setStyleSheet(
            f"QListWidget {{"
            f"  background-color: {RESUMEAI_COLORS['menu_bg']};"
            f"  border: 1px solid {RESUMEAI_COLORS['menu_border']};"
            f"  border-radius: 8px;"
            f"  padding: 4px;"
            f"  font-family: {RESUMEAI_FONT_FAMILY};"
            f"  font-size: 14px;"
            f"  color: {RESUMEAI_COLORS['text_primary']};"
            f"}}"
            f"QListWidget::item {{"
            f"  padding: 8px 12px;"
            f"  border-radius: 4px;"
            f"}}"
            f"QListWidget::item:hover {{"
            f"  background-color: {RESUMEAI_COLORS['hover_bg']};"
            f"}}"
            f"QListWidget::item:selected {{"
            f"  background-color: {RESUMEAI_COLORS['primary']};"
            f"  color: {RESUMEAI_COLORS['dark_text']};"
            f"}}"
        )
        self._list.setVisible(False)
        self._list.currentTextChanged.connect(self._on_select)

        for item in self._items:
            self._list.addItem(QListWidgetItem(item))

        layout.addWidget(self._list)

    def value(self) -> str:
        return self._value

    def setValue(self, text: str) -> None:
        self._value = text
        self._btn.setText(f"{text}  ▾")

    def setItems(self, items: list[str]) -> None:
        self._items = items
        self._list.clear()
        for item in items:
            self._list.addItem(QListWidgetItem(item))

    def _toggle_list(self) -> None:
        self._open = not self._open
        self._list.setVisible(self._open)

    def _on_select(self, text: str) -> None:
        if text:
            self._value = text
            self._btn.setText(f"{text}  ▾")
            self._list.setVisible(False)
            self._open = False
            self.selected.emit(text)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self._list.setVisible(False)
        self._open = False
