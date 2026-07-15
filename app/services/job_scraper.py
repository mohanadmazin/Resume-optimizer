"""Fetch a job posting from a URL and extract title, company, description.

LinkedIn now authwalls plain requests.get() almost every time (no
cookies / no browser fingerprint = treated as a bot), even for
"public" job pages. So LinkedIn URLs are rendered with a headless
Playwright browser reusing a persistent, already-logged-in profile
(see linkedin_login.py - run that once first). Other job boards still
use a fast plain-requests fetch.

Regardless of how the HTML was obtained, extraction always tries the
schema.org JobPosting JSON-LD block first (most reliable), then falls
back to a balanced-tag scrape of the largest "description"-classed
element (NOT a naive regex - that truncates on the first nested
closing tag, which is why an earlier version of this script kept
coming back empty/short on LinkedIn).
"""
import html
import json
import platform
import re
from html.parser import HTMLParser
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# If your Edge install is somewhere non-standard, hardcode the full
# path here (same as in indeed_login.py) and skip auto-detection.
EDGE_PATH_OVERRIDE = ""  # e.g. r"C:\path\to\msedge.exe"


def _find_edge_executable() -> str | None:
    """Returns Edge's executable path if found, else None (caller
    falls back to Playwright's bundled Chromium). Kept in sync with
    indeed_login.py -- the Cloudflare clearance cookie saved by that
    script can be tied to the browser fingerprint that earned it, so
    fetching with a different browser than you logged in with may not
    reuse the session correctly.
    """
    if EDGE_PATH_OVERRIDE:
        return EDGE_PATH_OVERRIDE

    system = platform.system()
    if system == "Windows":
        candidates = [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ]
    elif system == "Darwin":
        candidates = [Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")]
    else:
        candidates = [
            Path("/usr/bin/microsoft-edge"),
            Path("/usr/bin/microsoft-edge-stable"),
            Path("/opt/microsoft/msedge/msedge"),
        ]

    for path in candidates:
        if path.exists():
            return str(path)
    return None

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_LINKEDIN_PROFILE_DIR = "./linkedin_profile"
_BLOCK_TAGS = {"p", "li", "br", "div", "h1", "h2", "h3", "h4", "ul", "ol", "tr"}
_MIN_DESCRIPTION_CHARS = 200


# -----------------------------
# Plain-text extraction from an HTML fragment
# -----------------------------

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self._parts.append("\n\u2022 ")
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        lines = [ln.strip() for ln in raw.splitlines()]
        lines = [ln for ln in lines if ln]
        return "\n".join(lines)


def _html_to_text(fragment: str) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(fragment))
    return parser.text()


# -----------------------------
# JSON-LD (preferred)
# -----------------------------

def _extract_json_ld(page_html: str) -> dict | None:
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page_html,
        re.S | re.I,
    ):
        block = match.group(1).strip()
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type")
            if item_type == "JobPosting" or (
                isinstance(item_type, list) and "JobPosting" in item_type
            ):
                return item
            for node in item.get("@graph", []) if isinstance(item.get("@graph"), list) else []:
                if isinstance(node, dict) and node.get("@type") == "JobPosting":
                    return node
    return None


# -----------------------------
# Balanced-tag fallback (not a naive regex)
# -----------------------------

class _DescriptionBlockFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self._candidates: list[tuple[int, int]] = []
        self._raw = ""

    def feed(self, data: str) -> None:
        self._raw = data
        super().feed(data)

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        class_val = (attr_dict.get("class", "") or "").lower()
        id_val = (attr_dict.get("id", "") or "").lower()
        component_key = (attr_dict.get("componentkey", "") or "").lower()
        testid = (attr_dict.get("data-testid", "") or "").lower()
        automation = (attr_dict.get("data-automation", "") or "").lower()
        # LinkedIn now ships fully hashed/generated CSS class names
        # (e.g. class="_75228706 dec34939 ...") with NO readable
        # "description" class or id anywhere in the markup. The only
        # stable hooks left are semantic attributes: componentkey
        # (e.g. "JobDetails_AboutTheJob_<id>") on the section wrapper,
        # and data-testid="expandable-text-box" on the text node
        # itself. Matching on class/id alone (the old approach) will
        # never find anything on pages built this way.
        #
        # Jobstreet uses yet another scheme: data-automation="jobAdDetails"
        # on the description wrapper (also hashed CSS classes, no
        # readable class/id).
        is_match = (
            "description" in class_val
            or "description" in id_val
            or id_val == "job-details"
            or "jobs-box__html-content" in class_val
            or "aboutthejob" in component_key
            or "jobdescription" in component_key
            or testid == "expandable-text-box"
            or automation == "jobaddetails"
            or testid == "jobsearch-jobdescriptiontext"
            or id_val == "jobdescriptiontext"
        )
        if is_match:
            start = self._offset_of_current_tag()
            end = self._find_matching_close(tag, start)
            if start is not None and end is not None:
                self._candidates.append((start, end))

    def _offset_of_current_tag(self):
        line, col = self.getpos()
        return _line_col_to_offset(self._raw, line, col)

    def _find_matching_close(self, tag, start):
        if start is None:
            return None
        pattern = re.compile(rf"</?{re.escape(tag)}\b[^>]*>", re.I)
        depth = 0
        for m in pattern.finditer(self._raw, start):
            if m.group(0).lower().startswith(f"</{tag}"):
                depth -= 1
                if depth == 0:
                    return m.end()
            else:
                depth += 1
        return None

    def best_match(self) -> str:
        if not self._candidates:
            return ""
        start, end = max(self._candidates, key=lambda se: se[1] - se[0])
        return self._raw[start:end]


def _line_col_to_offset(text: str, line: int, col: int) -> int:
    lines = text.splitlines(keepends=True)
    return sum(len(ln) for ln in lines[: line - 1]) + col


def _fallback_description(page_html: str) -> str:
    finder = _DescriptionBlockFinder()
    try:
        finder.feed(page_html)
    except Exception:
        return ""
    block = finder.best_match()
    return _html_to_text(block) if block else ""


_SITE_SUFFIX = re.compile(r"\s*[|\-\u2013]\s*(LinkedIn|Indeed|Glassdoor|Jobstreet)\s*$", re.I)


def _fallback_title(page_html: str) -> str:
    match = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
        page_html,
        re.I,
    )
    if match:
        title = html.unescape(match.group(1)).strip()
        return _SITE_SUFFIX.sub("", title).strip()

    match = re.search(r"<title[^>]*>(.*?)</title>", page_html, re.S | re.I)
    if not match:
        return ""
    title = html.unescape(match.group(1)).strip()
    # LinkedIn's <title> is "<Job Title> | <Company> | LinkedIn" -- the
    # og:title meta (tried above) doesn't have this problem, but when
    # we fall back to <title> we need to take only the first segment,
    # not just strip a trailing "LinkedIn".
    if "|" in title:
        title = title.split("|")[0].strip()
    return _SITE_SUFFIX.sub("", title).strip()


_LINKEDIN_COMPANY_ARIA = re.compile(
    r'aria-label="Company,\s*([^".]+)\.?"', re.I
)
_LINKEDIN_TITLE_PARTS = re.compile(
    r"<title[^>]*>(.*?)</title>", re.S | re.I
)


def _linkedin_company_from_html(page_html: str) -> str:
    # Primary: LinkedIn stamps an explicit aria-label on the company
    # link/logo -- e.g. aria-label="Company, Vantage Data Centers."
    # This is far more reliable than trying to find a class/id for it,
    # since (as with the description) LinkedIn's classes here are
    # fully hashed/generated and carry no semantic meaning.
    m = _LINKEDIN_COMPANY_ARIA.search(page_html)
    if m:
        return html.unescape(m.group(1)).strip()

    # Fallback: the <title> tag follows "<Job Title> | <Company> | LinkedIn"
    m = _LINKEDIN_TITLE_PARTS.search(page_html)
    if m:
        title_text = html.unescape(m.group(1)).strip()
        parts = [p.strip() for p in title_text.split("|")]
        # drop trailing "LinkedIn" segment if present
        parts = [p for p in parts if p.lower() != "linkedin"]
        if len(parts) >= 2:
            return parts[-1]

    return ""


def _extract_by_data_automation(page_html: str, key: str) -> str:
    # Jobstreet (and other sites built on similar component libraries)
    # tag key elements with a stable data-automation attribute instead
    # of a readable class/id -- e.g. data-automation="job-detail-title"
    # and data-automation="advertiser-name". This is a simple
    # single-level (non-nested-tag-safe) grab, fine for short text
    # nodes like a title or company name that don't contain nested
    # tags of the same name.
    pattern = re.compile(
        r'<([a-zA-Z0-9]+)[^>]*\bdata-automation=["\']'
        + re.escape(key)
        + r'["\'][^>]*>(.*?)</\1>',
        re.S | re.I,
    )
    m = pattern.search(page_html)
    if not m:
        return ""
    return _html_to_text(m.group(2)).strip()


def _extract_by_data_testid(page_html: str, key: str) -> str:
    pattern = re.compile(
        r'<([a-zA-Z0-9]+)[^>]*\bdata-testid=["\']'
        + re.escape(key)
        + r'["\'][^>]*>(.*?)</\1>',
        re.S | re.I,
    )
    m = pattern.search(page_html)
    if not m:
        return ""
    return _html_to_text(m.group(2)).strip()


_LINKEDIN_JOB_ID = re.compile(r"(?:currentJobId=|/jobs/view/)(\d+)")


def _normalize_linkedin_url(url: str) -> str:
    if "linkedin.com" not in url.lower():
        return url
    m = _LINKEDIN_JOB_ID.search(url)
    if not m:
        return url
    return f"https://www.linkedin.com/jobs/view/{m.group(1)}/"


# -----------------------------
# Fetching
# -----------------------------

def _plain_fetch(url: str) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def _linkedin_browser_fetch(url: str) -> str:
    """Reuses the persistent, already-logged-in profile from
    linkedin_login.py. Run that script once before this will work."""
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=_LINKEDIN_PROFILE_DIR,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Kuala_Lumpur",
            user_agent=_HEADERS["User-Agent"],
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page.goto(url, wait_until="domcontentloaded", timeout=90000)

        # Click any "show more" style button so full text is present.
        for btn_selector in (
            "button.show-more-less-html__button",
            "button[aria-label*='see more']",
            "button.jobs-description__footer-button",
        ):
            try:
                btn = page.query_selector(btn_selector)
                if btn and btn.is_visible():
                    btn.click(timeout=3000)
                    page.wait_for_timeout(400)
            except Exception:
                continue

        page.wait_for_timeout(1000)
        content = page.content()
        context.close()
        return content


def _generic_browser_fetch(url: str, profile_dir: str) -> str:
    """For sites that block plain requests.get() (e.g. Indeed returns
    403 Forbidden to non-browser traffic) but don't require a login,
    unlike LinkedIn. A real headless browser with a normal fingerprint
    is enough to get past this -- no saved session needed."""
    edge_path = _find_edge_executable()
    with sync_playwright() as p:
        launch_kwargs = dict(
            user_data_dir=profile_dir,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Kuala_Lumpur",
            user_agent=_HEADERS["User-Agent"],
        )
        if edge_path:
            launch_kwargs["executable_path"] = edge_path
        context = p.chromium.launch_persistent_context(**launch_kwargs)
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # Indeed's Cloudflare check needs a beat to auto-clear even when
        # it doesn't show an interactive challenge.
        page.wait_for_timeout(3000)
        content = page.content()
        context.close()
        return content


def _looks_forbidden(page_html: str) -> bool:
    lowered = page_html.lower()
    return (
        len(page_html) < 3000
        and (
            "403 forbidden" in lowered
            or "access denied" in lowered
            or "are you a human" in lowered
        )
    )


def _cloudflare_challenged(page_html: str) -> bool:
    return (
        "Just a moment..." in page_html
        or '"PAGE_TYPE":"captcha"' in page_html
        or "PAGE_TYPE:\"captcha\"" in page_html
        or "cf-browser-verification" in page_html
    )


def _linkedin_authwalled(page_html: str) -> bool:
    return (
        "Sign Up | LinkedIn" in page_html
        or "Agree & Join LinkedIn" in page_html
        or "authwall" in page_html.lower()
    )


# -----------------------------
# Main entry point
# -----------------------------

def fetch_job_from_url(url: str) -> dict:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        raise ValueError("Enter a full URL, starting with http:// or https://")

    is_linkedin = "linkedin.com" in url.lower()
    is_indeed = "indeed.com" in url.lower()

    if is_indeed:
        # Indeed sits behind a Cloudflare bot challenge that beat every
        # automated approach tried (headless browser + saved session,
        # Brave, Edge, Google-search workaround). Rather than spend
        # 5-10s launching a browser just to fail every time, fail fast
        # with a clear message instead.
        raise ValueError(
            "Indeed job pages are protected by a Cloudflare challenge "
            "that automated fetching can't reliably get past. Please "
            "paste the job description in manually for Indeed listings."
        )

    if is_linkedin:
        url = _normalize_linkedin_url(url)
        try:
            page = _linkedin_browser_fetch(url)
        except Exception as exc:
            raise ValueError(
                f"Could not open LinkedIn in the browser: {exc}. "
                "Make sure you've run linkedin_login.py at least once."
            ) from exc

        if _linkedin_authwalled(page):
            raise ValueError(
                "LinkedIn still showed a login wall even with the saved "
                "session. Run linkedin_login.py again to refresh it, or "
                "paste the description in manually."
            )
    else:
        try:
            page = _plain_fetch(url)
        except requests.RequestException as exc:
            # Some boards 403 plain requests without needing a login
            # (bot-fingerprint check only) -- retry once with a real
            # browser before giving up.
            try:
                page = _generic_browser_fetch(url, "./generic_profile")
            except Exception:
                raise ValueError(f"Could not reach that URL: {exc}") from exc

    posting = _extract_json_ld(page)

    title, company, description = "", "", ""
    if posting:
        title = str(posting.get("title", "")).strip()
        org = posting.get("hiringOrganization")
        if isinstance(org, dict):
            company = str(org.get("name", "")).strip()
        raw_desc = posting.get("description", "")
        if raw_desc:
            description = _html_to_text(str(raw_desc))

    if len(description) < _MIN_DESCRIPTION_CHARS:
        fallback_desc = _fallback_description(page)
        if len(fallback_desc) > len(description):
            description = fallback_desc

    # Try the semantic on-page title element first (e.g. Jobstreet's
    # data-automation="job-detail-title") -- it's clean, whereas the
    # <title> tag fallback often has extra text baked in like
    # "... Job in Kuala Lumpur - Jobstreet" that isn't part of the
    # actual job title.
    if not title:
        title = _extract_by_data_automation(page, "job-detail-title")
    if not title:
        title = _extract_by_data_testid(page, "jobsearch-JobInfoHeader-title")
    if not title:
        title = _fallback_title(page)

    if not company and is_linkedin:
        company = _linkedin_company_from_html(page)
    if not company:
        company = _extract_by_data_automation(page, "advertiser-name")
    if not company:
        company = _extract_by_data_testid(page, "inlineHeader-companyName")

    if len(description) < _MIN_DESCRIPTION_CHARS:
        try:
            with open("last_fetch_debug.html", "w", encoding="utf-8") as f:
                f.write(page)
        except Exception:
            pass
        raise ValueError(
            "Could not extract enough job description text from that page "
            "(saved raw HTML to last_fetch_debug.html for inspection). "
            "Paste the description in manually instead."
        )

    return {"title": title, "company": company, "description": description}


if __name__ == "__main__":
    test_url = input("Job URL: ")
    result = fetch_job_from_url(test_url)
    print("\nTITLE:", result["title"])
    print("\nCOMPANY:", result["company"])
    print("\nDESCRIPTION:\n", result["description"][:2000])
