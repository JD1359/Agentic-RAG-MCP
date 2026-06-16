"""Cross-encoder reranker. Re-scores (query, candidate) pairs for higher precision."""
import logging
from functools import lru_cache

from agentic_rag_mcp.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_reranker():
    try:
        from sentence_transformers import CrossEncoder
        log.info("loading_reranker", extra={"model": settings.reranker_model})
        return CrossEncoder(settings.reranker_model)
    except Exception as e:
        log.warning("reranker_load_failed", extra={"error": str(e)})
        return None


def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Re-score candidates by cross-encoder relevance. Falls back to RRF order if model unavailable."""
    if not candidates:
        return []
    model = _get_reranker()
    if model is None:
        return candidates[:top_k]

    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs, show_progress_bar=False)
    for c, s in zip(candidates, scores):
        c["score"] = float(s)
    return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]
