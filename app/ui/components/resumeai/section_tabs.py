"""Horizontal resume-section tab bar used by the main window."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from app.ui.theme import RESUMEAI_COLORS

RESUMEAI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class SectionTab(QPushButton):
    """A single resume section tab button."""

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
                f"background-color: {RESUMEAI_COLORS['primary_dark']};"
                f"color: {RESUMEAI_COLORS['dark_text']};"
                "border: none; border-radius: 8px; padding: 4px 12px;"
                f"font-family: {RESUMEAI_FONT_FAMILY}; font-size: 11px;"
                "font-weight: 800;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background: transparent; border: none;"
                "border-radius: 8px; padding: 4px 12px;"
                f"color: {RESUMEAI_COLORS['text_primary']};"
                f"font-family: {RESUMEAI_FONT_FAMILY}; font-size: 11px;"
                "font-weight: 700; }"
                "QPushButton:hover { background-color: rgba(123, 139, 255, 0.15); }"
            )


class SectionTabBar(QWidget):
    """Horizontal tabs that select editable destinations in Resume Studio."""

    tab_selected = Signal(str)

    DEFAULT_SECTIONS = [
        "CONTACT",
        "SUMMARY",
        "EXPERIENCE",
        "PROJECTS",
        "EDUCATION",
        "SKILLS",
        "CERTIFICATIONS",
        "LANGUAGES",
        "SALARY",
        "REVIEW",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sections = list(self.DEFAULT_SECTIONS)
        self._tabs: dict[str, SectionTab] = {}
        self._selected = self._sections[0]

        self.setStyleSheet(
            f"background-color: {RESUMEAI_COLORS['window_bg']};"
            f"border: 1px solid {RESUMEAI_COLORS['border']};"
            "border-radius: 10px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(1)

        for name in self._sections:
            tab = SectionTab(name)
            tab.clicked.connect(lambda _checked=False, n=name: self.select_tab(n))
            layout.addWidget(tab)
            self._tabs[name] = tab

        self._overflow_btn = QPushButton("···")
        self._overflow_btn.setFixedSize(34, 34)
        self._overflow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._overflow_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            "border-radius: 8px; font-size: 16px; font-weight: bold;"
            f"color: {RESUMEAI_COLORS['text_secondary']}; }}"
            "QPushButton:hover { background-color: rgba(123, 139, 255, 0.15); }"
        )
        layout.addWidget(self._overflow_btn)
        self._tabs[self._selected].set_selected(True)

    @property
    def overflow_button(self) -> QPushButton:
        return self._overflow_btn

    @property
    def selected_section(self) -> str:
        return self._selected

    def select_tab(self, name: str, *, emit_signal: bool = True) -> None:
        if name not in self._tabs:
            return

        if self._selected in self._tabs:
            self._tabs[self._selected].set_selected(False)
        self._selected = name
        self._tabs[name].set_selected(True)

        if emit_signal:
            self.tab_selected.emit(name)

    def add_section(self, name: str) -> None:
        if name in self._tabs:
            return
        tab = SectionTab(name)
        tab.clicked.connect(lambda _checked=False, n=name: self.select_tab(n))
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
        tab = self._tabs.get(name)
        if tab is None or name in {"CONTACT", "REVIEW"}:
            return

        tab.setVisible(visible)
        if not visible and self._selected == name:
            for section in self._sections:
                candidate = self._tabs[section]
                if candidate.isVisible():
                    self.select_tab(section)
                    break

    def visible_sections(self) -> list[str]:
        return [name for name in self._sections if self._tabs[name].isVisible()]
