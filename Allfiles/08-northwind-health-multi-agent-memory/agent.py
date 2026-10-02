from __future__ import annotations

import json
import os
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

from src.config import load_settings
from src.context_budget import select_context
from src.embeddings import EmbeddingService
from src.memory_store import PatientMemoryStore


load_dotenv()


@tool(approval_mode="never_require")
async def recall_patient_memory(
    query: Annotated[str, Field(description="The clinical question to use for semantic memory recall.")],
    top_k: Annotated[int, Field(description="The maximum number of memories to retrieve.", ge=1, le=10)] = 5,
) -> str:
    """Recall bounded memory for the synthetic patient assigned to this agent."""
    settings = load_settings()
    patient_id = os.getenv("AGENT_PATIENT_ID", "synthetic-patient-100")
    store = PatientMemoryStore(
        settings.cosmos_endpoint,
        settings.database_name,
        settings.memory_container,
        settings.audit_container,
        patient_id,
        EmbeddingService(settings.openai_endpoint, settings.embedding_deployment),
    )
    try:
        memories = await store.vector_recall(patient_id, query, top_k)
        evidence = {
            "patientId": patient_id,
            "retrievedMemoryIds": [memory["id"] for memory in memories],
            "boundedContext": select_context(memories, token_budget=500),
        }
        return json.dumps(evidence, default=str)
    finally:
        await store.close()


def main() -> None:
    model_name = os.environ["FOUNDRY_MODEL_NAME"]
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=model_name,
        credential=DefaultAzureCredential(),
    )
    agent = Agent(
        name="NorthwindHealthMemoryCoordinator",
        client=client,
        instructions=(
            "You are Northwind Health's Memory Coordinator for a synthetic training scenario. "
            "Call recall_patient_memory before answering any patient-specific question. "
            "Use only the returned bounded context, identify the memory IDs that support the answer, "
            "and state when the memory store does not contain enough evidence. Never invent patient details."
        ),
        tools=[recall_patient_memory],
        default_options={"store": False},
    )
    ResponsesHostServer(agent).run()


if __name__ == "__main__":
    main()