"""Auto-fit service — binary search for optimal font/spacing scale."""
from __future__ import annotations

import logging
from typing import Protocol

from app.domain.templates import (
    MIN_BODY_SIZE_PT,
    FIT_RECOMMENDATIONS,
    CannotFitResumeError,
    FitResult,
    TemplateManifest,
)

logger = logging.getLogger(__name__)


class PageRenderer(Protocol):
    """Anything that can render a resume and report page count."""

    def __call__(
        self,
        font_scale: float = 1.0,
        spacing_scale: float = 1.0,
    ) -> int:
        """Render with given scales and return the number of pages."""
        ...


def auto_fit(
    renderer: PageRenderer,
    maximum_pages: int,
    template: TemplateManifest | None = None,
) -> FitResult:
    """Binary search for the largest font/spacing that fits within *maximum_pages*.

    Uses a bisection over [0.86, 1.00] with up to 10 iterations.
    Raises ``CannotFitResumeError`` if even the smallest scale doesn't fit.
    """
    lower_font_scale = 0.86
    upper_font_scale = 1.00
    best: FitResult | None = None

    # Check if the smallest scale is still too large
    min_body = (template.body_size_pt if template else 10.0) * lower_font_scale
    if min_body < MIN_BODY_SIZE_PT:
        logger.warning(
            "Minimum body size %.1fpt below threshold %.1fpt",
            min_body, MIN_BODY_SIZE_PT,
        )

    for _ in range(10):
        font_scale = (lower_font_scale + upper_font_scale) / 2

        pages = renderer(font_scale=font_scale, spacing_scale=font_scale)

        candidate = FitResult(
            font_scale=font_scale,
            spacing_scale=font_scale,
            page_count=pages,
        )

        if pages <= maximum_pages:
            best = candidate
            lower_font_scale = font_scale
        else:
            upper_font_scale = font_scale

    if best is None:
        raise CannotFitResumeError(
            "Content cannot fit without becoming unreadable.",
            recommendations=FIT_RECOMMENDATIONS,
        )

    logger.info(
        "Auto-fit: scale=%.3f pages=%d",
        best.font_scale, best.page_count,
    )
    return best
