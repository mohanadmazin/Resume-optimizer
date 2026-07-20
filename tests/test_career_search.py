"""Tests for Career Vectorizer and Search Index — Tasks 58-59."""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.career_embeddings import CareerVectorizer
from app.services.career_search import CareerSearchIndex, SearchHit


# ── TF-IDF Vectorizer (Task 58) ────────────────────────────────────

class TestCareerVectorizer:
    def test_empty_corpus_fit(self):
        vec = CareerVectorizer()
        vec.fit([])
        assert vec.vocab_size == 0

    def test_fit_builds_vocab(self):
        vec = CareerVectorizer()
        vec.fit(["python developer", "java developer", "data engineer"])
        assert vec.vocab_size > 0

    def test_transform_produces_vector(self):
        vec = CareerVectorizer()
        vec.fit(["python developer with experience"])
        v = vec.transform("python developer")
        assert len(v) > 0

    def test_transform_empty_text(self):
        vec = CareerVectorizer()
        vec.fit(["some corpus"])
        v = vec.transform("")
        assert len(v) == 0

    def test_transform_unfitted(self):
        vec = CareerVectorizer()
        v = vec.transform("hello")
        assert v == {}

    def test_similarity_ranking(self):
        vec = CareerVectorizer()
        docs = [
            "python developer with machine learning experience",
            "java enterprise application developer",
            "data scientist with python and ml skills",
        ]
        vec.fit(docs)
        results = vec.similarity("python machine learning", docs)
        assert len(results) == 3
        assert results[0][1] >= results[1][1]
        # The python ml doc should rank highest
        assert "python" in results[0][2]

    def test_similarity_empty_documents(self):
        vec = CareerVectorizer()
        vec.fit(["test"])
        results = vec.similarity("test", [])
        assert results == []

    def test_similarity_empty_query(self):
        vec = CareerVectorizer()
        vec.fit(["test document"])
        results = vec.similarity("", ["test document"])
        assert len(results) == 0  # empty query produces no matches

    def test_save_and_load(self):
        vec = CareerVectorizer()
        vec.fit(["python developer", "java developer"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "vec.json"
            vec.save(path)
            loaded = CareerVectorizer.load(path)
            assert loaded.vocab_size == vec.vocab_size
            v1 = vec.transform("python")
            v2 = loaded.transform("python")
            assert set(v1.keys()) == set(v2.keys())

    def test_stopwords_filtered(self):
        vec = CareerVectorizer()
        vec.fit(["the and or but in on at"])
        assert vec.vocab_size == 0

    def test_short_words_filtered(self):
        vec = CareerVectorizer()
        vec.fit(["a b cc dd"])
        assert vec.vocab_size == 2  # only cc and dd


# ── Search Index (Task 59) ──────────────────────────────────────────

class TestCareerSearchIndex:
    def test_index_fact(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "Built Python web application")
        assert idx.doc_count == 1

    def test_index_resume(self):
        idx = CareerSearchIndex()
        idx.index_resume(1, "Senior engineer with 10 years experience")
        assert idx.doc_count == 1

    def test_index_job(self):
        idx = CareerSearchIndex()
        idx.index_job(1, "Looking for Python developer")
        assert idx.doc_count == 1

    def test_remove_doc(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "Some fact")
        assert idx.remove_doc(1)
        assert idx.doc_count == 0

    def test_remove_nonexistent(self):
        idx = CareerSearchIndex()
        assert not idx.remove_doc(999)

    def test_rebuild(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "Python developer")
        idx.index_fact(2, "Java developer")
        idx.rebuild()
        assert idx.is_built

    def test_search_returns_results(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "Python machine learning data science")
        idx.index_fact(2, "Java enterprise application development")
        idx.index_fact(3, "Python deep learning neural networks")
        hits = idx.search("python machine learning", limit=2)
        assert len(hits) > 0
        assert hits[0].score > 0
        assert hits[0].source_type == "career_fact"

    def test_search_sorted_by_score(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "python developer with flask and django")
        idx.index_fact(2, "rust systems programming with tokio")
        idx.index_fact(3, "python data engineer with spark and airflow")
        hits = idx.search("python web development flask")
        if len(hits) >= 2:
            assert hits[0].score >= hits[1].score

    def test_search_with_limit(self):
        idx = CareerSearchIndex()
        for i in range(20):
            idx.index_fact(i, f"document number {i} about python")
        hits = idx.search("python", limit=5)
        assert len(hits) <= 5

    def test_search_empty_index(self):
        idx = CareerSearchIndex()
        hits = idx.search("anything")
        assert hits == []

    def test_save_and_load(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "Python developer")
        idx.index_fact(2, "Java developer")
        idx.rebuild()
        with tempfile.TemporaryDirectory() as td:
            idx.save(td)
            loaded = CareerSearchIndex.load(td)
            assert loaded.doc_count == 2
            hits = loaded.search("python developer")
            assert len(hits) > 0

    def test_health_check(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "fact one")
        idx.index_resume(1, "resume one")
        health = idx.health_check()
        assert health["document_count"] == 2
        assert health["source_counts"]["career_fact"] == 1
        assert health["source_counts"]["resume"] == 1

    def test_search_hit_attributes(self):
        idx = CareerSearchIndex()
        idx.index_fact(42, "AWS certified solutions architect")
        hits = idx.search("AWS certification")
        assert len(hits) > 0
        h = hits[0]
        assert isinstance(h, SearchHit)
        assert h.doc_id == "fact_42"
        assert h.metadata.get("fact_id") == 42

    def test_incremental_add(self):
        idx = CareerSearchIndex()
        idx.index_fact(1, "first document")
        idx.rebuild()
        assert idx.doc_count == 1
        idx.index_fact(2, "second document")
        assert idx.doc_count == 2
        assert not idx.is_built

    def test_load_nonexistent(self):
        idx = CareerSearchIndex.load("/nonexistent/path")
        assert idx.doc_count == 0
