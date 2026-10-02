"""Exercise deterministic and live Foundry multi-agent zero-trust paths."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from .security import VerifiedCaller, authorize_handoff, minimize_for_agent, validate_production_controls
from .security import select_authentication_flow

ROOT = Path(__file__).resolve().parents[1]
AGENT_INSTRUCTIONS = {
    "review-orchestrator": "Coordinate a synthetic code review. Never invent or change tenant context.",
    "security-scanner": "Return a concise security finding for the supplied synthetic source code.",
    "compliance-agent": "Assess residency, classification, and consent metadata. Never request source code.",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def deterministic_evidence(requests: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    results = []
    for request in requests:
        caller = VerifiedCaller(
            agent_id=request["verifiedCaller"]["agentId"],
            tenant_id=request["verifiedCaller"]["tenantId"],
        )
        try:
            authorize_handoff(caller, request["targetAgent"], request["tenantId"], policy)
            minimized = minimize_for_agent(request["targetAgent"], request["payload"])
            results.append(
                {
                    "case": request["case"],
                    "decision": "allow",
                    "target": request["targetAgent"],
                    "fieldsForwarded": sorted(minimized),
                }
            )
        except PermissionError as error:
            results.append({"case": request["case"], "decision": "deny", "reason": str(error)})
    authentication_flows = {
        "agentToAzure": select_authentication_flow({"supportsManagedIdentity": True}),
        "userToMicrosoftResource": select_authentication_flow(
            {"requiresUserPermissions": True, "resourceType": "microsoft"}
        ),
        "userToThirdParty": select_authentication_flow(
            {"requiresUserPermissions": True, "resourceType": "third_party"}
        ),
        "legacyApi": select_authentication_flow(
            {"keyStoredInKeyVault": True, "rotationDays": 90}
        ),
    }
    return {
        "productionControlFailures": validate_production_controls(policy),
        "authenticationFlows": authentication_flows,
        "decisions": results,
    }


def response_text(response: Any) -> str:
    return "\n".join(
        getattr(part, "text", "")
        for item in response.output
        if getattr(item, "type", None) == "message"
        for part in getattr(item, "content", [])
    ).strip()


def call_agent(openai: Any, payload: dict[str, Any]) -> dict[str, Any]:
    response = openai.responses.create(
        input=json.dumps(payload),
    )
    return {"responseId": response.id, "text": response_text(response)}


def cosmos_containers(credential: DefaultAzureCredential) -> tuple[Any, Any]:
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=credential)
    database = client.get_database_client(os.environ["COSMOS_DATABASE_NAME"])
    return (
        database.get_container_client(os.environ["COSMOS_POLICY_CONTAINER_NAME"]),
        database.get_container_client(os.environ["COSMOS_AUDIT_CONTAINER_NAME"]),
    )


def run_live(request: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    credential = DefaultAzureCredential()
    project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential)
    model = os.environ["FOUNDRY_MODEL_NAME"]
    versions = {
        name: project.agents.create_version(
            agent_name=name,
            definition=PromptAgentDefinition(model=model, instructions=instructions),
        ).name
        for name, instructions in AGENT_INSTRUCTIONS.items()
    }
    clients = {
        name: project.get_openai_client(agent_name=agent_name)
        for name, agent_name in versions.items()
    }
    caller = VerifiedCaller("review-orchestrator", request["tenantId"])
    policy_container, audit_container = cosmos_containers(credential)
    policy_container.upsert_item(
        {
            "id": "review-policy",
            "tenantId": request["tenantId"],
            "allowedRegion": request["payload"]["repositoryRegion"],
            "classification": request["payload"]["dataClassification"],
        }
    )
    tenant_policy = policy_container.read_item("review-policy", partition_key=request["tenantId"])
    try:
        authorize_handoff(
            VerifiedCaller("review-orchestrator", "tenant-b"),
            "security-scanner",
            request["tenantId"],
            policy,
        )
        cross_tenant_handoff_denied = False
    except PermissionError:
        cross_tenant_handoff_denied = True
    outputs: dict[str, Any] = {}
    for target in ("security-scanner", "compliance-agent"):
        authorize_handoff(caller, target, request["tenantId"], policy)
        outputs[target] = call_agent(
            clients[target],
            minimize_for_agent(target, request["payload"]),
        )
    orchestrator_output = call_agent(
        clients["review-orchestrator"],
        {
            "requestId": request["payload"]["requestId"],
            "tenantId": request["tenantId"],
            "specialistResults": outputs,
        },
    )
    event = {
        "id": str(uuid.uuid4()),
        "tenantId": request["tenantId"],
        "agentId": "review-orchestrator",
        "action": "multi_agent_review",
        "decision": "allow",
        "correlationId": request["payload"]["requestId"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    audit_container.create_item(event)
    return {
        "orchestratorAgent": versions["review-orchestrator"],
        "tenantPolicy": tenant_policy,
        "crossTenantHandoffDenied": cross_tenant_handoff_denied,
        "specialistOutputs": outputs,
        "orchestratorOutput": orchestrator_output,
        "auditEvent": event,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    policy = load_json(ROOT / "assets/security-policy.json")
    requests = load_json(ROOT / "assets/security-requests.json")
    result = run_live(requests[0], policy) if args.live else deterministic_evidence(requests, policy)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()