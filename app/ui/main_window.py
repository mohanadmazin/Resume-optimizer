# app/ui/main_window.py
from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import settings_service
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
from app.ui.pages.studio import ResumeStudioPage
from app.ui.state import AppState
from app.ui.theme import (
    DARK_STYLESHEET,
    LIGHT_STYLESHEET,
    create_dark_theme,
    create_light_theme,
)

PAGE_SPECS = (
    ("Dashboard", DashboardPage),
    ("Resume Upload", ResumeUploadPage),
    ("Resume Studio", ResumeStudioPage),
    ("Job Description", JobDescriptionPage),
    ("ATS Analysis", ATSAnalysisPage),
    ("Optimization", OptimizationPage),
    ("Cover Letter", CoverLetterPage),
    ("Skill Gap", SkillGapPage),
    ("Salary Estimate", SalaryEstimatePage),
    ("Settings", SettingsPage),
)
PAGE_NAMES = [name for name, _page_type in PAGE_SPECS]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Resume Optimizer")
        self.resize(1180, 760)

        self.state = AppState()
        self.pages: dict[str, QWidget] = {}
        self._warm_worker = None

        self.setup_ui()
        self.setup_pages()
        self.apply_theme(self.state.theme)
        settings_service.on_changed(self._on_settings_changed)
        QTimer.singleShot(1000, self._prewarm_model)

    def setup_ui(self) -> None:
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

        theme_layout = QHBoxLayout()
        self.theme_label = QLabel("Theme:")
        self.themeComboBox = QComboBox()
        self.themeComboBox.addItems(["Light", "Dark"])
        self.themeComboBox.setCurrentText(self.state.theme.capitalize())
        theme_layout.addWidget(self.theme_label)
        theme_layout.addWidget(self.themeComboBox)
        theme_layout.addItem(
            QSpacerItem(
                40,
                20,
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
        )
        main_layout.addLayout(theme_layout)

        self.nav.currentRowChanged.connect(self._switch)
        self.themeComboBox.currentTextChanged.connect(
            lambda value: self.apply_theme(value.lower())
        )

        self.ollama_status = OllamaStatusLabel(self.state.ollama_url)
        self.statusBar().addPermanentWidget(self.ollama_status)

    def setup_pages(self) -> None:
        for name, page_type in PAGE_SPECS:
            page = page_type(self)
            self.stack.addWidget(page)
            self.pages[name] = page

        # Explicit startup selection ensures Dashboard.on_show() runs.
        self.nav.setCurrentRow(0)

    def apply_theme(self, theme: str) -> None:
        theme = theme.lower()
        if theme == "dark":
            palette = create_dark_theme()
            stylesheet = DARK_STYLESHEET
        elif theme == "light":
            palette = create_light_theme()
            stylesheet = LIGHT_STYLESHEET
        else:
            raise ValueError("Invalid theme name")

        qt_palette = self.palette()
        for role, color in palette.items():
            qt_palette.setColor(role, color)
        self.setPalette(qt_palette)
        self.setStyleSheet(stylesheet)
        self.state.set_theme(theme)

        if self.themeComboBox.currentText().lower() != theme:
            self.themeComboBox.blockSignals(True)
            self.themeComboBox.setCurrentText(theme.capitalize())
            self.themeComboBox.blockSignals(False)

    def get_page(self, name: str) -> QWidget | None:
        return self.pages.get(name)

    def _switch(self, index: int) -> None:
        if index < 0 or index >= self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        page = self.stack.widget(index)
        if hasattr(page, "on_show"):
            page.on_show()

    def notify(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)

    def _prewarm_model(self) -> None:
        """Pre-warm Ollama in a background worker."""
        if self._warm_worker is not None:
            return

        from app.ai.ollama_client import OllamaClient
        from app.ui.workers import Worker

        worker = Worker(lambda: OllamaClient().pre_warm(), parent=self)
        self._warm_worker = worker
        worker.result.connect(lambda _result: None)
        worker.finished.connect(self._cleanup_warm_worker)
        worker.start()

    def _cleanup_warm_worker(self) -> None:
        worker = self._warm_worker
        self._warm_worker = None
        if worker is not None:
            worker.deleteLater()

    def _on_settings_changed(self, settings) -> None:
        self.ollama_status.set_base_url(settings.ai.ollama_url)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
