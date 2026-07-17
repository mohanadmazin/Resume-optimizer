# app/services/job_fetcher.py

"""Service to fetch and extract clean job description text from a URL."""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_REDIRECTS = 5


class JobFetcherError(Exception):
    """Raised when job fetching fails."""


# ── SSRF helpers ─────────────────────────────────────────────────────────────


def _validate_url(url: str) -> None:
    """Raise ``JobFetcherError`` if the URL scheme is not allowed or the
    hostname resolves to a private / reserved IP."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise JobFetcherError(f"URL scheme '{parsed.scheme}' is not allowed.")
    hostname = parsed.hostname
    if hostname and not _is_safe_ip(hostname):
        raise JobFetcherError(
            f"URL hostname '{hostname}' resolves to a private or reserved IP address."
        )


def _is_safe_ip(hostname: str) -> bool:
    """Return True if *hostname* resolves only to public, non-reserved IPs."""
    try:
        results = socket.getaddrinfo(hostname, None)
    except OSError:
        return False

    if not results:
        return False

    for family, _type, _proto, _canonname, sockaddr in results:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return False
    return True


def _safe_url_for_log(url: str) -> str:
    """Strip query params and fragments from a URL for safe logging."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


class JobFetcher:
    """Fetches and extracts job description text from web pages."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
    }

    TAGS_TO_REMOVE = [
        "script", "style", "noscript", "header", "footer",
        "nav", "aside", "meta", "head", "title", "svg", "button",
    ]

    @staticmethod
    def fetch_from_url(url: str, timeout: int = 10) -> str:
        """
        Fetch a webpage and extract the main text content.

        Args:
            url: The URL of the job posting.
            timeout: Request timeout in seconds.

        Returns:
            Extracted job description text.

        Raises:
            JobFetcherError: If fetching or parsing fails.
        """
        if not url or not url.strip():
            raise JobFetcherError("URL cannot be empty.")

        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        _validate_url(url)

        logger.info("Fetching job description from: %s", _safe_url_for_log(url))

        session = requests.Session()
        session.headers.update(JobFetcher.HEADERS)

        response = None
        current_url = url
        redirects_followed = 0

        try:
            while True:
                response = session.get(current_url, timeout=timeout, allow_redirects=False)
                if response.status_code in (301, 302, 303, 307, 308):
                    redirects_followed += 1
                    if redirects_followed > MAX_REDIRECTS:
                        raise JobFetcherError("Too many redirects.")
                    location = response.headers.get("Location")
                    if not location:
                        raise JobFetcherError("Redirect with missing Location header.")
                    response.close()
                    if location.startswith(("http://", "https://")):
                        current_url = location
                    else:
                        parsed = urlparse(current_url)
                        current_url = f"{parsed.scheme}://{parsed.netloc}{location}"
                    _validate_url(current_url)
                    continue
                response.raise_for_status()
                break
        except requests.exceptions.Timeout:
            raise JobFetcherError(f"Request timed out after {timeout} seconds.")
        except requests.exceptions.ConnectionError:
            raise JobFetcherError(f"Could not connect to {url}. Check the URL and your network.")
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            raise JobFetcherError(f"HTTP error {status} when fetching {url}.")
        except requests.exceptions.RequestException as exc:
            raise JobFetcherError(f"Failed to fetch URL: {exc}")

        try:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise JobFetcherError(
                    f"Unsupported content type: {content_type}. Only HTML pages are supported."
                )

            content = response.content
            if len(content) > MAX_RESPONSE_BYTES:
                raise JobFetcherError(
                    f"Response exceeds the {MAX_RESPONSE_BYTES // (1024 * 1024)} MB limit."
                )

            text = JobFetcher._extract_clean_text(content.decode("utf-8", errors="replace"))
        finally:
            response.close()

        if not text or len(text.strip()) < 20:
            raise JobFetcherError(
                "Could not extract meaningful text from this page. "
                "Try pasting the job description manually."
            )

        return text

    @staticmethod
    def _extract_clean_text(html_content: str) -> str:
        """Parse HTML and return cleaned plain text."""
        soup = BeautifulSoup(html_content, "html.parser")

        for tag_name in JobFetcher.TAGS_TO_REMOVE:
            for element in soup.find_all(tag_name):
                element.decompose()

        main_content = soup.find("main") or soup.find("article")
        if not main_content:
            main_content = soup.find("body")
        if not main_content:
            return ""

        lines = [line for line in main_content.stripped_strings]
        return "\n".join(lines)
