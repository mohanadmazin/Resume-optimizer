"""Evidence Vault page — manage verified career facts and sources."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.domain.evidence import CareerFact, FactConfidence, FactType
from app.services.evidence_vault import EvidenceVault

logger = logging.getLogger(__name__)

FACT_TYPES = [ft.value for ft in FactType]
CONFIDENCE_LEVELS = [fc.value for fc in FactConfidence]


class _FactDialog(QDialog):
    """Dialog for adding/editing a career fact."""

    def __init__(self, parent=None, fact: CareerFact | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Fact" if fact else "Add Fact")
        self.setMinimumWidth(500)
        self._fact = fact

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Statement:"))
        self._statement = QTextEdit()
        self._statement.setPlainText(fact.statement if fact else "")
        self._statement.setMaximumHeight(100)
        layout.addWidget(self._statement)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Type:"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(FACT_TYPES)
        if fact:
            idx = FACT_TYPES.index(fact.fact_type.value) if fact.fact_type.value in FACT_TYPES else 0
            self._type_combo.setCurrentIndex(idx)
        row1.addWidget(self._type_combo)
        row1.addWidget(QLabel("Confidence:"))
        self._conf_combo = QComboBox()
        self._conf_combo.addItems(CONFIDENCE_LEVELS)
        if fact:
            idx = CONFIDENCE_LEVELS.index(fact.confidence.value) if fact.confidence.value in CONFIDENCE_LEVELS else 2
            self._conf_combo.setCurrentIndex(idx)
        row1.addWidget(self._conf_combo)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Employer:"))
        self._employer = QLineEdit(fact.employer if fact else "")
        row2.addWidget(self._employer)
        row2.addWidget(QLabel("Project:"))
        self._project = QLineEdit(fact.project if fact else "")
        row2.addWidget(self._project)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("From:"))
        self._date_from = QLineEdit(fact.date_from if fact else "")
        self._date_from.setPlaceholderText("YYYY-MM")
        row3.addWidget(self._date_from)
        row3.addWidget(QLabel("To:"))
        self._date_to = QLineEdit(fact.date_to if fact else "")
        self._date_to.setPlaceholderText("YYYY-MM or Present")
        row3.addWidget(self._date_to)
        layout.addLayout(row3)

        layout.addWidget(QLabel("Notes:"))
        self._notes = QTextEdit()
        self._notes.setPlainText(fact.notes if fact else "")
        self._notes.setMaximumHeight(80)
        layout.addWidget(self._notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> dict[str, object]:
        return {
            "statement": self._statement.toPlainText().strip(),
            "fact_type": FactType(self._type_combo.currentText()),
            "confidence": FactConfidence(self._conf_combo.currentText()),
            "employer": self._employer.text().strip(),
            "project": self._project.text().strip(),
            "date_from": self._date_from.text().strip(),
            "date_to": self._date_to.text().strip(),
            "notes": self._notes.toPlainText().strip(),
        }


class EvidenceVaultPage(QWidget):
    """Career Evidence Vault — browse, add, and verify career facts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vault = EvidenceVault()
        self._selected_fact_id: int | None = None
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("Evidence Vault")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        stats_row = QHBoxLayout()
        self._stats_label = QLabel("")
        stats_row.addWidget(self._stats_label)
        stats_row.addStretch()

        self._filter_type = QComboBox()
        self._filter_type.addItem("All Types")
        self._filter_type.addItems(FACT_TYPES)
        self._filter_type.currentTextChanged.connect(self._apply_filter)
        stats_row.addWidget(QLabel("Filter:"))
        stats_row.addWidget(self._filter_type)
        layout.addLayout(stats_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search facts...")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("Add Fact")
        self._add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self._add_btn)
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.clicked.connect(self._on_edit)
        self._edit_btn.setEnabled(False)
        btn_row.addWidget(self._edit_btn)
        self._verify_btn = QPushButton("Verify")
        self._verify_btn.clicked.connect(self._on_verify)
        self._verify_btn.setEnabled(False)
        btn_row.addWidget(self._verify_btn)
        self._reject_btn = QPushButton("Reject")
        self._reject_btn.clicked.connect(self._on_reject)
        self._reject_btn.setEnabled(False)
        btn_row.addWidget(self._reject_btn)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete)
        self._delete_btn.setEnabled(False)
        btn_row.addWidget(self._delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Statement", "Type", "Confidence", "Employer", "Date"])
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self._tree.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self._tree)

        self._detail_label = QLabel("")
        self._detail_label.setWordWrap(True)
        self._detail_label.setStyleSheet("color: #666; font-size: 12px; padding: 8px;")
        layout.addWidget(self._detail_label)

    def refresh(self) -> None:
        self._tree.clear()
        facts = self._vault.list_facts()
        for fact in facts:
            item = QTreeWidgetItem([
                fact.statement[:80],
                fact.fact_type.value,
                fact.confidence.value,
                fact.employer,
                f"{fact.date_from} → {fact.date_to}" if fact.date_from else "",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, fact.id)
            self._tree.addTopLevelItem(item)
        stats = self._vault.get_vault_stats()
        self._stats_label.setText(
            f"{stats['total_facts']} facts total"
        )
        self._selected_fact_id = None
        self._update_buttons()

    def _on_selection(self) -> None:
        items = self._tree.selectedItems()
        if items:
            self._selected_fact_id = items[0].data(0, Qt.ItemDataRole.UserRole)
            self._show_detail(self._selected_fact_id)
        else:
            self._selected_fact_id = None
            self._detail_label.setText("")
        self._update_buttons()

    def _show_detail(self, fact_id: int) -> None:
        fws = self._vault.get_fact_with_sources(fact_id)
        if fws is None:
            self._detail_label.setText("")
            return
        src_names = [s.name for s in fws.sources]
        src_str = ", ".join(src_names) if src_names else "None"
        self._detail_label.setText(
            f"<b>Full:</b> {fws.fact.statement}  |  "
            f"<b>Sources:</b> ({fws.linked_content_count} links) {src_str}"
        )

    def _update_buttons(self) -> None:
        has = self._selected_fact_id is not None
        self._edit_btn.setEnabled(has)
        self._delete_btn.setEnabled(has)
        self._verify_btn.setEnabled(has)
        self._reject_btn.setEnabled(has)

    def _on_add(self) -> None:
        dlg = _FactDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            fact = CareerFact(
                statement=data["statement"],
                fact_type=data["fact_type"],
                confidence=data["confidence"],
                employer=data["employer"],
                project=data["project"],
                date_from=data["date_from"],
                date_to=data["date_to"],
                notes=data["notes"],
            )
            self._vault.add_fact(fact)
            self.refresh()

    def _on_edit(self) -> None:
        if self._selected_fact_id is None:
            return
        fact = self._vault.get_fact(self._selected_fact_id)
        if fact is None:
            return
        dlg = _FactDialog(self, fact=fact)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._vault.update_fact(self._selected_fact_id, dlg.get_data())
            self.refresh()

    def _on_verify(self) -> None:
        if self._selected_fact_id is None:
            return
        self._vault.verify_fact(self._selected_fact_id, FactConfidence.USER_CONFIRMED)
        self.refresh()

    def _on_reject(self) -> None:
        if self._selected_fact_id is None:
            return
        self._vault.reject_fact(self._selected_fact_id)
        self.refresh()

    def _on_delete(self) -> None:
        if self._selected_fact_id is None:
            return
        reply = QMessageBox.question(
            self, "Delete Fact", "Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._vault.delete_fact(self._selected_fact_id)
            self.refresh()

    def _on_search(self, text: str) -> None:
        self._tree.clear()
        facts = self._vault.search_facts(text) if text else self._vault.list_facts()
        for fact in facts:
            item = QTreeWidgetItem([
                fact.statement[:80],
                fact.fact_type.value,
                fact.confidence.value,
                fact.employer,
                f"{fact.date_from} → {fact.date_to}" if fact.date_from else "",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, fact.id)
            self._tree.addTopLevelItem(item)

    def _apply_filter(self, type_text: str) -> None:
        self._tree.clear()
        ft = type_text if type_text != "All Types" else None
        facts = self._vault.list_facts(fact_type=ft)
        for fact in facts:
            item = QTreeWidgetItem([
                fact.statement[:80],
                fact.fact_type.value,
                fact.confidence.value,
                fact.employer,
                f"{fact.date_from} → {fact.date_to}" if fact.date_from else "",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, fact.id)
            self._tree.addTopLevelItem(item)
