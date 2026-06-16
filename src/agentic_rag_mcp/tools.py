"""Tool definitions exposed via MCP."""
from typing import Any

import mcp.types as types

from agentic_rag_mcp.agentic import agentic_query
from agentic_rag_mcp.ingestion import ingest_path
from agentic_rag_mcp.retrieval import hybrid_search
from agentic_rag_mcp.storage import latest_eval, list_collections

TOOL_DEFINITIONS: list[types.Tool] = [
    types.Tool(
        name="ingest",
        description=(
            "Ingest a document or directory into a knowledge collection. "
            "Supports PDF, HTML, Markdown, plain text, and source code."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Local file or directory path"},
                "collection": {"type": "string", "description": "Collection name to ingest into"},
            },
            "required": ["path", "collection"],
        },
    ),
    types.Tool(
        name="semantic_search",
        description=(
            "Hybrid (vector + BM25) search over a collection. Returns top-k chunks "
            "with scores and metadata. No LLM generation — raw retrieval only."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "collection": {"type": "string"},
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
            },
            "required": ["query", "collection"],
        },
    ),
    types.Tool(
        name="agentic_query",
        description=(
            "Full agentic RAG loop: the LLM plans multi-step retrieval, expands queries "
            "if results are weak, reranks candidates, and produces a cited answer. "
            "Use this when you want a synthesized answer with sources."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "collection": {"type": "string"},
                "max_steps": {"type": "integer", "default": 5},
            },
            "required": ["query", "collection"],
        },
    ),
    types.Tool(
        name="list_collections",
        description="List all ingested knowledge collections.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="eval_metrics",
        description=(
            "Return the latest RAGAS evaluation scores for a collection: faithfulness, "
            "answer relevance, context precision, context recall."
        ),
        inputSchema={
            "type": "object",
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"],
        },
    ),
]


# --- Tool implementations ---


async def tool_ingest(path: str, collection: str) -> dict[str, Any]:
    result = await ingest_path(path, collection)
    return {
        "collection": collection,
        "documents_ingested": result.document_count,
        "chunks_created": result.chunk_count,
        "duration_ms": result.duration_ms,
    }


async def tool_semantic_search(query: str, collection: str, top_k: int = 5) -> dict[str, Any]:
    hits = await hybrid_search(query=query, collection=collection, top_k=top_k)
    return {
        "query": query,
        "collection": collection,
        "hits": [
            {
                "score": h.score,
                "text": h.text,
                "source": h.source,
                "chunk_id": h.chunk_id,
            }
            for h in hits
        ],
    }


async def tool_agentic_query(query: str, collection: str, max_steps: int = 5) -> dict[str, Any]:
    return await agentic_query(query=query, collection=collection, max_steps=max_steps)


async def tool_list_collections() -> dict[str, Any]:
    cols = await list_collections()
    return {"collections": cols}


async def tool_eval_metrics(collection: str) -> dict[str, Any]:
    metrics = await latest_eval(collection)
    return {"collection": collection, "metrics": metrics}
