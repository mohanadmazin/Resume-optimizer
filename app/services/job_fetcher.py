# app/services/job_fetcher.py

"""Fetch job descriptions from URLs.

Thin orchestrator that delegates to:
- security.py — SSRF protection, DNS resolution
- html_extractor.py — text extraction from HTML
- metadata.py — title/company/location extraction
"""

import logging
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests

from app.services.html_extractor import extract_text_from_soup
from app.services.metadata import JobMetadata, extract_metadata
from app.services.security import (
    SSRFError,
    ResolvedTarget,
    resolve_and_validate,
    validate_port,
    validate_scheme,
)

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FetchConfig:
    """Tunable limits for URL fetching."""

    max_bytes: int = 5 * 1024 * 1024  # 5 MB
    max_redirects: int = 5
    timeout: int = 10


DEFAULT_CONFIG = FetchConfig()


# ── Errors ───────────────────────────────────────────────────────────────────


class JobFetcherError(Exception):
    """Base error for job fetching."""


class InvalidURLError(JobFetcherError):
    """URL is malformed or uses a disallowed scheme."""


class FetchTimeoutError(JobFetcherError):
    """Request timed out."""


class ContentTooLargeError(JobFetcherError):
    """Response exceeds the size limit."""


class ExtractionError(JobFetcherError):
    """Could not extract meaningful text from the page."""


# ── Result ───────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class FetchResult:
    """Result from fetching a job posting URL."""

    text: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    source_url: str | None = None


# ── Fetcher ──────────────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    ),
    # Disable compression to prevent decompression bombs
    "Accept-Encoding": "identity",
}


def _build_direct_url(target: ResolvedTarget, path: str, query: str, fragment: str) -> str:
    """Build a URL pointing directly at the resolved IP with Host header."""
    scheme = target.scheme
    ip = target.ip
    port = target.port

    default_port = 443 if scheme == "https" else 80
    if port != default_port:
        base = f"{scheme}://{ip}:{port}"
    else:
        base = f"{scheme}://{ip}"

    url = f"{base}{path}"
    if query:
        url += f"?{query}"
    if fragment:
        url += f"#{fragment}"
    return url


def _build_host_header(hostname: str, port: int) -> str:
    default_port = 443 if urlparse(f"https://{hostname}").scheme == "https" else 80
    if port != default_port:
        return f"{hostname}:{port}"
    return hostname


def _connect(target: ResolvedTarget, url: str, config: FetchConfig) -> requests.Response:
    """Connect to a resolved target with Host header preservation."""
    parsed = urlparse(url)
    direct_url = _build_direct_url(target, parsed.path, parsed.query, parsed.fragment)

    headers = dict(_HEADERS)
    headers["Host"] = _build_host_header(target.hostname, target.port)

    session = requests.Session()
    session.headers.update(headers)
    return session.get(direct_url, timeout=config.timeout, allow_redirects=False)


def _safe_url_for_log(url: str) -> str:
    """Strip query params and fragments for safe logging."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


# ── Public API ───────────────────────────────────────────────────────────────


def fetch_from_url(url: str, config: FetchConfig = DEFAULT_CONFIG) -> FetchResult:
    """Fetch a job posting URL and extract text + metadata.

    Resolves DNS once per hostname and connects directly to the resolved
    IP to prevent DNS rebinding attacks.

    Args:
        url: The job posting URL.
        config: Tunable fetch limits.

    Returns:
        FetchResult with extracted text, title, company, location.

    Raises:
        JobFetcherError (or subclass) on any failure.
    """
    if not url or not url.strip():
        raise InvalidURLError("URL cannot be empty.")

    url = url.strip()

    # Reject non-HTTP schemes before prepending https://
    if url.startswith(("ftp://", "file://", "mailto:", "javascript:")):
        raise InvalidURLError(
            f"URL scheme not allowed. Only http:// and https:// URLs are supported."
        )

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Validate scheme and port before any network activity
    try:
        validate_scheme(url)
        validate_port(url)
    except SSRFError as exc:
        raise InvalidURLError(str(exc)) from exc

    logger.info("Fetching job description from: %s", _safe_url_for_log(url))

    current_url = url
    redirects_followed = 0

    while True:
        # Resolve DNS once and validate — prevents DNS rebinding
        try:
            target = resolve_and_validate(current_url)
        except SSRFError as exc:
            raise InvalidURLError(str(exc)) from exc

        try:
            response = _connect(target, current_url, config)
        except requests.exceptions.Timeout:
            raise FetchTimeoutError(f"Request timed out after {config.timeout} seconds.")
        except requests.exceptions.ConnectionError:
            raise JobFetcherError(
                f"Could not connect to {target.hostname}. Check the URL and your network."
            )
        except requests.exceptions.RequestException as exc:
            raise JobFetcherError(f"Failed to fetch URL: {exc}")

        try:
            # Handle redirects
            if response.status_code in (301, 302, 303, 307, 308):
                redirects_followed += 1
                if redirects_followed > config.max_redirects:
                    raise JobFetcherError("Too many redirects.")
                location = response.headers.get("Location")
                if not location:
                    raise JobFetcherError("Redirect with missing Location header.")
                current_url = urljoin(current_url, location)
                validate_scheme(current_url)
                continue

            # Handle HTTP errors
            if response.status_code >= 400:
                raise JobFetcherError(
                    f"HTTP error {response.status_code} when fetching {url}."
                )

            # Validate content type
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise JobFetcherError(
                    f"Unsupported content type: {content_type}. Only HTML pages are supported."
                )

            # Validate size
            content = response.content
            if len(content) > config.max_bytes:
                raise ContentTooLargeError(
                    f"Response exceeds the {config.max_bytes // (1024 * 1024)} MB limit."
                )

            # Single parse: extract metadata first (needs title/meta/script tags),
            # then clean text (removes those tags).
            html_str = content.decode("utf-8", errors="replace")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_str, "lxml")

            meta = extract_metadata(soup)
            text = extract_text_from_soup(soup)

            if not text or len(text.strip()) < 20:
                raise ExtractionError(
                    "Could not extract meaningful text from this page. "
                    "Try pasting the job description manually."
                )

            return FetchResult(
                text=text,
                title=meta.title or None,
                company=meta.company or None,
                location=meta.location or None,
                source_url=url,
            )
        finally:
            response.close()
