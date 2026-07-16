# app/ui/main_window.py

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QComboBox,
    QLabel,
    QSpacerItem,
    QSizePolicy,
)

from app.ui.components.ollama_status import OllamaStatusLabel
from app.ui.pages.ats_analysis import ATSAnalysisPage
from app.ui.pages.cover_letter import CoverLetterPage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.job_description import JobDescriptionPage
from app.ui.pages.optimization import OptimizationPage
from app.ui.pages.resume_upload import ResumeUploadPage
from app.ui.pages.salary_estimate import SalaryEstimatePage
from app.ui.pages.settings import SettingsPage
from app.ui.pages.skill_gap import SkillGapPage

from app.ui.state import AppState

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
    "Cover Letter",
    "Skill Gap",
    "Salary Estimate",
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

        self.apply_theme(
            self.state.theme    
        )

        # Pre-warm Ollama model in background after 1 second
        QTimer.singleShot(1000, self._prewarm_model)

    def apply_theme(self, theme):

        theme = theme.lower()


        if theme == "dark":

            self.setPalette(
                self.palette()
            )

            self.setStyleSheet(
                DARK_STYLESHEET
            )


        else:

            self.setStyleSheet(
                LIGHT_STYLESHEET
            )


        self.state.set_theme(
            theme
        )


        self.themeComboBox.blockSignals(
            True
        )


        self.themeComboBox.setCurrentText(
            theme.capitalize()
        )


        self.themeComboBox.blockSignals(
            False
        )
    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)


        content_layout = QHBoxLayout()


        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(220)
        self.nav.addItems(PAGE_NAMES)


        self.stack = QStackedWidget()


        content_layout.addWidget(self.nav)
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
            ]
        )
        self.themeComboBox.setCurrentText(
            self.state.theme.capitalize()
        )


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



    def apply_theme(self, theme):

        theme = theme.lower()

        if theme == "dark":

            palette = create_dark_theme()
            stylesheet = DARK_STYLESHEET

        elif theme == "light":

            palette = create_light_theme()
            stylesheet = LIGHT_STYLESHEET

        else:

            raise ValueError(
                "Invalid theme name"
            )


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



    def setup_pages(self):

        pages = [
            DashboardPage,
            ResumeUploadPage,
            JobDescriptionPage,
            ATSAnalysisPage,
            OptimizationPage,
            CoverLetterPage,
            SkillGapPage,
            SalaryEstimatePage,
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



if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())