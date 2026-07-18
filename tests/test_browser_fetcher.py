"""Tests for the browser fetcher and its integration with job_fetcher."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.browser_fetcher import (
    BrowserFetchError,
    fetch_rendered_page,
    requires_browser_render,
)
from app.services.job_fetcher import ExtractionError, FetchResult, fetch_from_url


# ── requires_browser_render ──────────────────────────────────────────────


class TestRequiresBrowserRender:
    def test_linkedin_detected(self):
        assert requires_browser_render("https://www.linkedin.com/jobs/view/123") is True

    def test_indeed_detected(self):
        assert requires_browser_render("https://indeed.com/viewjob?jk=abc") is True

    def test_glassdoor_detected(self):
        assert requires_browser_render("https://www.glassdoor.com/job-listing/123") is True

    def test_workday_detected(self):
        assert requires_browser_render("https://company.wd5.myworkdayjobs.com/en-US/jobs/123") is True

    def test_regular_site_not_detected(self):
        assert requires_browser_render("https://company.com/careers/backend-engineer") is False

    def test_github_not_detected(self):
        assert requires_browser_render("https://github.com/jobs/123") is False


# ── fetch_rendered_page ─────────────────────────────────────────────────


class TestFetchRenderedPage:
    def test_playwright_not_installed(self):
        with patch.dict("sys.modules", {"playwright": None, "playwright.sync_api": None}):
            with pytest.raises(BrowserFetchError, match="not installed"):
                fetch_rendered_page("https://example.com")

    def test_successful_render(self):
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body><main>Job content here</main></body></html>"
        mock_page.url = "https://example.com"
        mock_page.goto.return_value = MagicMock(status=200)

        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_pw = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with (
            patch("playwright.sync_api.sync_playwright") as mock_sync,
            patch("app.services.browser_fetcher.validate_scheme"),
            patch("app.services.browser_fetcher.validate_port"),
            patch("app.services.browser_fetcher.resolve_and_validate"),
        ):
            mock_sync.return_value.__enter__.return_value = mock_pw
            html, final_url = fetch_rendered_page("https://example.com")

        assert "<html" in html
        assert "Job content here" in html
        assert final_url == "https://example.com"
        mock_page.goto.assert_called_once()

    def test_browser_error_wrapped(self):
        mock_pw = MagicMock()
        mock_pw.chromium.launch.side_effect = RuntimeError("browser crashed")

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.__enter__.return_value = mock_pw
            with pytest.raises(BrowserFetchError, match="Browser fetch failed"):
                fetch_rendered_page("https://example.com")


# ── Integration: browser fallback in fetch_from_url ─────────────────────


class TestBrowserFallbackIntegration:
    def test_fallback_triggered_for_thin_text(self):
        """When static extraction returns thin text for a JS-heavy URL,
        browser fallback should be attempted."""
        thin_html = "<html><body><p>Sign in</p></body></html>"
        rich_html = (
            "<html><body><main>"
            "<h1>Software Engineer at Google</h1>"
            "<p>We are looking for a Python developer with Django experience. "
            "Must know Docker, PostgreSQL and AWS.</p>"
            "</main></body></html>"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = thin_html.encode()
        mock_response.iter_content.return_value = [thin_html.encode()]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.job_fetcher.resolve_and_validate") as mock_resolve,
            patch("app.services.job_fetcher._connect", return_value=mock_response),
            patch("app.services.job_fetcher.requires_browser_render", return_value=True),
            patch("app.services.job_fetcher.fetch_rendered_page", return_value=(rich_html, "https://www.linkedin.com/jobs/view/123")),
        ):
            mock_resolve.return_value = MagicMock(
                hostname="linkedin.com", port=443, ip="1.2.3.4"
            )
            result = fetch_from_url("https://www.linkedin.com/jobs/view/123")

        assert isinstance(result, FetchResult)
        assert "Python developer" in result.text

    def test_no_fallback_for_regular_site(self):
        """Regular sites should NOT trigger browser fallback."""
        minimal_html = (
            "<html><body>"
            "<h1>Backend Engineer at Acme Corporation</h1>"
            "<p>We need a Python developer with 3+ years of experience "
            "in Django and PostgreSQL.</p>"
            "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = minimal_html.encode()
        mock_response.iter_content.return_value = [minimal_html.encode()]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.job_fetcher.resolve_and_validate") as mock_resolve,
            patch("app.services.job_fetcher._connect", return_value=mock_response),
            patch("app.services.job_fetcher.fetch_rendered_page") as mock_browser,
        ):
            mock_resolve.return_value = MagicMock(
                hostname="company.com", port=443, ip="1.2.3.4"
            )
            result = fetch_from_url("https://company.com/careers/backend")

        mock_browser.assert_not_called()
        assert isinstance(result, FetchResult)

    def test_browser_failure_falls_through_to_extraction_error(self):
        """If browser fallback also fails, ExtractionError should be raised."""
        thin_html = "<html><body><p>Sign in</p></body></html>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = thin_html.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.job_fetcher.resolve_and_validate") as mock_resolve,
            patch("app.services.job_fetcher._connect", return_value=mock_response),
            patch("app.services.job_fetcher.requires_browser_render", return_value=True),
            patch("app.services.job_fetcher.fetch_rendered_page", side_effect=BrowserFetchError("crash")),
        ):
            mock_resolve.return_value = MagicMock(
                hostname="linkedin.com", port=443, ip="1.2.3.4"
            )
            with pytest.raises(ExtractionError, match="manually"):
                fetch_from_url("https://www.linkedin.com/jobs/view/123")
