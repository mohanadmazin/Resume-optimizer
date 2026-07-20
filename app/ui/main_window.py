# app/ui/main_window.py

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QLineEdit,
    QWidget,
    QComboBox,
    QLabel,
    QSpacerItem,
    QSizePolicy,
)

from app.ui.components.ollama_status import OllamaStatusLabel
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


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Resume Optimizer")
        self.resize(1180, 760)

        self.state = AppState()

        self.setup_ui()
        self.setup_pages()

        self.apply_theme(self.state.theme)

        settings_service.on_changed(self._on_settings_changed)

        self._show_onboarding_if_needed()

        # Pre-warm Ollama model in background after 1 second
        QTimer.singleShot(1000, self._prewarm_model)

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)


        content_layout = QHBoxLayout()

        nav_panel = QWidget()
        nav_panel.setFixedWidth(220)
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search)
        nav_layout.addWidget(self._search_input)

        self._search_results = QListWidget()
        self._search_results.setObjectName("nav")
        self._search_results.setMaximumHeight(150)
        self._search_results.currentRowChanged.connect(self._on_search_result_clicked)
        self._search_results.hide()
        nav_layout.addWidget(self._search_results)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.addItems(PAGE_NAMES)
        nav_layout.addWidget(self.nav)

        self.stack = QStackedWidget()

        content_layout.addWidget(nav_panel)
        content_layout.addWidget(self.stack)


        main_layout.addLayout(content_layout)


        # Theme selector
        theme_layout = QHBoxLayout()

        self.theme_label = QLabel("Theme:")

        self.themeComboBox = QComboBox()
        self.themeComboBox.addItems(
            [
                "Light",
                "Dark",
                "System",
            ]
        )
        current_theme = self.state.theme.capitalize()
        if current_theme in ("Light", "Dark", "System"):
            self.themeComboBox.setCurrentText(current_theme)
        else:
            self.themeComboBox.setCurrentText("Dark")


        theme_layout.addWidget(
            self.theme_label
        )

        theme_layout.addWidget(
            self.themeComboBox
        )


        spacer = QSpacerItem(
            40,
            20,
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )

        theme_layout.addItem(spacer)

        main_layout.addLayout(theme_layout)


        self.nav.currentRowChanged.connect(
            self._switch
        )


        self.themeComboBox.currentTextChanged.connect(
            lambda x: self.apply_theme(x.lower())
        )

        # Ollama status indicator in the status bar
        self.ollama_status = OllamaStatusLabel(self.state.ollama_url)
        self.statusBar().addPermanentWidget(self.ollama_status)

        self._setup_shortcuts()



    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+S"), self, self._shortcut_save)
        QShortcut(QKeySequence("Ctrl+E"), self, self._shortcut_export)
        QShortcut(QKeySequence("Ctrl+N"), self, self._shortcut_new_resume)
        QShortcut(QKeySequence("Ctrl+Left"), self, self._shortcut_prev_page)
        QShortcut(QKeySequence("Ctrl+Right"), self, self._shortcut_next_page)
        for i in range(1, 10):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, lambda idx=i: self._shortcut_goto_page(idx - 1))
        QShortcut(QKeySequence("Ctrl+0"), self, lambda: self._shortcut_goto_page(9))

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
        idx = PAGE_NAMES.index("Resume Upload") if "Resume Upload" in PAGE_NAMES else 0
        self.nav.setCurrentRow(idx)

    def _shortcut_prev_page(self) -> None:
        current = self.nav.currentRow()
        if current > 0:
            self.nav.setCurrentRow(current - 1)

    def _shortcut_next_page(self) -> None:
        current = self.nav.currentRow()
        if current < len(PAGE_NAMES) - 1:
            self.nav.setCurrentRow(current + 1)

    def _shortcut_goto_page(self, index: int) -> None:
        if 0 <= index < len(PAGE_NAMES):
            self.nav.setCurrentRow(index)

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

            # Fall back to dark for unknown themes
            palette = create_dark_theme()
            stylesheet = DARK_STYLESHEET


        qpalette = self.palette()

        for role, color in palette.items():

            qpalette.setColor(
                role,
                color
            )


        self.setPalette(
            qpalette
        )


        self.setStyleSheet(
            stylesheet
        )


        # Save selected theme
        self.state.set_theme(
            theme
        )

        # Keep dropdown synchronized
        if hasattr(self, "themeComboBox"):
            if self.themeComboBox.currentText().lower() != theme:
                self.themeComboBox.blockSignals(True)
                self.themeComboBox.setCurrentText(
                    theme.capitalize()
                )
                self.themeComboBox.blockSignals(False)

    @staticmethod
    def _detect_system_theme() -> str:
        """Detect the OS color scheme. Falls back to 'dark'."""
        try:
            from PySide6.QtCore import QSettings
            qs = QSettings()
            accent = qs.value("AccentColor", "")
            if isinstance(accent, str) and accent:
                # Windows accent color presence usually indicates light mode
                # unless the user has explicitly set dark mode
                dark_key = qs.value("AppsUseDarkTheme", None)
                if dark_key is not None:
                    return "light" if int(dark_key) == 0 else "dark"
        except Exception:
            pass
        return "dark"



    def setup_pages(self):

        pages = [
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

        for idx, page_cls in enumerate(pages):
            page = page_cls(self)
            self.stack.addWidget(page)
            self.pages[PAGE_NAMES[idx]] = page

    def get_page(self, name: str):
        return self.pages.get(name)



    def _switch(self, index: int):

        self.stack.setCurrentIndex(index)

        page = self.stack.widget(index)

        if hasattr(page, "on_show"):

            page.on_show()



    def notify(self, message: str):

        self.statusBar().showMessage(
            message,
            8000
        )

    def _prewarm_model(self) -> None:
        """Pre-warm Ollama model in background to reduce first-request latency."""
        from app.ui.workers import Worker

        def _do_warm():
            from app.ai.ollama_client import OllamaClient
            return OllamaClient().pre_warm()

        self._warm_worker = Worker(_do_warm)
        self._warm_worker.result.connect(
            lambda ok: None  # silently succeed or skip
        )
        self._warm_worker.start()

    def _on_settings_changed(self, settings) -> None:
        """React to settings changes from any source."""
        if hasattr(self, 'ollama_status'):
            self.ollama_status.set_base_url(settings.ai.ollama_url)

    def _show_onboarding_if_needed(self) -> None:
        """Show the onboarding wizard on first launch."""
        if settings_service.settings.onboarding_completed:
            return

        from app.ui.dialogs.onboarding import OnboardingWizard

        wizard = OnboardingWizard(self)
        result = wizard.exec()
        if result == OnboardingWizard.DialogCode.Accepted:
            self.state.reload_settings()
            self.apply_theme(self.state.theme)

    def _on_search(self, text: str) -> None:
        from app.services.global_search import global_search

        q = text.strip()
        if not q:
            self._search_results.hide()
            self._search_results.clear()
            return

        hits = global_search(q, limit=10)
        self._search_results.clear()
        self._search_hits = hits

        for hit in hits:
            label = f"[{hit.entity_type}] {hit.title}"
            item = QListWidgetItem(label)
            item.setToolTip(hit.snippet)
            self._search_results.addItem(item)

        self._search_results.setVisible(len(hits) > 0)

    def _on_search_result_clicked(self, row: int) -> None:
        if row < 0 or not hasattr(self, "_search_hits"):
            return
        hits = self._search_hits
        if row >= len(hits):
            return

        hit = hits[row]
        target_page = hit.page

        if target_page in PAGE_NAMES:
            idx = PAGE_NAMES.index(target_page)
            self.nav.setCurrentRow(idx)

        self._search_input.clear()
        self._search_results.hide()


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())