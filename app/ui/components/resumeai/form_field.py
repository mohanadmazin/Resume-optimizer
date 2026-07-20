# app/ui/components/resumeai/form_field.py
"""Form field with uppercase label, styled input, and optional toggle/icon."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.resumeai.toggle_switch import ResumeAiToggleSwitch
from app.ui.theme import RESUMEAI_COLORS


RESUMEAI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"

INPUT_STYLE = (
    f"QLineEdit {{"
    f"  background-color: {RESUMEAI_COLORS['input_bg']};"
    f"  border: 2px solid {RESUMEAI_COLORS['input_border']};"
    f"  border-radius: 5px;"
    f"  color: {RESUMEAI_COLORS['text_primary']};"
    f"  font-family: {RESUMEAI_FONT_FAMILY};"
    f"  font-size: 15px;"
    f"  font-weight: 600;"
    f"  padding-left: 18px;"
    f"  padding-right: 10px;"
    f"  selection-background-color: {RESUMEAI_COLORS['primary']};"
    f"}}"
    f"QLineEdit:focus {{"
    f"  border-color: {RESUMEAI_COLORS['input_border_focus']};"
    f"}}"
    f"QLineEdit::placeholder {{"
    f"  color: {RESUMEAI_COLORS['text_muted']};"
    f"  font-weight: 400;"
    f"}}"
)


class ResumeAiFormField(QWidget):
    """A form field with uppercase label and styled input."""

    value_changed = Signal(str)
    icon_clicked = Signal()

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        value: str = "",
        show_toggle: bool = False,
        toggle_checked: bool = True,
        show_icon: bool = False,
        icon_tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label_text = label

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── Top row: optional toggle ──
        if show_toggle:
            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.addStretch()
            toggle_label = QLabel("Show on resume")
            toggle_label.setStyleSheet(
                f"color: {RESUMEAI_COLORS['text_muted']}; font-size: 11px; "
                f"font-family: {RESUMEAI_FONT_FAMILY}; border: none; background: transparent;"
            )
            top_row.addWidget(toggle_label)
            self._toggle = ResumeAiToggleSwitch(checked=toggle_checked)
            top_row.addWidget(self._toggle)
            layout.addLayout(top_row)
        else:
            self._toggle = None

        # ── Label ──
        label = QLabel(self._label_text.upper())
        label.setStyleSheet(
            f"color: {RESUMEAI_COLORS['text_primary']};"
            f" font-size: 13px; font-weight: 800;"
            f" font-family: {RESUMEAI_FONT_FAMILY};"
            f" border: none; background: transparent;"
        )
        layout.addWidget(label)

        # ── Input row ──
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(0)

        self._input = QLineEdit(value)
        self._input.setPlaceholderText(placeholder)
        self._input.setFixedHeight(52)
        self._input.setStyleSheet(INPUT_STYLE)
        self._input.textChanged.connect(self.value_changed.emit)
        input_row.addWidget(self._input)

        # ── Optional icon button ──
        if show_icon:
            icon_btn = QPushButton("🔗")
            icon_btn.setFixedSize(36, 36)
            icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            icon_btn.setStyleSheet(
                f"QPushButton {{"
                f"  background: transparent; border: none;"
                f"  font-size: 16px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  color: {RESUMEAI_COLORS['primary']};"
                f"}}"
            )
            icon_btn.setToolTip(icon_tooltip)
            icon_btn.clicked.connect(self.icon_clicked.emit)
            # Overlay icon on the right side of the input
            input_row.addSpacing(-36)
            input_row.addWidget(icon_btn)

        layout.addLayout(input_row)

    @property
    def input(self) -> QLineEdit:
        return self._input

    @property
    def toggle(self) -> ResumeAiToggleSwitch | None:
        return self._toggle

    def value(self) -> str:
        return self._input.text()

    def setValue(self, text: str) -> None:
        self._input.setText(text)
