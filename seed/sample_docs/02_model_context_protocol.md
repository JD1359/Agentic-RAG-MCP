# Model Context Protocol (MCP)

## What is MCP?

Model Context Protocol is an open standard published by Anthropic in November
2024 for connecting AI models to tools and data. It defines a JSON-RPC-based
protocol over either standard input/output (stdio) or Server-Sent Events (SSE).
MCP servers expose **tools** (function-call-like operations), **resources**
(read-only data sources), and **prompts** (reusable prompt templates).

MCP is supported by Claude Desktop, Cursor, Cline, Continue, Zed, and Windsurf.

## Why stdio is the right default transport

The stdio transport runs the MCP server as a child process of the client
application. Communication is via stdin/stdout JSON-RPC frames. This is the
right default because: it requires no network configuration, gives the client
process-level isolation of the server, and works identically across operating
systems.

SSE is the right choice for remote/team deployments. SSE adds the complexity of
authentication and network setup but unlocks multi-tenant use cases.

## Tool definitions

Each MCP tool is defined with a unique name, a human-readable description, and
a JSON Schema for its input. The description matters more than developers
typically expect - the LLM uses it to decide when to call the tool. A vague
description like "search docs" produces fewer correct invocations than a
specific one like "hybrid vector and BM25 search over an ingested knowledge
collection, returning top-k chunks with scores."

## Comparison to OpenAI function calling

OpenAI's function-calling API is per-vendor and per-request: each chat request
includes the function definitions. MCP is host-application-level: tools are
registered with the host once, and every subsequent chat in any conversation
has access to them. MCP also has standardized lifecycle and discovery semantics
across vendors, which function-calling APIs lack.
