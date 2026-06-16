"""Ingest documents from a local directory into a collection.

Usage:
  python examples/ingest_docs.py <path> [collection]
"""
import asyncio
import sys

from agentic_rag_mcp.ingestion import ingest_path


async def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python examples/ingest_docs.py <path> [collection]", file=sys.stderr)
        return 1
    path = sys.argv[1]
    collection = sys.argv[2] if len(sys.argv) > 2 else "demo"
    print(f"ingesting {path!r} → collection={collection!r}...")
    result = await ingest_path(path, collection)
    print(f"  documents: {result.document_count}")
    print(f"  chunks:    {result.chunk_count}")
    print(f"  duration:  {result.duration_ms} ms")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
