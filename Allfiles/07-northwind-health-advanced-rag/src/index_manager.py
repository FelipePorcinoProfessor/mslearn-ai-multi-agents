from __future__ import annotations

from azure.core.credentials import TokenCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

INDEX_NAMES = {
    "formulary": "northwind-formulary-v1",
    "guidelines": "northwind-guidelines-v1",
    "labs": "northwind-labs-v1",
}


def create_or_update_indexes(
    endpoint: str,
    credential: TokenCredential,
    vector_dimensions: int,
    semantic_configuration: str,
) -> list[str]:
    """Create the three indexes needed by the routed retrieval pipeline."""
    # LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
    raise NotImplementedError("Complete create_or_update_indexes in Task 1")