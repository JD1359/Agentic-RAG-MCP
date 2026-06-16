"""Postgres + pgvector persistence layer."""
import json
import logging
from typing import Any

import asyncpg
from pgvector.asyncpg import register_vector

from agentic_rag_mcp.config import settings

log = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.postgres_url,
            min_size=2,
            max_size=10,
            init=_init_conn,
        )
    return _pool


async def _init_conn(conn: asyncpg.Connection) -> None:
    await register_vector(conn)


async def ensure_collection(name: str) -> None:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO collections (name) VALUES ($1) ON CONFLICT DO NOTHING",
            name,
        )


async def insert_chunks(rows: list[dict[str, Any]]) -> None:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO chunks (collection, source, chunk_id, text, embedding, ord)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (chunk_id) DO NOTHING
            """,
            [(r["collection"], r["source"], r["chunk_id"], r["text"], r["embedding"], r["ord"])
             for r in rows],
        )


async def vector_search(collection: str, query_vec: list[float], top_k: int) -> list[dict]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT chunk_id, text, source,
                   1 - (embedding <=> $1) AS score
            FROM chunks
            WHERE collection = $2
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            query_vec, collection, top_k,
        )
    return [dict(r) for r in rows]


async def fetch_collection_chunks(collection: str, limit: int = 5000) -> list[dict]:
    """Fetch chunks for in-memory BM25. For very large collections, swap with PG full-text."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chunk_id, text, source FROM chunks WHERE collection = $1 LIMIT $2",
            collection, limit,
        )
    return [dict(r) for r in rows]


async def list_collections() -> list[dict]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.name,
                   COUNT(ch.id) AS chunk_count,
                   COUNT(DISTINCT ch.source) AS doc_count,
                   c.created_at
            FROM collections c
            LEFT JOIN chunks ch ON ch.collection = c.name
            GROUP BY c.name, c.created_at
            ORDER BY c.created_at DESC
            """
        )
    return [
        {"name": r["name"], "documents": r["doc_count"],
         "chunks": r["chunk_count"], "created_at": str(r["created_at"])}
        for r in rows
    ]


async def latest_eval(collection: str) -> dict[str, Any]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT metrics, run_at FROM eval_runs
            WHERE collection = $1
            ORDER BY run_at DESC LIMIT 1
            """,
            collection,
        )
    if not row:
        return {}
    return {**json.loads(row["metrics"]), "run_at": str(row["run_at"])}


async def record_eval(collection: str, metrics: dict[str, Any]) -> None:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO eval_runs (collection, metrics) VALUES ($1, $2)",
            collection, json.dumps(metrics),
        )
