# app/services/job_fetcher.py

"""Fetch job descriptions from URLs.

Thin orchestrator that delegates to:
- security.py — SSRF protection, DNS resolution
- html_extractor.py — text extraction from HTML
- metadata.py — title/company/location extraction
"""

import logging
import socket
import threading
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests

from app.services.browser_fetcher import BrowserFetchError, fetch_rendered_page, requires_browser_render
from app.services.html_extractor import extract_text_from_html, extract_text_from_soup
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


class JobFetchError(JobFetcherError):
    """Raised when a job URL cannot be fetched (wraps all fetch failures)."""


# ── Result ───────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class FetchResult:
    """Result from fetching a job posting URL."""

    text: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    source_url: str | None = None
    requires_manual_input: bool = False


# ── Fetcher ──────────────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    ),
    # Disable compression to prevent decompression bombs
    "Accept-Encoding": "identity",
}

# Serialise DNS monkeypatching to avoid races with other networking threads.
_DNS_PATCH_LOCK = threading.Lock()


def _build_host_header(hostname: str, port: int, scheme: str) -> str:
    default_port = 443 if scheme == "https" else 80
    if port != default_port:
        return f"{hostname}:{port}"
    return hostname


def _pinned_getaddrinfo(
    original_getaddrinfo, target_ip: str, target_hostname: str, target_port: int
):
    """Return a getaddrinfo replacement that pins DNS to the validated IP."""

    def _pinned(host, port, family=0, type=0, proto=0, flags=0):
        if host == target_hostname:
            af = socket.AF_INET6 if ":" in target_ip else socket.AF_INET
            return [(af, socket.SOCK_STREAM, 6, "", (target_ip, port or target_port))]
        return original_getaddrinfo(host, port, family, type, proto, flags)

    return _pinned


def _connect(target: ResolvedTarget, url: str, config: FetchConfig) -> requests.Response:
    """Connect with DNS pinning to prevent rebinding.

    Resolves DNS once in resolve_and_validate(), validates the IP, then
    pins the resolution so that requests connects only to the validated IP
    while still using the hostname for TLS SNI.

    The DNS patch is serialised with a lock to prevent races with
    concurrent networking threads.
    """
    parsed = urlparse(url)
    original_getaddrinfo = socket.getaddrinfo

    with _DNS_PATCH_LOCK:
        socket.getaddrinfo = _pinned_getaddrinfo(
            original_getaddrinfo, target.ip, target.hostname, target.port
        )
        try:
            headers = dict(_HEADERS)
            headers["Host"] = _build_host_header(
                target.hostname, target.port, parsed.scheme,
            )

            session = requests.Session()
            session.headers.update(headers)
            return session.get(url, timeout=config.timeout, allow_redirects=False)
        finally:
            socket.getaddrinfo = original_getaddrinfo


def _read_limited_body(
    response: requests.Response,
    max_bytes: int,
) -> bytes:
    """Read response body in chunks, aborting if it exceeds *max_bytes*."""
    declared_size = response.headers.get("Content-Length")
    if declared_size:
        try:
            if int(declared_size) > max_bytes:
                raise ContentTooLargeError(
                    f"Response exceeds {max_bytes // (1024 * 1024)} MB limit."
                )
        except ValueError:
            pass

    body = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        if len(body) + len(chunk) > max_bytes:
            raise ContentTooLargeError(
                f"Response exceeds {max_bytes // (1024 * 1024)} MB limit."
            )
        body.extend(chunk)

    return bytes(body)


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
            # Handle redirects — validate port on every redirect target
            if response.status_code in (301, 302, 303, 307, 308):
                redirects_followed += 1
                if redirects_followed > config.max_redirects:
                    raise JobFetcherError("Too many redirects.")
                location = response.headers.get("Location")
                if not location:
                    raise JobFetcherError("Redirect with missing Location header.")
                current_url = urljoin(current_url, location)
                try:
                    validate_scheme(current_url)
                    validate_port(current_url)
                except SSRFError as exc:
                    raise InvalidURLError(str(exc)) from exc
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

            # Read body with streaming size check
            content = _read_limited_body(response, config.max_bytes)

            # Single parse: extract metadata first (needs title/meta/script tags),
            # then clean text (removes those tags).
            html_str = content.decode("utf-8", errors="replace")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_str, "lxml")

            meta = extract_metadata(soup)
            text = extract_text_from_soup(soup)

            # ── Browser fallback for JS-rendered pages ──────────────────
            if not text or len(text.strip()) < 100:
                if requires_browser_render(current_url):
                    logger.info("Static extraction thin (%d chars); trying browser render", len(text) if text else 0)
                    try:
                        rendered_html, rendered_url = fetch_rendered_page(current_url)
                        current_url = rendered_url
                        from bs4 import BeautifulSoup as _BS
                        browser_soup = _BS(rendered_html, "lxml")
                        text = extract_text_from_soup(browser_soup)
                        meta = extract_metadata(browser_soup)
                        logger.info("Browser fallback yielded %d chars of text", len(text) if text else 0)
                    except BrowserFetchError as exc:
                        logger.warning("Browser fallback failed: %s", exc)

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
                source_url=current_url,
            )
        finally:
            response.close()


# ── High-level API ───────────────────────────────────────────────────────────


_MIN_JD_LENGTH = 200


def fetch_job(url: str) -> FetchResult:
    """Fetch a job posting URL with graceful degradation.

    Tries the full fetch pipeline (requests + browser fallback).
    If extraction yields fewer than ``_MIN_JD_LENGTH`` chars or any
    error occurs, returns a result with ``requires_manual_input=True``
    instead of raising.

    The caller (UI) can then prompt the user to paste the JD manually.
    """
    try:
        result = fetch_from_url(url)

        if len(result.text.strip()) < _MIN_JD_LENGTH:
            logger.info(
                "LinkedIn blocked extraction (%d chars) for %s",
                len(result.text), url,
            )
            return FetchResult(
                text="",
                title=result.title,
                company=result.company,
                location=result.location,
                source_url=url,
                requires_manual_input=True,
            )

        return result

    except Exception as exc:
        logger.warning("fetch_job failed for %s: %s", url, exc)
        return FetchResult(
            text="",
            source_url=url,
            requires_manual_input=True,
        )
