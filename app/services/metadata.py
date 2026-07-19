# app/services/metadata.py

"""Job metadata extraction: title, company, location from HTML."""

import json
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# Job board site names that should NOT be used as company names
_JOB_BOARD_SITES: frozenset[str] = frozenset({
    "linkedin", "indeed", "glassdoor", "monster", "ziprecruiter",
    "careerbuilder", "simplyhired", "github jobs", "stackoverflow",
    "dribbble", "behance", "google careers", "amazon jobs",
    "apple jobs", "microsoft careers", "bayt", "naukri",
    "seek", "jobsdb", "jobstreet", "careerjet", "jooble",
    "reed", "totaljobs", "stepstone", "xing",
})
_JOB_BOARD_NORMALIZED: frozenset[str] = frozenset(
    s.replace(" ", "") for s in _JOB_BOARD_SITES
)

# ── Title parsing ────────────────────────────────────────────────────────────

# Each pattern returns (title, company, location, confidence)
_TITLE_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    # "X at Company in Location" — high confidence, specific structure
    (re.compile(
        r"^(?P<title>.+?)\s+(?:at|@)\s+(?P<company>.+?)"
        r"(?:\s+(?:in|—|-)\s+(?P<location>.+))?$",
        re.IGNORECASE,
    ), 0.90),
    # "Company hiring Title in Location" (LinkedIn style)
    (re.compile(
        r"^(?P<company>.+?)\s+(?:is\s+)?hiring\s+(?:a|an|for\s+)?(?P<title>.+?)"
        r"(?:\s+in\s+(?P<location>.+))?$",
        re.IGNORECASE,
    ), 0.85),
    # "Company is hiring a Title for Location"
    (re.compile(
        r"^(?P<company>.+?)\s+is\s+hiring\s+(?:a|an)\s+(?P<title>.+?)"
        r"(?:\s+(?:for|in)\s+(?P<location>.+))?$",
        re.IGNORECASE,
    ), 0.85),
]


@dataclass(slots=True)
class TitleCandidate:
    """A parsed title with confidence score."""

    title: str
    company: str
    location: str
    confidence: float


def _score_delimited_parts(parts: list[str]) -> TitleCandidate | None:
    """Score a title split by common delimiters (|, -, —, ·, ::)."""
    if len(parts) >= 3:
        # Heuristic: last part is usually location (contains comma or state code)
        return TitleCandidate(
            title=parts[0],
            company=parts[1],
            location=parts[-1],
            confidence=0.80,
        )
    if len(parts) == 2:
        return TitleCandidate(
            title=parts[0],
            company=parts[1],
            location="",
            confidence=0.70,
        )
    return None


_DELIMITERS = (" | ", " — ", " - ", " · ", " :: ")


def parse_title_string(raw: str) -> TitleCandidate:
    """Parse a page title into the best (title, company, location) candidate.

    Generates multiple candidates from different strategies and returns the
    highest-confidence one.
    """
    if not raw:
        return TitleCandidate(title="", company="", location="", confidence=0.0)

    candidates: list[TitleCandidate] = []

    # Try structured patterns
    for pattern, base_confidence in _TITLE_PATTERNS:
        m = pattern.match(raw)
        if m:
            gd = m.groupdict()
            candidates.append(TitleCandidate(
                title=gd.get("title", "").strip(),
                company=gd.get("company", "").strip(),
                location=(gd.get("location") or "").strip(),
                confidence=base_confidence,
            ))

    # Try delimiter-based splitting
    for sep in _DELIMITERS:
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            candidate = _score_delimited_parts(parts)
            if candidate:
                candidates.append(candidate)
            break  # Only use the first matching delimiter

    # Fallback: whole string as title
    if not candidates:
        candidates.append(TitleCandidate(
            title=raw, company="", location="", confidence=0.30,
        ))

    # Return highest confidence
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[0]


# ── JSON-LD extraction ───────────────────────────────────────────────────────


@dataclass(slots=True)
class JsonLdData:
    """Structured data from schema.org JobPosting JSON-LD."""

    title: str
    company: str
    location: str


def extract_jsonld(soup: BeautifulSoup) -> JsonLdData:
    """Extract JobPosting structured data from JSON-LD script tags."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(data, list):
            data = data[0] if data else {}
        if not isinstance(data, dict):
            continue
        if data.get("@type") != "JobPosting":
            continue

        title = data.get("title", "")
        company = _extract_org_name(data.get("organization", {}))
        location = _extract_job_location(data.get("jobLocation", {}))

        return JsonLdData(title=title, company=company, location=location)

    return JsonLdData(title="", company="", location="")


def _extract_org_name(org) -> str:
    if isinstance(org, dict):
        return org.get("name", "")
    if isinstance(org, str):
        return org
    return ""


def _extract_job_location(loc) -> str:
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            parts = [
                addr.get("addressLocality", ""),
                addr.get("addressRegion", ""),
                addr.get("addressCountry", ""),
            ]
            return ", ".join(p for p in parts if p)
        if isinstance(addr, str):
            return addr
    if isinstance(loc, str):
        return loc
    return ""


# ── Full metadata extraction ────────────────────────────────────────────────

_BOARD_SUFFIX_RE = re.compile(
    r"\s*[\|–—-]\s*(" + "|".join(re.escape(s) for s in _JOB_BOARD_SITES) + r")\s*$",
    re.IGNORECASE,
)


def _strip_board_suffix(title: str) -> str:
    """Remove trailing ' | LinkedIn', ' - Indeed', etc. from title strings."""
    return _BOARD_SUFFIX_RE.sub("", title).strip()


@dataclass(slots=True)
class JobMetadata:
    """Extracted metadata from a job posting page."""

    title: str
    company: str
    location: str


def extract_metadata(soup: BeautifulSoup) -> JobMetadata:
    """Extract job title, company, and location from a parsed HTML tree.

    Uses a single soup (no double-parsing). Strategy in priority order:
    1. JSON-LD structured data (most reliable)
    2. <title> / og:title tag parsed through scoring
    3. <h1> tag parsed through scoring
    4. og:site_name as company fallback
    """
    # 1. JSON-LD (most structured/reliable)
    jsonld = extract_jsonld(soup)

    # 2. <title> and og:title
    page_title = ""
    if soup.title and soup.title.string:
        page_title = soup.title.string.strip()

    og_title = ""
    og_tag = soup.find("meta", property="og:title")
    if og_tag and og_tag.get("content"):
        og_title = og_tag["content"].strip()

    # 3. <h1>
    h1_text = ""
    h1_tag = soup.find("h1")
    if h1_tag:
        h1_text = h1_tag.get_text(strip=True)

    # Pick best raw title source, strip job board suffixes like " | LinkedIn"
    raw_title = og_title or page_title or h1_text
    raw_title = _strip_board_suffix(raw_title)
    parsed = parse_title_string(raw_title)

    # Assemble: JSON-LD is most reliable, use it first; fall back to parsed/h1
    title = jsonld.title or parsed.title or h1_text
    company = jsonld.company or parsed.company
    location = jsonld.location or parsed.location

    # og:site_name as company fallback (filter job boards)
    if not company:
        og_site = ""
        site_tag = soup.find("meta", property="og:site_name")
        if site_tag and site_tag.get("content"):
            og_site = site_tag["content"].strip()
        if og_site and og_site.lower().replace(" ", "") not in _JOB_BOARD_NORMALIZED:
            company = og_site

    return JobMetadata(title=title, company=company, location=location)
