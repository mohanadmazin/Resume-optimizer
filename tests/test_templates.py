"""Tests for templates, auto-fit, and CannotFitResumeError."""
import pytest

from app.domain.templates import (
    MIN_BODY_SIZE_PT,
    TEMPLATES,
    CannotFitResumeError,
    FitResult,
    TemplateManifest,
)
from app.services.auto_fit import auto_fit


# ── TemplateManifest ──────────────────────────────────────────────────────


def test_all_seven_templates_exist():
    assert len(TEMPLATES) == 7
    for tid in ("standard", "compact", "modern-minimal", "harvard", "executive", "technical", "graduate"):
        assert tid in TEMPLATES


def test_template_fields_valid():
    for tid, t in TEMPLATES.items():
        assert t.template_id == tid
        assert t.body_size_pt >= MIN_BODY_SIZE_PT
        assert t.heading_size_pt >= t.body_size_pt
        assert 1.0 <= t.line_height <= 2.0
        assert t.page_margin_mm > 0
        assert len(t.section_order) > 0
        assert t.ats_safe is True


def test_compact_has_smaller_sizes():
    std = TEMPLATES["standard"]
    cmp = TEMPLATES["compact"]
    assert cmp.body_size_pt < std.body_size_pt
    assert cmp.page_margin_mm < std.page_margin_mm
    assert cmp.section_spacing_pt < std.section_spacing_pt


def test_executive_has_larger_sizes():
    exe = TEMPLATES["executive"]
    std = TEMPLATES["standard"]
    assert exe.body_size_pt >= std.body_size_pt
    assert exe.line_height >= std.line_height
    assert exe.page_margin_mm >= std.page_margin_mm


def test_technical_starts_with_skills():
    tech = TEMPLATES["technical"]
    assert tech.section_order[0] == "skills"


def test_graduate_starts_with_education():
    grad = TEMPLATES["graduate"]
    assert grad.section_order[0] == "education"


def test_template_manifest_roundtrip():
    t = TEMPLATES["standard"]
    d = t.model_dump()
    t2 = TemplateManifest.model_validate(d)
    assert t2.template_id == t.template_id
    assert t2.body_size_pt == t.body_size_pt


# ── FitResult ──────────────────────────────────────────────────────────────


def test_fit_result_frozen():
    fr = FitResult(font_scale=0.9, spacing_scale=0.9, page_count=1)
    with pytest.raises(AttributeError):
        fr.font_scale = 0.8


def test_fit_result_fields():
    fr = FitResult(font_scale=0.95, spacing_scale=0.95, page_count=2)
    assert fr.font_scale == 0.95
    assert fr.page_count == 2


# ── CannotFitResumeError ──────────────────────────────────────────────────


def test_cannot_fit_has_recommendations():
    err = CannotFitResumeError(
        "Content cannot fit",
        recommendations=["Remove a bullet", "Shorten summary"],
    )
    assert len(err.recommendations) == 2
    assert "Remove a bullet" in err.recommendations


def test_cannot_fit_default_recommendations_empty():
    err = CannotFitResumeError("Too long")
    assert err.recommendations == []


# ── auto_fit ──────────────────────────────────────────────────────────────


def test_auto_fit_fits_on_one_page():
    """Mock renderer that always fits on 1 page — should return scale near 1.0."""
    def renderer(font_scale=1.0, spacing_scale=1.0) -> int:
        return 1

    result = auto_fit(renderer, maximum_pages=1)
    assert result.page_count == 1
    assert 0.86 <= result.font_scale <= 1.0
    assert 0.86 <= result.spacing_scale <= 1.0


def test_auto_fit_needs_shrink():
    """Mock renderer: fits at 0.90 scale but not at 0.95."""
    def renderer(font_scale=1.0, spacing_scale=1.0) -> int:
        if font_scale >= 0.95:
            return 2
        return 1

    result = auto_fit(renderer, maximum_pages=1)
    assert result.page_count == 1
    assert result.font_scale < 0.95


def test_auto_fit_needs_significant_shrink():
    """Mock renderer: only fits at 0.86 scale."""
    def renderer(font_scale=1.0, spacing_scale=1.0) -> int:
        if font_scale >= 0.87:
            return 3
        return 1

    result = auto_fit(renderer, maximum_pages=1)
    assert result.page_count == 1
    assert result.font_scale <= 0.87


def test_auto_fit_raises_when_impossible():
    """Mock renderer that never fits — should raise CannotFitResumeError."""
    def renderer(font_scale=1.0, spacing_scale=1.0) -> int:
        return 5

    with pytest.raises(CannotFitResumeError) as exc_info:
        auto_fit(renderer, maximum_pages=1)
    assert "unreadable" in str(exc_info.value).lower()
    assert len(exc_info.value.recommendations) > 0


def test_auto_fit_two_pages_allowed():
    """Mock renderer: fits at full scale on 2 pages."""
    def renderer(font_scale=1.0, spacing_scale=1.0) -> int:
        return 2

    result = auto_fit(renderer, maximum_pages=2)
    assert result.page_count == 2
    assert result.font_scale >= 0.93


def test_auto_fit_converges_within_iterations():
    """Binary search should converge in at most 10 iterations."""
    call_count = {"n": 0}

    def renderer(font_scale=1.0, spacing_scale=1.0) -> int:
        call_count["n"] += 1
        if font_scale >= 0.92:
            return 2
        return 1

    result = auto_fit(renderer, maximum_pages=1)
    assert call_count["n"] <= 10
    assert result.page_count == 1
