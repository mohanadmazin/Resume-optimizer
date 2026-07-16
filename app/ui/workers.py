"""Background thread worker so AI calls never block the UI."""
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, parent: object = None, **kwargs: Any):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.error.emit(str(exc))
