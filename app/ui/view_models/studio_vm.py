"""ResumeStudioViewModel — MVVM bridge between UI and application layer."""
from __future__ import annotations

import copy
import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.domain.analysis import ATSResult
from app.domain.resume import ResumeData
from app.ui.state import AppState
from app.ui.undo_stack import UndoCommand, UndoStack

logger = logging.getLogger(__name__)

SECTION_NAMES: list[str] = [
    "Contact",
    "Summary",
    "Experience",
    "Projects",
    "Education",
    "Skills",
    "Certifications",
    "Languages",
]


class ResumeStudioViewModel(QObject):
    """ViewModel for the Resume Studio page.

    Holds the resume data, selected section, ATS analysis results,
    and undo/redo stack.  Exposes Qt signals for reactive UI updates.
    """

    resume_changed = Signal()
    section_changed = Signal(str)
    ats_changed = Signal()
    undoStateChanged = Signal()

    def __init__(self, state: AppState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._resume: ResumeData | None = None
        self._selected_section: str = "Contact"
        self._ats: ATSResult | None = None
        self._undo_stack = UndoStack()

    # ── Resume access ────────────────────────────────────────────────

    @property
    def resume(self) -> ResumeData | None:
        return self._resume

    @resume.setter
    def resume(self, value: ResumeData | None) -> None:
        self._resume = value
        self._state.resume = value
        self.resume_changed.emit()

    @property
    def ats(self) -> ATSResult | None:
        return self._ats

    @ats.setter
    def ats(self, value: ATSResult | None) -> None:
        self._ats = value
        self._state.ats = value
        self.ats_changed.emit()

    # ── Section selection ────────────────────────────────────────────

    @property
    def selected_section(self) -> str:
        return self._selected_section

    def select_section(self, name: str) -> None:
        if name != self._selected_section:
            self._selected_section = name
            self.section_changed.emit(name)

    # ── Undo / redo ─────────────────────────────────────────────────

    @property
    def can_undo(self) -> bool:
        return self._undo_stack.can_undo

    @property
    def can_redo(self) -> bool:
        return self._undo_stack.can_redo

    def undo(self) -> str | None:
        desc = self._undo_stack.undo()
        if desc is not None:
            self._apply_to_state()
            self.undoStateChanged.emit()
            self.resume_changed.emit()
        return desc

    def redo(self) -> str | None:
        desc = self._undo_stack.redo()
        if desc is not None:
            self._apply_to_state()
            self.undoStateChanged.emit()
            self.resume_changed.emit()
        return desc

    def push_command(self, command: UndoCommand) -> None:
        """Push an already-constructed command onto the undo stack.

        ``command.execute()`` is called immediately by ``UndoStack.push``.
        After push, the resume state is synced to ``AppState`` and signals
        are emitted.
        """
        self._undo_stack.push(command)
        self._apply_to_state()
        self.undoStateChanged.emit()
        self.resume_changed.emit()

    def _apply_to_state(self) -> None:
        """Copy the current undo-stack-top resume into AppState."""
        top = self._undo_stack._undo_stack[-1] if self._undo_stack._undo_stack else None
        if top is not None:
            self._state.resume = self._resume

    # ── Section mutation helpers ─────────────────────────────────────

    def update_section(self, section: str, old_value: Any, new_value: Any) -> None:
        """Create and push an undo command for a section-level update."""
        if old_value == new_value:
            return

        def _execute() -> None:
            self._set_section_value(section, new_value)

        def _undo() -> None:
            self._set_section_value(section, old_value)

        cmd = UndoCommand(
            description=f"Edit {section}",
            execute=_execute,
            undo=_undo,
        )
        self.push_command(cmd)

    def _set_section_value(self, section: str, value: Any) -> None:
        """Apply *value* to the resume for the given section name."""
        if self._resume is None:
            return

        if section == "Contact":
            self._resume.contact = value
        elif section == "Summary":
            self._resume.summary = value
        elif section == "Experience":
            self._resume.experience = value
        elif section == "Projects":
            self._resume.projects = value
        elif section == "Education":
            self._resume.education = value
        elif section == "Skills":
            self._resume.skills = value
        elif section == "Certifications":
            self._resume.certifications = value
        elif section == "Languages":
            self._resume.languages = value

    # ── Helpers for editor ───────────────────────────────────────────

    def get_section_value(self, section: str) -> Any:
        if self._resume is None:
            return None
        mapping = {
            "Contact": self._resume.contact,
            "Summary": self._resume.summary,
            "Experience": self._resume.experience,
            "Projects": self._resume.projects,
            "Education": self._resume.education,
            "Skills": self._resume.skills,
            "Certifications": self._resume.certifications,
            "Languages": self._resume.languages,
        }
        return mapping.get(section)

    def job_text(self) -> str:
        return self._state.job_text or ""

    def has_resume(self) -> bool:
        return self._resume is not None

    def has_job_text(self) -> bool:
        return bool(self._state.job_text)

    def clear(self) -> None:
        self._undo_stack.clear()
        self.undoStateChanged.emit()
