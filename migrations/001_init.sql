-- pgvector schema for agentic-rag-mcp

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS collections (
    name        TEXT PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id          BIGSERIAL PRIMARY KEY,
    collection  TEXT NOT NULL REFERENCES collections(name) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    chunk_id    TEXT NOT NULL UNIQUE,
    text        TEXT NOT NULL,
    embedding   vector(384) NOT NULL,
    ord         INT  NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chunks_collection ON chunks(collection);
CREATE INDEX IF NOT EXISTS idx_chunks_source     ON chunks(source);

-- HNSW index for fast approximate nearest-neighbor search.
-- m = 16, ef_construction = 64 (good defaults for under 10M vectors).
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS eval_runs (
    id          BIGSERIAL PRIMARY KEY,
    collection  TEXT NOT NULL,
    metrics     JSONB NOT NULL,
    run_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_collection_run_at
    ON eval_runs(collection, run_at DESC);
