# app/services/job_fetcher.py

"""Service to fetch and extract clean job description text from a URL."""

import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_REDIRECTS = 5


class JobFetcherError(Exception):
    """Raised when job fetching fails."""


def _parse_title_string(raw: str) -> tuple[str, str, str]:
    """Parse a page title into (title, company, location).

    Handles common job board patterns:
    - "Senior Dev - Acme Corp - Kuala Lumpur, Malaysia"
    - "Senior Dev at Acme Corp in Kuala Lumpur"
    - "Senior Dev | Acme Corp | Remote"
    - "Senior Dev - Acme Corp"
    - "Acme Corp is hiring a Senior Dev in Kuala Lumpur"
    """
    if not raw:
        return "", "", ""

    title = ""
    company = ""
    location = ""

    # Pattern: "X at Company in Location" or "X @ Company"
    m = re.match(r"^(.+?)\s+(?:at|@)\s+(.+?)(?:\s+(?:in|—|-)\s+(.+))?$", raw, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), (m.group(3) or "").strip()

    # Pattern: "Company is hiring a X in Location"
    m = re.match(r"^(.+?)\s+(?:is\s+)?hiring\s+(?:a|an|for)\s+(.+?)(?:\s+in\s+(.+))?$", raw, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(1).strip(), (m.group(3) or "").strip()

    # Common delimiters: " | ", " - ", " — ", " · ", " :: "
    for sep in [" | ", " — ", " - ", " · ", " :: "]:
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            if len(parts) >= 3:
                # Heuristic: last part is usually location (contains comma or state code)
                location = parts[-1]
                title = parts[0]
                company = parts[1]
                return title, company, location
            elif len(parts) == 2:
                title = parts[0]
                company = parts[1]
                return title, company, ""

    # If only one delimiter found, treat as "Title - Company"
    for sep in [" | ", " — ", " - ", " · ", " :: "]:
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            if len(parts) == 2:
                return parts[0], parts[1], ""

    # No delimiter — return as title only
    return raw, "", ""


@dataclass
class FetchResult:
    """Result from fetching a job posting URL."""

    text: str
    title: str = ""
    company: str = ""
    location: str = ""


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
    def fetch_from_url(url: str, timeout: int = 10) -> FetchResult:
        """
        Fetch a webpage and extract the main text content plus metadata.

        Args:
            url: The URL of the job posting.
            timeout: Request timeout in seconds.

        Returns:
            FetchResult with text, title, company, and location.

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

            html_str = content.decode("utf-8", errors="replace")
            text = JobFetcher._extract_clean_text(html_str)
            title, company, location = JobFetcher._extract_metadata(html_str)
        finally:
            response.close()

        if not text or len(text.strip()) < 20:
            raise JobFetcherError(
                "Could not extract meaningful text from this page. "
                "Try pasting the job description manually."
            )

        return FetchResult(text=text, title=title, company=company, location=location)

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

    @staticmethod
    def _extract_metadata(html_content: str) -> tuple[str, str, str]:
        """Extract job title, company, and location from HTML metadata.

        Strategy (in priority order):
        1. <title> tag — most job boards put "Job Title - Company - Location" there
        2. <h1> tag — often the job title on listing pages
        3. og:title / og:site_name meta tags
        4. JSON-LD structured data (schema.org JobPosting)
        5. Heuristic patterns in the first lines of body text
        """
        soup = BeautifulSoup(html_content, "html.parser")
        title = ""
        company = ""
        location = ""

        # ── 1. Try <title> tag ────────────────────────────────────────────
        page_title = ""
        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()

        # ── 2. Try og:title meta tag ──────────────────────────────────────
        og_title = ""
        og_tag = soup.find("meta", property="og:title")
        if og_tag and og_tag.get("content"):
            og_title = og_tag["content"].strip()

        # ── 3. Try <h1> tag ───────────────────────────────────────────────
        h1_text = ""
        h1_tag = soup.find("h1")
        if h1_tag:
            h1_text = h1_tag.get_text(strip=True)

        # ── 4. Try JSON-LD structured data ────────────────────────────────
        jsonld_company = ""
        jsonld_location = ""
        jsonld_title = ""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0] if data else {}
                if not isinstance(data, dict):
                    continue
                if data.get("@type") == "JobPosting":
                    jsonld_title = data.get("title", "")
                    org = data.get("organization", {})
                    if isinstance(org, dict):
                        jsonld_company = org.get("name", "")
                    elif isinstance(org, str):
                        jsonld_company = org
                    loc = data.get("jobLocation", {})
                    if isinstance(loc, dict):
                        addr = loc.get("address", {})
                        if isinstance(addr, dict):
                            parts = [
                                addr.get("addressLocality", ""),
                                addr.get("addressRegion", ""),
                                addr.get("addressCountry", ""),
                            ]
                            jsonld_location = ", ".join(p for p in parts if p)
                        elif isinstance(addr, str):
                            jsonld_location = addr
                    elif isinstance(loc, str):
                        jsonld_location = loc
            except (json.JSONDecodeError, TypeError, KeyError, ValueError):
                pass

        # ── 5. Try og:site_name meta tag ──────────────────────────────────
        og_site = ""
        site_tag = soup.find("meta", property="og:site_name")
        if site_tag and site_tag.get("content"):
            og_site = site_tag["content"].strip()

        # ── Resolve title ─────────────────────────────────────────────────
        # Prefer <title> or og:title, fall back to <h1>
        raw_title = og_title or page_title or h1_text

        # Many job boards use "Job Title - Company - Location" or "Job Title at Company in Location"
        # Try to split on common delimiters
        title, company, location = _parse_title_string(raw_title)

        # Fill gaps from JSON-LD (most structured/reliable)
        if not title and jsonld_title:
            title = jsonld_title
        if not company and jsonld_company:
            company = jsonld_company
        if not location and jsonld_location:
            location = jsonld_location

        # If title is still empty, use h1 as fallback
        if not title and h1_text:
            title = h1_text

        # If company is still empty, use og:site_name (but only if it looks like
        # a company name, not a job board like "LinkedIn" or "Indeed")
        if not company and og_site:
            job_board_sites = {
                "linkedin", "indeed", "glassdoor", "monster", "ziprecruiter",
                "careerbuilder", "simplyhired", "github jobs", "stackoverflow",
                "dribbble", "behance", "google careers", "amazon jobs",
                "apple jobs", "microsoft careers",
            }
            if og_site.lower().replace(" ", "") not in {s.replace(" ", "") for s in job_board_sites}:
                company = og_site

        return title, company, location
