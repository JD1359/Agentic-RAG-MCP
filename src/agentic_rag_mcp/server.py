"""MCP server entrypoint — wires Tools to the official Anthropic MCP SDK."""
import json
import logging
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
import mcp.types as types

from agentic_rag_mcp.tools import (
    TOOL_DEFINITIONS,
    tool_ingest,
    tool_semantic_search,
    tool_agentic_query,
    tool_list_collections,
    tool_eval_metrics,
)
from agentic_rag_mcp.observability import setup_logging

log = logging.getLogger(__name__)


def build_server() -> Server:
    server = Server("agentic-rag-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        log.info("tool_call", extra={"name": name, "args": list(arguments.keys())})
        match name:
            case "ingest":
                result = await tool_ingest(**arguments)
            case "semantic_search":
                result = await tool_semantic_search(**arguments)
            case "agentic_query":
                result = await tool_agentic_query(**arguments)
            case "list_collections":
                result = await tool_list_collections(**arguments)
            case "eval_metrics":
                result = await tool_eval_metrics(**arguments)
            case _:
                return [types.TextContent(type="text", text=f"unknown tool: {name}")]
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


async def run_stdio() -> None:
    setup_logging()
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name="agentic-rag-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


async def run_sse(host: str, port: int) -> None:
    """Run as an SSE server for remote use."""
    from fastapi import FastAPI
    import uvicorn

    setup_logging()
    server = build_server()
    sse = SseServerTransport("/messages/")

    app = FastAPI(title="agentic-rag-mcp")

    @app.get("/sse")
    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (r, w):
            await server.run(r, w, server.create_initialization_options())

    app.mount("/messages/", sse.handle_post_message)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()
