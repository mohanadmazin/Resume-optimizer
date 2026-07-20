# app/ui/main_window.py

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from app.ui.pages.agent import AgentPage
from app.ui.pages.applications import ApplicationsPage
from app.ui.pages.ats_analysis import ATSAnalysisPage
from app.ui.pages.cover_letter import CoverLetterPage
from app.ui.pages.cover_letter_library import CoverLetterLibraryPage
from app.ui.pages.comparison import ComparisonPage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.evidence_vault import EvidenceVaultPage
from app.ui.pages.import_linkedin import LinkedInImportPage
from app.ui.pages.interview_prep import InterviewPrepPage
from app.ui.pages.job_description import JobDescriptionPage
from app.ui.pages.master_profile import MasterProfilePage
from app.ui.pages.requirement_matrix import RequirementMatrixPage
from app.ui.pages.discovery import DiscoveryPage
from app.ui.pages.optimization import OptimizationPage
from app.ui.pages.resume_upload import ResumeUploadPage
from app.ui.pages.salary_estimate import SalaryEstimatePage
from app.ui.pages.settings import SettingsPage
from app.ui.pages.skill_gap import SkillGapPage
from app.ui.pages.studio import ResumeStudioPage

# ResumeAI-style components
from app.ui.components.resumeai.sidebar import ResumeAiSidebar
from app.ui.components.resumeai.top_nav import ResumeAiTopNav
from app.ui.components.resumeai.section_menu import SectionMenu
from app.ui.pages.resumeai_contact import ResumeAiContactPage
from app.ui.pages.resumeai_placeholder import ResumeAiPlaceholderPage

from app.ui.state import AppState
from app.core.settings import settings_service

from app.ui.theme import (
    create_dark_theme,
    create_light_theme,
    DARK_STYLESHEET,
    LIGHT_STYLESHEET,
)


PAGE_NAMES = [
    "Dashboard",
    "Resume Upload",
    "Job Description",
    "ATS Analysis",
    "Optimization",
    "Resume Studio",
    "Agent",
    "Cover Letter",
    "Skill Gap",
    "Salary Estimate",
    "Applications",
    "Cover Letter Library",
    "Interview Prep",
    "LinkedIn Import",
    "Compare Resumes",
    "Evidence Vault",
    "Master Profile",
    "Requirement Matrix",
    "Discovery Interview",
    "Settings",
]

# Sidebar icon index -> page name
_SIDEBAR_PAGE_MAP = {
    0: "Resume Upload",
    1: "Dashboard",
    2: "Optimization",
    3: "Resume Studio",
    4: "Cover Letter",
    5: "Applications",
    6: "Settings",
}

# Section tab name -> ResumeAI page key
_SECTION_PAGE_MAP = {
    "CONTACT": "resumeai_contact",
    "EXPERIENCE": "resumeai_experience",
    "PROJECT": "resumeai_project",
    "EDUCATION": "resumeai_education",
    "CERTIFICATIONS": "resumeai_certifications",
    "COURSEWORK": "resumeai_coursework",
    "INVOLVEMENT": "resumeai_involvement",
    "SKILLS": "resumeai_skills",
    "SUMMARY": "resumeai_summary",
}


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Resume Optimizer")
        self.setMinimumSize(1366, 768)
        self.resize(2048, 1042)

        self.state = AppState()

        self.setup_ui()
        self.setup_pages()

        self.apply_theme(self.state.theme)

        settings_service.on_changed(self._on_settings_changed)

        self._show_onboarding_if_needed()

        QTimer.singleShot(1000, self._prewarm_model)

    # ── UI setup ───────────────────────────────────────────────────────

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Left: icon sidebar ──
        self._sidebar = ResumeAiSidebar()
        self._sidebar.page_selected.connect(self._on_sidebar_page)
        main_layout.addWidget(self._sidebar)

        # ── Right: top nav + content stack ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._top_nav = ResumeAiTopNav()
        self._top_nav.section_changed.connect(self._on_section_changed)
        self._top_nav.resume_dropdown_clicked.connect(self._on_resume_dropdown)
        self._top_nav.action_clicked.connect(self._on_action)
        right_layout.addWidget(self._top_nav)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)

        main_layout.addWidget(right_panel, 1)

        # ── Floating section menu ──
        self._section_menu = SectionMenu()
        self._section_menu.section_toggled.connect(self._on_section_toggled)
        self._top_nav.tab_bar.overflow_button.clicked.connect(self._toggle_section_menu)

        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+S"), self, self._shortcut_save)
        QShortcut(QKeySequence("Ctrl+E"), self, self._shortcut_export)
        QShortcut(QKeySequence("Ctrl+N"), self, self._shortcut_new_resume)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)

    # ── Page setup ─────────────────────────────────────────────────────

    def setup_pages(self):
        legacy_pages = [
            DashboardPage,
            ResumeUploadPage,
            JobDescriptionPage,
            ATSAnalysisPage,
            OptimizationPage,
            ResumeStudioPage,
            AgentPage,
            CoverLetterPage,
            SkillGapPage,
            SalaryEstimatePage,
            ApplicationsPage,
            CoverLetterLibraryPage,
            InterviewPrepPage,
            LinkedInImportPage,
            ComparisonPage,
            EvidenceVaultPage,
            MasterProfilePage,
            RequirementMatrixPage,
            DiscoveryPage,
            SettingsPage,
        ]

        self.pages = {}
        self.resumeai_pages = {}

        # Add legacy pages to the stack
        for idx, page_cls in enumerate(legacy_pages):
            page = page_cls(self)
            self.stack.addWidget(page)
            self.pages[PAGE_NAMES[idx]] = page

        # Add ResumeAI section pages
        resumeai_pages_map = {
            "resumeai_contact": lambda: ResumeAiContactPage(state=self.state),
            "resumeai_experience": lambda: ResumeAiPlaceholderPage("Experience"),
            "resumeai_project": lambda: ResumeAiPlaceholderPage("Project"),
            "resumeai_education": lambda: ResumeAiPlaceholderPage("Education"),
            "resumeai_certifications": lambda: ResumeAiPlaceholderPage("Certifications"),
            "resumeai_coursework": lambda: ResumeAiPlaceholderPage("Coursework"),
            "resumeai_involvement": lambda: ResumeAiPlaceholderPage("Involvement"),
            "resumeai_skills": lambda: ResumeAiPlaceholderPage("Skills"),
            "resumeai_summary": lambda: ResumeAiPlaceholderPage("Summary"),
        }

        for key, factory in resumeai_pages_map.items():
            page = factory()
            self.stack.addWidget(page)
            self.resumeai_pages[key] = page

        # Show contact page by default
        if "resumeai_contact" in self.resumeai_pages:
            self.stack.setCurrentWidget(self.resumeai_pages["resumeai_contact"])

    def get_page(self, name: str):
        return self.pages.get(name)

    @property
    def nav(self):
        """Compatibility shim for legacy pages that reference self.window.nav."""
        return _NavCompat(self)

    # ── Navigation ──────────────────────────────────────────────────────

    def _switch(self, index: int):
        self.stack.setCurrentIndex(index)
        page = self.stack.widget(index)
        if hasattr(page, "on_show"):
            page.on_show()

    def _on_sidebar_page(self, index: int) -> None:
        target = _SIDEBAR_PAGE_MAP.get(index)
        if target and target in PAGE_NAMES:
            idx = PAGE_NAMES.index(target)
            self._switch(idx)

    def _on_section_changed(self, name: str) -> None:
        page_key = _SECTION_PAGE_MAP.get(name)
        if page_key and page_key in self.resumeai_pages:
            self.stack.setCurrentWidget(self.resumeai_pages[page_key])

    def _toggle_section_menu(self) -> None:
        if self._section_menu.isVisible():
            self._section_menu.hide()
            return
        btn = self._top_nav.tab_bar.overflow_button
        pos = btn.mapToGlobal(btn.rect().bottomLeft())
        self._section_menu.move(pos.x(), pos.y() + 4)
        self._section_menu.show()
        self._section_menu.raise_()

    def _on_section_toggled(self, name: str, visible: bool) -> None:
        self._top_nav.tab_bar.set_section_visible(name, visible)

    def _on_resume_dropdown(self) -> None:
        self.notify("Resume dropdown — select a saved resume")

    def _on_action(self, action: str) -> None:
        if action == "ai_cover_letter":
            self._switch(PAGE_NAMES.index("Cover Letter"))
        else:
            self.notify(action.replace("_", " ").title())

    def _on_escape(self) -> None:
        if self._section_menu.isVisible():
            self._section_menu.hide()

    # ── Shortcuts ───────────────────────────────────────────────────────

    def _shortcut_save(self) -> None:
        page = self.stack.currentWidget()
        if hasattr(page, "force_save"):
            page.force_save()
            self.notify("Saved.")
        else:
            self.notify("No save action available on this page.")

    def _shortcut_export(self) -> None:
        page = self.stack.currentWidget()
        if hasattr(page, "export"):
            page.export()
        else:
            self.notify("No export action available on this page.")

    def _shortcut_new_resume(self) -> None:
        idx = PAGE_NAMES.index("Resume Upload")
        self._switch(idx)

    # ── Theme ───────────────────────────────────────────────────────────

    def apply_theme(self, theme):
        theme = theme.lower()
        if theme == "system":
            theme = self._detect_system_theme()

        if theme == "dark":
            palette = create_dark_theme()
            stylesheet = DARK_STYLESHEET
        elif theme == "light":
            palette = create_light_theme()
            stylesheet = LIGHT_STYLESHEET
        else:
            palette = create_dark_theme()
            stylesheet = DARK_STYLESHEET

        qpalette = self.palette()
        for role, color in palette.items():
            qpalette.setColor(role, color)
        self.setPalette(qpalette)
        self.setStyleSheet(stylesheet)
        self.state.set_theme(theme)

    @staticmethod
    def _detect_system_theme() -> str:
        try:
            from PySide6.QtCore import QSettings
            qs = QSettings()
            dark_key = qs.value("AppsUseDarkTheme", None)
            if dark_key is not None:
                return "light" if int(dark_key) == 0 else "dark"
        except Exception:
            pass
        return "dark"

    # ── Notifications ───────────────────────────────────────────────────

    def notify(self, message: str):
        self.statusBar().showMessage(message, 8000)

    # ── Background tasks ────────────────────────────────────────────────

    def _prewarm_model(self) -> None:
        from app.ui.workers import Worker

        def _do_warm():
            from app.ai.ollama_client import OllamaClient
            return OllamaClient().pre_warm()

        self._warm_worker = Worker(_do_warm)
        self._warm_worker.result.connect(lambda ok: None)
        self._warm_worker.start()

    def _on_settings_changed(self, settings) -> None:
        if hasattr(self, 'ollama_status'):
            self.ollama_status.set_base_url(settings.ai.ollama_url)

    def _show_onboarding_if_needed(self) -> None:
        if settings_service.settings.onboarding_completed:
            return
        from app.ui.dialogs.onboarding import OnboardingWizard
        wizard = OnboardingWizard(self)
        result = wizard.exec()
        if result == OnboardingWizard.DialogCode.Accepted:
            self.state.reload_settings()
            self.apply_theme(self.state.theme)


class _NavCompat:
    """Compatibility shim so legacy pages can call self.window.nav.setCurrentRow()."""

    def __init__(self, window: MainWindow) -> None:
        self._window = window

    def setCurrentRow(self, index: int) -> None:
        target = _SIDEBAR_PAGE_MAP.get(index)
        if target and target in PAGE_NAMES:
            self._window._switch(PAGE_NAMES.index(target))

    def findItems(self, name: str, _flags=None) -> list:
        if name in PAGE_NAMES:
            return [name]
        return []

    def setCurrentItem(self, item) -> None:
        if item in PAGE_NAMES:
            self._window._switch(PAGE_NAMES.index(item))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
