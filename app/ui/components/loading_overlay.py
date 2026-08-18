# app/ui/components/loading_overlay.py

"""Semi-transparent overlay with spinner for blocking operations."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class LoadingOverlay(QWidget):
    """Full-widget overlay with indeterminate spinner and status message."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = QProgressBar()
        self._spinner.setRange(0, 0)
        self._spinner.setFixedSize(48, 48)
        self._spinner.setStyleSheet(
            """
            QProgressBar {
                border: 3px solid rgba(59, 130, 246, 0.5);
                border-radius: 24px;
                background-color: transparent;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 21px;
            }
            """
        )
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        self._message = QLabel("Processing...")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setStyleSheet(
            "color: white; font-size: 13px; font-weight: bold; "
            "background: transparent; padding: 8px;"
        )
        layout.addWidget(self._message, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
        self.hide()

    def show_with_message(self, message: str = "Processing...") -> None:
        self._message.setText(message)
        parent_widget = self.parentWidget()
        if parent_widget is not None:
            self.setGeometry(parent_widget.rect())
        self.show()
        self.raise_()
        self.setFocus()

    def resizeEvent(self, event) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.resize(parent.size())
        super().resizeEvent(event)


class LoadingOverlayManager:
    """Manages one LoadingOverlay per parent widget."""

    def __init__(self):
        self._overlays: dict[int, LoadingOverlay] = {}

    def show(self, parent: QWidget, message: str = "Processing...") -> None:
        pid = id(parent)
        if pid in self._overlays:
            self._overlays[pid].show_with_message(message)
            return
        overlay = LoadingOverlay(parent)
        overlay.show_with_message(message)
        self._overlays[pid] = overlay

    def hide(self, parent: QWidget | None = None) -> None:
        if parent is None:
            for overlay in self._overlays.values():
                overlay.hide()
                overlay.deleteLater()
            self._overlays.clear()
            return
        pid = id(parent)
        existing = self._overlays.get(pid)
        if existing is not None:
            self._overlays.pop(pid)
            existing.hide()
            existing.deleteLater()
