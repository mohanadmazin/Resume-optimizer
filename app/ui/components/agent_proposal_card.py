"""Agent proposal card — displays a single agent action with Accept/Reject."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.domain.agent import AgentAction


class AgentProposalCard(QFrame):
    """Card showing one proposed change from the agent with Accept/Reject buttons."""

    accepted = Signal(int)  # action index in the proposal
    rejected = Signal(int)  # action index in the proposal

    def __init__(self, action: AgentAction, index: int, parent=None) -> None:
        super().__init__(parent)
        self._action = action
        self._index = index
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()

        tool_label = QLabel(action.tool.value.replace("_", " ").upper())
        tool_label.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 2px 8px; "
            "border-radius: 4px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(tool_label)

        if action.section:
            section_label = QLabel(action.section)
            section_label.setStyleSheet("color: #6B7280; font-size: 11px;")
            header.addWidget(section_label)

        header.addStretch()
        layout.addLayout(header)

        if action.description:
            desc = QLabel(action.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("font-size: 12px; color: #374151;")
            layout.addWidget(desc)

        if action.original:
            orig_label = QLabel("Current:")
            orig_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #6B7280;")
            layout.addWidget(orig_label)

            orig_text = QTextEdit()
            orig_text.setPlainText(action.original)
            orig_text.setReadOnly(True)
            orig_text.setMaximumHeight(60)
            orig_text.setStyleSheet("background-color: #F3F4F6; border: 1px solid #D1D5DB; border-radius: 4px; font-size: 12px;")
            layout.addWidget(orig_text)

        if action.proposed:
            prop_label = QLabel("Proposed:")
            prop_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            layout.addWidget(prop_label)

            prop_text = QTextEdit()
            prop_text.setPlainText(action.proposed)
            prop_text.setReadOnly(True)
            prop_text.setMaximumHeight(60)
            prop_text.setStyleSheet("background-color: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 4px; font-size: 12px;")
            layout.addWidget(prop_text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._accept_btn = QPushButton("Accept")
        self._accept_btn.setStyleSheet(
            "background-color: #059669; color: white; padding: 4px 16px; "
            "border-radius: 4px; font-size: 12px; font-weight: bold;"
        )
        self._accept_btn.clicked.connect(lambda: self.accepted.emit(self._index))
        btn_row.addWidget(self._accept_btn)

        self._reject_btn = QPushButton("Reject")
        self._reject_btn.setStyleSheet(
            "background-color: #DC2626; color: white; padding: 4px 16px; "
            "border-radius: 4px; font-size: 12px; font-weight: bold;"
        )
        self._reject_btn.clicked.connect(lambda: self.rejected.emit(self._index))
        btn_row.addWidget(self._reject_btn)

        layout.addLayout(btn_row)

    def set_decided(self, accepted: bool) -> None:
        """Disable buttons after a decision is made."""
        self._accept_btn.setEnabled(False)
        self._reject_btn.setEnabled(False)
        if accepted:
            self._accept_btn.setText("Accepted")
            self._reject_btn.hide()
        else:
            self._reject_btn.setText("Rejected")
            self._accept_btn.hide()
