"""Final review panel for approving and exporting a resume revision."""
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
    """Display the exact working resume and its export readiness."""

    approved = Signal()
    export_docx_requested = Signal()
    export_pdf_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resumeReviewPanel")
        self._resume_loaded = False
        self._blockers: list[str] = []
        self._warnings: list[str] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Review Resume")
        title.setObjectName("reviewTitle")
        root.addWidget(title)

        helper = QLabel(
            "Review the final content below. Approval applies only to this "
            "revision; any later edit, undo, or redo requires approval again."
        )
        helper.setWordWrap(True)
        helper.setObjectName("reviewHelp")
        root.addWidget(helper)

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
        self._refresh_validation()

    def set_resume(self, resume: ResumeData | None) -> None:
        self._resume_loaded = resume is not None
        if resume is None:
            self.preview.clear()
            self._warnings = []
            self._blockers = ["No resume is loaded."]
            self.set_export_enabled(False)
            self._refresh_validation()
            return

        self.preview.setPlainText(to_markdown(resume))
        self._blockers = []
        self._warnings = self.validation_warnings(resume)
        self._refresh_validation()

    def set_review_issues(
        self,
        *,
        blockers: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        """Add workflow-level issues such as pending Fact Guard changes."""
        self._blockers = list(blockers or [])
        if warnings is not None:
            self._warnings = list(warnings)
        self._refresh_validation()

    def set_export_enabled(self, enabled: bool) -> None:
        self.docx_button.setEnabled(enabled)
        self.pdf_button.setEnabled(enabled)
        self.approval_label.setText(
            "Approved for export" if enabled else "Not approved for export"
        )
        self.approve_button.setText(
            "Approved" if enabled else "Approve Current Resume"
        )
        self._refresh_approve_enabled(enabled)

    def _refresh_approve_enabled(self, approved: bool = False) -> None:
        self.approve_button.setEnabled(
            self._resume_loaded and not self._blockers and not approved
        )

    def _refresh_validation(self) -> None:
        parts: list[str] = []
        if self._blockers:
            parts.append(
                "Resolve before approval:\n"
                + "\n".join(f"• {message}" for message in self._blockers)
            )
        if self._warnings:
            parts.append(
                "Recommended review:\n"
                + "\n".join(f"• {message}" for message in self._warnings)
            )
        if not parts:
            parts.append("All required resume information is ready for review.")
        self.validation_label.setText("\n\n".join(parts))
        self._refresh_approve_enabled(self.docx_button.isEnabled())

    @staticmethod
    def validation_warnings(resume: ResumeData) -> list[str]:
        warnings: list[str] = []
        if not resume.summary.strip():
            warnings.append("Professional summary is empty.")
        if not resume.experience:
            warnings.append("No professional experience is listed.")
        if not resume.skills:
            warnings.append("Skills section is empty.")
        if not resume.projects:
            warnings.append("Projects section is empty.")
        return warnings
