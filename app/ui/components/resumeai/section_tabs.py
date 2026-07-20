# app/ui/components/resumeai/section_tabs.py
"""Horizontal scrollable section tab bar with overflow menu."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from app.ui.theme import RESUMEAI_COLORS


class SectionTab(QPushButton):
    """A single section tab button."""

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(name, parent)
        self._name = name
        self._is_selected = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self._update_style()

    @property
    def section_name(self) -> str:
        return self._name

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self.setChecked(selected)
        self._update_style()

    def _update_style(self) -> None:
        if self._is_selected:
            self.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: {RESUMEAI_COLORS['primary_dark']};"
                f"  color: {RESUMEAI_COLORS['dark_text']};"
                f"  border: none;"
                f"  border-radius: 8px;"
                f"  padding: 4px 14px;"
                f"  font-family: {RESUMEAI_FONT_FAMILY};"
                f"  font-size: 12px;"
                f"  font-weight: 800;"
                f"}}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton {{"
                f"  background: transparent;"
                f"  color: {RESUMEAI_COLORS['text_primary']};"
                f"  border: none;"
                f"  border-radius: 8px;"
                f"  padding: 4px 14px;"
                f"  font-family: {RESUMEAI_FONT_FAMILY};"
                f"  font-size: 12px;"
                f"  font-weight: 700;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: rgba(123, 139, 255, 0.15);"
                f"}}"
            )


RESUMEAI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class SectionTabBar(QWidget):
    """Scrollable horizontal tab bar for resume sections."""

    tab_selected = Signal(str)

    DEFAULT_SECTIONS = [
        "CONTACT",
        "EXPERIENCE",
        "PROJECT",
        "EDUCATION",
        "CERTIFICATIONS",
        "COURSEWORK",
        "INVOLVEMENT",
        "SKILLS",
        "SUMMARY",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sections = list(self.DEFAULT_SECTIONS)
        self._tabs: dict[str, SectionTab] = {}
        self._selected: str = "CONTACT"

        self.setStyleSheet(
            f"background-color: {RESUMEAI_COLORS['window_bg']};"
            f"border: 1px solid {RESUMEAI_COLORS['border']};"
            f"border-radius: 10px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        for name in self._sections:
            tab = SectionTab(name)
            tab.clicked.connect(lambda checked=False, n=name: self.select_tab(n))
            layout.addWidget(tab)
            self._tabs[name] = tab

        # Three-dot overflow button
        self._overflow_btn = QPushButton("···")
        self._overflow_btn.setFixedSize(34, 34)
        self._overflow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._overflow_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  color: {RESUMEAI_COLORS['text_secondary']};"
            f"  border: none;"
            f"  border-radius: 8px;"
            f"  font-size: 16px;"
            f"  font-weight: bold;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: rgba(123, 139, 255, 0.15);"
            f"}}"
        )
        layout.addWidget(self._overflow_btn)

        self._tabs["CONTACT"].set_selected(True)

    @property
    def overflow_button(self) -> QPushButton:
        return self._overflow_btn

    @property
    def selected_section(self) -> str:
        return self._selected

    def select_tab(self, name: str) -> None:
        if name in self._tabs:
            self._tabs[self._selected].set_selected(False)
            self._selected = name
            self._tabs[name].set_selected(True)
            self.tab_selected.emit(name)

    def add_section(self, name: str) -> None:
        if name in self._tabs:
            return
        tab = SectionTab(name)
        tab.clicked.connect(lambda checked=False, n=name: self.select_tab(n))
        # Insert before the overflow button
        self.layout().insertWidget(self.layout().count() - 1, tab)
        self._tabs[name] = tab
        self._sections.append(name)

    def remove_section(self, name: str) -> None:
        if name not in self._tabs:
            return
        tab = self._tabs.pop(name)
        self.layout().removeWidget(tab)
        tab.deleteLater()
        self._sections.remove(name)
        if self._selected == name and self._sections:
            self.select_tab(self._sections[0])

    def set_section_visible(self, name: str, visible: bool) -> None:
        if name not in self._tabs:
            return
        if visible:
            self._tabs[name].setVisible(True)
        else:
            self._tabs[name].setVisible(False)
            if self._selected == name:
                for s in self._sections:
                    if self._tabs[s].isVisible():
                        self.select_tab(s)
                        break

    def visible_sections(self) -> list[str]:
        return [s for s in self._sections if self._tabs[s].isVisible()]
