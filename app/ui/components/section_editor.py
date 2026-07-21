"""Dynamic form editor for structured resume sections."""
from __future__ import annotations

import copy
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
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

from app.domain.certification import certification_parts, format_certification
from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ProjectItem,
)


class SectionEditor(QWidget):
    """Dynamic editor for the currently selected resume section.

    Emits section_edited(section, old_value, new_value) on commit.
    Emits text_changed(section, old_value, new_value) on every keystroke.
    """

    section_edited = Signal(str, object, object)
    text_changed = Signal(str, object, object)
    generate_summary_requested = Signal()
    generate_headline_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_section: str = ""
        self._current_value: Any = None
        self._old_value: Any = None
        self._reload_callback: Callable[[], None] | None = None
        self._list_widget: QListWidget | None = None
        self._text_widget: QTextEdit | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel()
        self._title.setObjectName("editorTitle")
        root.addWidget(self._title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._container: QWidget | None = None
        self._container_layout: QVBoxLayout | None = None
        self._replace_container()
        root.addWidget(self._scroll)

    def _replace_container(self) -> None:
        """Install a fresh editor container and detach the previous tree.

        Reusing one layout while its widgets are pending ``deleteLater()`` can
        leave old controls visible for another event-loop cycle. Rapid section
        changes then make those controls overlap. Swapping the scroll area's
        widget removes the old tree from view immediately.
        """
        old_container = self._scroll.takeWidget()
        if old_container is not None:
            old_container.hide()
            old_container.setParent(None)
            old_container.deleteLater()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._container = container
        self._container_layout = layout
        self._scroll.setWidget(container)
        self._scroll.verticalScrollBar().setValue(0)

    def set_reload_callback(self, callback: Callable[[], None]) -> None:
        self._reload_callback = callback

    def _reload(self) -> None:
        if self._reload_callback is not None:
            self._reload_callback()

    def load(self, section: str, value: Any) -> None:
        self._current_section = section
        self._old_value = copy.deepcopy(value)
        self._current_value = copy.deepcopy(value)
        self._list_widget = None
        self._text_widget = None
        self._title.setText(section)

        self._replace_container()
        assert self._container_layout is not None

        if section == "Contact":
            self._build_contact_editor(value or ContactInfo())
        elif section == "Summary":
            self._build_text_editor("summary", value or "")
        elif section == "Skills":
            self._build_list_editor("Skills", value or [])
        elif section == "Certifications":
            self._build_certifications_editor(value or [])
        elif section == "Languages":
            self._build_list_editor("Languages", value or [])
        elif section == "Experience":
            self._build_experience_editor(value or [])
        elif section == "Projects":
            self._build_projects_editor(value or [])
        elif section == "Education":
            self._build_education_editor(value or [])
        else:
            lbl = QLabel(f"Editor for \'{section}\' is not yet implemented.")
            lbl.setStyleSheet("color: #888; font-style: italic;")
            self._container_layout.addWidget(lbl)

        self._container_layout.addStretch()

    # -- Contact editor --

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
            le.textChanged.connect(self._on_contact_text_changed)
            self._line_edits[field_name] = le
            form.addRow(field_name.capitalize() + ":", le)
        self._container_layout.addLayout(form)

        gen_btn = QPushButton("Generate Headline with AI")
        gen_btn.setObjectName("generateHeadlineBtn")
        gen_btn.clicked.connect(self.generate_headline_requested.emit)
        self._container_layout.addWidget(gen_btn)

    def _on_contact_text_changed(self) -> None:
        new_contact = copy.deepcopy(self._current_value)
        for field_name, le in self._line_edits.items():
            setattr(new_contact, field_name, le.text())
        self.text_changed.emit(
            "Contact", copy.deepcopy(self._old_value), new_contact
        )

    def _on_contact_field(self, field_name: str) -> None:
        old_contact = copy.deepcopy(self._current_value)
        new_contact = copy.deepcopy(self._current_value)
        setattr(new_contact, field_name, self._line_edits[field_name].text())
        if new_contact == old_contact:
            return
        self.section_edited.emit("Contact", old_contact, new_contact)
        self._current_value = copy.deepcopy(new_contact)
        self._old_value = copy.deepcopy(new_contact)

    # -- Text editor (Summary) --

    def _build_text_editor(self, field_name: str, text: str) -> None:
        te = QTextEdit()
        self._text_widget = te
        te.setPlainText(text or "")
        te.setAcceptRichText(False)
        te.setMinimumHeight(100)
        te.setObjectName(field_name + "_editor")
        te.editingFinished = lambda: None
        _orig_focus = te.focusOutEvent

        def _on_focus_out(event) -> None:
            _orig_focus(event)
            new_val = te.toPlainText()
            if new_val != (self._old_value or ""):
                old_value = copy.deepcopy(self._current_value)
                self.section_edited.emit(
                    self._current_section, old_value, new_val
                )
                self._current_value = new_val
                self._old_value = new_val

        te.focusOutEvent = _on_focus_out  # type: ignore[assignment]
        te.textChanged.connect(lambda w=te: self._on_text_edit_changed(w))
        self._container_layout.addWidget(te)

        if field_name == "summary":
            gen_btn = QPushButton("Generate with AI")
            gen_btn.setObjectName("generateSummaryBtn")
            gen_btn.clicked.connect(self.generate_summary_requested.emit)
            self._container_layout.addWidget(gen_btn)

    def _on_text_edit_changed(self, te: QTextEdit) -> None:
        new_val = te.toPlainText()
        self.text_changed.emit(
            self._current_section, self._old_value, new_val
        )

    # -- List editor (Skills/Certifications/Languages) --

    def _build_list_editor(self, label: str, items: list[str]) -> None:
        self._list_widget = QListWidget()
        for value in items:
            self._list_widget.addItem(value)
            item = self._list_widget.item(self._list_widget.count() - 1)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

        self._list_widget.itemChanged.connect(self._commit_list)
        self._list_widget.model().rowsRemoved.connect(
            lambda: self._commit_list()
        )
        self._list_widget.model().rowsInserted.connect(
            lambda: self._commit_list()
        )

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(lambda: self._add_list_item())
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_list_item())
        up_btn = QPushButton("\u2191")
        up_btn.setFixedWidth(30)
        up_btn.clicked.connect(lambda: self._move_list_item(-1))
        down_btn = QPushButton("\u2193")
        down_btn.setFixedWidth(30)
        down_btn.clicked.connect(lambda: self._move_list_item(1))
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        btn_row.addStretch()

        self._container_layout.addWidget(self._list_widget)
        self._container_layout.addLayout(btn_row)

    def _add_list_item(self) -> None:
        self._list_widget.addItem("(new)")
        new_item = self._list_widget.item(self._list_widget.count() - 1)
        new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._list_widget.editItem(new_item)

    def _remove_list_item(self) -> None:
        row = self._list_widget.currentRow()
        if row >= 0:
            self._list_widget.takeItem(row)

    def _move_list_item(self, direction: int) -> None:
        widget = self._list_widget
        if widget is None:
            return
        row = widget.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if new_row < 0 or new_row >= widget.count():
            return
        widget.blockSignals(True)
        widget.model().blockSignals(True)
        try:
            item = widget.takeItem(row)
            widget.insertItem(new_row, item)
            widget.setCurrentRow(new_row)
        finally:
            widget.model().blockSignals(False)
            widget.blockSignals(False)
        self._commit_list()

    # -- Certifications editor --

    def _build_certifications_editor(self, certifications: list[str]) -> None:
        for idx, certification in enumerate(certifications):
            title, issuer, year = certification_parts(certification)
            card = QFrame()
            card.setObjectName("certCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)

            top_row = QHBoxLayout()
            label = QLabel(f"Certification #{idx + 1}")
            label.setStyleSheet("font-weight: bold;")
            top_row.addWidget(label)
            top_row.addStretch()
            delete_btn = QPushButton("Delete")
            delete_btn.setFixedWidth(60)
            delete_btn.clicked.connect(lambda _checked=False, i=idx: self._delete_certification(i))
            top_row.addWidget(delete_btn)
            card_layout.addLayout(top_row)

            form = QFormLayout()
            title_edit = QLineEdit(title)
            issuer_edit = QLineEdit(issuer)
            year_edit = QLineEdit(year)
            year_edit.setPlaceholderText("e.g. 2025")

            title_edit.editingFinished.connect(
                lambda i=idx, widget=title_edit: self._on_certification_field(i, "title", widget.text())
            )
            issuer_edit.editingFinished.connect(
                lambda i=idx, widget=issuer_edit: self._on_certification_field(i, "issuer", widget.text())
            )
            year_edit.editingFinished.connect(
                lambda i=idx, widget=year_edit: self._on_certification_field(i, "year", widget.text())
            )
            form.addRow("Certification:", title_edit)
            form.addRow("Issuer:", issuer_edit)
            form.addRow("Year obtained:", year_edit)
            card_layout.addLayout(form)
            self._container_layout.addWidget(card)

        add_btn = QPushButton("+ Add Certification")
        add_btn.setObjectName("addCertificationBtn")
        add_btn.clicked.connect(self._add_certification)
        self._container_layout.addWidget(add_btn)

    def _on_certification_field(self, idx: int, field: str, value: str) -> None:
        if idx >= len(self._current_value):
            return
        new_values = copy.deepcopy(self._current_value)
        title, issuer, year = certification_parts(new_values[idx])
        fields = {"title": title, "issuer": issuer, "year": year}
        fields[field] = value
        new_values[idx] = format_certification(
            fields["title"], fields["issuer"], fields["year"]
        )
        old_values = copy.deepcopy(self._current_value)
        if new_values == old_values:
            return
        self.section_edited.emit("Certifications", old_values, new_values)
        self._current_value = copy.deepcopy(new_values)
        self._old_value = copy.deepcopy(new_values)

    def _add_certification(self) -> None:
        new_values = copy.deepcopy(self._current_value)
        new_values.append("")
        self.section_edited.emit(
            "Certifications", copy.deepcopy(self._current_value), new_values
        )
        self._current_value = copy.deepcopy(new_values)
        self._old_value = copy.deepcopy(new_values)
        self._reload()

    def _delete_certification(self, idx: int) -> None:
        new_values = copy.deepcopy(self._current_value)
        if idx < len(new_values):
            new_values.pop(idx)
        self.section_edited.emit(
            "Certifications", copy.deepcopy(self._current_value), new_values
        )
        self._current_value = copy.deepcopy(new_values)
        self._old_value = copy.deepcopy(new_values)
        self._reload()

    # -- Experience editor --

    def _build_experience_editor(self, experience: list[ExperienceItem]) -> None:
        for idx, exp in enumerate(experience):
            card = QFrame()
            card.setObjectName("expCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)

            top_row = QHBoxLayout()
            top_lbl = QLabel(f"Experience #{idx + 1}")
            top_lbl.setStyleSheet("font-weight: bold;")
            top_row.addWidget(top_lbl)
            top_row.addStretch()
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("deleteExpBtn")
            del_btn.setFixedWidth(60)
            del_btn.clicked.connect(lambda i=idx: self._delete_experience(i))
            top_row.addWidget(del_btn)
            card_layout.addLayout(top_row)

            form = QFormLayout()

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

            card_layout.addLayout(form)

            bullets_lbl = QLabel("Bullets:")
            card_layout.addWidget(bullets_lbl)

            for j, bullet in enumerate(exp.bullets):
                bullet_row = QHBoxLayout()
                bullet_le = QLineEdit(bullet)
                bullet_le.editingFinished.connect(
                    lambda i=idx, b=j, le=bullet_le: self._on_bullet_edit(i, b, le.text())
                )
                bullet_row.addWidget(bullet_le, 1)

                up_bullet = QPushButton("\u2191")
                up_bullet.setFixedWidth(28)
                up_bullet.clicked.connect(
                    lambda i=idx, b=j: self._move_bullet(i, b, -1)
                )
                bullet_row.addWidget(up_bullet)

                down_bullet = QPushButton("\u2193")
                down_bullet.setFixedWidth(28)
                down_bullet.clicked.connect(
                    lambda i=idx, b=j: self._move_bullet(i, b, 1)
                )
                bullet_row.addWidget(down_bullet)

                del_bullet = QPushButton("\u00d7")
                del_bullet.setFixedWidth(28)
                del_bullet.clicked.connect(
                    lambda i=idx, b=j: self._delete_bullet(i, b)
                )
                bullet_row.addWidget(del_bullet)

                card_layout.addLayout(bullet_row)

            add_bullet_btn = QPushButton("+ Add Bullet")
            add_bullet_btn.clicked.connect(lambda i=idx: self._add_bullet(i))
            card_layout.addWidget(add_bullet_btn)

            self._container_layout.addWidget(card)
            if idx < len(experience) - 1:
                sep = QLabel("")
                sep.setFixedHeight(1)
                self._container_layout.addWidget(sep)

        add_btn = QPushButton("+ Add Experience")
        add_btn.setObjectName("addExpBtn")
        add_btn.clicked.connect(self._add_experience)
        self._container_layout.addWidget(add_btn)

    def _add_experience(self) -> None:
        new_exp = copy.deepcopy(self._current_value)
        new_exp.append(ExperienceItem())
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._old_value), new_exp
        )
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)
        self._reload()

    def _delete_experience(self, idx: int) -> None:
        new_exp = copy.deepcopy(self._current_value)
        if idx < len(new_exp):
            new_exp.pop(idx)
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._old_value), new_exp
        )
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)
        self._reload()

    def _add_bullet(self, exp_idx: int) -> None:
        new_exp = copy.deepcopy(self._current_value)
        if exp_idx < len(new_exp):
            new_exp[exp_idx].bullets.append("")
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._old_value), new_exp
        )
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)
        self._reload()

    def _delete_bullet(self, exp_idx: int, bullet_idx: int) -> None:
        new_exp = copy.deepcopy(self._current_value)
        if exp_idx < len(new_exp) and bullet_idx < len(new_exp[exp_idx].bullets):
            new_exp[exp_idx].bullets.pop(bullet_idx)
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._old_value), new_exp
        )
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)
        self._reload()

    def _move_bullet(self, exp_idx: int, bullet_idx: int, direction: int) -> None:
        new_exp = copy.deepcopy(self._current_value)
        if exp_idx >= len(new_exp):
            return
        bullets = new_exp[exp_idx].bullets
        new_idx = bullet_idx + direction
        if new_idx < 0 or new_idx >= len(bullets):
            return
        bullets[bullet_idx], bullets[new_idx] = bullets[new_idx], bullets[bullet_idx]
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._old_value), new_exp
        )
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)
        self._reload()

    def _on_exp_field(self, idx: int, field: str, value: str) -> None:
        new_exp = copy.deepcopy(self._current_value)
        old_exp = copy.deepcopy(self._old_value)
        setattr(new_exp[idx], field, value)
        self.section_edited.emit("Experience", old_exp, new_exp)
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)

    def _on_exp_dates(self, idx: int, text: str) -> None:
        new_exp = copy.deepcopy(self._current_value)
        old_exp = copy.deepcopy(self._old_value)
        parts = text.split(" - ", 1)
        new_exp[idx].start_date = parts[0].strip()
        new_exp[idx].end_date = parts[1].strip() if len(parts) > 1 else ""
        self.section_edited.emit("Experience", old_exp, new_exp)
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)

    def _on_bullet_edit(self, exp_idx: int, bullet_idx: int, value: str) -> None:
        new_exp = copy.deepcopy(self._current_value)
        old_exp = copy.deepcopy(self._old_value)
        if bullet_idx < len(new_exp[exp_idx].bullets):
            new_exp[exp_idx].bullets[bullet_idx] = value
        self.section_edited.emit("Experience", old_exp, new_exp)
        self._current_value = copy.deepcopy(new_exp)
        self._old_value = copy.deepcopy(new_exp)

    # -- Projects editor --

    def _build_projects_editor(self, projects: list[ProjectItem]) -> None:
        for idx, proj in enumerate(projects):
            card = QFrame()
            card.setObjectName("projCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)

            top_row = QHBoxLayout()
            top_lbl = QLabel(f"Project #{idx + 1}")
            top_lbl.setStyleSheet("font-weight: bold;")
            top_row.addWidget(top_lbl)
            top_row.addStretch()
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("deleteProjBtn")
            del_btn.setFixedWidth(60)
            del_btn.clicked.connect(lambda _checked=False, i=idx: self._delete_project(i))
            top_row.addWidget(del_btn)
            card_layout.addLayout(top_row)

            form = QFormLayout()
            title_le = QLineEdit(proj.title)
            meta_le = QLineEdit(proj.meta)
            start_le = QLineEdit(proj.start_date)
            end_le = QLineEdit(proj.end_date)
            desc_te = QTextEdit(proj.description)
            desc_te.setAcceptRichText(False)
            desc_te.setMaximumHeight(80)

            title_le.editingFinished.connect(
                lambda i=idx, le=title_le: self._on_proj_field(i, "title", le.text())
            )
            meta_le.editingFinished.connect(
                lambda i=idx, le=meta_le: self._on_proj_field(i, "meta", le.text())
            )
            start_le.editingFinished.connect(
                lambda i=idx, le=start_le: self._on_proj_field(i, "start_date", le.text())
            )
            end_le.editingFinished.connect(
                lambda i=idx, le=end_le: self._on_proj_field(i, "end_date", le.text())
            )
            original_focus = desc_te.focusOutEvent

            def _on_desc_focus(event, i=idx, editor=desc_te, original=original_focus):
                original(event)
                self._on_proj_field(i, "description", editor.toPlainText())

            desc_te.focusOutEvent = _on_desc_focus  # type: ignore[assignment]
            form.addRow("Title:", title_le)
            form.addRow("Context / Client:", meta_le)
            form.addRow("Start date:", start_le)
            form.addRow("End date:", end_le)
            form.addRow("Description:", desc_te)
            card_layout.addLayout(form)

            bullets_label = QLabel("Bullets:")
            bullets_label.setStyleSheet("font-weight: bold;")
            card_layout.addWidget(bullets_label)
            for bullet_idx, bullet in enumerate(proj.bullets):
                row = QHBoxLayout()
                edit = QLineEdit(bullet)
                edit.editingFinished.connect(
                    lambda i=idx, b=bullet_idx, widget=edit: self._on_project_bullet_edit(i, b, widget.text())
                )
                remove = QPushButton("Remove")
                remove.setFixedWidth(70)
                remove.clicked.connect(
                    lambda _checked=False, i=idx, b=bullet_idx: self._delete_project_bullet(i, b)
                )
                row.addWidget(edit, 1)
                row.addWidget(remove)
                card_layout.addLayout(row)

            add_bullet = QPushButton("+ Add Bullet")
            add_bullet.clicked.connect(lambda _checked=False, i=idx: self._add_project_bullet(i))
            card_layout.addWidget(add_bullet)
            self._container_layout.addWidget(card)

        add_btn = QPushButton("+ Add Project")
        add_btn.setObjectName("addProjBtn")
        add_btn.clicked.connect(self._add_project)
        self._container_layout.addWidget(add_btn)

    def _add_project(self) -> None:
        new_proj = copy.deepcopy(self._current_value)
        new_proj.append(ProjectItem())
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._current_value), new_proj
        )
        self._current_value = copy.deepcopy(new_proj)
        self._old_value = copy.deepcopy(new_proj)
        self._reload()

    def _delete_project(self, idx: int) -> None:
        new_proj = copy.deepcopy(self._current_value)
        if idx < len(new_proj):
            new_proj.pop(idx)
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._current_value), new_proj
        )
        self._current_value = copy.deepcopy(new_proj)
        self._old_value = copy.deepcopy(new_proj)
        self._reload()

    def _on_proj_field(self, idx: int, field: str, value: str) -> None:
        if idx >= len(self._current_value):
            return
        old_proj = copy.deepcopy(self._current_value)
        new_proj = copy.deepcopy(self._current_value)
        setattr(new_proj[idx], field, value)
        if new_proj == old_proj:
            return
        self.section_edited.emit("Projects", old_proj, new_proj)
        self._current_value = copy.deepcopy(new_proj)
        self._old_value = copy.deepcopy(new_proj)

    def _add_project_bullet(self, project_idx: int) -> None:
        new_proj = copy.deepcopy(self._current_value)
        if project_idx < len(new_proj):
            new_proj[project_idx].bullets.append("")
        self.section_edited.emit("Projects", copy.deepcopy(self._current_value), new_proj)
        self._current_value = copy.deepcopy(new_proj)
        self._old_value = copy.deepcopy(new_proj)
        self._reload()

    def _delete_project_bullet(self, project_idx: int, bullet_idx: int) -> None:
        new_proj = copy.deepcopy(self._current_value)
        if project_idx < len(new_proj) and bullet_idx < len(new_proj[project_idx].bullets):
            new_proj[project_idx].bullets.pop(bullet_idx)
        self.section_edited.emit("Projects", copy.deepcopy(self._current_value), new_proj)
        self._current_value = copy.deepcopy(new_proj)
        self._old_value = copy.deepcopy(new_proj)
        self._reload()

    def _on_project_bullet_edit(self, project_idx: int, bullet_idx: int, value: str) -> None:
        if project_idx >= len(self._current_value):
            return
        old_proj = copy.deepcopy(self._current_value)
        new_proj = copy.deepcopy(self._current_value)
        if bullet_idx < len(new_proj[project_idx].bullets):
            new_proj[project_idx].bullets[bullet_idx] = value
        if new_proj == old_proj:
            return
        self.section_edited.emit("Projects", old_proj, new_proj)
        self._current_value = copy.deepcopy(new_proj)
        self._old_value = copy.deepcopy(new_proj)

    # -- Education editor --

    def _build_education_editor(self, education: list[EducationItem]) -> None:
        for idx, edu in enumerate(education):
            card = QFrame()
            card.setObjectName("eduCard")
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)

            top_row = QHBoxLayout()
            top_lbl = QLabel(f"Education #{idx + 1}")
            top_lbl.setStyleSheet("font-weight: bold;")
            top_row.addWidget(top_lbl)
            top_row.addStretch()
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("deleteEduBtn")
            del_btn.setFixedWidth(60)
            del_btn.clicked.connect(lambda i=idx: self._delete_education(i))
            top_row.addWidget(del_btn)
            card_layout.addLayout(top_row)

            form = QFormLayout()

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

            location_le = QLineEdit(edu.location)
            location_le.editingFinished.connect(
                lambda i=idx, le=location_le: self._on_edu_field(i, "location", le.text())
            )
            form.addRow("Institution location:", location_le)

            cgpa_le = QLineEdit(edu.cgpa)
            cgpa_le.setPlaceholderText("e.g. 3.625 or 3.625/4.0")
            cgpa_le.editingFinished.connect(
                lambda i=idx, le=cgpa_le: self._on_edu_field(i, "cgpa", le.text())
            )
            form.addRow("CGPA / GPA:", cgpa_le)

            year_le = QLineEdit(edu.year)
            year_le.editingFinished.connect(
                lambda i=idx, le=year_le: self._on_edu_field(i, "year", le.text())
            )
            form.addRow("Year:", year_le)

            card_layout.addLayout(form)

            self._container_layout.addWidget(card)
            if idx < len(education) - 1:
                sep = QLabel("")
                sep.setFixedHeight(1)
                self._container_layout.addWidget(sep)

        add_btn = QPushButton("+ Add Education")
        add_btn.setObjectName("addEduBtn")
        add_btn.clicked.connect(self._add_education)
        self._container_layout.addWidget(add_btn)

    def _add_education(self) -> None:
        new_edu = copy.deepcopy(self._current_value)
        new_edu.append(EducationItem())
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._old_value), new_edu
        )
        self._current_value = copy.deepcopy(new_edu)
        self._old_value = copy.deepcopy(new_edu)
        self._reload()

    def _delete_education(self, idx: int) -> None:
        new_edu = copy.deepcopy(self._current_value)
        if idx < len(new_edu):
            new_edu.pop(idx)
        self.section_edited.emit(
            self._current_section, copy.deepcopy(self._old_value), new_edu
        )
        self._current_value = copy.deepcopy(new_edu)
        self._old_value = copy.deepcopy(new_edu)
        self._reload()

    def _on_edu_field(self, idx: int, field: str, value: str) -> None:
        new_edu = copy.deepcopy(self._current_value)
        old_edu = copy.deepcopy(self._old_value)
        setattr(new_edu[idx], field, value)
        self.section_edited.emit("Education", old_edu, new_edu)
        self._current_value = copy.deepcopy(new_edu)
        self._old_value = copy.deepcopy(new_edu)

    # -- Pending list commit --

    def save_pending_list(self) -> None:
        """Commit the active list or text editor before navigation/export."""
        if self._list_widget is not None:
            self._commit_list()
        if self._text_widget is not None:
            new_value = self._text_widget.toPlainText()
            if new_value != self._current_value:
                old_value = copy.deepcopy(self._current_value)
                self.section_edited.emit(
                    self._current_section,
                    old_value,
                    new_value,
                )
                self._current_value = new_value
                self._old_value = new_value

    def _commit_list(self, *_args) -> None:
        widget = self._list_widget
        if widget is None:
            return
        new_items = [
            widget.item(index).text().strip()
            for index in range(widget.count())
            if widget.item(index).text().strip()
        ]
        if new_items != self._current_value:
            old_items = copy.deepcopy(self._current_value)
            self.section_edited.emit(
                self._current_section,
                old_items,
                new_items,
            )
            self._current_value = copy.deepcopy(new_items)
            self._old_value = copy.deepcopy(new_items)

    # -- Scroll --

    def scroll_to_field(self, field_name: str) -> None:
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
