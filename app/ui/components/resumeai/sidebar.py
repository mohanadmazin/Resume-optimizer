# app/ui/components/resumeai/sidebar.py
"""Icon-only sidebar with logo, navigation icons, and bottom items."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import RESUMEAI_COLORS


# ── Icon painter helpers ──────────────────────────────────────────────────

def _draw_plus_icon(painter: QPainter, x: int, y: int, size: int) -> None:
    """Draw a plus sign (new document)."""
    pen = QPen(QColor(RESUMEAI_COLORS["icon_inactive"]), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    half = size // 2
    margin = size // 4
    painter.drawLine(x + margin, y + half, x + size - margin, y + half)
    painter.drawLine(x + half, y + margin, x + half, y + size - margin)


def _draw_document_icon(painter: QPainter, x: int, y: int, size: int) -> None:
    """Draw a document icon (folded corner rectangle)."""
    pen = QPen(QColor(RESUMEAI_COLORS["icon_inactive"]), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    fold = size // 3
    # Main rectangle
    painter.drawRect(x + 4, y + 2, size - 8, size - 4)
    # Fold line
    painter.drawLine(x + size - 4 - fold, y + 2, x + size - 4, y + 2 + fold)


def _draw_sparkles_icon(painter: QPainter, x: int, y: int, size: int) -> None:
    """Draw a sparkles/AI icon (star shape)."""
    pen = QPen(QColor(RESUMEAI_COLORS["icon_inactive"]), 1.5)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cx, cy = x + size // 2, y + size // 2
    # Four-point star
    r_outer = size // 2 - 3
    r_inner = size // 6
    import math
    points = []
    for i in range(8):
        angle = math.pi / 2 * i / 4 - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF
    polygon = QPolygonF([QPointF(px, py) for px, py in points])
    painter.drawPolygon(polygon)


def _draw_layout_icon(painter: QPainter, x: int, y: int, size: int) -> None:
    """Draw a document with layout panel."""
    pen = QPen(QColor(RESUMEAI_COLORS["icon_inactive"]), 1.5)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(x + 4, y + 2, size - 8, size - 4)
    # Layout lines inside
    line_y = y + size // 3
    painter.drawLine(x + 8, line_y, x + size - 8, line_y)
    painter.drawLine(x + 8, line_y + 4, x + size - 8, line_y + 4)
    # Small panel on right
    panel_x = x + size // 2 + 2
    painter.drawRect(panel_x, line_y + 6, size // 2 - 6, size // 3)


def _draw_heart_icon(painter: QPainter, x: int, y: int, size: int) -> None:
    """Draw a document with heart."""
    pen = QPen(QColor(RESUMEAI_COLORS["icon_inactive"]), 1.5)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(x + 4, y + 2, size - 8, size - 4)
    # Simple heart approximation
    hx = x + size // 2
    hy = y + size // 2 + 2
    painter.drawText(hx - 4, hy + 4, "♥")


def _draw_lines_icon(painter: QPainter, x: int, y: int, size: int) -> None:
    """Draw a document with horizontal text lines."""
    pen = QPen(QColor(RESUMEAI_COLORS["icon_inactive"]), 1.5)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(x + 4, y + 2, size - 8, size - 4)
    for i in range(3):
        ly = y + 8 + i * 6
        w = size - 14 if i < 2 else size - 20
        painter.drawLine(x + 8, ly, x + 8 + w, ly)


def _draw_check_icon(painter: QPainter, x: int, y: int, size: int) -> None:
    """Draw a document with checkmark."""
    pen = QPen(QColor(RESUMEAI_COLORS["icon_inactive"]), 1.5)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(x + 4, y + 2, size - 8, size - 4)
    # Checkmark
    cx = x + size // 2
    cy = y + size // 2 + 2
    painter.drawLine(cx - 5, cy, cx - 1, cy + 4)
    painter.drawLine(cx - 1, cy + 4, cx + 5, cy - 3)


# ── Sidebar icon button ──────────────────────────────────────────────────

_ICON_PAINTERS = [
    _draw_plus_icon,       # New document
    _draw_document_icon,   # Document
    _draw_sparkles_icon,   # AI / Sparkles
    _draw_layout_icon,     # Layout panel
    _draw_heart_icon,      # Heart / Cover letter
    _draw_lines_icon,      # Text lines / Applications
    _draw_check_icon,      # Checkmark / Completed
]


class SidebarIconButton(QWidget):
    """A single icon button in the sidebar."""

    clicked = Signal()

    def __init__(self, index: int, tooltip: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self._tooltip = tooltip
        self._hovered = False
        self._selected = False
        self.setFixedSize(48, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._hovered or self._selected:
            from PySide6.QtGui import QBrush
            path = QPainterPath()
            path.addRoundedRect(2, 2, 44, 44, 8, 8)
            bg = QColor(RESUMEAI_COLORS["primary"]) if self._selected else QColor(123, 139, 255, 30)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg))
            painter.drawPath(path)

        if 0 <= self._index < len(_ICON_PAINTERS):
            _ICON_PAINTERS[self._index](painter, 8, 8, 32)


# ── Main sidebar widget ──────────────────────────────────────────────────

class ResumeAiSidebar(QWidget):
    """Fixed-width icon sidebar with logo, nav icons, and bottom items."""

    page_selected = Signal(int)

    _TOOLTIPS = [
        "New Resume",
        "Dashboard",
        "AI Optimize",
        "Studio Editor",
        "Cover Letter",
        "Applications",
        "Settings",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(80)
        self.setStyleSheet(
            f"background-color: {RESUMEAI_COLORS['sidebar_bg']};"
            f"border: none;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        # ── Logo ──
        logo_btn = _LogoButton()
        layout.addWidget(logo_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(20)

        # ── Nav icons ──
        self._buttons: list[SidebarIconButton] = []
        for i, tooltip in enumerate(self._TOOLTIPS):
            btn = SidebarIconButton(i, tooltip)
            btn.clicked.connect(lambda idx=i: self._on_click(idx))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addSpacing(6)
            self._buttons.append(btn)

        layout.addStretch()

        # ── Bottom spacer ──
        layout.addStretch()

        layout.addSpacing(20)

    def set_selected(self, index: int) -> None:
        """Update the highlighted sidebar item without emitting navigation."""
        for i, button in enumerate(self._buttons):
            button.set_selected(i == index)

    def _on_click(self, index: int) -> None:
        self.set_selected(index)
        self.page_selected.emit(index)


class _LogoButton(QWidget):
    """Purple gradient square logo with 'R'."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Purple gradient rounded rect
        from PySide6.QtGui import QBrush, QLinearGradient
        gradient = QLinearGradient(0, 0, 42, 42)
        gradient.setColorAt(0, QColor("#7a22ad"))
        gradient.setColorAt(1, QColor("#5a1a8a"))

        path = QPainterPath()
        path.addRoundedRect(0, 0, 42, 42, 7, 7)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)

        # "R" letter
        painter.setPen(QColor("white"))
        font = QFont("Inter", 20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "R")
