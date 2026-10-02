"""HTTP adapter for authenticated Teams or Power Automate review submissions."""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable, Iterable
from wsgiref.simple_server import make_server


def queue_submission(payload: dict[str, Any], reviewer_id: str) -> dict[str, str]:
    required = {"workflow_id", "decision", "comment", "category"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"Missing adaptive-card fields: {', '.join(missing)}")
    decision = str(payload["decision"]).upper()
    if decision not in {"APPROVED", "REJECTED", "OVERRIDDEN"}:
        raise ValueError(f"Unsupported decision {decision}")
    from .main import queue_decision

    queue_decision(
        str(payload["workflow_id"]),
        decision,
        reviewer_id,
        str(payload["comment"]),
        str(payload["category"]),
    )
    return {"status": "queued", "workflow_id": str(payload["workflow_id"])}


def application(
    environ: dict[str, Any], start_response: Callable[[str, list[tuple[str, str]]], None]
) -> Iterable[bytes]:
    if environ.get("PATH_INFO") != "/api/reviewer-decisions" or environ.get("REQUEST_METHOD") != "POST":
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [b'{"error":"not_found"}']
    reviewer_id = environ.get("HTTP_X_MS_CLIENT_PRINCIPAL_ID")
    if not reviewer_id:
        start_response("401 Unauthorized", [("Content-Type", "application/json")])
        return [b'{"error":"authenticated_reviewer_required"}']
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        payload = json.loads(environ["wsgi.input"].read(length))
        result = queue_submission(payload, reviewer_id)
        body = json.dumps(result).encode()
        start_response("202 Accepted", [("Content-Type", "application/json")])
        return [body]
    except (ValueError, json.JSONDecodeError) as exc:
        body = json.dumps({"error": str(exc)}).encode()
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [body]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with make_server(args.host, args.port, application) as server:
        print(f"Reviewer webhook listening on http://{args.host}:{args.port}/api/reviewer-decisions")
        server.serve_forever()


if __name__ == "__main__":
    main()