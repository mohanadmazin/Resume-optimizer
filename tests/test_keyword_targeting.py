"""Tests for Rezi-style keyword targeting."""
from app.domain.keyword_targeting import (
    JobRequirement,
    KeywordStatus,
    KeywordTarget,
    ResumeTextIndex,
    normalize,
)
from app.services.keyword_targeting import match_requirement, suggest_placement_paths


# ── normalize ──────────────────────────────────────────────────────────────


def test_normalize_lowercases_and_strips():
    assert normalize("Python") == "python"
    assert normalize("  DJANGO  ") == "django"


def test_normalize_removes_punctuation():
    assert normalize("C++") == "c++"
    assert normalize("Node.js") == "node.js"
    assert normalize("CI/CD") == "cicd"


def test_normalize_keeps_digits():
    assert normalize("react18") == "react18"


# ── ResumeTextIndex ────────────────────────────────────────────────────────


def _index() -> ResumeTextIndex:
    return ResumeTextIndex(path_text=[
        ("summary", "python developer experienced with django and rest apis."),
        ("skills[0]", "python"),
        ("skills[1]", "django"),
        ("skills[2]", "postgresql"),
        ("experience[0].title", "senior developer"),
        ("experience[0].bullets[0]", "built rest apis with django serving 1m users"),
        ("experience[0].bullets[1]", "managed postgresql database migrations"),
    ])


def test_find_any_returns_matching_paths():
    idx = _index()
    matches = idx.find_any({"python", "nonexistent"})
    paths = [m.path for m in matches]
    assert "summary" in paths
    assert "skills[0]" in paths


def test_find_any_returns_empty_for_no_match():
    idx = _index()
    matches = idx.find_any({"kubernetes", "terraform"})
    assert matches == []


def test_find_semantic_overlap_detects_partial():
    idx = _index()
    assert idx.find_semantic_overlap("rest") is True
    assert idx.find_semantic_overlap("python") is True


def test_find_semantic_overlap_returns_false_when_absent():
    idx = _index()
    assert idx.find_semantic_overlap("kubernetes") is False


# ── match_requirement ──────────────────────────────────────────────────────


def test_match_present_keyword():
    req = JobRequirement(
        name="python",
        aliases=["py", "python3"],
        importance=1.0,
        frequency=5,
        source_phrases=["python", "Python"],
    )
    target = match_requirement(req, _index())
    assert target.status == KeywordStatus.PRESENT
    assert target.canonical_name == "python"
    assert len(target.evidence_paths) > 0
    assert target.requires_user_confirmation is True


def test_match_missing_keyword():
    req = JobRequirement(
        name="kubernetes",
        aliases=["k8s"],
        importance=0.8,
        frequency=3,
        source_phrases=["kubernetes", "K8s"],
    )
    target = match_requirement(req, _index())
    assert target.status == KeywordStatus.MISSING
    assert target.evidence_paths == []
    assert len(target.suggested_paths) >= 0


def test_match_alias_present():
    req = JobRequirement(
        name="postgresql",
        aliases=["postgres", "psql"],
        importance=0.9,
        frequency=2,
        source_phrases=["PostgreSQL"],
    )
    target = match_requirement(req, _index())
    assert target.status == KeywordStatus.PRESENT
    assert "skills[2]" in target.evidence_paths


def test_match_partial_keyword():
    req = JobRequirement(
        name="restful",
        aliases=[],
        importance=0.5,
        frequency=1,
        source_phrases=["RESTful"],
    )
    target = match_requirement(req, _index())
    assert target.status == KeywordStatus.PARTIAL


def test_match_importance_preserved():
    req = JobRequirement(name="django", importance=0.95, frequency=4)
    target = match_requirement(req, _index())
    assert target.importance == 0.95
    assert target.frequency_in_job == 4


# ── suggest_placement_paths ────────────────────────────────────────────────


def test_suggests_bullets():
    req = JobRequirement(name="docker")
    paths = suggest_placement_paths(req, _index())
    assert any("bullets" in p for p in paths)


def test_suggests_skills_section():
    req = JobRequirement(name="docker")
    idx_no_skills = ResumeTextIndex(path_text=[
        ("summary", "devops engineer"),
        ("experience[0].bullets[0]", "deployed applications to cloud"),
    ])
    paths = suggest_placement_paths(req, idx_no_skills)
    assert "skills" in paths


def test_suggests_limit_four():
    req = JobRequirement(name="docker")
    idx_many_bullets = ResumeTextIndex(path_text=[
        (f"experience[0].bullets[{i}]", f"bullet {i} with some content here for testing")
        for i in range(20)
    ])
    paths = suggest_placement_paths(req, idx_many_bullets)
    assert len(paths) <= 4
