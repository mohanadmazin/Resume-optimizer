"""Master Profile page — build career profile and compile targeted resumes."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories.master_profile_repository import MasterProfileRepository
from app.domain.master_profile import (
    EmphasisType,
    MasterCareerProfile,
    ResumeCompilerConfig,
)
from app.services.evidence_vault import EvidenceVault
from app.services.profile_compiler import compile_resume

logger = logging.getLogger(__name__)


class MasterProfilePage(QWidget):
    """Master Career Profile — import, build, and compile targeted resumes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = MasterProfileRepository()
        self._vault = EvidenceVault()
        self._profile: MasterCareerProfile | None = None
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("Master Career Profile")
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        # ── Profile stats ──
        self._stats_label = QLabel("No profile loaded")
        layout.addWidget(self._stats_label)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        self._import_btn = QPushButton("Import from Resume")
        self._import_btn.setToolTip(
            "Extract career facts from all existing resumes into the vault"
        )
        self._import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self._import_btn)

        self._build_btn = QPushButton("Build Profile")
        self._build_btn.setToolTip(
            "Assemble master profile from all vault facts"
        )
        self._build_btn.clicked.connect(self._on_build)
        btn_row.addWidget(self._build_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Career entries tree ──
        entries_group = QGroupBox("Career Entries")
        entries_layout = QVBoxLayout(entries_group)
        self._entries_tree = QTreeWidget()
        self._entries_tree.setHeaderLabels(
            ["Role / Company", "Dates", "Bullets", "Tags"]
        )
        self._entries_tree.setSelectionMode(
            QTreeWidget.SelectionMode.SingleSelection
        )
        entries_layout.addWidget(self._entries_tree)
        layout.addWidget(entries_group)

        # ── Skills cloud ──
        skills_group = QGroupBox("Skills")
        skills_layout = QVBoxLayout(skills_group)
        self._skills_label = QLabel("")
        self._skills_label.setWordWrap(True)
        self._skills_label.setStyleSheet("padding: 8px;")
        skills_layout.addWidget(self._skills_label)
        layout.addWidget(skills_group)

        # ── Certifications ──
        certs_group = QGroupBox("Certifications")
        certs_layout = QVBoxLayout(certs_group)
        self._certs_label = QLabel("None")
        certs_layout.addWidget(self._certs_label)
        layout.addWidget(certs_group)

        # ── Resume Compiler section ──
        compiler_group = QGroupBox("Resume Compiler")
        compiler_layout = QVBoxLayout(compiler_group)

        # Job selection
        job_row = QHBoxLayout()
        job_row.addWidget(QLabel("Target Job:"))
        self._job_combo = QComboBox()
        self._job_combo.setMinimumWidth(250)
        self._refresh_jobs()
        job_row.addWidget(self._job_combo)
        job_row.addStretch()
        compiler_layout.addLayout(job_row)

        # Config row
        config_row = QHBoxLayout()
        config_row.addWidget(QLabel("Max Pages:"))
        self._max_pages = QLineEdit("1")
        self._max_pages.setMaximumWidth(50)
        config_row.addWidget(self._max_pages)

        config_row.addWidget(QLabel("Emphasis:"))
        self._emphasis_combo = QComboBox()
        self._emphasis_combo.addItems([e.value for e in EmphasisType])
        config_row.addWidget(self._emphasis_combo)

        self._compile_btn = QPushButton("Compile Resume")
        self._compile_btn.clicked.connect(self._on_compile)
        config_row.addWidget(self._compile_btn)
        config_row.addStretch()
        compiler_layout.addLayout(config_row)

        # Compiled output
        self._compiled_label = QLabel("Compile a resume to see output here.")
        self._compiled_label.setWordWrap(True)
        self._compiled_label.setStyleSheet(
            "padding: 8px; background-color: rgba(128,128,128,0.1);"
            " border-radius: 4px;"
        )
        compiler_layout.addWidget(self._compiled_label)

        layout.addWidget(compiler_group)

    def refresh(self) -> None:
        """Reload profile from database."""
        self._profile = self._repo.get()
        self._refresh_jobs()
        if self._profile is None:
            self._stats_label.setText(
                "No profile yet. Import facts from resumes, then build."
            )
            self._entries_tree.clear()
            self._skills_label.setText("")
            self._certs_label.setText("None")
            return

        self._stats_label.setText(
            f"{len(self._profile.entries)} entries | "
            f"{len(self._profile.skills)} skills | "
            f"{len(self._profile.certifications)} certifications | "
            f"{self._profile.total_fact_count} vault facts"
        )

        # Populate entries tree
        self._entries_tree.clear()
        for entry in self._profile.entries:
            item = QTreeWidgetItem([
                f"{entry.role} — {entry.company}" if entry.role else entry.company,
                f"{entry.date_from} → {entry.date_to}" if entry.date_from else "",
                str(len(entry.bullets)),
                ", ".join(entry.tags[:5]),
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, entry.id)
            self._entries_tree.addTopLevelItem(item)

            # Show bullets as children
            for bullet in entry.bullets:
                child = QTreeWidgetItem(["", "", bullet[:80], ""])
                item.addChild(child)

        # Skills
        if self._profile.skills:
            self._skills_label.setText(" | ".join(self._profile.skills))
        else:
            self._skills_label.setText("No skills imported yet.")

        # Certifications
        if self._profile.certifications:
            self._certs_label.setText(
                " | ".join(self._profile.certifications)
            )
        else:
            self._certs_label.setText("None")

    def _refresh_jobs(self) -> None:
        """Reload job descriptions into the combo box."""
        self._job_combo.clear()
        self._job_combo.addItem("(No job selected)", None)
        try:
            from app.database.repositories.job_repository import JobRepository
            repo = JobRepository()
            jobs = repo.get_all()
            for job in jobs:
                self._job_combo.addItem(job.title, job.id)
        except Exception:
            logger.debug("Could not load job descriptions", exc_info=True)

    def _on_import(self) -> None:
        """Import facts from all existing resumes into the vault."""
        from app.domain.resume import ResumeData

        try:
            from app.database.repositories.resume_repository import ResumeRepository
            resume_repo = ResumeRepository()
            resumes_raw = resume_repo.get_all()

            if not resumes_raw:
                QMessageBox.information(
                    self, "No Resumes",
                    "Import resumes first before building your career profile.",
                )
                return

            total_imported = 0
            for resume_info in resumes_raw:
                rid = resume_info.get("id") if isinstance(resume_info, dict) else resume_info.id
                orm_resume = resume_repo.get_by_id(rid)
                if orm_resume is None:
                    continue
                try:
                    resume_data = ResumeData.model_validate_json(orm_resume.data_json)
                except Exception:
                    continue
                ids = self._vault.import_from_resume_data(resume_data)
                total_imported += len(ids)

            QMessageBox.information(
                self, "Import Complete",
                f"Imported {total_imported} new facts from "
                f"{len(resumes_raw)} resume(s) into the vault.",
            )
            self.refresh()
        except Exception as exc:
            logger.exception("Failed to import from resumes")
            QMessageBox.warning(self, "Import Failed", str(exc))

    def _on_build(self) -> None:
        """Build master profile from vault facts."""
        try:
            profile = self._vault.build_master_profile()
            if not profile.entries and not profile.skills:
                QMessageBox.information(
                    self, "Empty Vault",
                    "No career facts in the vault yet. "
                    "Import from resumes first.",
                )
                return

            pid = self._repo.save(profile)
            profile.id = pid
            self._profile = profile
            self.refresh()
            QMessageBox.information(
                self, "Profile Built",
                f"Master profile created with "
                f"{len(profile.entries)} career entries and "
                f"{len(profile.skills)} skills.",
            )
        except Exception as exc:
            logger.exception("Failed to build profile")
            QMessageBox.warning(self, "Build Failed", str(exc))

    def _on_compile(self) -> None:
        """Compile a targeted resume from the master profile."""
        if self._profile is None:
            QMessageBox.information(
                self, "No Profile",
                "Build a master profile first before compiling.",
            )
            return

        # Get job requirements if a job is selected
        from app.domain.job_requirements import JobRequirements
        job_req = JobRequirements()
        job_id = self._job_combo.currentData()
        if job_id is not None:
            try:
                from app.database.repositories.job_repository import JobRepository
                job_repo = JobRepository()
                job = job_repo.get_by_id(job_id)
                if job:
                    job_req = JobRequirements(
                        required_skills=[
                            __import__(
                                "app.domain.job_requirements",
                                fromlist=["Requirement"],
                            ).Requirement(name=kw)
                            for kw in (job.content or "").split()
                            if len(kw) >= 3
                        ][:20],
                    )
            except Exception:
                logger.debug("Could not load job requirements", exc_info=True)

        # Parse config
        try:
            max_pages = int(self._max_pages.text() or "1")
        except ValueError:
            max_pages = 1
        emphasis = EmphasisType(self._emphasis_combo.currentText())

        config = ResumeCompilerConfig(
            max_pages=max_pages,
            emphasis=emphasis,
        )

        try:
            result = compile_resume(self._profile, job_req, config)

            # Format output
            lines = [f"Compiled {result.total_items} items:"]
            for section in result.sections:
                lines.append(f"\n  {section.section_name} "
                             f"({len(section.items)} items):")
                for item in section.items[:5]:
                    lines.append(f"    - {item.text[:60]}")
                if len(section.items) > 5:
                    lines.append(
                        f"    ... and {len(section.items) - 5} more"
                    )

            if result.exclusions:
                lines.append(
                    f"\n  Excluded {len(result.exclusions)} items"
                )

            self._compiled_label.setText("\n".join(lines))
        except Exception as exc:
            logger.exception("Compilation failed")
            QMessageBox.warning(self, "Compilation Failed", str(exc))
