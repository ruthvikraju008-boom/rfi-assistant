"""
Feature 2 (semantic half) — turns RFI text into vectors for similarity search.

Tries to use sentence-transformers (all-MiniLM-L6-v2, as recommended in the
project plan) for real semantic embeddings. If that package / model isn't
available in the environment (it's a large download requiring torch), the
engine transparently falls back to a TF-IDF vectorizer from scikit-learn so
the app still runs and still returns meaningful "similar wording" matches --
just without deep semantic generalisation. Either way, the rest of the app
(search.py) doesn't need to know which backend is active.
"""
from typing import List
import numpy as np

from core.config import EMBEDDING_MODEL_NAME

_backend = None       # "sentence-transformers" | "tfidf"
_model = None         # SentenceTransformer instance
_vectorizer = None    # sklearn TfidfVectorizer instance (fitted lazily per corpus)


def _load_sentence_transformer():
    global _model, _backend
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        _backend = "sentence-transformers"
        return True
    except Exception:
        return False


def get_backend_name() -> str:
    if _backend is None:
        _load_sentence_transformer()
    return _backend or "tfidf"


def embed_corpus(texts: List[str], query: str = None):
    """
    Embed a list of documents (and optionally a query) into a shared vector
    space. Returns (doc_vectors, query_vector_or_None).

    For sentence-transformers this is a straightforward encode() call.
    For the TF-IDF fallback, the vectorizer must be fit on doc+query together
    so that they live in the same vector space -- it is refit per call, which
    is perfectly fine at hackathon scale (hundreds of documents).
    """
    if _backend is None:
        _load_sentence_transformer()

    if not texts:
        empty = np.zeros((0, 1))
        return empty, (np.zeros((1,)) if query is not None else None)

    if _backend == "sentence-transformers":
        doc_vecs = _model.encode(texts, normalize_embeddings=True)
        q_vec = None
        if query is not None:
            q_vec = _model.encode([query], normalize_embeddings=True)[0]
        return np.array(doc_vecs), q_vec

    # --- TF-IDF fallback ---
    from sklearn.feature_extraction.text import TfidfVectorizer
    global _vectorizer
    corpus = list(texts) + ([query] if query is not None else [])
    _vectorizer = TfidfVectorizer(stop_words="english", max_features=4096)
    matrix = _vectorizer.fit_transform(corpus).toarray()
    if query is not None:
        doc_vecs, q_vec = matrix[:-1], matrix[-1]
    else:
        doc_vecs, q_vec = matrix, None
    return doc_vecs, q_vec


def cosine_similarities(doc_vecs: np.ndarray, q_vec: np.ndarray) -> np.ndarray:
    if doc_vecs.shape[0] == 0:
        return np.zeros((0,))
    doc_norms = np.linalg.norm(doc_vecs, axis=1)
    q_norm = np.linalg.norm(q_vec)
    denom = (doc_norms * q_norm)
    denom[denom == 0] = 1e-9
    sims = (doc_vecs @ q_vec) / denom
    return np.clip(sims, 0.0, 1.0)
