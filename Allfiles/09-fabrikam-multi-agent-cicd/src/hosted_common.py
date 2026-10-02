from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

ROOT = Path(__file__).resolve().parents[1]


def load_definition(service: str) -> dict[str, Any]:
    path = ROOT / "agents" / f"{service}.yml"
    if not path.exists():
        raise RuntimeError(f"Missing agent definition: {path}")
    definition = yaml.safe_load(path.read_text(encoding="utf-8"))
    if definition.get("name") != service:
        raise RuntimeError(f"Agent definition {path} does not declare name: {service}")
    return definition


def create_agent(service: str, *, tools: list[Any] | None = None) -> Agent:
    definition = load_definition(service)
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["FOUNDRY_MODEL_NAME"],
        credential=DefaultAzureCredential(),
    )
    contract = json.dumps(definition["tools"], sort_keys=True)
    instructions = (
        f"{definition['instructions']}\n\n"
        "Return concise JSON-compatible output that honors this source-controlled contract: "
        f"{contract}"
    )
    return Agent(
        name=f"Fabrikam{service.title()}",
        client=client,
        instructions=instructions,
        tools=tools or [],
        default_options={"store": False},
    )
