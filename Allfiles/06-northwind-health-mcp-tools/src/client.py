from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import httpx
from azure.identity.aio import DefaultAzureCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .catalog import select_compatible_tool
from .result_validation import validate_or_fallback


async def _authorization_headers(server_url: str, token_scope: str | None) -> dict[str, str]:
    if urlparse(server_url).hostname in {"127.0.0.1", "localhost"}:
        return {}
    if not token_scope:
        raise ValueError("MCP_TOKEN_SCOPE is required for a remote MCP server")
    async with DefaultAzureCredential() as credential:
        token = await credential.get_token(token_scope)
    return {"Authorization": f"Bearer {token.token}"}


async def discover_tools(server_url: str, token_scope: str | None = None) -> list[dict[str, Any]]:
    """Initialize an MCP session and return protocol-discovered tool metadata."""
    headers = await _authorization_headers(server_url, token_scope)
    # LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
    raise NotImplementedError("Complete discover_tools in Task 4")


async def call_catalog_tool(
    server_url: str,
    request: dict[str, Any],
    token_scope: str | None = None,
) -> dict[str, Any]:
    """Discover, select, invoke, and validate an MCP tool."""
    headers = await _authorization_headers(server_url, token_scope)
    # LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.
    raise NotImplementedError("Complete call_catalog_tool in Task 5")