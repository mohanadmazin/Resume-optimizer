# app/ui/components/rezi/section_menu.py
"""Floating section menu with checkboxes and submenu support."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import REZI_COLORS


REZI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class _Checkbox(QWidget):
    """Small custom checkbox with purple checked state."""

    checked_changed = Signal(bool)

    SIZE = 18

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        self._checked = checked
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.checked_changed.emit(self._checked)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.SIZE, self.SIZE, 4, 4)

        if self._checked:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(REZI_COLORS["purple_check"]))
            painter.drawPath(path)
            # Checkmark
            painter.setPen(QPen(QColor(REZI_COLORS["dark_text"]), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(4, 9, 7, 13)
            painter.drawLine(7, 13, 14, 4)
        else:
            painter.setPen(QPen(QColor(REZI_COLORS["input_border"]), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        painter.end()


class _MenuItem(QWidget):
    """A single menu item with optional checkbox."""

    toggled = Signal(str, bool)

    def __init__(self, name: str, checked: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        self._checkbox = _Checkbox(checked)
        self._checkbox.checked_changed.connect(lambda c: self.toggled.emit(name, c))
        layout.addWidget(self._checkbox)

        lbl = QLabel(name)
        lbl.setStyleSheet(
            f"color: {REZI_COLORS['text_primary']};"
            f" font-size: 13px; font-family: {REZI_FONT_FAMILY};"
            f" border: none; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addStretch()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        if self._hovered:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(2, 2, self.width() - 4, self.height() - 4, 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(123, 139, 255, 20))
            painter.drawPath(path)
            painter.end()
        super().paintEvent(event)


class _SubmenuItem(QWidget):
    """Menu item with list icon and chevron for submenu."""

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # List icon placeholder
        icon = QLabel("≡")
        icon.setFixedWidth(18)
        icon.setStyleSheet(
            f"color: {REZI_COLORS['text_secondary']}; font-size: 16px;"
            f" border: none; background: transparent;"
        )
        layout.addWidget(icon)

        lbl = QLabel(name)
        lbl.setStyleSheet(
            f"color: {REZI_COLORS['text_primary']};"
            f" font-size: 13px; font-family: {REZI_FONT_FAMILY};"
            f" border: none; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addStretch()

        chevron = QLabel("›")
        chevron.setStyleSheet(
            f"color: {REZI_COLORS['text_muted']}; font-size: 16px;"
            f" border: none; background: transparent;"
        )
        layout.addWidget(chevron)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def paintEvent(self, event) -> None:
        if self._hovered:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(2, 2, self.width() - 4, self.height() - 4, 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(123, 139, 255, 20))
            painter.drawPath(path)
            painter.end()
        super().paintEvent(event)


class SectionMenu(QWidget):
    """Floating dropdown menu for toggling section visibility."""

    section_toggled = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(190, 245)
        self.setStyleSheet(
            f"background-color: {REZI_COLORS['menu_bg']};"
            f"border: 1px solid {REZI_COLORS['menu_border']};"
            f"border-radius: 10px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(0)

        # Checked items
        self._checked_items = ["Project", "Certifications", "Coursework", "Involvement"]
        self._menu_items: dict[str, _MenuItem] = {}

        for name in self._checked_items:
            item = _MenuItem(name, checked=True)
            item.toggled.connect(self.section_toggled.emit)
            layout.addWidget(item)
            self._menu_items[name] = item

        # Submenu items
        for name in ["Academic", "Other"]:
            item = _SubmenuItem(name)
            layout.addWidget(item)

        layout.addStretch()

    def set_checked(self, name: str, checked: bool) -> None:
        if name in self._menu_items:
            self._menu_items[name].setChecked(checked)

    def is_checked(self, name: str) -> bool:
        if name in self._menu_items:
            return self._menu_items[name]._checkbox.isChecked()
        return False
