"""SectionNavigator — left panel listing resume sections with reorder and rename."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SectionNavigator(QFrame):
    """A vertical list of resume section names with reorder and rename support.

    Emits ``section_selected(name)`` on click, ``section_reorder(name, direction)``
    on move buttons, and ``section_renamed(old, new)`` on double-click edit.
    """

    section_selected = Signal(str)
    section_reorder = Signal(str, int)
    section_renamed = Signal(str, str)

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
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
            self._list.addItem(item)

        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._up_btn = QPushButton("\u25B2")
        self._up_btn.setFixedSize(28, 24)
        self._up_btn.setToolTip("Move section up")
        self._up_btn.clicked.connect(self._on_move_up)
        btn_row.addWidget(self._up_btn)

        self._down_btn = QPushButton("\u25BC")
        self._down_btn.setFixedSize(28, 24)
        self._down_btn.setToolTip("Move section down")
        self._down_btn.clicked.connect(self._on_move_down)
        btn_row.addWidget(self._down_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._list.currentRowChanged.connect(self._on_row_changed)
        self._list.itemDoubleClicked.connect(self._on_double_click)

        self._renaming = False

    def _on_row_changed(self, row: int) -> None:
        if self._renaming:
            return
        if row >= 0:
            item = self._list.item(row)
            if item is not None:
                self.section_selected.emit(item.text())

    def _on_move_up(self) -> None:
        row = self._list.currentRow()
        if row > 0:
            item = self._list.takeItem(row)
            self._list.insertItem(row - 1, item)
            self._list.setCurrentItem(item)
            self.section_reorder.emit(item.text(), -1)

    def _on_move_down(self) -> None:
        row = self._list.currentRow()
        if row >= 0 and row < self._list.count() - 1:
            item = self._list.takeItem(row)
            self._list.insertItem(row + 1, item)
            self._list.setCurrentItem(item)
            self.section_reorder.emit(item.text(), 1)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self._renaming = True
        self._list.editItem(item)
        old_name = item.text()

        def _on_edit_finished() -> None:
            self._renaming = False
            new_name = item.text().strip()
            if new_name and new_name != old_name:
                self.section_renamed.emit(old_name, new_name)

        self._list.itemChanged.connect(
            lambda changed_item: (
                _on_edit_finished()
                if changed_item is item
                else None
            ),
            Qt.ConnectionType.SingleShotConnection,
        )

    def select_section(self, name: str) -> None:
        """Programmatically select a section by name."""
        for i in range(self._list.count()):
            if self._list.item(i).text() == name:
                self._list.blockSignals(True)
                self._list.setCurrentRow(i)
                self._list.blockSignals(False)
                return

    def set_sections(self, names: list[str]) -> None:
        """Replace the entire section list (e.g. after reorder or rename)."""
        self._list.blockSignals(True)
        self._list.clear()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
            self._list.addItem(item)
        self._list.blockSignals(False)
