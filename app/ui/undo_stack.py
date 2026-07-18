"""Lightweight undo stack for resume edits."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class UndoCommand:
    description: str
    execute: Callable[[], None]
    undo: Callable[[], None]


class UndoStack:
    """Simple undo/redo stack for resume mutations."""

    def __init__(self) -> None:
        self._undo_stack: list[UndoCommand] = []
        self._redo_stack: list[UndoCommand] = []

    def push(self, command: UndoCommand) -> None:
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def undo(self) -> str | None:
        if not self._undo_stack:
            return None
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        return cmd.description

    def redo(self) -> str | None:
        if not self._redo_stack:
            return None
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        return cmd.description

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
