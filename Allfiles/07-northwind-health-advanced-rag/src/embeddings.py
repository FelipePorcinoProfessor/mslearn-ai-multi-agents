from __future__ import annotations

from collections.abc import Sequence

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI


def create_embedding_client(endpoint: str) -> AzureOpenAI:
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
    )


def embed_texts(client: AzureOpenAI, deployment: str, texts: Sequence[str]) -> list[list[float]]:
    """Generate embeddings in input order through the configured deployment."""
    # LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
    raise NotImplementedError("Complete embed_texts in Task 2")