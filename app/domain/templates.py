"""Template manifest and auto-fit domain models."""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


class TemplateManifest(BaseModel):
    """Data-driven template definition — no separate exporter functions."""
    template_id: str
    display_name: str

    font_family: str
    body_size_pt: float
    heading_size_pt: float
    line_height: float

    page_margin_mm: float
    section_spacing_pt: float
    bullet_spacing_pt: float

    section_order: list[str]
    show_contact_icons: bool = False
    accent_color: str = "#222222"

    ats_safe: bool = True


# ── Preset templates ──────────────────────────────────────────────────────

TEMPLATES: dict[str, TemplateManifest] = {
    "standard": TemplateManifest(
        template_id="standard",
        display_name="Standard",
        font_family="Arial",
        body_size_pt=10.0,
        heading_size_pt=11.0,
        line_height=1.15,
        page_margin_mm=15.0,
        section_spacing_pt=8.0,
        bullet_spacing_pt=2.0,
        section_order=[
            "summary", "experience", "projects",
            "skills", "education", "certifications", "languages",
        ],
        accent_color="#1A5276",
    ),
    "compact": TemplateManifest(
        template_id="compact",
        display_name="Compact",
        font_family="Arial",
        body_size_pt=9.0,
        heading_size_pt=10.0,
        line_height=1.10,
        page_margin_mm=12.0,
        section_spacing_pt=5.0,
        bullet_spacing_pt=1.0,
        section_order=[
            "summary", "experience", "skills", "education",
            "projects", "certifications", "languages",
        ],
        accent_color="#333333",
    ),
    "modern-minimal": TemplateManifest(
        template_id="modern-minimal",
        display_name="Modern Minimal",
        font_family="Helvetica",
        body_size_pt=10.0,
        heading_size_pt=12.0,
        line_height=1.20,
        page_margin_mm=18.0,
        section_spacing_pt=10.0,
        bullet_spacing_pt=2.0,
        section_order=[
            "experience", "skills", "summary", "projects",
            "education", "certifications", "languages",
        ],
        accent_color="#222222",
    ),
    "harvard": TemplateManifest(
        template_id="harvard",
        display_name="Harvard",
        font_family="Times New Roman",
        body_size_pt=10.5,
        heading_size_pt=12.0,
        line_height=1.15,
        page_margin_mm=20.0,
        section_spacing_pt=8.0,
        bullet_spacing_pt=2.0,
        section_order=[
            "summary", "experience", "education",
            "skills", "projects", "certifications", "languages",
        ],
        accent_color="#000000",
    ),
    "executive": TemplateManifest(
        template_id="executive",
        display_name="Executive",
        font_family="Garamond",
        body_size_pt=10.5,
        heading_size_pt=13.0,
        line_height=1.25,
        page_margin_mm=22.0,
        section_spacing_pt=12.0,
        bullet_spacing_pt=3.0,
        section_order=[
            "summary", "experience", "education",
            "certifications", "skills", "projects", "languages",
        ],
        accent_color="#1C1C1C",
    ),
    "technical": TemplateManifest(
        template_id="technical",
        display_name="Technical",
        font_family="Consolas",
        body_size_pt=9.5,
        heading_size_pt=10.5,
        line_height=1.12,
        page_margin_mm=14.0,
        section_spacing_pt=6.0,
        bullet_spacing_pt=1.5,
        section_order=[
            "skills", "experience", "projects",
            "summary", "education", "certifications", "languages",
        ],
        accent_color="#1A5276",
    ),
    "graduate": TemplateManifest(
        template_id="graduate",
        display_name="Graduate",
        font_family="Arial",
        body_size_pt=10.0,
        heading_size_pt=11.5,
        line_height=1.15,
        page_margin_mm=18.0,
        section_spacing_pt=8.0,
        bullet_spacing_pt=2.0,
        section_order=[
            "education", "summary", "experience",
            "projects", "skills", "certifications", "languages",
        ],
        accent_color="#2C3E50",
    ),
}

DEFAULT_TEMPLATE = "standard"

# Minimum body size to prevent unreadable text
MIN_BODY_SIZE_PT = 7.5


@dataclass(frozen=True)
class FitResult:
    font_scale: float
    spacing_scale: float
    page_count: int


class CannotFitResumeError(Exception):
    """Raised when content cannot fit without becoming unreadable."""

    def __init__(self, message: str, recommendations: list[str] | None = None):
        super().__init__(message)
        self.recommendations = recommendations or []


# ── Default recommendations when content won't fit ─────────────────────────

FIT_RECOMMENDATIONS = [
    "Remove the least relevant bullet.",
    "Shorten the summary.",
    "Move an old role into 'Additional Experience.'",
    "Use the compact template.",
    "Allow a second page.",
]
