"""
Feature 2 — Intelligent RFI Repository + Hybrid Search.

Combines a simple keyword overlap score (exact regulatory terminology) with
a semantic similarity score (meaning) so that a query like
"protocol amendment impact on informed consent" surfaces both exact-term
matches and conceptually similar historical RFIs, even if the wording differs.
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from core.models import RFI
from core.database import all_rfis
from core.embeddings import embed_corpus, cosine_similarities
from core.config import DEFAULT_KEYWORD_WEIGHT, DEFAULT_SEMANTIC_WEIGHT

_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "for", "and", "or", "on", "is",
    "are", "with", "this", "that", "please", "confirm", "was", "were",
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return [w for w in words if w not in _STOPWORDS]


def _keyword_score(query_terms: List[str], doc_text: str) -> float:
    if not query_terms:
        return 0.0
    doc_lower = doc_text.lower()
    hits = sum(1 for t in query_terms if t in doc_lower)
    return hits / len(query_terms)


@dataclass
class SearchResult:
    rfi: RFI
    keyword_score: float
    semantic_score: float
    combined_score: float


def hybrid_search(
    session,
    query: str,
    top_k: int = 5,
    statuses: Optional[List[str]] = None,
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
) -> List[SearchResult]:
    """Search the repository for RFIs most relevant to `query`."""
    statuses = statuses or ["approved"]
    candidates = all_rfis(session, statuses=statuses)
    if not candidates:
        return []

    texts = [c.searchable_text() for c in candidates]
    query_terms = _tokenize(query)

    doc_vecs, q_vec = embed_corpus(texts, query=query)
    semantic_scores = cosine_similarities(doc_vecs, q_vec) if q_vec is not None else [0.0] * len(candidates)

    total_w = (keyword_weight + semantic_weight) or 1.0
    kw_w, sem_w = keyword_weight / total_w, semantic_weight / total_w

    results = []
    for rfi_obj, text, sem_score in zip(candidates, texts, semantic_scores):
        kw_score = _keyword_score(query_terms, text)
        combined = kw_w * kw_score + sem_w * float(sem_score)
        results.append(SearchResult(
            rfi=rfi_obj,
            keyword_score=round(kw_score, 3),
            semantic_score=round(float(sem_score), 3),
            combined_score=round(combined, 3),
        ))

    results.sort(key=lambda r: r.combined_score, reverse=True)
    return results[:top_k]
