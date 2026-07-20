# app/ui/components/rezi/toggle_switch.py
"""Animated toggle switch widget."""

from __future__ import annotations


from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal, Property
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from app.ui.theme import REZI_COLORS


class ReziToggleSwitch(QWidget):
    """A custom toggle switch with animated thumb."""

    toggled = Signal(bool)

    WIDTH = 44
    HEIGHT = 22
    THUMB_RADIUS = 8
    TRACK_RADIUS = 11

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._thumb_x = self._target_thumb_x()

        # Animation
        self._anim = QPropertyAnimation(self, b"thumb_x")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _target_thumb_x(self) -> float:
        return self.WIDTH - self.THUMB_RADIUS - 4 - 1 if self._checked else self.THUMB_RADIUS + 4

    @Property(float)
    def thumb_x(self) -> float:
        return self._thumb_x

    @thumb_x.setter
    def thumb_x(self, value: float) -> None:
        self._thumb_x = value
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        self._anim.setStartValue(self._thumb_x)
        self._anim.setEndValue(self._target_thumb_x())
        self._anim.start()
        self.toggled.emit(checked)

    def toggle(self) -> None:
        self.setChecked(not self._checked)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        if self._checked:
            track_color = QColor(REZI_COLORS["toggle_track_on"])
        else:
            track_color = QColor(REZI_COLORS["toggle_track_off"])

        track_path = QPainterPath()
        track_path.addRoundedRect(0, 0, self.WIDTH, self.HEIGHT, self.TRACK_RADIUS, self.TRACK_RADIUS)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawPath(track_path)

        # Thumb
        thumb_color = QColor(REZI_COLORS["toggle_thumb_on"] if self._checked else REZI_COLORS["toggle_thumb_off"])
        painter.setBrush(QBrush(thumb_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(self._thumb_x - self.THUMB_RADIUS), self.HEIGHT // 2 - self.THUMB_RADIUS,
                            self.THUMB_RADIUS * 2, self.THUMB_RADIUS * 2)

        painter.end()
