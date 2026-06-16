"""Optional API-key middleware for the SSE transport.

Set the `MCP_API_KEY` env var to require clients to send `X-API-Key: <value>` on
every request. If unset, the server runs open (suitable for local dev and stdio).
"""
import os

from fastapi import HTTPException, Request

API_KEY_HEADER = "X-API-Key"


def require_api_key(request: Request) -> None:
    expected = os.environ.get("MCP_API_KEY")
    if not expected:
        return
    provided = request.headers.get(API_KEY_HEADER)
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
