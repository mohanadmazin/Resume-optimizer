"""Tests for global search service."""
from __future__ import annotations

import json

import pytest

from app.database.models import (
    CoverLetter,
    JobApplication,
    JobDescription,
    Resume,
)
from app.database.session import get_session
from app.services.global_search import global_search, _extract_snippet


@pytest.fixture(autouse=True)
def _seed_data():
    """Insert test data into the in-memory database."""
    with get_session() as session:
        resume = Resume(
            name="Software Engineer Resume",
            data_json=json.dumps({"contact": {"name": "Alice"}}),
            source_type="upload",
        )
        session.add(resume)
        session.flush()

        job = JobDescription(
            title="Backend Developer",
            content="Python, Django, PostgreSQL experience required.",
        )
        session.add(job)
        session.flush()

        session.add(CoverLetter(
            resume_id=resume.id,
            job_id=job.id,
            content="I am excited to apply for this role.",
        ))
        session.add(JobApplication(
            resume_id=resume.id,
            job_id=job.id,
            status="applied",
            notes="Applied via LinkedIn for the position.",
        ))
    yield
    with get_session() as session:
        for model in [Resume, JobDescription, CoverLetter, JobApplication]:
            session.query(model).delete()


class TestGlobalSearch:
    def test_empty_query(self):
        assert global_search("") == []
        assert global_search("   ") == []

    def test_search_resumes(self):
        results = global_search("software engineer")
        assert len(results) >= 1
        assert results[0].entity_type == "resume"
        assert results[0].page == "Resume Upload"

    def test_search_jobs(self):
        results = global_search("backend developer")
        assert any(r.entity_type == "job" for r in results)

    def test_search_cover_letters(self):
        results = global_search("excited to apply")
        assert any(r.entity_type == "cover_letter" for r in results)

    def test_search_applications(self):
        results = global_search("linkedin")
        assert any(r.entity_type == "application" for r in results)

    def test_no_results(self):
        results = global_search("xyznonexistent")
        assert results == []

    def test_case_insensitive(self):
        results = global_search("SOFTWARE")
        assert len(results) >= 1

    def test_limit(self):
        results = global_search("a", limit=1)
        assert len(results) <= 1

    def test_snippet_extraction(self):
        text = "A" * 200 + " keyword " + "B" * 200
        snippet = _extract_snippet(text, "keyword")
        assert "keyword" in snippet
        assert snippet.startswith("...") or snippet.endswith("...")

    def test_snippet_no_match(self):
        text = "Some text with no match"
        snippet = _extract_snippet(text, "missing")
        assert snippet == text[:120]


class TestSemanticSearch:
    def test_empty_index(self):
        from app.services.global_search import semantic_search
        results = semantic_search("python developer")
        assert results == []

    def test_rebuild_index(self):
        from app.services.global_search import rebuild_search_index
        count = rebuild_search_index()
        assert count >= 0

    def test_auto_index_fact(self):
        from app.services.global_search import auto_index_fact
        auto_index_fact(999, "Test fact for indexing")

    def test_remove_fact_from_index(self):
        from app.services.global_search import remove_fact_from_index
        remove_fact_from_index(999)
