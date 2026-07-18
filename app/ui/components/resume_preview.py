"""ResumePreview — center tab showing the resume as rendered markdown."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class ResumePreview(QWidget):
    """Read-only text preview of the current resume content."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setObjectName("resumePreview")
        layout.addWidget(self._preview)

    def set_markdown(self, text: str) -> None:
        """Display resume content as plain text (markdown source)."""
        self._preview.setPlainText(text)

    def clear(self) -> None:
        self._preview.clear()
