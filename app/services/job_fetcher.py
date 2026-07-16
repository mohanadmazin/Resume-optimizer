# app/services/job_fetcher.py

"""Service to fetch and extract clean job description text from a URL."""

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobFetcherError(Exception):
    """Raised when job fetching fails."""


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

        try:
            logger.info("Fetching job description from: %s", url)
            response = requests.get(url, headers=JobFetcher.HEADERS, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise JobFetcherError(f"Request timed out after {timeout} seconds.")
        except requests.exceptions.ConnectionError:
            raise JobFetcherError(f"Could not connect to {url}. Check the URL and your network.")
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            raise JobFetcherError(f"HTTP error {status} when fetching {url}.")
        except requests.exceptions.RequestException as exc:
            raise JobFetcherError(f"Failed to fetch URL: {exc}")

        text = JobFetcher._extract_clean_text(response.text)

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
