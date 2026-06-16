"""Unit tests for chunking + RRF fusion."""
from agentic_rag_mcp.ingestion import _chunk
from agentic_rag_mcp.retrieval import _rrf_fuse, _tokenize


def test_chunk_short_text_returns_single_chunk():
    chunks = _chunk("Hello world. This is a short doc.")
    assert len(chunks) == 1


def test_chunk_long_text_splits_with_overlap():
    long = ("Lorem ipsum dolor sit amet. " * 500).strip()
    chunks = _chunk(long)
    assert len(chunks) > 1
    # Adjacent chunks should overlap
    assert any(chunks[0][-20:] in chunks[1] for _ in range(1))


def test_rrf_fuse_promotes_items_in_both_lists():
    vec = [{"chunk_id": "a", "text": "...", "source": "x", "score": 0.9},
           {"chunk_id": "b", "text": "...", "source": "x", "score": 0.8}]
    bm25 = [("b", "...", "x", 5.0),  # also in vec
            ("c", "...", "x", 3.0)]
    fused = _rrf_fuse(vec, bm25, top_k=3)
    ids = [f["chunk_id"] for f in fused]
    assert ids[0] == "b"  # appears in both → highest RRF score
    assert set(ids) == {"a", "b", "c"}


def test_tokenize_lowercases_and_splits():
    assert _tokenize("Hello, World!") == ["hello", "world"]
