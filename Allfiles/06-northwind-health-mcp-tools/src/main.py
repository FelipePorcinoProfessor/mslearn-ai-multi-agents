from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .client import call_catalog_tool, discover_tools


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Northwind Health MCP lab client")
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover = subparsers.add_parser("discover")
    discover.add_argument("--server-url", required=True)
    call = subparsers.add_parser("call")
    call.add_argument("--server-url", required=True)
    call.add_argument("--request", type=Path, required=True)
    return parser


async def _run() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    args = _parser().parse_args()
    token_scope = os.getenv("MCP_TOKEN_SCOPE") or None
    if args.command == "discover":
        output = await discover_tools(args.server_url, token_scope)
    else:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        output = await call_catalog_tool(args.server_url, request, token_scope)
    print(json.dumps(output, indent=2))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()