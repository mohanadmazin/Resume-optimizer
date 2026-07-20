"""Resume Studio view model and approved-export revision tracking."""
from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.domain.analysis import ATSResult
from app.domain.resume import ResumeData
from app.ui.state import AppState
from app.ui.undo_stack import UndoCommand, UndoStack

EDITABLE_SECTION_NAMES: list[str] = [
    "Contact",
    "Summary",
    "Experience",
    "Projects",
    "Education",
    "Skills",
    "Certifications",
    "Languages",
]
SECTION_NAMES = EDITABLE_SECTION_NAMES + ["Salary"]
_MUTABLE_FIELDS = set(EDITABLE_SECTION_NAMES) | {"Headline"}


class ResumeStudioViewModel(QObject):
    """Reactive state for the persistent Resume Studio page."""

    resume_changed = Signal()
    section_changed = Signal(str)
    ats_changed = Signal()
    undoStateChanged = Signal()
    section_order_changed = Signal()
    custom_headings_changed = Signal()
    reviewStateChanged = Signal()

    def __init__(self, state: AppState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._resume: ResumeData | None = None
        self._selected_section = "Contact"
        self._ats: ATSResult | None = None
        self._undo_stack = UndoStack()
        self._section_order = list(SECTION_NAMES)
        self._custom_headings: dict[str, str] = {}

        self._revision = 0
        self._approved_revision: int | None = None
        self._approved_snapshot: ResumeData | None = None

    # ── Resume access ───────────────────────────────────────────────

    @property
    def resume(self) -> ResumeData | None:
        return self._resume

    @resume.setter
    def resume(self, value: ResumeData | None) -> None:
        self._undo_stack.clear()
        self._resume = value
        self._ats = None
        self._revision = 0
        self._approved_revision = None
        self._approved_snapshot = None
        self._apply_to_state()

        self.undoStateChanged.emit()
        self.ats_changed.emit()
        self.reviewStateChanged.emit()
        self.resume_changed.emit()

    @property
    def ats(self) -> ATSResult | None:
        return self._ats

    @ats.setter
    def ats(self, value: ATSResult | None) -> None:
        # This result describes the editable Studio draft.  ``state.ats`` is
        # the original ATS baseline used by Optimization and must not be
        # overwritten here.
        self._ats = value
        self.ats_changed.emit()

    # ── Review / approved export snapshot ───────────────────────────

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def is_approved_for_export(self) -> bool:
        return (
            self._approved_snapshot is not None
            and self._approved_revision == self._revision
        )

    @property
    def approved_resume(self) -> ResumeData | None:
        if not self.is_approved_for_export:
            return None
        return copy.deepcopy(self._approved_snapshot)

    def approve_for_export(self) -> None:
        if self._resume is None:
            return
        self._approved_snapshot = copy.deepcopy(self._resume)
        self._approved_revision = self._revision
        self.reviewStateChanged.emit()

    def invalidate_review(self) -> None:
        if self._approved_snapshot is None and self._approved_revision is None:
            return
        self._approved_snapshot = None
        self._approved_revision = None
        self.reviewStateChanged.emit()

    def _record_change(self) -> None:
        self._revision += 1
        self.invalidate_review()

    # ── Section selection ───────────────────────────────────────────

    @property
    def selected_section(self) -> str:
        return self._selected_section

    def select_section(self, name: str) -> None:
        if name not in SECTION_NAMES or name == self._selected_section:
            return
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
        description = self._undo_stack.undo()
        if description is not None:
            self._apply_to_state()
            self._record_change()
            self.undoStateChanged.emit()
            self.resume_changed.emit()
            self.section_changed.emit(self._selected_section)
        return description

    def redo(self) -> str | None:
        description = self._undo_stack.redo()
        if description is not None:
            self._apply_to_state()
            self._record_change()
            self.undoStateChanged.emit()
            self.resume_changed.emit()
            self.section_changed.emit(self._selected_section)
        return description

    def push_command(self, command: UndoCommand) -> None:
        self._undo_stack.push(command)
        self._apply_to_state()
        self._record_change()
        self.undoStateChanged.emit()
        self.resume_changed.emit()

    def _apply_to_state(self) -> None:
        self._state.resume = self._resume

    # ── Section mutation helpers ────────────────────────────────────

    def update_section(self, section: str, old_value: Any, new_value: Any) -> None:
        if section not in _MUTABLE_FIELDS or old_value == new_value:
            return

        old_snapshot = copy.deepcopy(old_value)
        new_snapshot = copy.deepcopy(new_value)

        def _execute() -> None:
            self._set_section_value(section, copy.deepcopy(new_snapshot))

        def _undo() -> None:
            self._set_section_value(section, copy.deepcopy(old_snapshot))

        self.push_command(
            UndoCommand(
                description=f"Edit {section}",
                execute=_execute,
                undo=_undo,
            )
        )

    def _set_section_value(self, section: str, value: Any) -> None:
        if self._resume is None:
            return

        if section == "Contact":
            self._resume.contact = value
        elif section == "Summary":
            self._resume.summary = value
        elif section == "Headline":
            self._resume.headline = value
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

    def get_section_value(self, section: str) -> Any:
        if self._resume is None:
            return None
        mapping = {
            "Contact": self._resume.contact,
            "Summary": self._resume.summary,
            "Headline": self._resume.headline,
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
        self._resume = None
        self._ats = None
        self._revision = 0
        self._approved_revision = None
        self._approved_snapshot = None
        self._apply_to_state()
        self.undoStateChanged.emit()
        self.ats_changed.emit()
        self.reviewStateChanged.emit()
        self.resume_changed.emit()

    # ── Section order ───────────────────────────────────────────────

    @property
    def section_order(self) -> list[str]:
        return list(self._section_order)

    def move_section(self, section: str, direction: int) -> None:
        internal = self.get_internal_name(section)
        if internal not in self._section_order:
            return
        index = self._section_order.index(internal)
        new_index = index + direction
        if new_index < 0 or new_index >= len(self._section_order):
            return
        self._section_order.pop(index)
        self._section_order.insert(new_index, internal)
        self.section_order_changed.emit()

    # ── Custom headings ─────────────────────────────────────────────

    @property
    def custom_headings(self) -> dict[str, str]:
        return dict(self._custom_headings)

    def set_custom_heading(self, section: str, heading: str) -> None:
        internal = self.get_internal_name(section)
        clean_heading = heading.strip()
        if clean_heading and clean_heading != internal:
            self._custom_headings[internal] = clean_heading
        else:
            self._custom_headings.pop(internal, None)
        self.custom_headings_changed.emit()

    def get_display_name(self, section: str) -> str:
        return self._custom_headings.get(section, section)

    def get_internal_name(self, display_name: str) -> str:
        for internal, custom in self._custom_headings.items():
            if custom == display_name:
                return internal
        return display_name

    # ── Duplicate ───────────────────────────────────────────────────

    def duplicate_resume(self) -> ResumeData | None:
        if self._resume is None:
            return None
        duplicate = copy.deepcopy(self._resume)
        duplicate.contact = duplicate.contact.model_copy(
            update={"name": f"{duplicate.contact.name} (Copy)".strip()}
        )
        return duplicate
