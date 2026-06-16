"""Environment-driven configuration via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Postgres
    postgres_url: str = "postgres://app:app@localhost:5432/rag"

    # LLM provider
    llm_provider: str = "openai"   # openai / anthropic / local
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Embeddings + reranker
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    embedding_dim: int = 384

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Retrieval
    top_k_retrieval: int = 20
    top_k_rerank: int = 5
    bm25_weight: float = 0.5

    # Agentic loop
    max_agent_steps: int = 5

    # MCP transport
    mcp_transport: str = "stdio"   # stdio / sse
    http_port: int = 8080

    # Observability
    log_level: str = "info"
    prometheus_port: int = 9090


settings = Settings()
