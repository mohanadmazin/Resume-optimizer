"""Browser-based HTML fetcher for JavaScript-heavy job sites.

Launches a headless Chromium instance via Playwright to render pages
that return empty or minimal content from plain HTTP requests
(e.g. LinkedIn, Indeed, Workday).

All browser requests are routed through SSRF validation to prevent
the browser from accessing private, loopback, or blocked targets.
"""
import logging
from urllib.parse import urlparse

from app.services.security import (
    SSRFError,
    resolve_and_validate,
    validate_port,
    validate_scheme,
)

logger = logging.getLogger(__name__)

# Domains known to require JavaScript rendering.
JS_HEAVY_DOMAINS: frozenset[str] = frozenset({
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "workday.com",
    "workdayjobs.com",
    "myworkdayjobs.com",
})

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


class BrowserFetchError(Exception):
    """Raised when the headless browser cannot render the page."""


def requires_browser_render(url: str) -> bool:
    """Return True if *url* belongs to a JS-heavy domain."""
    hostname = (urlparse(url).hostname or "").lower().rstrip(".")
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in JS_HEAVY_DOMAINS
    )


def _secure_route(route) -> None:
    """Playwright route handler: enforce SSRF checks on every browser request."""
    request = route.request

    try:
        validate_scheme(request.url)
        validate_port(request.url)
        resolve_and_validate(request.url)
    except SSRFError:
        logger.warning("Blocked unsafe browser request: %s", request.url)
        route.abort("blockedbyclient")
        return

    if request.resource_type in _BLOCKED_RESOURCE_TYPES:
        route.abort("blockedbyclient")
        return

    route.continue_()


def fetch_rendered_page(url: str, timeout: int = 30_000) -> tuple[str, str]:
    """Open *url* in headless Chromium and return the rendered HTML and final URL.

    Args:
        url: The URL to fetch.
        timeout: Navigation timeout in milliseconds.

    Returns:
        A tuple of (rendered HTML, final URL after redirects).

    Raises:
        BrowserFetchError: If Playwright is unavailable or rendering fails.
    """
    # Validate syntax immediately, but defer DNS resolution until after
    # Playwright is available and Chromium launches. This keeps missing-browser
    # errors deterministic in offline environments while still validating the
    # target before any navigation occurs.
    validate_scheme(url)
    validate_port(url)

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
                # Resolve immediately before creating a page or navigating.
                resolve_and_validate(url)
                context = browser.new_context(
                    user_agent=_USER_AGENT,
                    service_workers="block",
                )
                context.route("**/*", _secure_route)

                page = context.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout)

                if response is None:
                    raise BrowserFetchError("Navigation returned no response.")

                final_url = page.url
                validate_scheme(final_url)
                validate_port(final_url)
                resolve_and_validate(final_url)

                html = page.content()
                logger.info("Browser-rendered page: %d chars of HTML", len(html))
                return html, final_url
            finally:
                browser.close()

    except BrowserFetchError:
        raise
    except Exception as exc:
        raise BrowserFetchError(f"Browser fetch failed: {exc}") from exc
