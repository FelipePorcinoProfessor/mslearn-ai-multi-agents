from __future__ import annotations

import json
import os
from typing import Annotated

from agent_framework import tool
from agent_framework_foundry_hosting import ResponsesHostServer
from pydantic import Field

from src.hosted_common import create_agent
from src.responses_client import invoke_responses_endpoint


async def _invoke_specialist(service: str, repository: str, commit: str, change_summary: str) -> str:
    prefix = service.upper()
    prompt = json.dumps(
        {
            "repository": repository,
            "commit": commit,
            "change_summary": change_summary,
            "requested_contract": service,
        },
        separators=(",", ":"),
    )
    result = await invoke_responses_endpoint(
        os.environ[f"{prefix}_RESPONSES_ENDPOINT"],
        os.environ[f"{prefix}_AGENT_NAME"],
        os.environ[f"{prefix}_AGENT_VERSION"],
        prompt,
    )
    return json.dumps(
        {
            "invocation": result.to_dict(),
        },
        separators=(",", ":"),
    )


@tool(approval_mode="never_require")
async def scan_code(
    repository: Annotated[str, Field(description="Synthetic repository identifier.")],
    commit: Annotated[str, Field(description="Source commit under review.")],
    change_summary: Annotated[str, Field(description="Summary of the code change.")],
) -> str:
    """Invoke the immutable scanner version selected for this release set."""
    return await _invoke_specialist("scanner", repository, commit, change_summary)


@tool(approval_mode="never_require")
async def review_change(
    repository: Annotated[str, Field(description="Synthetic repository identifier.")],
    commit: Annotated[str, Field(description="Source commit under review.")],
    change_summary: Annotated[str, Field(description="Summary of the code change.")],
) -> str:
    """Invoke the immutable reviewer version selected for this release set."""
    return await _invoke_specialist("reviewer", repository, commit, change_summary)


def main() -> None:
    agent = create_agent("orchestrator", tools=[scan_code, review_change])
    ResponsesHostServer(agent).run()


if __name__ == "__main__":
    main()
