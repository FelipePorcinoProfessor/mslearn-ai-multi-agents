"""Run a responsible AI governance workflow across three Foundry agents."""

import argparse
import json
import os
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from .governance import (
    append_evidence,
    build_agent_payload,
    build_governance_evidence,
    emit_evidence_to_azure_monitor,
    load_policy,
)

ROOT = Path(__file__).resolve().parents[1]
AGENT_INSTRUCTIONS = {
    "security-reviewer": (
        "Review only the supplied synthetic source. Return a concise finding, recommendation, "
        "confidence, and the supplied external evidence reference. Do not quote the full source."
    ),
    "fairness-auditor": (
        "Explain whether the supplied group rates exceed the policy threshold. Identify the lower-rate "
        "group without inferring protected characteristics or requesting source code."
    ),
    "governance-orchestrator": (
        "Combine the supplied specialist results and deterministic policy decision into a concise, "
        "attributed recommendation. Never request raw source, tenant identity, or hidden reasoning."
    ),
}


def response_text(response: Any) -> str:
    return "\n".join(
        getattr(part, "text", "")
        for item in response.output
        if getattr(item, "type", None) == "message"
        for part in getattr(item, "content", [])
    ).strip()


def call_agent(openai: Any, payload: dict[str, Any]) -> dict[str, str]:
    response = openai.responses.create(
        input=json.dumps(payload),
    )
    return {"responseId": response.id, "text": response_text(response)}


def create_agents(project: AIProjectClient, model: str) -> dict[str, str]:
    return {
        name: project.agents.create_version(
            agent_name=name,
            definition=PromptAgentDefinition(model=model, instructions=instructions),
        ).name
        for name, instructions in AGENT_INSTRUCTIONS.items()
    }


def deterministic_responses() -> dict[str, dict[str, str]]:
    return {
        "security-reviewer": {
            "responseId": "local-security-response",
            "text": "Use a parameterized query; evidence reference CWE-89.",
        },
        "fairness-auditor": {
            "responseId": "local-fairness-response",
            "text": "The Node probe rate is lower and exceeds the allowed disparity.",
        },
        "governance-orchestrator": {
            "responseId": "local-governance-response",
            "text": "Route this review to a human with attributed specialist evidence.",
        },
    }


def run_pipeline(scenario: dict[str, Any], policy: dict[str, Any], live: bool) -> dict[str, Any]:
    evidence = build_governance_evidence(scenario, policy)

    if live:
        credential = DefaultAzureCredential()
        project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential)
        versions = create_agents(project, os.environ["FOUNDRY_MODEL_NAME"])
        clients = {
            name: project.get_openai_client(agent_name=agent_name)
            for name, agent_name in versions.items()
        }
        security = call_agent(
            clients["security-reviewer"],
            build_agent_payload("security-reviewer", scenario, evidence),
        )
        fairness = call_agent(
            clients["fairness-auditor"],
            build_agent_payload("fairness-auditor", scenario, evidence),
        )
        specialist_outputs = {
            "security-reviewer": security,
            "fairness-auditor": fairness,
        }
        orchestrator = call_agent(
            clients["governance-orchestrator"],
            build_agent_payload("governance-orchestrator", scenario, evidence, specialist_outputs),
        )
        responses = {**specialist_outputs, "governance-orchestrator": orchestrator}
    else:
        responses = deterministic_responses()

    evidence["agent_response_ids"] = {
        name: response["responseId"] for name, response in responses.items()
    }
    append_evidence(str(ROOT / "evidence/governance-evidence.jsonl"), evidence)
    if live:
        emit_evidence_to_azure_monitor(evidence)

    return {
        "mode": "live" if live else "deterministic",
        "agentResponses": responses,
        "payloadFields": {
            name: sorted(build_agent_payload(
                name,
                scenario,
                evidence,
                {key: responses[key] for key in ("security-reviewer", "fairness-auditor")},
            ))
            for name in AGENT_INSTRUCTIONS
        },
        "governanceEvidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    scenario = json.loads((ROOT / "assets/governance-scenario.json").read_text(encoding="utf-8"))
    policy = load_policy(str(ROOT / "policy/governance-policy.yaml"))
    print(json.dumps(run_pipeline(scenario, policy, args.live), indent=2))


if __name__ == "__main__":
    main()