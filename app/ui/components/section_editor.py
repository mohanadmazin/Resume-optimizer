"""Dynamic editor for the selected structured-resume section."""
from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ProjectItem,
)


class CommitTextEdit(QTextEdit):
    """QTextEdit that emits an editing-finished signal on focus loss."""

    editing_finished = Signal()

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().focusOutEvent(event)
        self.editing_finished.emit()


class SectionEditor(QWidget):
    """Edit one section of the working resume.

    ``section_edited`` always contains the value immediately before the edit and
    the value immediately after it.  This makes each edit independently undoable
    instead of reverting every change made since the section was opened.
    """

    section_edited = Signal(str, object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_section = ""
        self._current_value: Any = None
        self._old_value: Any = None
        self._list_widget: QListWidget | None = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel()
        self._title.setObjectName("editorTitle")
        root.addWidget(self._title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(8, 8, 8, 8)
        self._container_layout.setSpacing(8)
        scroll.setWidget(self._container)
        root.addWidget(scroll)

    def load(self, section: str, value: Any) -> None:
        """Display a fresh editor for ``section`` using a defensive snapshot."""
        self._loading = True
        self._current_section = section
        self._current_value = copy.deepcopy(value)
        self._old_value = copy.deepcopy(value)
        self._list_widget = None
        self._title.setText(section)
        self._clear_layout(self._container_layout)

        if section == "Contact":
            self._build_contact_editor(self._current_value or ContactInfo())
        elif section == "Summary":
            self._build_text_editor("summary", self._current_value or "")
        elif section in {"Skills", "Certifications", "Languages"}:
            self._build_list_editor(list(self._current_value or []))
        elif section == "Experience":
            self._build_experience_editor(list(self._current_value or []))
        elif section == "Projects":
            self._build_projects_editor(list(self._current_value or []))
        elif section == "Education":
            self._build_education_editor(list(self._current_value or []))
        else:
            label = QLabel(f"Unknown resume section: {section}")
            label.setStyleSheet("color: #888; font-style: italic;")
            self._container_layout.addWidget(label)

        self._container_layout.addStretch()
        self._loading = False

    def save_pending_list(self) -> None:
        """Commit pending edits from list sections before navigation/export."""
        widget = self._list_widget
        if widget is None or self._current_section not in {
            "Skills",
            "Certifications",
            "Languages",
        }:
            return

        values = [
            widget.item(index).text().strip()
            for index in range(widget.count())
            if widget.item(index).text().strip()
        ]
        self._commit(values)

    def _commit(self, new_value: Any) -> None:
        if self._loading:
            return

        old_snapshot = copy.deepcopy(self._current_value)
        new_snapshot = copy.deepcopy(new_value)
        if old_snapshot == new_snapshot:
            return

        self.section_edited.emit(
            self._current_section,
            old_snapshot,
            new_snapshot,
        )
        self._current_value = copy.deepcopy(new_snapshot)
        self._old_value = copy.deepcopy(new_snapshot)

    @classmethod
    def _clear_layout(cls, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                cls._clear_layout(child_layout)
                child_layout.deleteLater()

    # Contact and summary -------------------------------------------------

    def _build_contact_editor(self, contact: ContactInfo) -> None:
        form = QFormLayout()
        fields = (
            ("name", contact.name),
            ("email", contact.email),
            ("phone", contact.phone),
            ("location", contact.location),
            ("linkedin", contact.linkedin),
            ("website", contact.website),
        )
        self._line_edits: dict[str, QLineEdit] = {}
        for field_name, current in fields:
            editor = QLineEdit(current)
            editor.setObjectName(field_name)
            editor.editingFinished.connect(
                lambda name=field_name: self._on_contact_field(name)
            )
            self._line_edits[field_name] = editor
            form.addRow(field_name.capitalize() + ":", editor)
        self._container_layout.addLayout(form)

    def _on_contact_field(self, field_name: str) -> None:
        contact = copy.deepcopy(self._current_value or ContactInfo())
        setattr(contact, field_name, self._line_edits[field_name].text().strip())
        self._commit(contact)

    def _build_text_editor(self, field_name: str, text: str) -> None:
        editor = CommitTextEdit()
        editor.setPlainText(text)
        editor.setAcceptRichText(False)
        editor.setMinimumHeight(140)
        editor.setObjectName(field_name + "_editor")
        editor.editing_finished.connect(
            lambda: self._commit(editor.toPlainText().strip())
        )
        self._container_layout.addWidget(editor)

    # Simple list sections -----------------------------------------------

    def _build_list_editor(self, items: list[str]) -> None:
        self._list_widget = QListWidget()
        self._list_widget.setObjectName("sectionListEditor")
        for value in items:
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self._list_widget.addItem(item)
        self._list_widget.itemChanged.connect(lambda _item: self.save_pending_list())

        controls = QHBoxLayout()
        add_button = QPushButton("+ Add")
        add_button.clicked.connect(self._add_list_item)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._remove_list_item)
        controls.addWidget(add_button)
        controls.addWidget(remove_button)
        controls.addStretch()

        self._container_layout.addWidget(self._list_widget)
        self._container_layout.addLayout(controls)

    def _add_list_item(self) -> None:
        widget = self._list_widget
        if widget is None:
            return
        widget.blockSignals(True)
        item = QListWidgetItem("")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        widget.addItem(item)
        widget.setCurrentItem(item)
        widget.blockSignals(False)
        widget.editItem(item)

    def _remove_list_item(self) -> None:
        widget = self._list_widget
        if widget is None:
            return
        row = widget.currentRow()
        if row >= 0:
            widget.takeItem(row)
            self.save_pending_list()

    # Experience ---------------------------------------------------------

    def _build_experience_editor(self, experience: list[ExperienceItem]) -> None:
        add_button = QPushButton("+ Add Experience")
        add_button.clicked.connect(self._add_experience)
        self._container_layout.addWidget(add_button)

        if not experience:
            self._container_layout.addWidget(QLabel("No experience entries yet."))
            return

        for index, entry in enumerate(experience):
            card = QFrame()
            card.setObjectName("expCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            form = QFormLayout()
            card_layout.addLayout(form)

            for field, label, value in (
                ("title", "Title:", entry.title),
                ("company", "Company:", entry.company),
                ("location", "Location:", entry.location),
                ("start_date", "Start:", entry.start_date),
                ("end_date", "End:", entry.end_date),
            ):
                line = QLineEdit(value)
                line.editingFinished.connect(
                    lambda i=index, f=field, widget=line: self._on_exp_field(
                        i, f, widget.text().strip()
                    )
                )
                form.addRow(label, line)

            bullets_label = QLabel("Bullets")
            bullets_label.setObjectName("sectionLabel")
            card_layout.addWidget(bullets_label)
            for bullet_index, bullet in enumerate(entry.bullets):
                row = QHBoxLayout()
                line = QLineEdit(bullet)
                line.editingFinished.connect(
                    lambda i=index, b=bullet_index, widget=line: self._on_exp_bullet(
                        i, b, widget.text().strip()
                    )
                )
                remove = QPushButton("Remove")
                remove.clicked.connect(
                    lambda _checked=False, i=index, b=bullet_index: self._remove_exp_bullet(i, b)
                )
                row.addWidget(line, 1)
                row.addWidget(remove)
                card_layout.addLayout(row)

            actions = QHBoxLayout()
            add_bullet = QPushButton("+ Add Bullet")
            add_bullet.clicked.connect(
                lambda _checked=False, i=index: self._add_exp_bullet(i)
            )
            remove_entry = QPushButton("Remove Experience")
            remove_entry.clicked.connect(
                lambda _checked=False, i=index: self._remove_experience(i)
            )
            actions.addWidget(add_bullet)
            actions.addStretch()
            actions.addWidget(remove_entry)
            card_layout.addLayout(actions)
            self._container_layout.addWidget(card)

    def _on_exp_field(self, index: int, field: str, value: str) -> None:
        entries = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(entries):
            setattr(entries[index], field, value)
            self._commit(entries)

    def _on_exp_bullet(self, index: int, bullet_index: int, value: str) -> None:
        entries = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(entries) and 0 <= bullet_index < len(entries[index].bullets):
            entries[index].bullets[bullet_index] = value
            self._commit(entries)

    def _add_experience(self) -> None:
        entries = copy.deepcopy(self._current_value or [])
        entries.append(ExperienceItem())
        self._commit(entries)
        self.load("Experience", entries)

    def _remove_experience(self, index: int) -> None:
        entries = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(entries):
            entries.pop(index)
            self._commit(entries)
            self.load("Experience", entries)

    def _add_exp_bullet(self, index: int) -> None:
        entries = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(entries):
            entries[index].bullets.append("")
            self._commit(entries)
            self.load("Experience", entries)

    def _remove_exp_bullet(self, index: int, bullet_index: int) -> None:
        entries = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(entries) and 0 <= bullet_index < len(entries[index].bullets):
            entries[index].bullets.pop(bullet_index)
            self._commit(entries)
            self.load("Experience", entries)

    # Projects -----------------------------------------------------------

    def _build_projects_editor(self, projects: list[ProjectItem]) -> None:
        add_button = QPushButton("+ Add Project")
        add_button.clicked.connect(self._add_project)
        self._container_layout.addWidget(add_button)

        if not projects:
            self._container_layout.addWidget(QLabel("No project entries yet."))
            return

        for index, project in enumerate(projects):
            card = QFrame()
            card.setObjectName("projCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            form = QFormLayout()
            card_layout.addLayout(form)

            for field, label, value in (
                ("title", "Title:", project.title),
                ("meta", "Meta:", project.meta),
                ("start_date", "Start:", project.start_date),
                ("end_date", "End:", project.end_date),
            ):
                line = QLineEdit(value)
                line.editingFinished.connect(
                    lambda i=index, f=field, widget=line: self._on_project_field(
                        i, f, widget.text().strip()
                    )
                )
                form.addRow(label, line)

            description = CommitTextEdit()
            description.setPlainText(project.description)
            description.setAcceptRichText(False)
            description.setMaximumHeight(100)
            description.editing_finished.connect(
                lambda i=index, widget=description: self._on_project_field(
                    i, "description", widget.toPlainText().strip()
                )
            )
            form.addRow("Description:", description)

            for bullet_index, bullet in enumerate(project.bullets):
                row = QHBoxLayout()
                line = QLineEdit(bullet)
                line.editingFinished.connect(
                    lambda i=index, b=bullet_index, widget=line: self._on_project_bullet(
                        i, b, widget.text().strip()
                    )
                )
                remove = QPushButton("Remove")
                remove.clicked.connect(
                    lambda _checked=False, i=index, b=bullet_index: self._remove_project_bullet(i, b)
                )
                row.addWidget(line, 1)
                row.addWidget(remove)
                card_layout.addLayout(row)

            actions = QHBoxLayout()
            add_bullet = QPushButton("+ Add Bullet")
            add_bullet.clicked.connect(
                lambda _checked=False, i=index: self._add_project_bullet(i)
            )
            remove_entry = QPushButton("Remove Project")
            remove_entry.clicked.connect(
                lambda _checked=False, i=index: self._remove_project(i)
            )
            actions.addWidget(add_bullet)
            actions.addStretch()
            actions.addWidget(remove_entry)
            card_layout.addLayout(actions)
            self._container_layout.addWidget(card)

    def _on_project_field(self, index: int, field: str, value: str) -> None:
        projects = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(projects):
            setattr(projects[index], field, value)
            self._commit(projects)

    def _on_project_bullet(self, index: int, bullet_index: int, value: str) -> None:
        projects = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(projects) and 0 <= bullet_index < len(projects[index].bullets):
            projects[index].bullets[bullet_index] = value
            self._commit(projects)

    def _add_project(self) -> None:
        projects = copy.deepcopy(self._current_value or [])
        projects.append(ProjectItem())
        self._commit(projects)
        self.load("Projects", projects)

    def _remove_project(self, index: int) -> None:
        projects = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(projects):
            projects.pop(index)
            self._commit(projects)
            self.load("Projects", projects)

    def _add_project_bullet(self, index: int) -> None:
        projects = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(projects):
            projects[index].bullets.append("")
            self._commit(projects)
            self.load("Projects", projects)

    def _remove_project_bullet(self, index: int, bullet_index: int) -> None:
        projects = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(projects) and 0 <= bullet_index < len(projects[index].bullets):
            projects[index].bullets.pop(bullet_index)
            self._commit(projects)
            self.load("Projects", projects)

    # Education ----------------------------------------------------------

    def _build_education_editor(self, education: list[EducationItem]) -> None:
        add_button = QPushButton("+ Add Education")
        add_button.clicked.connect(self._add_education)
        self._container_layout.addWidget(add_button)

        if not education:
            self._container_layout.addWidget(QLabel("No education entries yet."))
            return

        for index, entry in enumerate(education):
            card = QFrame()
            card.setObjectName("eduCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            form = QFormLayout()
            card_layout.addLayout(form)

            for field, label, value in (
                ("degree", "Degree:", entry.degree),
                ("institution", "Institution:", entry.institution),
                ("year", "Year:", entry.year),
            ):
                line = QLineEdit(value)
                line.editingFinished.connect(
                    lambda i=index, f=field, widget=line: self._on_education_field(
                        i, f, widget.text().strip()
                    )
                )
                form.addRow(label, line)

            remove = QPushButton("Remove Education")
            remove.clicked.connect(
                lambda _checked=False, i=index: self._remove_education(i)
            )
            card_layout.addWidget(remove)
            self._container_layout.addWidget(card)

    def _on_education_field(self, index: int, field: str, value: str) -> None:
        education = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(education):
            setattr(education[index], field, value)
            self._commit(education)

    def _add_education(self) -> None:
        education = copy.deepcopy(self._current_value or [])
        education.append(EducationItem())
        self._commit(education)
        self.load("Education", education)

    def _remove_education(self, index: int) -> None:
        education = copy.deepcopy(self._current_value or [])
        if 0 <= index < len(education):
            education.pop(index)
            self._commit(education)
            self.load("Education", education)
