param(
    [string]$RepoPath = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

Set-Location $RepoPath

if (-not (Test-Path ".git")) {
    Fail "Run this script from the Resume-optimizer repository root."
}

$requiredCommit = "81d4154"
git cat-file -e "$requiredCommit^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail "Commit 81d4154 is not available. Run: git fetch --all --prune"
}

$dirty = git status --porcelain
if ($dirty) {
    Write-Host "Your working tree has changes:" -ForegroundColor Yellow
    git status --short
    Fail "Commit or stash those changes before running this installer."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$branchName = "fix/non-destructive-studio-integration"
$currentBranch = git branch --show-current

if ($currentBranch -ne $branchName) {
    $branchExists = git branch --list $branchName
    if ($branchExists) {
        git switch $branchName
    } else {
        git switch -c $branchName
    }
    if ($LASTEXITCODE -ne 0) {
        Fail "Could not create or switch to $branchName."
    }
}

$backupTag = "backup/studio-before-merge-$timestamp"
git tag $backupTag
if ($LASTEXITCODE -ne 0) {
    Fail "Could not create backup tag."
}

Write-Host "Backup tag created: $backupTag" -ForegroundColor Green
Write-Host "Restoring the feature-rich Studio from $requiredCommit..." -ForegroundColor Cyan

$restoreFiles = @(
    "app/ui/main_window.py",
    "app/ui/pages/studio.py",
    "app/ui/components/section_editor.py",
    "app/ui/components/section_navigator.py",
    "app/ui/view_models/studio_vm.py",
    "tests/test_studio.py"
)

git checkout $requiredCommit -- $restoreFiles
if ($LASTEXITCODE -ne 0) {
    Fail "Could not restore the Studio files from $requiredCommit."
}

$pythonPatch = @'
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, pattern: str, replacement: str, *, flags: int = 0, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Could not apply integration step: {label}")
    return updated


# Main window: use the real Studio for top section tabs.
path = "app/ui/main_window.py"
text = read(path)
text = replace_once(
    text,
    r"# Section tab name -> ResumeAI page key\n_SECTION_PAGE_MAP = \{.*?\n\}",
    '''# Top section tab -> existing Resume Studio section
_SECTION_STUDIO_MAP = {
    "CONTACT": "Contact",
    "SUMMARY": "Summary",
    "EXPERIENCE": "Experience",
    "PROJECT": "Projects",
    "EDUCATION": "Education",
    "SKILLS": "Skills",
    "CERTIFICATIONS": "Certifications",
    "LANGUAGES": "Languages",
    "REVIEW": "Review",
}''',
    flags=re.S,
    label="main-window section map",
)
text = replace_once(
    text,
    r'''        # Add ResumeAI section pages\n.*?        # Show contact page by default\n        if "resumeai_contact" in self\.resumeai_pages:\n            self\.stack\.setCurrentWidget\(self\.resumeai_pages\["resumeai_contact"\]\)\n''',
    '''        # Top section tabs reuse the existing feature-rich Studio.
        # No duplicate placeholder pages are created.
        studio = self.pages.get("Resume Studio")
        if studio is not None:
            self.stack.setCurrentWidget(studio)
            studio.show_destination("Contact")
''',
    flags=re.S,
    label="remove placeholder pages",
)
text = replace_once(
    text,
    r'''    def _on_section_changed\(self, name: str\) -> None:\n.*?\n    def _toggle_section_menu''',
    '''    def _on_section_changed(self, name: str) -> None:
        section = _SECTION_STUDIO_MAP.get(name)
        studio = self.get_page("Resume Studio")
        if section is None or studio is None:
            return
        self.stack.setCurrentWidget(studio)
        studio.show_destination(section)

    def _toggle_section_menu''',
    flags=re.S,
    label="route top tabs to Studio",
)
text = replace_once(
    text,
    r'''    def _on_section_toggled\(self, name: str, visible: bool\) -> None:\n        self\._top_nav\.tab_bar\.set_section_visible\(name, visible\)''',
    '''    def _on_section_toggled(self, name: str, visible: bool) -> None:
        tab_name = name.upper()
        if tab_name == "PROJECTS":
            tab_name = "PROJECT"
        self._top_nav.tab_bar.set_section_visible(tab_name, visible)''',
    label="section-menu case mapping",
)
text = replace_once(
    text,
    r'''    def _on_action\(self, action: str\) -> None:\n.*?\n    def _on_escape''',
    '''    def _on_action(self, action: str) -> None:
        if action == "finish_preview":
            studio = self.get_page("Resume Studio")
            if studio is not None:
                self.stack.setCurrentWidget(studio)
                studio.show_destination("Review")
            return
        if action == "ai_cover_letter":
            self._switch(PAGE_NAMES.index("Cover Letter"))
            return
        self.notify(action.replace("_", " ").title())

    def _on_escape''',
    flags=re.S,
    label="finish-and-preview action",
)
write(path, text)


# Top tabs: only real editable sections plus Review.
path = "app/ui/components/resumeai/section_tabs.py"
text = read(path)
text = replace_once(
    text,
    r'''    DEFAULT_SECTIONS = \[\n.*?    \]''',
    '''    DEFAULT_SECTIONS = [
        "CONTACT",
        "SUMMARY",
        "EXPERIENCE",
        "PROJECT",
        "EDUCATION",
        "SKILLS",
        "CERTIFICATIONS",
        "LANGUAGES",
        "REVIEW",
    ]''',
    flags=re.S,
    label="top-tab section list",
)
write(path, text)


# View model: approved snapshot and review invalidation.
path = "app/ui/view_models/studio_vm.py"
text = read(path)
text = text.replace(
    "    custom_headings_changed = Signal()\n",
    "    custom_headings_changed = Signal()\n    reviewStateChanged = Signal()\n",
    1,
)
text = text.replace(
    "        self._custom_headings: dict[str, str] = {}\n",
    "        self._custom_headings: dict[str, str] = {}\n"
    "        self._revision = 0\n"
    "        self._approved_revision: int | None = None\n"
    "        self._approved_snapshot: ResumeData | None = None\n",
    1,
)
text = replace_once(
    text,
    r'''    @resume\.setter\n    def resume\(self, value: ResumeData \| None\) -> None:\n.*?\n    @property\n    def ats''',
    '''    @resume.setter
    def resume(self, value: ResumeData | None) -> None:
        self._undo_stack.clear()
        self._resume = copy.deepcopy(value)
        self._state.resume = copy.deepcopy(value)
        self._ats = None
        self._revision = 0
        self._approved_revision = None
        self._approved_snapshot = None
        self.undoStateChanged.emit()
        self.ats_changed.emit()
        self.reviewStateChanged.emit()
        self.resume_changed.emit()

    @property
    def ats''',
    flags=re.S,
    label="resume load/reset",
)
text = replace_once(
    text,
    r'''    @ats\.setter\n    def ats\(self, value: ATSResult \| None\) -> None:\n        self\._ats = value\n        self\._state\.ats = value\n        self\.ats_changed\.emit\(\)''',
    '''    @ats.setter
    def ats(self, value: ATSResult | None) -> None:
        # Studio ATS describes the editable draft. Keep state.ats as the
        # original pre-optimization baseline used elsewhere in the app.
        self._ats = value
        self.ats_changed.emit()''',
    label="separate Studio ATS",
)
review_api = '''
    # Review / approved export snapshot
    @property
    def revision(self) -> int:
        return self._revision

    @property
    def is_approved_for_export(self) -> bool:
        return (
            self._approved_revision is not None
            and self._approved_revision == self._revision
            and self._approved_snapshot is not None
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
        if self._approved_revision is None and self._approved_snapshot is None:
            return
        self._approved_revision = None
        self._approved_snapshot = None
        self.reviewStateChanged.emit()

    def _record_change(self) -> None:
        self._revision += 1
        self.invalidate_review()

'''
text = text.replace(
    "    # ── Section selection ────────────────────────────────────────────\n",
    review_api + "    # ── Section selection ────────────────────────────────────────────\n",
    1,
)
text = text.replace(
    "            self._apply_to_state()\n            self.undoStateChanged.emit()\n            self.resume_changed.emit()\n",
    "            self._apply_to_state()\n            self._record_change()\n            self.undoStateChanged.emit()\n            self.resume_changed.emit()\n",
    2,
)
text = text.replace(
    "        self._undo_stack.push(command)\n        self._apply_to_state()\n",
    "        self._undo_stack.push(command)\n        self._apply_to_state()\n        self._record_change()\n",
    1,
)
text = replace_once(
    text,
    r'''    def clear\(self\) -> None:\n        self\._undo_stack\.clear\(\)\n        self\.undoStateChanged\.emit\(\)''',
    '''    def clear(self) -> None:
        self._undo_stack.clear()
        self._resume = None
        self._ats = None
        self._approved_revision = None
        self._approved_snapshot = None
        self._revision = 0
        self.undoStateChanged.emit()
        self.ats_changed.emit()
        self.reviewStateChanged.emit()
        self.resume_changed.emit()''',
    label="complete Studio clear",
)
write(path, text)


# Studio page: preserve advanced features and add Review/export gating.
path = "app/ui/pages/studio.py"
text = read(path)
text = text.replace("import logging\n", "import logging\nimport re\n", 1)
text = text.replace("    QComboBox,\n", "    QComboBox,\n    QFileDialog,\n", 1)
text = text.replace("    QLabel,\n", "    QLabel,\n    QMessageBox,\n", 1)
text = text.replace(
    "from app.ui.components.resume_preview import ResumePreview\n",
    "from app.ui.components.resume_preview import ResumePreview\n"
    "from app.ui.components.resume_review_panel import ResumeReviewPanel\n",
    1,
)
text = text.replace(
    "        splitter.addWidget(self._nav)\n",
    "        # MainWindow's top tabs are the primary section navigation.\n"
    "        # Keep this navigator internally for order/rename behavior, but\n"
    "        # do not render a duplicate left-side section list.\n",
    1,
)
text = text.replace(
    '        self._tabs.addTab(self._preview, "Preview")\n',
    '        self._tabs.addTab(self._preview, "Preview")\n'
    "        self._review = ResumeReviewPanel()\n"
    "        self._review.approved.connect(self._approve_review)\n"
    '        self._review.export_docx_requested.connect(lambda: self._export_as("DOCX"))\n'
    '        self._review.export_pdf_requested.connect(lambda: self._export_as("PDF"))\n'
    '        self._tabs.addTab(self._review, "Review")\n',
    1,
)
text = text.replace("        splitter.setSizes([180, 600, 280])\n", "        splitter.setSizes([780, 300])\n", 1)
text = text.replace(
    "        self._vm.custom_headings_changed.connect(self._on_custom_headings_changed)\n",
    "        self._vm.custom_headings_changed.connect(self._on_custom_headings_changed)\n"
    "        self._vm.reviewStateChanged.connect(self._on_review_state_changed)\n",
    1,
)
text = text.replace("        self._export_btn.setEnabled(has)\n", "        self._export_btn.setEnabled(self._vm.is_approved_for_export)\n", 2)
show_destination = '''
    def show_destination(self, destination: str) -> None:
        """Open an editable section or the final Review screen."""
        self._editor.save_pending_list()
        if destination == "Review":
            self._show_review()
            return
        if destination not in SECTION_NAMES:
            return
        self._tabs.setCurrentWidget(self._editor)
        self._nav.select_section(self._vm.get_display_name(destination))
        self._vm.select_section(destination)
        value = self._vm.get_section_value(destination)
        self._editor.load(destination, copy.deepcopy(value))

'''
text = text.replace("    # ── Navigation ───────────────────────────────────────────────────\n", show_destination + "    # ── Navigation ───────────────────────────────────────────────────\n", 1)
text = text.replace(
    "    def _on_section_selected(self, name: str) -> None:\n        self._editor.save_pending_list()\n",
    "    def _on_section_selected(self, name: str) -> None:\n        self._editor.save_pending_list()\n        self._tabs.setCurrentWidget(self._editor)\n",
    1,
)
text = text.replace(
    "    def _on_section_changed(self, name: str) -> None:\n        self._editor.save_pending_list()\n",
    "    def _on_section_changed(self, name: str) -> None:\n        self._editor.save_pending_list()\n        self._tabs.setCurrentWidget(self._editor)\n",
    1,
)
text = replace_once(
    text,
    r'''    def _on_resume_changed\(self\) -> None:\n.*?\n    def _update_preview''',
    '''    def _on_resume_changed(self) -> None:
        resume = self._vm.resume
        if resume is not None:
            self._preview.set_markdown(to_markdown(resume))
        else:
            self._preview.clear()
        self._review.set_resume(resume)
        self._on_review_state_changed()

    def _update_preview''',
    flags=re.S,
    label="refresh Review",
)
review_methods = '''
    # Review and approved export
    def _show_review(self) -> None:
        self._editor.save_pending_list()
        self._review.set_resume(self._vm.resume)
        self._review.set_export_enabled(self._vm.is_approved_for_export)
        self._tabs.setCurrentWidget(self._review)

    def _blocking_export_issues(self) -> list[str]:
        resume = self._vm.resume
        if resume is None:
            return ["No resume is loaded."]
        issues: list[str] = []
        if not resume.contact.name.strip():
            issues.append("Candidate name is required.")
        if not resume.contact.email.strip():
            issues.append("Email address is required.")
        fact_guard = getattr(self.window.state, "fact_guard", None)
        flagged = getattr(fact_guard, "flagged_changes", []) if fact_guard else []
        pending = [c for c in flagged if getattr(c, "accepted", None) is None]
        if pending:
            issues.append(f"Review {len(pending)} pending AI-generated change(s).")
        return issues

    def _approve_review(self) -> None:
        self._editor.save_pending_list()
        issues = self._blocking_export_issues()
        if issues:
            QMessageBox.warning(
                self,
                "Resume cannot be approved",
                "\\n".join(f"• {issue}" for issue in issues),
            )
            return
        self._vm.approve_for_export()
        self.window.notify("Current resume revision approved for export.")

    def _on_review_state_changed(self) -> None:
        approved = self._vm.is_approved_for_export
        self._review.set_export_enabled(approved)
        self._export_btn.setEnabled(approved)

    @staticmethod
    def _safe_export_name(name: str) -> str:
        cleaned = re.sub(r'[<>:"/\\\\|?*\\x00-\\x1F]+', "_", name)
        return cleaned.strip(" ._") or "Resume"

    def _export_as(self, format_name: str) -> None:
        self._export_format.setCurrentText(format_name)
        self._on_export()

    def export(self) -> None:
        self._on_export()

'''
text = text.replace("    # ── Export ──────────────────────────────────────────────────────\n", review_methods + "    # ── Export ──────────────────────────────────────────────────────\n", 1)
text = replace_once(
    text,
    r'''    def _on_export\(self\) -> None:\n.*\Z''',
    '''    def _on_export(self) -> None:
        """Export the exact approved resume snapshot."""
        resume = self._vm.approved_resume
        if resume is None:
            QMessageBox.warning(
                self,
                "Review required",
                "Open Review and approve the current resume before exporting.",
            )
            return
        fmt = self._export_format.currentText()
        template_name = self._export_template.currentText()
        ext_map = {"PDF": "pdf", "DOCX": "docx", "Markdown": "md"}
        ext = ext_map.get(fmt, "pdf")
        default_name = self._safe_export_name(resume.contact.name)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Approved Resume",
            f"{default_name}_Resume.{ext}",
            f"{fmt} Files (*.{ext})",
        )
        if not path:
            return
        if not path.lower().endswith(f".{ext}"):
            path += f".{ext}"
        try:
            from app.exports.exporter import export_docx, export_markdown, export_pdf, get_template
            theme = get_template(template_name)
            if fmt == "PDF":
                export_pdf(resume, path, theme=theme)
            elif fmt == "DOCX":
                export_docx(resume, path, theme=theme)
            else:
                export_markdown(resume, path)
            QMessageBox.information(self, "Export Complete", f"Approved resume exported to:\\n{path}")
        except Exception as exc:
            logger.exception("Export failed")
            QMessageBox.critical(self, "Export Failed", str(exc))
''',
    flags=re.S,
    label="approved snapshot export",
)
write(path, text)


# Focused review regression tests.
review_tests = '''"""Tests for non-destructive Studio review integration."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.domain.resume import ContactInfo, ResumeData
from app.ui.view_models.studio_vm import ResumeStudioViewModel


def _state() -> MagicMock:
    state = MagicMock()
    state.resume = None
    state.ats = None
    state.job_text = ""
    state.fact_guard = None
    return state


def _resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Alice", email="alice@example.com"),
        summary="Engineer",
        skills=["Python"],
    )


def test_edit_invalidates_approved_snapshot() -> None:
    vm = ResumeStudioViewModel(_state())
    vm.resume = _resume()
    vm.approve_for_export()
    assert vm.is_approved_for_export
    vm.update_section("Summary", "Engineer", "Senior Engineer")
    assert not vm.is_approved_for_export
    assert vm.approved_resume is None


def test_approved_resume_is_defensive_copy() -> None:
    vm = ResumeStudioViewModel(_state())
    vm.resume = _resume()
    vm.approve_for_export()
    exported = vm.approved_resume
    assert exported is not None
    exported.summary = "Changed elsewhere"
    assert vm.approved_resume is not None
    assert vm.approved_resume.summary == "Engineer"


def test_studio_ats_does_not_overwrite_original_baseline() -> None:
    state = _state()
    original = object()
    state.ats = original
    vm = ResumeStudioViewModel(state)
    vm.ats = MagicMock()
    assert state.ats is original
'''
write("tests/test_studio_review.py", review_tests)

print("Integration edits applied successfully.")
'@

$tempPatch = Join-Path $env:TEMP "merge_resume_studio_$timestamp.py"
Set-Content -Path $tempPatch -Value $pythonPatch -Encoding UTF8
python $tempPatch
if ($LASTEXITCODE -ne 0) {
    Fail "Integration failed. Restore with: git reset --hard $backupTag"
}
Remove-Item $tempPatch -Force

Write-Host "Checking Python syntax..." -ForegroundColor Cyan
python -m compileall -q app tests
if ($LASTEXITCODE -ne 0) {
    Fail "Syntax validation failed. Restore with: git reset --hard $backupTag"
}

Write-Host "Running focused Studio tests..." -ForegroundColor Cyan
pytest tests/test_studio.py tests/test_studio_review.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Files were installed, but tests failed." -ForegroundColor Yellow
    Write-Host "Restore with: git reset --hard $backupTag"
    exit 1
}

Write-Host ""
Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "Branch: $branchName"
Write-Host "Backup tag: $backupTag"
Write-Host ""
Write-Host "Next commands:"
Write-Host "  python main.py"
Write-Host "  git status"
Write-Host "  git diff --stat"
Write-Host '  git add app tests'
Write-Host '  git commit -m "Integrate top section editing review and approved export"'
Write-Host "  git push -u origin $branchName"
