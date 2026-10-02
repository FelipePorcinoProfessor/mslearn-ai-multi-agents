from __future__ import annotations

from typing import Any

from azure.core.credentials import TokenCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

from .embeddings import embed_texts
from .experiment import embedding_text
from .index_manager import INDEX_NAMES


def upload_documents(
    endpoint: str,
    credential: TokenCredential,
    embedding_client: AzureOpenAI,
    embedding_deployment: str,
    documents: list[dict[str, Any]],
) -> dict[str, int]:
    """Embed and upload both generated chunk strategies to category indexes."""
    # LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
    raise NotImplementedError("Complete upload_documents in Task 3")