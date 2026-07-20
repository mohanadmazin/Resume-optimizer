"""Career Vectorizer — lightweight TF-IDF without external ML dependencies."""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "this", "that",
    "these", "those", "it", "its", "i", "we", "you", "he", "she", "they",
    "my", "our", "your", "his", "her", "their", "what", "which", "who",
    "whom", "where", "when", "why", "how", "not", "no", "nor", "if",
    "then", "than", "so", "just", "about", "also", "very", "too",
})


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercasing tokenizer, filtering stopwords."""
    return [
        w for w in text.lower().split()
        if w.isalpha() and len(w) >= 2 and w not in _STOPWORDS
    ]


class CareerVectorizer:
    """TF-IDF vectorizer for career documents.

    Pure Python implementation — no numpy/scipy/sklearn dependency.
    """

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._doc_count: int = 0
        self._fitted: bool = False

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)

    def fit(self, corpus: Sequence[str]) -> CareerVectorizer:
        """Build vocabulary and IDF weights from a corpus of documents."""
        if not corpus:
            return self

        self._doc_count = len(corpus)
        df: dict[str, int] = {}

        for doc in corpus:
            tokens = set(_tokenize(doc))
            for token in tokens:
                df[token] = df.get(token, 0) + 1

        self._vocab = {word: idx for idx, word in enumerate(sorted(df.keys()))}

        for word, freq in df.items():
            # IDF with smoothing: log((1 + N) / (1 + df)) + 1
            self._idf[word] = math.log((1 + self._doc_count) / (1 + freq)) + 1.0

        self._fitted = True
        return self

    def transform(self, text: str) -> dict[int, float]:
        """Transform a single document into a sparse TF-IDF vector.

        Returns {vocab_index: tfidf_weight}.
        """
        if not self._fitted:
            return {}

        tokens = _tokenize(text)
        if not tokens:
            return {}

        # Term frequency
        tf_counts: dict[str, int] = {}
        for token in tokens:
            tf_counts[token] = tf_counts.get(token, 0) + 1

        n_tokens = len(tokens)
        vector: dict[int, float] = {}
        for token, count in tf_counts.items():
            if token in self._vocab:
                tf = count / n_tokens
                idf = self._idf.get(token, 1.0)
                idx = self._vocab[token]
                vector[idx] = tf * idf

        return vector

    def similarity(
        self,
        query: str,
        documents: Sequence[str],
    ) -> list[tuple[int, float, str]]:
        """Rank documents by cosine similarity to query.

        Returns list of (original_index, score, document_text) sorted by score.
        """
        if not self._fitted or not documents:
            return []

        query_vec = self.transform(query)
        if not query_vec:
            return []

        query_norm = math.sqrt(sum(v * v for v in query_vec.values()))
        if query_norm == 0:
            return []

        results: list[tuple[int, float, str]] = []
        for idx, doc in enumerate(documents):
            doc_vec = self.transform(doc)
            if not doc_vec:
                results.append((idx, 0.0, doc))
                continue

            # Dot product
            dot = 0.0
            for k, v in query_vec.items():
                if k in doc_vec:
                    dot += v * doc_vec[k]

            doc_norm = math.sqrt(sum(v * v for v in doc_vec.values()))
            if doc_norm == 0:
                results.append((idx, 0.0, doc))
                continue

            score = dot / (query_norm * doc_norm)
            results.append((idx, score, doc))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def save(self, path: str | Path) -> None:
        """Persist vocabulary and IDF weights to JSON."""
        data = {
            "vocab": self._vocab,
            "idf": self._idf,
            "doc_count": self._doc_count,
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> CareerVectorizer:
        """Load a previously saved vectorizer."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        vec = cls()
        vec._vocab = data["vocab"]
        vec._idf = data["idf"]
        vec._doc_count = data["doc_count"]
        vec._fitted = True
        return vec
