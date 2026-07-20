"""Horizontal navigation for editable resume sections and final review."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabBar, QWidget


class SectionNavigator(QTabBar):
    """Top navigation for Resume Studio.

    The tabs do not create separate pages.  They select the content displayed by
    the shared :class:`SectionEditor`, with one final destination for reviewing
    and exporting the working resume.
    """

    destination_selected = Signal(str)
    # Kept for compatibility with older Studio wiring and tests.
    section_selected = Signal(str)

    REVIEW_TAB = "Review"

    def __init__(
        self,
        sections: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sectionNavigator")
        self.setDocumentMode(True)
        self.setMovable(False)
        self.setExpanding(False)
        self.setUsesScrollButtons(True)
        self.setStyleSheet(
            """
            QTabBar#sectionNavigator::tab {
                background: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 7px;
                padding: 8px 12px;
                margin-right: 4px;
            }
            QTabBar#sectionNavigator::tab:hover {
                background: palette(alternate-base);
            }
            QTabBar#sectionNavigator::tab:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
                font-weight: 600;
            }
            """
        )

        for section in sections:
            self.addTab(section)
        self.addTab(self.REVIEW_TAB)

        self.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, index: int) -> None:
        if index < 0:
            return
        destination = self.tabText(index)
        self.destination_selected.emit(destination)
        if destination != self.REVIEW_TAB:
            self.section_selected.emit(destination)

    def select_destination(self, name: str) -> None:
        """Select a section or the Review destination without re-emitting."""
        for index in range(self.count()):
            if self.tabText(index) == name:
                self.blockSignals(True)
                self.setCurrentIndex(index)
                self.blockSignals(False)
                return

    def select_section(self, name: str) -> None:
        """Backward-compatible alias for selecting an editable section."""
        self.select_destination(name)
