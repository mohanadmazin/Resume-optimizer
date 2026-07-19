"""SectionEditor — dynamic form that adapts to the selected resume section."""
from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
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


class SectionEditor(QWidget):
    """Dynamic editor for the currently selected resume section.

    Emits ``section_edited(section, old_value, new_value)`` whenever the
    user commits a change (field lost focus or explicit save).
    """

    section_edited = Signal(str, object, object)
    generate_summary_requested = Signal()
    generate_headline_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_section: str = ""
        self._current_value: Any = None
        self._old_value: Any = None

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
        """Replace the editor contents for *section*."""
        self._current_section = section
        self._old_value = copy.deepcopy(value)
        self._current_value = value
        self._title.setText(section)

        # Clear old widgets
        while self._container_layout.count():
            child = self._container_layout.takeAt(0)
            w = child.widget()
            if w is not None:
                w.deleteLater()

        if section == "Contact":
            self._build_contact_editor(value)
        elif section == "Summary":
            self._build_text_editor("summary", value)
        elif section == "Skills":
            self._build_list_editor("Skills", value)
        elif section == "Certifications":
            self._build_list_editor("Certifications", value)
        elif section == "Languages":
            self._build_list_editor("Languages", value)
        elif section == "Experience":
            self._build_experience_editor(value)
        elif section == "Projects":
            self._build_projects_editor(value)
        elif section == "Education":
            self._build_education_editor(value)
        else:
            lbl = QLabel(f"Editor for '{section}' is not yet implemented.")
            lbl.setStyleSheet("color: #888; font-style: italic;")
            self._container_layout.addWidget(lbl)

        self._container_layout.addStretch()

    # ── Builders ─────────────────────────────────────────────────────

    def _build_contact_editor(self, contact: ContactInfo) -> None:
        form = QFormLayout()
        fields = [
            ("name", contact.name),
            ("email", contact.email),
            ("phone", contact.phone),
            ("location", contact.location),
            ("linkedin", contact.linkedin),
            ("website", contact.website),
        ]
        self._line_edits: dict[str, QLineEdit] = {}
        for field_name, current in fields:
            le = QLineEdit(current)
            le.setObjectName(field_name)
            le.editingFinished.connect(
                lambda f=field_name: self._on_contact_field(f)
            )
            self._line_edits[field_name] = le
            form.addRow(field_name.capitalize() + ":", le)
        self._container_layout.addLayout(form)

        gen_btn = QPushButton("Generate Headline with AI")
        gen_btn.setObjectName("generateHeadlineBtn")
        gen_btn.clicked.connect(self.generate_headline_requested.emit)
        self._container_layout.addWidget(gen_btn)

    def _on_contact_field(self, field_name: str) -> None:
        old_contact = copy.deepcopy(self._old_value)
        new_contact = copy.deepcopy(self._current_value)
        setattr(new_contact, field_name, self._line_edits[field_name].text())
        self.section_edited.emit("Contact", old_contact, new_contact)
        self._current_value = new_contact

    def _build_text_editor(self, field_name: str, text: str) -> None:
        te = QTextEdit()
        te.setPlainText(text or "")
        te.setAcceptRichText(False)
        te.setMinimumHeight(100)
        te.setObjectName(field_name + "_editor")
        te.editingFinished = lambda: None  # QTextEdit has no editingFinished
        # Use focusOutEvent proxy
        _orig_focus = te.focusOutEvent

        def _on_focus_out(event) -> None:
            _orig_focus(event)
            new_val = te.toPlainText()
            if new_val != (self._old_value or ""):
                self.section_edited.emit(
                    self._current_section, self._old_value, new_val
                )
                self._old_value = new_val

        te.focusOutEvent = _on_focus_out  # type: ignore[assignment]
        self._container_layout.addWidget(te)

        if field_name == "summary":
            gen_btn = QPushButton("Generate with AI")
            gen_btn.setObjectName("generateSummaryBtn")
            gen_btn.clicked.connect(self.generate_summary_requested.emit)
            self._container_layout.addWidget(gen_btn)

    def _build_list_editor(self, label: str, items: list[str]) -> None:
        self._list_widget = QListWidget()
        for item in items:
            self._list_widget.addItem(item)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(lambda: self._add_list_item())
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_list_item())
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()

        self._container_layout.addWidget(self._list_widget)
        self._container_layout.addLayout(btn_row)

    def _add_list_item(self) -> None:
        self._list_widget.addItem("(new)")
        self._list_widget.editItem(self._list_widget.item(self._list_widget.count() - 1))

    def _remove_list_item(self) -> None:
        row = self._list_widget.currentRow()
        if row >= 0:
            self._list_widget.takeItem(row)

    def _build_experience_editor(self, experience: list[ExperienceItem]) -> None:
        if not experience:
            self._container_layout.addWidget(QLabel("No experience entries."))
            return
        for idx, exp in enumerate(experience):
            card = QFrame()
            card.setObjectName("expCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            form = QFormLayout(card)
            form.setContentsMargins(8, 8, 8, 8)

            title_le = QLineEdit(exp.title)
            title_le.setPlaceholderText("Job Title")
            title_le.editingFinished.connect(
                lambda i=idx, le=title_le: self._on_exp_field(i, "title", le.text())
            )
            form.addRow("Title:", title_le)

            company_le = QLineEdit(exp.company)
            company_le.setPlaceholderText("Company")
            company_le.editingFinished.connect(
                lambda i=idx, le=company_le: self._on_exp_field(i, "company", le.text())
            )
            form.addRow("Company:", company_le)

            dates_le = QLineEdit(f"{exp.start_date} - {exp.end_date}")
            dates_le.setPlaceholderText("Start - End")
            dates_le.editingFinished.connect(
                lambda i=idx, le=dates_le: self._on_exp_dates(i, le.text())
            )
            form.addRow("Dates:", dates_le)

            bullets_lbl = QLabel("Bullets:")
            form.addRow(bullets_lbl)
            for j, bullet in enumerate(exp.bullets):
                bullet_le = QLineEdit(bullet)
                bullet_le.editingFinished.connect(
                    lambda i=idx, b=j, le=bullet_le: self._on_bullet_edit(i, b, le.text())
                )
                form.addRow("  •", bullet_le)

            self._container_layout.addWidget(card)
            if idx < len(experience) - 1:
                sep = QLabel("")
                sep.setFixedHeight(1)
                self._container_layout.addWidget(sep)

    def _on_exp_field(self, idx: int, field: str, value: str) -> None:
        new_exp = copy.deepcopy(self._current_value)
        old_exp = copy.deepcopy(self._old_value)
        setattr(new_exp[idx], field, value)
        self.section_edited.emit("Experience", old_exp, new_exp)
        self._current_value = new_exp

    def _on_exp_dates(self, idx: int, text: str) -> None:
        new_exp = copy.deepcopy(self._current_value)
        old_exp = copy.deepcopy(self._old_value)
        parts = text.split(" - ", 1)
        new_exp[idx].start_date = parts[0].strip()
        new_exp[idx].end_date = parts[1].strip() if len(parts) > 1 else ""
        self.section_edited.emit("Experience", old_exp, new_exp)
        self._current_value = new_exp

    def _on_bullet_edit(self, exp_idx: int, bullet_idx: int, value: str) -> None:
        new_exp = copy.deepcopy(self._current_value)
        old_exp = copy.deepcopy(self._old_value)
        if bullet_idx < len(new_exp[exp_idx].bullets):
            new_exp[exp_idx].bullets[bullet_idx] = value
        self.section_edited.emit("Experience", old_exp, new_exp)
        self._current_value = new_exp

    def _build_projects_editor(self, projects: list[ProjectItem]) -> None:
        if not projects:
            self._container_layout.addWidget(QLabel("No project entries."))
            return
        for idx, proj in enumerate(projects):
            card = QFrame()
            card.setObjectName("projCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            form = QFormLayout(card)
            form.setContentsMargins(8, 8, 8, 8)

            title_le = QLineEdit(proj.title)
            title_le.editingFinished.connect(
                lambda i=idx, le=title_le: self._on_proj_field(i, "title", le.text())
            )
            form.addRow("Title:", title_le)

            desc_te = QTextEdit(proj.description)
            desc_te.setAcceptRichText(False)
            desc_te.setMaximumHeight(80)
            _orig_focus = desc_te.focusOutEvent

            def _on_desc_focus(ev, i=idx, te=desc_te):
                _orig_focus(ev)
                self._on_proj_field(i, "description", te.toPlainText())

            desc_te.focusOutEvent = _on_desc_focus  # type: ignore[assignment]
            form.addRow("Description:", desc_te)

            self._container_layout.addWidget(card)

    def _on_proj_field(self, idx: int, field: str, value: str) -> None:
        new_proj = copy.deepcopy(self._current_value)
        old_proj = copy.deepcopy(self._old_value)
        setattr(new_proj[idx], field, value)
        self.section_edited.emit("Projects", old_proj, new_proj)
        self._current_value = new_proj

    def _build_education_editor(self, education: list[EducationItem]) -> None:
        if not education:
            self._container_layout.addWidget(QLabel("No education entries."))
            return
        for idx, edu in enumerate(education):
            card = QFrame()
            card.setObjectName("eduCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            form = QFormLayout(card)
            form.setContentsMargins(8, 8, 8, 8)

            degree_le = QLineEdit(edu.degree)
            degree_le.editingFinished.connect(
                lambda i=idx, le=degree_le: self._on_edu_field(i, "degree", le.text())
            )
            form.addRow("Degree:", degree_le)

            inst_le = QLineEdit(edu.institution)
            inst_le.editingFinished.connect(
                lambda i=idx, le=inst_le: self._on_edu_field(i, "institution", le.text())
            )
            form.addRow("Institution:", inst_le)

            year_le = QLineEdit(edu.year)
            year_le.editingFinished.connect(
                lambda i=idx, le=year_le: self._on_edu_field(i, "year", le.text())
            )
            form.addRow("Year:", year_le)

            self._container_layout.addWidget(card)

    def _on_edu_field(self, idx: int, field: str, value: str) -> None:
        new_edu = copy.deepcopy(self._current_value)
        old_edu = copy.deepcopy(self._old_value)
        setattr(new_edu[idx], field, value)
        self.section_edited.emit("Education", old_edu, new_edu)
        self._current_value = new_edu

    def save_pending_list(self) -> None:
        """Emit the edited signal for list-type sections (Skills, Certifications, Languages)."""
        if not hasattr(self, "_list_widget"):
            return
        new_items = [
            self._list_widget.item(i).text()
            for i in range(self._list_widget.count())
        ]
        if new_items != self._old_value:
            self.section_edited.emit(
                self._current_section,
                copy.deepcopy(self._old_value),
                new_items,
            )
            self._old_value = new_items

    def scroll_to_field(self, field_name: str) -> None:
        """Scroll the editor to reveal the named field."""
        container = self._container
        if container is None:
            return
        for child in container.findChildren(QWidget):
            obj_name = child.objectName()
            if obj_name == field_name or obj_name == field_name.lower():
                child.setFocus()
                scroll_area = self.parent()
                while scroll_area is not None:
                    if hasattr(scroll_area, "ensureWidgetVisible"):
                        scroll_area.ensureWidgetVisible(child)
                        break
                    scroll_area = scroll_area.parent()
                return
