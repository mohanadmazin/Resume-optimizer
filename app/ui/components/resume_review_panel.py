"""Final resume review and export controls for Resume Studio."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.resume import ResumeData
from app.exports.exporter import to_markdown


class ResumeReviewPanel(QWidget):
    """Show the exact resume snapshot that can be approved for export."""

    approved = Signal()
    export_docx_requested = Signal()
    export_pdf_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resumeReviewPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Review Resume")
        title.setObjectName("reviewTitle")
        root.addWidget(title)

        self.validation_label = QLabel()
        self.validation_label.setObjectName("reviewValidation")
        self.validation_label.setWordWrap(True)
        root.addWidget(self.validation_label)

        self.preview = QTextEdit()
        self.preview.setObjectName("finalResumePreview")
        self.preview.setReadOnly(True)
        root.addWidget(self.preview, 1)

        self.approval_label = QLabel("Not approved for export")
        self.approval_label.setObjectName("reviewApprovalStatus")
        root.addWidget(self.approval_label)

        buttons = QHBoxLayout()
        self.approve_button = QPushButton("Approve Current Resume")
        self.approve_button.clicked.connect(self.approved.emit)
        buttons.addWidget(self.approve_button)
        buttons.addStretch()

        self.docx_button = QPushButton("Export DOCX")
        self.docx_button.clicked.connect(self.export_docx_requested.emit)
        buttons.addWidget(self.docx_button)

        self.pdf_button = QPushButton("Export PDF")
        self.pdf_button.clicked.connect(self.export_pdf_requested.emit)
        buttons.addWidget(self.pdf_button)
        root.addLayout(buttons)

        self.set_export_enabled(False)

    def set_resume(self, resume: ResumeData | None) -> None:
        if resume is None:
            self.preview.clear()
            self.validation_label.setText("No resume is loaded.")
            self.approve_button.setEnabled(False)
            self.set_export_enabled(False)
            return

        self.preview.setPlainText(to_markdown(resume))
        self.approve_button.setEnabled(True)
        warnings = self.validation_warnings(resume)
        if warnings:
            self.validation_label.setText(
                "Please review:\n" + "\n".join(f"• {warning}" for warning in warnings)
            )
        else:
            self.validation_label.setText(
                "All recommended resume information is present."
            )

    def set_export_enabled(self, enabled: bool) -> None:
        self.docx_button.setEnabled(enabled)
        self.pdf_button.setEnabled(enabled)
        self.approval_label.setText(
            "Approved for export" if enabled else "Not approved for export"
        )
        self.approve_button.setText(
            "Approved" if enabled else "Approve Current Resume"
        )

    @staticmethod
    def validation_warnings(resume: ResumeData) -> list[str]:
        warnings: list[str] = []
        if not resume.contact.name.strip():
            warnings.append("Candidate name is missing.")
        if not resume.contact.email.strip():
            warnings.append("Email address is missing.")
        if not resume.summary.strip():
            warnings.append("Professional summary is empty.")
        if not resume.experience:
            warnings.append("No professional experience is listed.")
        if not resume.skills:
            warnings.append("Skills section is empty.")
        return warnings
