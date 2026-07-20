"""Global search — cross-entity full-text and semantic search across all stored data."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from app.database.session import get_session
from app.database.models import (
    CoverLetter,
    JobApplication,
    JobDescription,
    Resume,
)

logger = logging.getLogger(__name__)

# Lazy-loaded semantic index
_search_index = None
_index_lock = threading.Lock()


def _get_search_index():
    """Get or initialize the semantic search index."""
    global _search_index
    if _search_index is not None:
        return _search_index
    try:
        from app.services.career_search import CareerSearchIndex
        _search_index = CareerSearchIndex.load()
        return _search_index
    except Exception:
        logger.debug("Could not load search index")
        return None


@dataclass(frozen=True)
class SearchResult:
    """A single search hit."""
    entity_type: str  # "resume", "job", "cover_letter", "application"
    entity_id: int
    title: str
    snippet: str
    page: str  # navigation target
    score: float = 0.0
    semantic: bool = False


def global_search(query: str, limit: int = 20) -> list[SearchResult]:
    """Search across resumes, jobs, cover letters, and applications."""
    q = query.strip().lower()
    if not q:
        return []

    results: list[SearchResult] = []

    try:
        with get_session() as session:
            for row in session.query(Resume).all():
                name = (row.name or "").lower()
                data = (row.data_json or "").lower()
                if q in name or q in data:
                    snippet = _extract_snippet(row.data_json or "", q)
                    results.append(SearchResult(
                        entity_type="resume",
                        entity_id=row.id,
                        title=row.name or f"Resume #{row.id}",
                        snippet=snippet,
                        page="Resume Upload",
                    ))

            for row in session.query(JobDescription).all():
                title = (row.title or "").lower()
                content = (row.content or "").lower()
                if q in title or q in content:
                    snippet = _extract_snippet(row.content or "", q)
                    results.append(SearchResult(
                        entity_type="job",
                        entity_id=row.id,
                        title=row.title or f"Job #{row.id}",
                        snippet=snippet,
                        page="Job Description",
                    ))

            for row in session.query(CoverLetter).all():
                content = (row.content or "").lower()
                if q in content:
                    snippet = _extract_snippet(row.content or "", q)
                    results.append(SearchResult(
                        entity_type="cover_letter",
                        entity_id=row.id,
                        title=f"Cover Letter #{row.id}",
                        snippet=snippet,
                        page="Cover Letter Library",
                    ))

            for row in session.query(JobApplication).all():
                notes = (row.notes or "").lower()
                status = (row.status or "").lower()
                if q in notes or q in status:
                    results.append(SearchResult(
                        entity_type="application",
                        entity_id=row.id,
                        title=f"Application #{row.id} ({row.status})",
                        snippet=(row.notes or "")[:120],
                        page="Applications",
                    ))

    except Exception:
        logger.exception("Global search failed")
        return []

    return results[:limit]


def semantic_search(query: str, limit: int = 20) -> list[SearchResult]:
    """Semantic search using TF-IDF similarity over career facts."""
    index = _get_search_index()
    if index is None or index.doc_count == 0:
        return []

    hits = index.search(query, limit=limit)
    results: list[SearchResult] = []
    for hit in hits:
        page = "Evidence Vault" if hit.source_type == "career_fact" else "Resume Upload"
        results.append(SearchResult(
            entity_type=hit.source_type,
            entity_id=_extract_id(hit.metadata),
            title=f"{hit.source_type.replace('_', ' ').title()} #{hit.doc_id}",
            snippet=hit.text[:120],
            page=page,
            score=hit.score,
            semantic=True,
        ))
    return results


def _extract_id(metadata: dict) -> int:
    """Extract numeric ID from metadata dict."""
    for key in ("fact_id", "resume_id", "job_id"):
        if key in metadata:
            try:
                return int(metadata[key])
            except (ValueError, TypeError):
                pass
    return 0


def rebuild_search_index() -> int:
    """Rebuild the semantic search index from all career facts.

    Returns the number of indexed documents.
    """
    from app.services.career_search import CareerSearchIndex

    global _search_index

    try:
        index = CareerSearchIndex()

        # Index career facts from vault
        from app.services.evidence_vault import EvidenceVault
        vault = EvidenceVault()
        facts = vault.list_facts()
        for f in facts:
            fid = getattr(f, "id", 0)
            stmt = getattr(f, "statement", "")
            if stmt:
                index.index_fact(str(fid), stmt)

        # Index resumes
        with get_session() as session:
            for row in session.query(Resume).all():
                data = row.data_json or ""
                if data:
                    index.index_resume(str(row.id), data[:2000])

            for row in session.query(JobDescription).all():
                content = row.content or ""
                if content:
                    index.index_job(str(row.id), content[:2000])

        index.rebuild()
        index.save()
        _search_index = index
        return index.doc_count
    except Exception:
        logger.exception("Failed to rebuild search index")
        return 0


def auto_index_fact(fact_id: int, statement: str) -> None:
    """Add or update a single fact in the search index (incremental)."""
    index = _get_search_index()
    if index is not None:
        index.index_fact(str(fact_id), statement)
        index.rebuild()


def remove_fact_from_index(fact_id: int) -> None:
    """Remove a fact from the search index."""
    index = _get_search_index()
    if index is not None:
        index.remove_doc(str(fact_id))
        index.rebuild()


def _extract_snippet(text: str, query: str, context: int = 60) -> str:
    """Extract a snippet of text around the first occurrence of *query*."""
    lower = text.lower()
    idx = lower.find(query)
    if idx == -1:
        return text[:120]

    start = max(0, idx - context)
    end = min(len(text), idx + len(query) + context)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet
