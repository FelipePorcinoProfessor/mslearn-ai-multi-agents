from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential

AI_SCOPE = "https://ai.azure.com/.default"
RESPONSES_SUFFIX = "/endpoint/protocols/openai/responses"


@dataclass(frozen=True)
class InvocationEvidence:
    text: str
    agent_name: str
    requested_version: str
    served_version: str
    agent_session_id: str
    response_id: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for output in payload.get("output", []):
        for content in output.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    if not chunks:
        raise RuntimeError("The hosted-agent Responses endpoint returned no text output.")
    return "\n".join(chunks)


def _agent_urls(endpoint: str, agent_name: str) -> tuple[str, str]:
    parsed = urlsplit(endpoint)
    marker = f"/agents/{agent_name}"
    if marker not in parsed.path or not parsed.path.endswith(RESPONSES_SUFFIX):
        raise ValueError(
            "Responses endpoint must identify the configured agent and end with "
            f"{RESPONSES_SUFFIX}: {endpoint}"
        )
    agent_path = parsed.path.split(marker, 1)[0] + marker
    query = dict(parse_qsl(parsed.query))
    query.setdefault("api-version", "v1")
    session_url = urlunsplit(
        (parsed.scheme, parsed.netloc, f"{agent_path}/endpoint/sessions", urlencode(query), "")
    )
    responses_url = urlunsplit(
        (parsed.scheme, parsed.netloc, f"{agent_path}{RESPONSES_SUFFIX}", urlencode(query), "")
    )
    return session_url, responses_url


def version_endpoint(endpoint: str, agent_name: str, agent_version: str) -> str:
    parsed = urlsplit(endpoint)
    marker = f"/agents/{agent_name}"
    if marker not in parsed.path:
        raise ValueError(f"Responses endpoint does not identify agent {agent_name}: {endpoint}")
    prefix = parsed.path.split(marker, 1)[0]
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            f"{prefix}{marker}/versions/{agent_version}",
            "",
            "",
        )
    )


async def invoke_responses_endpoint(
    endpoint: str,
    agent_name: str,
    agent_version: str,
    prompt: str,
    *,
    credential: AsyncTokenCredential | None = None,
    client: httpx.AsyncClient | None = None,
) -> InvocationEvidence:
    owns_credential = credential is None
    owns_client = client is None
    credential = credential or DefaultAzureCredential()
    client = client or httpx.AsyncClient(timeout=120)
    try:
        token: AccessToken = await credential.get_token(AI_SCOPE)
        headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
        session_url, responses_url = _agent_urls(endpoint, agent_name)
        session_response = await client.post(
            session_url,
            headers=headers,
            json={
                "version_indicator": {
                    "type": "version_ref",
                    "agent_version": agent_version,
                }
            },
        )
        session_response.raise_for_status()
        session = session_response.json()
        session_id = session.get("agent_session_id")
        served_version = (session.get("version_indicator") or {}).get("agent_version")
        if not isinstance(session_id, str) or not session_id:
            raise RuntimeError("Foundry did not return an agent_session_id.")
        if str(served_version) != agent_version:
            raise RuntimeError(
                f"Foundry bound session to version {served_version!r}, expected {agent_version!r}."
            )
        response = await client.post(
            responses_url,
            headers=headers,
            json={"input": prompt, "agent_session_id": session_id},
        )
        response.raise_for_status()
        payload = response.json()
        header_version = response.headers.get("x-ms-agent-version")
        if header_version and header_version != agent_version:
            raise RuntimeError(
                f"Foundry response reported version {header_version!r}, expected {agent_version!r}."
            )
        return InvocationEvidence(
            text=response_text(payload),
            agent_name=agent_name,
            requested_version=agent_version,
            served_version=header_version or str(served_version),
            agent_session_id=session_id,
            response_id=payload.get("id") if isinstance(payload.get("id"), str) else None,
        )
    finally:
        if owns_client:
            await client.aclose()
        if owns_credential:
            await credential.close()
