# app/ui/components/ollama_status.py

"""Ollama connection status indicator."""

import requests
from PySide6.QtCore import QThread, QTimer, Signal
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
        new_url = url.rstrip("/")
        if new_url == self.base_url:
            return
        self.base_url = new_url
        self.check()

    def check(self) -> None:
        if self._checker is not None and self._checker.isRunning():
            return
        self._set_checking()
        checker = OllamaCheckerThread(self.base_url, parent=self)
        self._checker = checker
        checker.status_changed.connect(
            lambda online, c=checker: self._apply_checker_result(c, online)
        )
        checker.finished.connect(
            lambda c=checker: self._cleanup_checker(c)
        )
        checker.start()

    def _apply_checker_result(self, checker: OllamaCheckerThread, is_online: bool) -> None:
        if checker is not self._checker:
            return
        if checker.base_url != self.base_url.rstrip("/"):
            return
        self._update_ui(is_online)

    def _cleanup_checker(self, checker: OllamaCheckerThread) -> None:
        if checker is self._checker:
            self._checker = None
        checker.deleteLater()

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
