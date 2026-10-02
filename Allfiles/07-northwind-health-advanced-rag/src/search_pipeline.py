from __future__ import annotations

from typing import Any

from azure.core.credentials import TokenCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

from .embeddings import embed_texts


def hybrid_semantic_search(
    endpoint: str,
    index_name: str,
    credential: TokenCredential,
    embedding_client: AzureOpenAI,
    embedding_deployment: str,
    semantic_configuration: str,
    query: str,
    mode: str = "hybrid",
    vector_field: str = "content_vector",
    vector_weight: float = 0.7,
    top: int = 5,
    filter_expression: str | None = None,
) -> list[dict[str, Any]]:
    """Run vector-only, hybrid, or semantic ranking through Azure AI Search."""
    # LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.
    raise NotImplementedError("Complete hybrid_semantic_search in Task 5")