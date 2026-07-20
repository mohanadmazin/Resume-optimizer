# app/ui/components/rezi/toast.py
"""Toast notification widget."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QWidget

from app.ui.theme import REZI_COLORS


REZI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class ReziToast(QLabel):
    """Small auto-dismissing success toast."""

    def __init__(self, message: str, parent: QWidget | None = None, duration_ms: int = 2500) -> None:
        super().__init__(message, parent)
        self.setStyleSheet(
            f"background-color: {REZI_COLORS['primary']};"
            f"color: {REZI_COLORS['dark_text']};"
            f"font-family: {REZI_FONT_FAMILY};"
            f"font-size: 13px;"
            f"font-weight: 700;"
            f"padding: 10px 20px;"
            f"border-radius: 8px;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(38)
        self._duration = duration_ms
        self.hide()

    def show_toast(self) -> None:
        """Show the toast, positioned at bottom-right of parent, then auto-hide."""
        if self.parent():
            pw = self.parent().width()
            self.setFixedWidth(min(300, pw // 3))
            self.move(pw - self.width() - 30, self.parent().height() - 60)
        self.show()
        self.raise_()
        QTimer.singleShot(self._duration, self.hide)
