from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.getenv("PORT", "8000"))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("northwind.mcp")
mcp = FastMCP("Northwind Clinical Tools v1", stateless_http=True, host="0.0.0.0", port=PORT)


def _load_json(name: str) -> list[dict[str, object]]:
    return json.loads((ROOT / "assets" / name).read_text(encoding="utf-8"))


def _log_invocation(tool_name: str, correlation_id: str, status: str) -> None:
    logger.info(
        json.dumps(
            {
                "event": "mcp_tool_invocation",
                "tool_name": tool_name,
                "correlation_id": correlation_id,
                "status": status,
            }
        )
    )


@mcp.tool()
async def lookup_drug_interaction(
    drug_a: str,
    drug_b: str,
    correlation_id: str,
) -> dict[str, object]:
    """Look up a medication pair in the synthetic interaction catalog."""
    # LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
    raise NotImplementedError("Complete lookup_drug_interaction in Task 1")


@mcp.tool()
async def get_appointment_capacity(
    site: str,
    date: str,
    correlation_id: str,
) -> dict[str, object]:
    """Return synthetic appointment capacity for a site and date."""
    # LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
    raise NotImplementedError("Complete get_appointment_capacity in Task 2")


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()