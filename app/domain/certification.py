"""Helpers for backward-compatible structured certification editing.

Certifications remain serialized as strings so existing databases and prompts
continue to work.  The GUI and exporters use these helpers to expose title,
issuer, and year as separate fields.
"""
from __future__ import annotations

import re

_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")


def certification_parts(value: str) -> tuple[str, str, str]:
    """Return ``(title, issuer, year)`` from legacy or normalized text."""
    text = (value or "").strip()
    if not text:
        return "", "", ""

    parts = [
        part.strip()
        for part in re.split(r"\s*(?:\||\t+)\s*", text)
        if part.strip()
    ]
    if len(parts) >= 3:
        year = parts[-1] if _YEAR_RE.fullmatch(parts[-1]) else ""
        if year:
            return " | ".join(parts[:-2]), parts[-2], year
        return parts[0], " | ".join(parts[1:]), ""
    if len(parts) == 2:
        if _YEAR_RE.fullmatch(parts[1]):
            return parts[0], "", parts[1]
        return parts[0], parts[1], ""

    year_match = re.search(r"\b((?:19|20)\d{2})\s*$", text)
    if year_match:
        without_year = text[: year_match.start()].rstrip(" -·|\t")
        # A tab usually separates title and issuer in DOCX extraction.
        legacy = [part.strip() for part in re.split(r"\t+", without_year) if part.strip()]
        if len(legacy) >= 2:
            return " | ".join(legacy[:-1]), legacy[-1], year_match.group(1)
        return without_year, "", year_match.group(1)
    return text, "", ""


def format_certification(title: str, issuer: str = "", year: str = "") -> str:
    """Serialize certification fields in the canonical pipe-separated form."""
    return " | ".join(
        part.strip() for part in (title, issuer, year) if part and part.strip()
    )
