"""Embedding service. Uses local sentence-transformers by default; falls back to
a deterministic hash-based embedding when the model is not available so the
pipeline still runs offline."""
import hashlib
import logging
from functools import lru_cache

import numpy as np

from agentic_rag_mcp.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    try:
        from sentence_transformers import SentenceTransformer
        log.info("loading_embedding_model", extra={"model": settings.embedding_model})
        return SentenceTransformer(settings.embedding_model)
    except Exception as e:
        log.warning("embedding_model_load_failed", extra={"error": str(e)})
        return None


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    if model is not None:
        vecs = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return [v.tolist() for v in vecs]
    log.warning("using_hash_embedding_fallback", extra={"count": len(texts)})
    return [_hash_embed(t) for t in texts]


def _hash_embed(text: str) -> list[float]:
    """Content-addressable deterministic embedding using BLAKE2b (stable across runs)."""
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    seed = int.from_bytes(digest, "big") % (2**32)
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(settings.embedding_dim).astype(np.float32)
    v /= np.linalg.norm(v) + 1e-9
    return v.tolist()
