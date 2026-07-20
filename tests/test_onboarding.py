"""Tests for the onboarding wizard."""
from __future__ import annotations

import pytest

from app.core.settings import settings_service


@pytest.fixture(autouse=True)
def _reset_onboarding():
    """Ensure onboarding is not completed before each test."""
    settings = settings_service.settings.model_copy(deep=True)
    settings.onboarding_completed = False
    settings_service.save(settings)
    yield
    settings = settings_service.settings.model_copy(deep=True)
    settings.onboarding_completed = True
    settings_service.save(settings)


@pytest.fixture(autouse=True)
def _qapp():
    """Ensure a QApplication exists for widget creation."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestOnboardingWizard:
    def test_wizard_creates(self):
        from app.ui.dialogs.onboarding import OnboardingWizard

        wizard = OnboardingWizard()
        assert wizard.windowTitle() == "Welcome to Resume Optimizer"
        assert wizard._stack.count() == 3

    def test_wizard_navigation(self):
        from app.ui.dialogs.onboarding import OnboardingWizard

        wizard = OnboardingWizard()
        assert wizard._stack.currentIndex() == 0
        assert not wizard._prev_btn.isEnabled()

        wizard._go_next()
        assert wizard._stack.currentIndex() == 1
        assert wizard._prev_btn.isEnabled()

        wizard._go_next()
        assert wizard._stack.currentIndex() == 2
        assert wizard._next_btn.isHidden()
        assert not wizard._finish_btn.isHidden()

        wizard._go_prev()
        assert wizard._stack.currentIndex() == 1
        assert not wizard._next_btn.isHidden()
        assert wizard._finish_btn.isHidden()

    def test_finish_saves_settings(self):
        from app.ui.dialogs.onboarding import OnboardingWizard

        wizard = OnboardingWizard()
        wizard._url_input.setText("http://custom:9999")
        wizard._theme_combo.setCurrentText("Light")
        wizard._stack.setCurrentIndex(2)

        wizard._finish()

        saved = settings_service.settings
        assert saved.onboarding_completed is True
        assert saved.ai.ollama_url == "http://custom:9999"
        assert saved.appearance.theme == "light"

    def test_finish_no_url_keeps_default(self):
        from app.ui.dialogs.onboarding import OnboardingWizard

        wizard = OnboardingWizard()
        wizard._stack.setCurrentIndex(2)
        wizard._finish()

        saved = settings_service.settings
        assert saved.onboarding_completed is True

    def test_already_completed(self):
        settings = settings_service.settings.model_copy(deep=True)
        settings.onboarding_completed = True
        settings_service.save(settings)

        from app.ui.dialogs.onboarding import OnboardingWizard  # noqa: F401
        OnboardingWizard()
        assert settings_service.settings.onboarding_completed is True
