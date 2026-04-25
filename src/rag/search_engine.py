"""Advanced search pipeline (sprint 01).

This module is the new retrieval facade. It composes three stages on top of
the existing FAISS / sentence-transformers stack from :mod:`rag.query`:

1. :func:`hybrid_retrieve` — runs BM25 in parallel with the vector index and
   merges the two ranked lists with Reciprocal Rank Fusion (RRF).
2. (later in this sprint) :func:`rerank` — cross-encoder rerank of the top-N
   hybrid candidates.
3. (later in this sprint) :func:`maybe_expand_query` + :func:`search` —
   query expansion via Ollama and the public facade used by the assistant.

Only :func:`hybrid_retrieve` is implemented in task 01.3.1; the rest of the
functions are added in 01.3.2 / 01.3.3 / 01.3.4.

Design notes
------------

* The BM25 index lives in process memory next to the FAISS index. It is
  rebuilt lazily on first use from the cached ``chunks`` list (which is
  already loaded by :mod:`rag.query`). For the corpus sizes the project
  targets (≤ 10k chunks) this takes well below 100 ms, so we deliberately
  do **not** persist BM25 to disk — the source of truth stays in
  ``chunks.pkl``.
* Tokenisation for BM25 is intentionally minimal in this first version
  (``text.lower().split()``). Stemming / language-aware tokenisation is
  out of scope for this sprint (see ``_docs/current-state.md`` § 2.2).
* The cached ``chunks`` from :mod:`rag.query` are **never mutated**. Every
  function in this module returns fresh ``dict`` instances with an
  additional ``score`` field.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import faiss
from rank_bm25 import BM25Okapi

# Make ``config`` importable when this module is loaded as ``rag.search_engine``
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import RRF_K, TOP_K_HYBRID  # noqa: E402
from rag import query as _query  # noqa: E402  (reuse FAISS index + embedder)


# ---------------------------------------------------------------------------
# BM25 lazy index
# ---------------------------------------------------------------------------

_bm25: Optional[BM25Okapi] = None
_bm25_chunk_count: int = 0


def _tokenize(text: str) -> List[str]:
    """Minimal whitespace tokenizer used for BM25.

    Lower-cases the text and splits on whitespace. Punctuation is left
    attached to the token; it does not hurt BM25 ranking because the same
    tokenizer is applied to both the query and the documents.
    """
    return text.lower().split()


def _ensure_bm25() -> Optional[BM25Okapi]:
    """Lazily build the BM25 index over the cached chunks.

    Returns ``None`` if the chunk cache is empty (no documents indexed yet).
    Rebuilds the index when the chunk cache size has changed (e.g. after
    ``build-index`` was re-run inside the same process).
    """
    global _bm25, _bm25_chunk_count

    chunks = _query.chunks
    if not chunks:
        # FAISS index missing — let the caller fall back to vector retrieval,
        # which itself returns ``[]`` in this state.
        _bm25 = None
        _bm25_chunk_count = 0
        return None

    if _bm25 is None or _bm25_chunk_count != len(chunks):
        tokenized = [_tokenize(c["text"]) for c in chunks]
        _bm25 = BM25Okapi(tokenized)
        _bm25_chunk_count = len(chunks)

    return _bm25


# ---------------------------------------------------------------------------
# Vector retrieval helper (top-N, not the global TOP_K)
# ---------------------------------------------------------------------------


def _vector_topn(query: str, top_n: int) -> List[int]:
    """Return the indices of the top-``top_n`` chunks ranked by FAISS.

    This mirrors :func:`rag.query.retrieve` but uses ``top_n`` instead of the
    global ``TOP_K`` and returns indices into the cached ``chunks`` list, so
    the caller can attach scores from a different ranker (BM25 / RRF).
    """
    if _query.index is None or len(_query.chunks) == 0:
        if not _query._ensure_index_exists():
            return []

    if _query.index is None or len(_query.chunks) == 0:
        return []

    q_emb = _query.model.encode([query])
    faiss.normalize_L2(q_emb)
    _, ids = _query.index.search(q_emb, top_n)
    return [int(i) for i in ids[0] if i >= 0]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def _rrf_merge(
    ranked_lists: List[List[int]],
    *,
    k: int = RRF_K,
) -> List[tuple[int, float]]:
    """Merge several ranked lists of chunk indices via RRF.

    For every list ``L`` and every chunk ``c`` at 1-based rank ``r`` in
    ``L``, contribute ``1 / (k + r)`` to ``c``'s RRF score. Chunks missing
    from a list do not contribute from it (their term is implicitly zero).

    Returns a list of ``(chunk_index, rrf_score)`` pairs sorted by score
    descending.
    """
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, idx in enumerate(ranked, start=1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def hybrid_retrieve(query: str, top_n: int = TOP_K_HYBRID) -> List[dict]:
    """Return the top-``top_n`` chunks ranked by RRF(vector + BM25).

    Each returned dict has the same shape as the cached chunks
    (``text``, ``source``, ``chunk_id``) plus a ``score`` field whose value
    is the RRF score (higher is better). The cached ``chunks`` are not
    mutated — fresh dicts are produced via ``{**chunk, "score": ...}``.

    On an empty index the function returns ``[]`` so that the rest of the
    pipeline can degrade gracefully.
    """
    chunks = _query.chunks
    if not chunks:
        if not _query._ensure_index_exists():
            return []
        chunks = _query.chunks
        if not chunks:
            return []

    vector_ids = _vector_topn(query, top_n)

    bm25 = _ensure_bm25()
    if bm25 is None:
        bm25_ids: List[int] = []
    else:
        bm25_scores = bm25.get_scores(_tokenize(query))
        # Sort indices by BM25 score descending, keep top_n.
        bm25_ids = sorted(
            range(len(chunks)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:top_n]

    merged = _rrf_merge([vector_ids, bm25_ids])[:top_n]
    return [
        {**chunks[idx], "score": float(rrf_score)}
        for idx, rrf_score in merged
    ]
