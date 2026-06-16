"""Hybrid retrieval: pgvector ANN + BM25 lexical, fused with RRF, then reranked."""
import logging
import re
import time
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from agentic_rag_mcp.config import settings
from agentic_rag_mcp.embeddings import embed_texts
from agentic_rag_mcp.reranker import rerank
from agentic_rag_mcp.storage import vector_search, fetch_collection_chunks
from agentic_rag_mcp.observability import retrieval_latency, retrieval_hits

log = logging.getLogger(__name__)


@dataclass
class RetrievalHit:
    chunk_id: str
    text: str
    source: str
    score: float


async def hybrid_search(
    query: str,
    collection: str,
    top_k: int | None = None,
) -> list[RetrievalHit]:
    """
    Hybrid search:
      1. Vector ANN search via pgvector (top N)
      2. BM25 lexical search over the same collection (top N)
      3. Fuse with Reciprocal Rank Fusion (RRF)
      4. Cross-encoder rerank top top_k_retrieval -> top_k_rerank
    """
    started = time.perf_counter()
    top_k = top_k or settings.top_k_rerank

    # Vector search
    [qvec] = await embed_texts([query])
    vec_hits = await vector_search(
        collection=collection,
        query_vec=qvec,
        top_k=settings.top_k_retrieval,
    )

    # BM25 over the collection
    all_chunks = await fetch_collection_chunks(collection)
    if all_chunks:
        bm25 = BM25Okapi([_tokenize(c["text"]) for c in all_chunks])
        scores = bm25.get_scores(_tokenize(query))
        bm25_ranked = sorted(
            zip(all_chunks, scores), key=lambda x: x[1], reverse=True
        )[: settings.top_k_retrieval]
        bm25_hits = [
            (c["chunk_id"], c["text"], c["source"], float(s))
            for c, s in bm25_ranked
        ]
    else:
        bm25_hits = []

    # Reciprocal Rank Fusion
    fused = _rrf_fuse(vec_hits, bm25_hits, top_k=settings.top_k_retrieval)

    # Cross-encoder rerank
    reranked = rerank(query=query, candidates=fused, top_k=top_k)

    elapsed = time.perf_counter() - started
    retrieval_latency.observe(elapsed)
    retrieval_hits.observe(len(reranked))

    return [
        RetrievalHit(chunk_id=h["chunk_id"], text=h["text"], source=h["source"],
                     score=h["score"])
        for h in reranked
    ]


def _rrf_fuse(vec_hits, bm25_hits, top_k: int, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion — see Cormack et al. 2009."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for rank, h in enumerate(vec_hits):
        chunk_id = h["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank + 1)
        items[chunk_id] = h

    for rank, (cid, text, source, _bm25_score) in enumerate(bm25_hits):
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
        if cid not in items:
            items[cid] = {"chunk_id": cid, "text": text, "source": source, "score": 0}

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    out = []
    for cid, fused_score in ordered:
        item = items[cid].copy()
        item["score"] = fused_score
        out.append(item)
    return out


_token_re = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _token_re.findall(text)]
