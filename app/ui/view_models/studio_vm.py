"""MVVM bridge for editing, reviewing, and exporting a resume."""
from __future__ import annotations

import copy
from typing import Any, Literal

from PySide6.QtCore import QObject, Signal

from app.domain.analysis import ATSResult
from app.domain.resume import ResumeData
from app.ui.state import AppState
from app.ui.undo_stack import UndoCommand, UndoStack

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

StateTarget = Literal["resume", "optimized"]


class ResumeStudioViewModel(QObject):
    """Own the single working resume used by editor, preview, and exporters."""

    resume_changed = Signal()
    section_changed = Signal(str)
    ats_changed = Signal()
    undoStateChanged = Signal()
    reviewStateChanged = Signal()

    def __init__(self, state: AppState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._resume: ResumeData | None = None
        self._selected_section = "Contact"
        self._ats: ATSResult | None = None
        self._undo_stack = UndoStack()
        self._state_target: StateTarget = "resume"
        self._approved_resume: ResumeData | None = None

    @property
    def resume(self) -> ResumeData | None:
        return self._resume

    @resume.setter
    def resume(self, value: ResumeData | None) -> None:
        self.load_resume(value, target="resume")

    def load_resume(
        self,
        value: ResumeData | None,
        *,
        target: StateTarget = "resume",
    ) -> None:
        """Load a new working resume and reset history/review approval."""
        self._undo_stack.clear()
        self._state_target = target
        self._resume = value
        self._sync_to_state()
        self._approved_resume = None
        self.undoStateChanged.emit()
        self.reviewStateChanged.emit()
        self.resume_changed.emit()

    @property
    def ats(self) -> ATSResult | None:
        return self._ats

    @ats.setter
    def ats(self, value: ATSResult | None) -> None:
        self._ats = value
        self._state.ats = value
        self.ats_changed.emit()

    @property
    def selected_section(self) -> str:
        return self._selected_section

    def select_section(self, name: str) -> None:
        if name not in SECTION_NAMES:
            raise ValueError(f"Unknown resume section: {name}")
        if name != self._selected_section:
            self._selected_section = name
            self.section_changed.emit(name)

    @property
    def can_undo(self) -> bool:
        return self._undo_stack.can_undo

    @property
    def can_redo(self) -> bool:
        return self._undo_stack.can_redo

    def undo(self) -> str | None:
        description = self._undo_stack.undo()
        if description is not None:
            self._sync_to_state()
            self._invalidate_review()
            self.undoStateChanged.emit()
            self.resume_changed.emit()
            self.section_changed.emit(self._selected_section)
        return description

    def redo(self) -> str | None:
        description = self._undo_stack.redo()
        if description is not None:
            self._sync_to_state()
            self._invalidate_review()
            self.undoStateChanged.emit()
            self.resume_changed.emit()
            self.section_changed.emit(self._selected_section)
        return description

    def push_command(self, command: UndoCommand) -> None:
        self._undo_stack.push(command)
        self._sync_to_state()
        self._invalidate_review()
        self.undoStateChanged.emit()
        self.resume_changed.emit()

    def update_section(self, section: str, old_value: Any, new_value: Any) -> None:
        """Create a self-contained undo command for one section edit."""
        if old_value == new_value:
            return

        old_snapshot = copy.deepcopy(old_value)
        new_snapshot = copy.deepcopy(new_value)

        def execute() -> None:
            self._set_section_value(section, copy.deepcopy(new_snapshot))

        def undo() -> None:
            self._set_section_value(section, copy.deepcopy(old_snapshot))

        self.push_command(
            UndoCommand(
                description=f"Edit {section}",
                execute=execute,
                undo=undo,
            )
        )

    def _set_section_value(self, section: str, value: Any) -> None:
        if self._resume is None:
            return

        attribute_by_section = {
            "Contact": "contact",
            "Summary": "summary",
            "Experience": "experience",
            "Projects": "projects",
            "Education": "education",
            "Skills": "skills",
            "Certifications": "certifications",
            "Languages": "languages",
        }
        attribute = attribute_by_section.get(section)
        if attribute is None:
            raise ValueError(f"Unknown resume section: {section}")
        setattr(self._resume, attribute, value)

    def get_section_value(self, section: str) -> Any:
        if self._resume is None:
            return None
        attribute_by_section = {
            "Contact": "contact",
            "Summary": "summary",
            "Experience": "experience",
            "Projects": "projects",
            "Education": "education",
            "Skills": "skills",
            "Certifications": "certifications",
            "Languages": "languages",
        }
        attribute = attribute_by_section.get(section)
        return getattr(self._resume, attribute) if attribute else None

    @property
    def is_approved_for_export(self) -> bool:
        return self._approved_resume is not None

    @property
    def approved_resume(self) -> ResumeData | None:
        """Return a copy of the exact snapshot approved by the user."""
        return copy.deepcopy(self._approved_resume)

    def approve_for_export(self) -> None:
        if self._resume is None:
            return
        self._approved_resume = copy.deepcopy(self._resume)
        self.reviewStateChanged.emit()

    def _invalidate_review(self) -> None:
        if self._approved_resume is not None:
            self._approved_resume = None
            self.reviewStateChanged.emit()

    def _sync_to_state(self) -> None:
        setattr(self._state, self._state_target, self._resume)

    def job_text(self) -> str:
        return self._state.job_text or ""

    def has_resume(self) -> bool:
        return self._resume is not None

    def has_job_text(self) -> bool:
        return bool(self._state.job_text)

    def clear(self) -> None:
        self._undo_stack.clear()
        self._approved_resume = None
        self.undoStateChanged.emit()
        self.reviewStateChanged.emit()
