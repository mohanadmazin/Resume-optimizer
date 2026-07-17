"""Browser-based HTML fetcher for JavaScript-heavy job sites.

Launches a headless Chromium instance via Playwright to render pages
that return empty or minimal content from plain HTTP requests
(e.g. LinkedIn, Indeed, Workday).
"""
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Domains known to require JavaScript rendering.
JS_HEAVY_DOMAINS: frozenset[str] = frozenset({
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "workday.com",
    "workdayjobs.com",
})

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class BrowserFetchError(Exception):
    """Raised when the headless browser cannot render the page."""


def requires_browser_render(url: str) -> bool:
    """Return True if *url* belongs to a JS-heavy domain."""
    hostname = urlparse(url).hostname or ""
    return any(d in hostname for d in JS_HEAVY_DOMAINS)


def fetch_rendered_page(url: str, timeout: int = 30_000) -> str:
    """Open *url* in headless Chromium and return the rendered HTML.

    Args:
        url: The URL to fetch.
        timeout: Navigation timeout in milliseconds.

    Returns:
        The fully rendered HTML string.

    Raises:
        BrowserFetchError: If Playwright is unavailable or rendering fails.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise BrowserFetchError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=_USER_AGENT)

                page.goto(url, wait_until="domcontentloaded", timeout=timeout)

                # Wait for main content container — LinkedIn uses <main>
                try:
                    page.wait_for_selector("main", timeout=10_000)
                except Exception:
                    # Not all sites use <main>; fall back to a short wait
                    page.wait_for_timeout(3_000)

                html = page.content()
                logger.info("Browser-rendered page: %d chars of HTML", len(html))
                return html
            finally:
                browser.close()

    except BrowserFetchError:
        raise
    except Exception as exc:
        raise BrowserFetchError(f"Browser fetch failed: {exc}") from exc
