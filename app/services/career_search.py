"""Career Search Index — TF-IDF indexing and retrieval over career documents."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.services.career_embeddings import CareerVectorizer

logger = logging.getLogger(__name__)

_INDEX_DIR = Path.home() / ".resume_optimizer" / "search_index"


class SearchHit:
    """A single search result."""

    __slots__ = ("doc_id", "source_type", "text", "score", "metadata")

    def __init__(
        self,
        doc_id: str,
        source_type: str,
        text: str,
        score: float,
        metadata: dict | None = None,
    ) -> None:
        self.doc_id = doc_id
        self.source_type = source_type
        self.text = text
        self.score = score
        self.metadata = metadata or {}


class CareerSearchIndex:
    """TF-IDF backed career document search index."""

    def __init__(self) -> None:
        self._vectorizer = CareerVectorizer()
        self._docs: dict[str, dict] = {}  # doc_id → {source_type, text, metadata}
        self._built = False

    @property
    def doc_count(self) -> int:
        return len(self._docs)

    @property
    def is_built(self) -> bool:
        return self._built

    def index_fact(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        """Add a career fact to the index."""
        self._docs[f"fact_{doc_id}"] = {
            "source_type": "career_fact",
            "text": text,
            "metadata": metadata or {"fact_id": doc_id},
        }
        self._built = False

    def index_resume(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        """Add resume content to the index."""
        self._docs[f"resume_{doc_id}"] = {
            "source_type": "resume",
            "text": text,
            "metadata": metadata or {"resume_id": doc_id},
        }
        self._built = False

    def index_job(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        """Add job description content to the index."""
        self._docs[f"job_{doc_id}"] = {
            "source_type": "job",
            "text": text,
            "metadata": metadata or {"job_id": doc_id},
        }
        self._built = False

    def remove_doc(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        removed = False
        for prefix in ("fact_", "resume_", "job_"):
            key = f"{prefix}{doc_id}"
            if key in self._docs:
                del self._docs[key]
                removed = True
                self._built = False
        return removed

    def rebuild(self) -> None:
        """Rebuild the TF-IDF index from all indexed documents."""
        corpus = [d["text"] for d in self._docs.values()]
        if corpus:
            self._vectorizer.fit(corpus)
        self._built = True

    def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        """Search the index for documents similar to query."""
        if not self._built:
            self.rebuild()
        if not self._docs:
            return []

        texts = [d["text"] for d in self._docs.values()]
        ids = list(self._docs.keys())
        results = self._vectorizer.similarity(query, texts)

        hits: list[SearchHit] = []
        for orig_idx, score, text in results[:limit]:
            if score <= 0:
                continue
            doc_id = ids[orig_idx]
            doc = self._docs[doc_id]
            hits.append(SearchHit(
                doc_id=doc_id,
                source_type=doc["source_type"],
                text=text,
                score=score,
                metadata=doc["metadata"],
            ))
        return hits

    def save(self, directory: str | Path | None = None) -> None:
        """Persist index to disk."""
        d = Path(directory) if directory else _INDEX_DIR
        d.mkdir(parents=True, exist_ok=True)

        self._vectorizer.save(d / "vectorizer.json")

        docs_path = d / "documents.json"
        docs_path.write_text(
            json.dumps(self._docs, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: str | Path | None = None) -> CareerSearchIndex:
        """Load index from disk."""
        d = Path(directory) if directory else _INDEX_DIR
        index = cls()
        try:
            index._vectorizer = CareerVectorizer.load(d / "vectorizer.json")
            docs_raw = json.loads((d / "documents.json").read_text(encoding="utf-8"))
            index._docs = docs_raw
            index._built = True
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("No valid index found at %s", d)
        return index

    def health_check(self) -> dict:
        """Return index health information."""
        return {
            "document_count": len(self._docs),
            "vocab_size": self._vectorizer.vocab_size,
            "is_built": self._built,
            "source_counts": self._count_by_source(),
        }

    def _count_by_source(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for doc in self._docs.values():
            st = doc["source_type"]
            counts[st] = counts.get(st, 0) + 1
        return counts
