"""Main application window and navigation wiring."""
from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import settings_service
from app.ui.components.resumeai.section_menu import SectionMenu
from app.ui.components.resumeai.sidebar import ResumeAiSidebar
from app.ui.components.resumeai.top_nav import ResumeAiTopNav
from app.ui.pages.agent import AgentPage
from app.ui.pages.applications import ApplicationsPage
from app.ui.pages.ats_analysis import ATSAnalysisPage
from app.ui.pages.comparison import ComparisonPage
from app.ui.pages.cover_letter import CoverLetterPage
from app.ui.pages.cover_letter_library import CoverLetterLibraryPage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.discovery import DiscoveryPage
from app.ui.pages.evidence_vault import EvidenceVaultPage
from app.ui.pages.import_linkedin import LinkedInImportPage
from app.ui.pages.interview_prep import InterviewPrepPage
from app.ui.pages.job_description import JobDescriptionPage
from app.ui.pages.master_profile import MasterProfilePage
from app.ui.pages.optimization import OptimizationPage
from app.ui.pages.requirement_matrix import RequirementMatrixPage
from app.ui.pages.resume_upload import ResumeUploadPage
from app.ui.pages.salary_estimate import SalaryEstimatePage
from app.ui.pages.settings import SettingsPage
from app.ui.pages.skill_gap import SkillGapPage
from app.ui.pages.studio import ResumeStudioPage
from app.ui.state import AppState
from app.ui.theme import (
    DARK_STYLESHEET,
    LIGHT_STYLESHEET,
    create_dark_theme,
    create_light_theme,
)


PAGE_SPECS = [
    ("Dashboard", DashboardPage),
    ("Resume Upload", ResumeUploadPage),
    ("Job Description", JobDescriptionPage),
    ("ATS Analysis", ATSAnalysisPage),
    ("Optimization", OptimizationPage),
    ("Resume Studio", ResumeStudioPage),
    ("Agent", AgentPage),
    ("Cover Letter", CoverLetterPage),
    ("Skill Gap", SkillGapPage),
    ("Salary Estimate", SalaryEstimatePage),
    ("Applications", ApplicationsPage),
    ("Cover Letter Library", CoverLetterLibraryPage),
    ("Interview Prep", InterviewPrepPage),
    ("LinkedIn Import", LinkedInImportPage),
    ("Compare Resumes", ComparisonPage),
    ("Evidence Vault", EvidenceVaultPage),
    ("Master Profile", MasterProfilePage),
    ("Requirement Matrix", RequirementMatrixPage),
    ("Discovery Interview", DiscoveryPage),
    ("Settings", SettingsPage),
]
PAGE_NAMES = [name for name, _page_type in PAGE_SPECS]

# Sidebar icon index -> application page name.
_SIDEBAR_PAGE_MAP = {
    0: "Resume Upload",
    1: "Dashboard",
    2: "Optimization",
    3: "Resume Studio",
    4: "Cover Letter",
    5: "Applications",
    6: "Settings",
}

# Top navigation tab -> existing Resume Studio destination.
_SECTION_STUDIO_MAP = {
    "CONTACT": "Contact",
    "SUMMARY": "Summary",
    "EXPERIENCE": "Experience",
    "PROJECTS": "Projects",
    "EDUCATION": "Education",
    "SKILLS": "Skills",
    "CERTIFICATIONS": "Certifications",
    "LANGUAGES": "Languages",
    "REVIEW": "Review",
}
_STUDIO_SECTION_MAP = {value: key for key, value in _SECTION_STUDIO_MAP.items()}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Resume Optimizer")
        self.setMinimumSize(1366, 768)
        self.resize(2048, 1042)

        self.state = AppState()
        self.pages: dict[str, QWidget] = {}

        self.setup_ui()
        self.setup_pages()
        self.apply_theme(self.state.theme)

        settings_service.on_changed(self._on_settings_changed)
        self._show_onboarding_if_needed()
        QTimer.singleShot(1000, self._prewarm_model)

    # ── UI setup ────────────────────────────────────────────────────

    def setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._sidebar = ResumeAiSidebar()
        self._sidebar.page_selected.connect(self._on_sidebar_page)
        main_layout.addWidget(self._sidebar)

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

        self._section_menu = SectionMenu()
        self._section_menu.section_toggled.connect(self._on_section_toggled)
        self._top_nav.tab_bar.overflow_button.clicked.connect(
            self._toggle_section_menu
        )

        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+S"), self, self._shortcut_save)
        QShortcut(QKeySequence("Ctrl+E"), self, self._shortcut_export)
        QShortcut(QKeySequence("Ctrl+N"), self, self._shortcut_new_resume)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)

    # ── Page setup ──────────────────────────────────────────────────

    def setup_pages(self) -> None:
        """Create every application page, including ResumeStudioPage."""
        for name, page_type in PAGE_SPECS:
            page = page_type(self)
            self.stack.addWidget(page)
            self.pages[name] = page

        studio = self.get_page("Resume Studio")
        if studio is not None and hasattr(studio, "destination_changed"):
            studio.destination_changed.connect(self._on_studio_destination_changed)

        # Top section tabs are the primary resume editing navigation.
        self._show_studio_destination("Contact")

    def get_page(self, name: str):
        return self.pages.get(name)

    @property
    def nav(self):
        """Compatibility shim for pages that still use QListWidget-style calls."""
        return _NavCompat(self)

    # ── Navigation ──────────────────────────────────────────────────

    def _switch(self, index: int) -> None:
        if index < 0 or index >= self.stack.count():
            return

        self.stack.setCurrentIndex(index)
        page = self.stack.widget(index)
        if hasattr(page, "on_show"):
            page.on_show()

    def _switch_to_page(self, name: str) -> None:
        page = self.get_page(name)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        if hasattr(page, "on_show"):
            page.on_show()

    def _on_sidebar_page(self, index: int) -> None:
        target = _SIDEBAR_PAGE_MAP.get(index)
        if target is None:
            return

        if target == "Resume Studio":
            destination = _SECTION_STUDIO_MAP.get(
                self._top_nav.tab_bar.selected_section,
                "Contact",
            )
            self._show_studio_destination(destination)
            return

        self._switch_to_page(target)

    def _show_studio_destination(self, destination: str) -> None:
        studio = self.get_page("Resume Studio")
        if studio is None:
            return

        self.stack.setCurrentWidget(studio)
        if hasattr(studio, "on_show"):
            studio.on_show()
        studio.show_destination(destination)
        self._sidebar.set_selected(3)

        tab_name = _STUDIO_SECTION_MAP.get(destination)
        if tab_name is not None:
            self._top_nav.tab_bar.select_tab(tab_name, emit_signal=False)

    def _on_section_changed(self, name: str) -> None:
        destination = _SECTION_STUDIO_MAP.get(name)
        if destination is not None:
            self._show_studio_destination(destination)

    def _on_studio_destination_changed(self, destination: str) -> None:
        tab_name = _STUDIO_SECTION_MAP.get(destination)
        if tab_name is not None:
            self._top_nav.tab_bar.select_tab(tab_name, emit_signal=False)

    def _toggle_section_menu(self) -> None:
        if self._section_menu.isVisible():
            self._section_menu.hide()
            return

        button = self._top_nav.tab_bar.overflow_button
        position = button.mapToGlobal(button.rect().bottomLeft())
        self._section_menu.move(position.x(), position.y() + 4)
        self._section_menu.show()
        self._section_menu.raise_()

    def _on_section_toggled(self, name: str, visible: bool) -> None:
        tab_name = name.upper()
        self._top_nav.tab_bar.set_section_visible(tab_name, visible)

    def _on_resume_dropdown(self) -> None:
        self.notify("Resume dropdown — select a saved resume")

    def _on_action(self, action: str) -> None:
        if action == "finish_preview":
            self._show_studio_destination("Review")
        elif action == "ai_cover_letter":
            self._switch_to_page("Cover Letter")
        else:
            self.notify(action.replace("_", " ").title())

    def _on_escape(self) -> None:
        if self._section_menu.isVisible():
            self._section_menu.hide()

    # ── Shortcuts ───────────────────────────────────────────────────

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
        self._switch_to_page("Resume Upload")

    # ── Theme ───────────────────────────────────────────────────────

    def apply_theme(self, theme: str) -> None:
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
            theme = "dark"

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

            settings = QSettings()
            dark_key = settings.value("AppsUseDarkTheme", None)
            if dark_key is not None:
                return "light" if int(dark_key) == 0 else "dark"
        except Exception:
            pass
        return "dark"

    # ── Notifications ───────────────────────────────────────────────

    def notify(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)

    # ── Background tasks ────────────────────────────────────────────

    def _prewarm_model(self) -> None:
        from app.ui.workers import Worker

        def _do_warm():
            from app.ai.ollama_client import OllamaClient

            return OllamaClient().pre_warm()

        worker = Worker(_do_warm, parent=self)
        self._warm_worker = worker
        worker.result.connect(lambda _ok: None)
        worker.finished.connect(self._cleanup_warm_worker)
        worker.start()

    def _cleanup_warm_worker(self) -> None:
        worker = getattr(self, "_warm_worker", None)
        self._warm_worker = None
        if worker is not None:
            worker.deleteLater()

    def _on_settings_changed(self, settings) -> None:
        if hasattr(self, "ollama_status"):
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
    """Compatibility shim for legacy pages using QListWidget-like navigation."""

    def __init__(self, window: MainWindow) -> None:
        self._window = window

    def setCurrentRow(self, index: int) -> None:
        target = _SIDEBAR_PAGE_MAP.get(index)
        if target is not None:
            self._window._switch_to_page(target)

    def findItems(self, name: str, _flags=None) -> list:
        return [name] if name in PAGE_NAMES else []

    def setCurrentItem(self, item) -> None:
        if item in PAGE_NAMES:
            self._window._switch_to_page(item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
