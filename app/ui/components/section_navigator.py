"""SectionNavigator — left panel listing resume sections."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SectionNavigator(QFrame):
    """A vertical list of resume section names. Emits ``section_selected(name)`` on click."""

    section_selected = Signal(str)

    def __init__(self, sections: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sectionNavigator")
        self.setFixedWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(4)

        header = QLabel("SECTIONS")
        header.setObjectName("navHeader")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setObjectName("sectionList")
        self._list.setSpacing(2)
        for name in sections:
            item = QListWidgetItem(name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
            self._list.addItem(item)

        layout.addWidget(self._list)

        self._list.currentRowChanged.connect(self._on_row_changed)

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            item = self._list.item(row)
            if item is not None:
                self.section_selected.emit(item.text())

    def select_section(self, name: str) -> None:
        """Programmatically select a section by name."""
        for i in range(self._list.count()):
            if self._list.item(i).text() == name:
                self._list.blockSignals(True)
                self._list.setCurrentRow(i)
                self._list.blockSignals(False)
                return
