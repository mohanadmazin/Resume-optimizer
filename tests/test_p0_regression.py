"""Regression tests for P0 bug fixes: noise matching, cancellation, Studio page, pipeline."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

# Ensure QApplication exists for widget tests
_app = QApplication.instance() or QApplication(sys.argv)


# ── HTML noise matching (token-based) ─────────────────────────────────────


class TestNoiseTokenMatching:
    """Verify that noise detection uses token-based matching, not substring."""

    def test_tokenize_class_attr_with_string(self):
        from app.services.html_extractor import _tokenize_class_attr
        tokens = _tokenize_class_attr("job-card related-jobs sidebar")
        assert tokens == {"job", "card", "related", "jobs", "sidebar"}

    def test_tokenize_class_attr_with_list(self):
        from app.services.html_extractor import _tokenize_class_attr
        tokens = _tokenize_class_attr(["nav-bar", "cookie_banner"])
        assert "nav" in tokens
        assert "bar" in tokens
        assert "cookie" in tokens
        assert "banner" in tokens

    def test_tokenize_class_attr_underscores_normalized(self):
        from app.services.html_extractor import _tokenize_class_attr
        tokens = _tokenize_class_attr("my_class_name")
        assert tokens == {"my", "class", "name"}

    def test_has_noise_tokens_exact_match(self):
        from app.services.html_extractor import _has_noise_tokens, _NOISE_CLASS_HINTS
        assert _has_noise_tokens("sidebar", _NOISE_CLASS_HINTS)
        assert _has_noise_tokens("job-sidebar", _NOISE_CLASS_HINTS)

    def test_has_noise_tokens_no_false_positive(self):
        """Substring of a noise token should NOT match — only exact token matches."""
        from app.services.html_extractor import _has_noise_tokens, _NOISE_CLASS_HINTS
        # "sidebar" IS noise, but "card" is not — verify no substring false positives
        assert not _has_noise_tokens("card", _NOISE_CLASS_HINTS)
        assert not _has_noise_tokens("info-panel", _NOISE_CLASS_HINTS)

    def test_has_noise_tokens_empty_class(self):
        from app.services.html_extractor import _has_noise_tokens, _NOISE_CLASS_HINTS
        assert not _has_noise_tokens("", _NOISE_CLASS_HINTS)

    def test_noise_class_not_in_content(self):
        from app.services.html_extractor import strip_noise_tags
        from bs4 import BeautifulSoup
        html = (
            '<div class="sidebar">'
            '<p class="job-sidebar">Main job content here</p>'
            '</div>'
            '<div class="job-content"><p>Actual job description</p></div>'
        )
        soup = BeautifulSoup(html, "lxml")
        strip_noise_tags(soup)
        text = soup.get_text()
        assert "Actual job description" in text

    def test_real_world_false_positive_no_longer_strips(self):
        """Regression: class names like 'description' should not be noise-stripped."""
        from app.services.html_extractor import strip_noise_tags
        from bs4 import BeautifulSoup
        html = (
            '<div class="job-description">'
            '<p>We are looking for a senior Python engineer</p>'
            '</div>'
        )
        soup = BeautifulSoup(html, "lxml")
        strip_noise_tags(soup)
        text = soup.get_text()
        assert "senior Python engineer" in text

    def test_extract_text_full_pipeline(self):
        from app.services.html_extractor import extract_text_from_html
        html = (
            "<html><body>"
            '<div class="job-description">'
            "<h1>Software Engineer</h1>"
            "<p>Build scalable systems with Python and SQL.</p>"
            "</div>"
            '<div class="cookie-banner">Accept cookies</div>'
            '<div class="sidebar"><p>Related jobs</p></div>'
            "</body></html>"
        )
        text = extract_text_from_html(html)
        assert "Software Engineer" in text
        assert "Python" in text
        assert "Accept cookies" not in text


# ── Cancellation normalization ────────────────────────────────────────────


class TestCancellationNormalization:
    """PipelineWorker should emit cancelled for both OperationCancelled and OllamaCancelledError."""

    def test_operation_cancelled_emits_cancelled(self):
        from app.ui.workers import PipelineWorker
        from app.ai.ollama_client import OllamaCancelledError
        worker = PipelineWorker(
            resume=MagicMock(),
            job_text="test",
            job_title="Engineer",
            job_location="Remote",
            job_id=None,
            resume_id=None,
        )
        spy_result = MagicMock()
        spy_error = MagicMock()
        spy_cancelled = MagicMock()
        worker.result.connect(spy_result)
        worker.error.connect(spy_error)
        worker.cancelled.connect(spy_cancelled)

        def fake_run(*args, **kwargs):
            raise OllamaCancelledError()

        with patch(
            "app.application.optimize_resume.RunPipelineUseCase"
        ) as mock_uc:
            mock_uc.return_value.run = fake_run
            worker.run()

        spy_cancelled.assert_called_once()
        spy_error.assert_not_called()

    def test_ollama_cancelled_error_emits_cancelled(self):
        from app.ui.workers import PipelineWorker, OperationCancelled
        worker = PipelineWorker(
            resume=MagicMock(),
            job_text="test",
            job_title="Engineer",
            job_location="Remote",
            job_id=None,
            resume_id=None,
        )
        spy_cancelled = MagicMock()
        spy_error = MagicMock()
        worker.cancelled.connect(spy_cancelled)
        worker.error.connect(spy_error)

        def fake_run(*args, **kwargs):
            raise OperationCancelled("user cancelled")

        with patch(
            "app.application.optimize_resume.RunPipelineUseCase"
        ) as mock_uc:
            mock_uc.return_value.run = fake_run
            worker.run()

        spy_cancelled.assert_called_once()
        spy_error.assert_not_called()


# ── ResumeStudioPage construction ─────────────────────────────────────────


class TestStudioPageConstruction:
    """ResumeStudioPage should be importable and constructable with a mock window."""

    def test_studio_page_instantiates(self):
        from app.ui.pages.studio import ResumeStudioPage
        window = MagicMock()
        window.state = MagicMock()
        window.state.resume = None
        window.state.active_resume_id = None
        window.state.theme = "dark"
        page = ResumeStudioPage(window)
        assert page is not None
        assert page.window is window

    def test_studio_page_has_required_widgets(self):
        from app.ui.pages.studio import ResumeStudioPage
        window = MagicMock()
        window.state = MagicMock()
        window.state.resume = None
        window.state.active_resume_id = None
        window.state.theme = "dark"
        page = ResumeStudioPage(window)
        assert hasattr(page, "_nav")
        assert hasattr(page, "_editor")
        assert hasattr(page, "_preview")
        assert hasattr(page, "_insights")
        assert hasattr(page, "_auto_save_timer")

    def test_studio_page_is_in_main_window_pages(self):
        from app.ui.main_window import MainWindow
        # Verify ResumeStudioPage is referenced in setup_pages source
        import inspect
        source = inspect.getsource(MainWindow.setup_pages)
        assert "ResumeStudioPage" in source


# ── Full pipeline test ───────────────────────────────────────────────────


class TestFullPipelineConstruction:
    """RunPipelineUseCase should be instantiable and its run method callable."""

    def test_pipeline_use_case_instantiates(self):
        from app.application.optimize_resume import RunPipelineUseCase
        uc = RunPipelineUseCase()
        assert uc is not None

    def test_pipeline_worker_stores_fields(self):
        from app.ui.workers import PipelineWorker
        resume = MagicMock()
        worker = PipelineWorker(
            resume=resume,
            job_text="Python engineer",
            job_title="Engineer",
            job_location="Remote",
            job_id=42,
            resume_id=10,
            job_company="Acme",
        )
        assert worker.resume is resume
        assert worker.job_text == "Python engineer"
        assert worker.job_title == "Engineer"
        assert worker.job_location == "Remote"
        assert worker.job_id == 42
        assert worker.resume_id == 10
        assert worker.job_company == "Acme"

    def test_pipeline_worker_cancel_sets_event(self):
        from app.ui.workers import PipelineWorker
        worker = PipelineWorker(
            resume=MagicMock(),
            job_text="test",
            job_title="Engineer",
            job_location="Remote",
            job_id=None,
            resume_id=None,
        )
        assert not worker._token.event.is_set()
        worker.cancel()
        assert worker._token.event.is_set()
