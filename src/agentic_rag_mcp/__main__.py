"""Entry point: `python -m agentic_rag_mcp`."""
import asyncio
import sys

from agentic_rag_mcp.config import settings
from agentic_rag_mcp.server import run_sse, run_stdio


def main() -> int:
    if settings.mcp_transport == "stdio":
        asyncio.run(run_stdio())
    elif settings.mcp_transport == "sse":
        asyncio.run(run_sse(host="0.0.0.0", port=settings.http_port))
    else:
        print(f"unknown MCP_TRANSPORT: {settings.mcp_transport}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
