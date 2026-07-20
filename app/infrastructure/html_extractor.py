# app/services/html_extractor.py

"""HTML text extraction: strip noise, extract readable content."""

import re

from bs4 import BeautifulSoup, Tag

# Tags to always remove entirely
_TAGS_TO_REMOVE: frozenset[str] = frozenset({
    "script", "style", "noscript", "header", "footer",
    "nav", "aside", "meta", "head", "title", "svg", "button",
    "form", "input", "select", "textarea", "label",
    "iframe", "dialog", "modal",
})

# Normalized class/id tokens that indicate noise containers (not substrings)
_NOISE_CLASS_HINTS: frozenset[str] = frozenset({
    "signin", "sign-in", "signup", "sign-up",
    "login", "modal", "overlay", "auth",
    "similar-jobs", "people-also-viewed",
    "job-alert", "related-jobs", "sidebar",
    "cookie-banner", "newsletter", "advertisement",
})

_NOISE_ID_HINTS: frozenset[str] = frozenset({
    "signin", "sign-in", "login", "modal", "auth",
    "similar", "related", "sidebar", "footer",
})


def _tokenize_class_attr(class_val) -> set[str]:
    """Normalize a class attribute into a set of lowercased dash-separated tokens."""
    if isinstance(class_val, list):
        parts = " ".join(class_val)
    else:
        parts = str(class_val)
    tokens: set[str] = set()
    for segment in parts.split():
        for token in segment.replace("_", "-").split("-"):
            if token:
                tokens.add(token.lower())
    return tokens


def _has_noise_tokens(text: str, hints: frozenset[str]) -> bool:
    """Check if *text* contains any normalized noise tokens (exact match, not substring)."""
    tokens = _tokenize_class_attr(text)
    return bool(tokens & hints)

# Line-level noise patterns (login prompts, timestamps, etc.)
_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p) for p in [
        r"(?i)^sign in to\b",
        r"(?i)^join now$",
        r"(?i)^forgot password\??$",
        r"(?i)^email or phone$",
        r"(?i)^new to \w+\??$",
        r"(?i)^password$",
        r"(?i)^cookie policy$",
        r"(?i)^privacy policy$",
        r"(?i)^user agreement$",
        r"(?i)^by clicking continue\b",
        r"(?i)^similar jobs$",
        r"(?i)^people also viewed$",
        r"(?i)^explore top content\b",
        r"(?i)^see who\b.*hired\b",
        r"(?i)^referrals increase\b",
        r"(?i)^get notified when\b",
        r"(?i)^set alert$",
        r"(?i)^sign in to set\b",
        r"(?i)^sign in to evaluate\b",
        r"(?i)^sign in to tailor\b",
        r"(?i)^sign in to access\b",
        r"(?i)^direct message the job poster\b",
        r"(?i)^use ai to assess\b",
        r"(?i)^\d+ applicants?$",
        r"(?i)^\d+ (hours?|days?|weeks?|months?) ago$",
        r"(?i)^save$",
        r"(?i)^report this job$",
        r"(?i)^all jobs$",
        r"(?i)^view top content$",
        r"(?i)^find curated posts\b",
    ]
)


def strip_noise_tags(soup: Tag | BeautifulSoup) -> None:
    """Remove tags and containers that are not part of job content.

    Mutates *soup* in place.
    """
    # Remove entire tags by name
    for tag_name in _TAGS_TO_REMOVE:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Collect elements to remove (class/id based), then remove in batch
    to_remove = []
    for el in soup.find_all(True):
        attrs = el.attrs
        if not attrs:
            continue
        class_val = attrs.get("class")
        if class_val:
            if _has_noise_tokens(
                " ".join(class_val) if isinstance(class_val, list) else str(class_val),
                _NOISE_CLASS_HINTS,
            ):
                to_remove.append(el)
                continue
        id_val = attrs.get("id")
        if id_val and _has_noise_tokens(str(id_val), _NOISE_ID_HINTS):
            to_remove.append(el)

    for el in to_remove:
        if el.parent is not None:
            el.decompose()


def find_job_content(soup: Tag | BeautifulSoup) -> Tag | None:
    """Locate the main job content container within *soup*.

    Tries progressively narrower selectors before falling back to <body>.
    """
    # Try <main> or <article> first
    for tag_name in ("main", "article"):
        el = soup.find(tag_name)
        if el:
            return el

    # Try elements with "job" in class or id
    for attr, pattern in [("class", "job"), ("id", "job")]:
        el = soup.find(attrs={attr: lambda v: v and pattern in " ".join(v).lower() if isinstance(v, list) else v and pattern in v.lower()})
        if el:
            return el

    return soup.find("body")


def extract_text_from_soup(soup: BeautifulSoup) -> str:
    """Extract cleaned text from an already-parsed BeautifulSoup tree.

    This is the primary entry point for text extraction when you already
    have a parsed soup (avoids double-parsing).
    """
    strip_noise_tags(soup)
    content = find_job_content(soup)
    if not content:
        return ""

    lines = [line.strip() for line in content.stripped_strings]
    return _filter_noise_lines(lines)


def extract_text_from_html(html: str) -> str:
    """Parse HTML and extract cleaned text in one step.

    Use this when you don't need the soup for other purposes.
    """
    soup = BeautifulSoup(html, "lxml")
    return extract_text_from_soup(soup)


def _filter_noise_lines(lines: list[str]) -> str:
    """Remove short/empty lines and lines matching noise patterns."""
    cleaned: list[str] = []
    for line in lines:
        if not line or len(line) < 2:
            continue
        if any(p.match(line) for p in _NOISE_PATTERNS):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)
