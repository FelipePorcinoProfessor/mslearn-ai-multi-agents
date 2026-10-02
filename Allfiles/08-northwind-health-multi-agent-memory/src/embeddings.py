from __future__ import annotations

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI


class EmbeddingService:
    def __init__(self, endpoint: str, deployment: str) -> None:
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
        self._client = AzureOpenAI(azure_endpoint=endpoint, azure_ad_token_provider=token_provider, api_version="2024-10-21")
        self._deployment = deployment

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self._deployment, input=[text])
        return response.data[0].embedding