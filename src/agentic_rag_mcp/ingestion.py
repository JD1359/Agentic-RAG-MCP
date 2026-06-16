"""Multi-format ingestion: parse, chunk, embed, store."""
import hashlib
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import tiktoken
from bs4 import BeautifulSoup
from markdownify import markdownify
from pypdf import PdfReader

from agentic_rag_mcp.config import settings
from agentic_rag_mcp.embeddings import embed_texts
from agentic_rag_mcp.storage import insert_chunks, ensure_collection

log = logging.getLogger(__name__)
_tokenizer = tiktoken.get_encoding("cl100k_base")

SUPPORTED_EXT = {".pdf", ".md", ".markdown", ".html", ".htm", ".txt",
                 ".py", ".go", ".js", ".ts", ".java", ".rs", ".c", ".cpp", ".rb"}


@dataclass
class IngestionResult:
    document_count: int
    chunk_count: int
    duration_ms: int


async def ingest_path(path: str, collection: str) -> IngestionResult:
    started = time.perf_counter()
    await ensure_collection(collection)

    p = Path(path)
    if p.is_file():
        files = [p]
    elif p.is_dir():
        files = [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXT]
    else:
        raise FileNotFoundError(f"path not found: {path}")

    total_chunks = 0
    for f in files:
        text = _read_file(f)
        if not text.strip():
            continue
        chunks = _chunk(text)
        if not chunks:
            continue
        embeddings = await embed_texts(chunks)
        rows = [
            {
                "collection": collection,
                "source": str(f),
                "chunk_id": _chunk_id(f, i, ch),
                "text": ch,
                "embedding": emb,
                "ord": i,
            }
            for i, (ch, emb) in enumerate(zip(chunks, embeddings))
        ]
        await insert_chunks(rows)
        total_chunks += len(rows)
        log.info("ingested", extra={"file": str(f), "chunks": len(rows)})

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return IngestionResult(document_count=len(files), chunk_count=total_chunks, duration_ms=elapsed_ms)


def _read_file(p: Path) -> str:
    ext = p.suffix.lower()
    if ext == ".pdf":
        return _read_pdf(p)
    if ext in {".html", ".htm"}:
        html = p.read_text(encoding="utf-8", errors="replace")
        return markdownify(html, heading_style="ATX")
    # Markdown, text, code — read as-is
    return p.read_text(encoding="utf-8", errors="replace")


def _read_pdf(p: Path) -> str:
    reader = PdfReader(str(p))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _chunk(text: str) -> list[str]:
    """Token-aware sliding window with paragraph-boundary preference."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []

    tokens = _tokenizer.encode(text)
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    if len(tokens) <= size:
        return [text]

    chunks = []
    i = 0
    while i < len(tokens):
        window = tokens[i : i + size]
        chunks.append(_tokenizer.decode(window))
        if i + size >= len(tokens):
            break
        i += size - overlap
    return chunks


def _chunk_id(path: Path, ord_: int, text: str) -> str:
    """Stable content-addressed ID. Allows re-ingestion to dedupe."""
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{path.name}:{ord_}:{h}"
