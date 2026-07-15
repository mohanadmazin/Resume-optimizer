"""Background thread worker so AI calls never block the UI."""
from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, parent=None, **kwargs):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.error.emit(str(exc))
