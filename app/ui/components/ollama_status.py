# app/ui/components/ollama_status.py

"""Ollama connection status indicator."""

import requests
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class OllamaCheckerThread(QThread):
    """Background thread that checks Ollama availability."""

    status_changed = Signal(bool)

    def __init__(self, base_url: str, parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")

    def run(self) -> None:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self.status_changed.emit(resp.status_code == 200)
        except requests.RequestException:
            self.status_changed.emit(False)


class OllamaStatusLabel(QWidget):
    """Status indicator showing Ollama connection state."""

    def __init__(self, base_url: str = "http://localhost:11434", parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self._checker = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        layout.addWidget(self._dot)

        self._label = QLabel("Ollama: Checking...")
        layout.addWidget(self._label)

        self._set_checking()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check)
        self._timer.start(10_000)

        self.check()

    def set_base_url(self, url: str) -> None:
        self.base_url = url.rstrip("/")
        self.check()

    def check(self) -> None:
        if self._checker and self._checker.isRunning():
            return
        self._cleanup_checker()
        self._checker = OllamaCheckerThread(self.base_url)
        self._checker.status_changed.connect(self._update_ui)
        self._checker.finished.connect(self._cleanup_checker)
        self._checker.start()

    def _cleanup_checker(self) -> None:
        if self._checker:
            self._checker.deleteLater()
            self._checker = None

    def _set_checking(self) -> None:
        self._dot.setStyleSheet(
            "background-color: #9CA3AF; border-radius: 4px;"
        )
        self._label.setText("Ollama: Checking...")
        self._label.setStyleSheet("color: #9CA3AF;")

    def _update_ui(self, is_online: bool) -> None:
        if is_online:
            self._dot.setStyleSheet(
                "background-color: #22C55E; border-radius: 4px;"
            )
            self._label.setText("Ollama: Online")
            self._label.setStyleSheet("color: #22C55E;")
        else:
            self._dot.setStyleSheet(
                "background-color: #EF4444; border-radius: 4px;"
            )
            self._label.setText("Ollama: Offline")
            self._label.setStyleSheet("color: #EF4444;")
