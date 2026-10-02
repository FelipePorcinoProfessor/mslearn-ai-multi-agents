from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from azure.core.credentials import TokenCredential
from openai import AzureOpenAI

from .router import route_query
from .search_pipeline import hybrid_semantic_search


def embedding_text(document: dict[str, Any], profile: str) -> str:
    """Build a stable embedding input that preserves content-specific signals."""
    if profile == "baseline":
        return str(document["content"])
    if profile != "content-aware":
        raise ValueError(f"Unknown embedding profile: {profile}")
    category = str(document["category"])
    labels = {
        "formulary": "Medication monograph; preserve exact drug names and interaction section.",
        "guidelines": "Clinical workflow guideline; preserve recommendation and parent topic.",
        "labs": "Laboratory reference; preserve test names, units, ranges, and escalation language.",
    }
    if category not in labels:
        raise ValueError(f"Unknown content category: {category}")
    return "\n".join(
        (
            labels[category],
            f"Title: {document['title']}",
            f"Parent: {document['parent_id']}",
            f"Chunk: {document['chunk_order']}",
            f"Content: {document['content']}",
        )
    )


def reciprocal_rank(results: list[dict[str, Any]], expected_parent_ids: set[str]) -> float:
    for rank, result in enumerate(results, start=1):
        if str(result.get("parent_id")) in expected_parent_ids:
            return 1.0 / rank
    return 0.0


def run_experiment(
    endpoint: str,
    credential: TokenCredential,
    embedding_client: AzureOpenAI,
    embedding_deployment: str,
    semantic_configuration: str,
    queries: list[dict[str, Any]],
    chunk_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Collect live ranking, latency, and embedding-input evidence."""
    documents = list(chunk_manifest["chunks"])
    strategies = [summary["strategy"] for summary in chunk_manifest["strategy_summaries"]]
    trials: list[dict[str, Any]] = []
    for case in queries:
        expected_parent_ids = {str(value) for value in case["expected_parent_ids"]}
        for strategy in strategies:
            for index_name in route_query(str(case["query"])):
                for mode in ("vector", "hybrid", "semantic"):
                    profiles = ("baseline", "content-aware") if mode in {"vector", "hybrid"} else ("not-applicable",)
                    for profile in profiles:
                        started = time.perf_counter()
                        results = hybrid_semantic_search(
                            endpoint,
                            index_name,
                            credential,
                            embedding_client,
                            embedding_deployment,
                            semantic_configuration,
                            str(case["query"]),
                            mode=mode,
                            vector_field="optimized_vector" if profile == "content-aware" else "content_vector",
                            filter_expression=f"chunk_strategy eq '{strategy}'",
                        )
                        trials.append(
                            {
                                "query": case["query"],
                                "index": index_name,
                                "chunk_strategy": strategy,
                                "mode": mode,
                                "embedding_profile": profile,
                                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                                "reciprocal_rank": reciprocal_rank(results, expected_parent_ids),
                                "ranking": [
                                    {
                                        "id": result.get("id"),
                                        "parent_id": result.get("parent_id"),
                                    }
                                    for result in results
                                ],
                                "scores": [
                                    {
                                        "id": result.get("id"),
                                        "search_score": result.get("@search.score"),
                                        "reranker_score": result.get("@search.reranker_score"),
                                    }
                                    for result in results
                                ],
                            }
                        )
    aggregates: list[dict[str, Any]] = []
    aggregate_keys = sorted(
        {(trial["chunk_strategy"], trial["mode"], trial["embedding_profile"]) for trial in trials}
    )
    for strategy, mode, profile in aggregate_keys:
        matching = [
            trial
            for trial in trials
            if (trial["chunk_strategy"], trial["mode"], trial["embedding_profile"])
            == (strategy, mode, profile)
        ]
        aggregates.append(
            {
                "chunk_strategy": strategy,
                "mode": mode,
                "embedding_profile": profile,
                "trial_count": len(matching),
                "mrr": round(sum(trial["reciprocal_rank"] for trial in matching) / len(matching), 4),
                "average_latency_ms": round(sum(trial["latency_ms"] for trial in matching) / len(matching), 2),
            }
        )
    return {
        "service": "Azure AI Search",
        "chunk_strategies": chunk_manifest["strategy_summaries"],
        "aggregates": aggregates,
        "trials": trials,
        "embedding_inputs": [
            {
                "id": document["id"],
                "category": document["category"],
                "chunk_strategy": document["chunk_strategy"],
                "parent_id": document["parent_id"],
                "boundary_start": document["boundary_start"],
                "boundary_end": document["boundary_end"],
                "section_heading": document["section_heading"],
                "baseline_chars": len(embedding_text(document, "baseline")),
                "content_aware_chars": len(embedding_text(document, "content-aware")),
            }
            for document in documents
        ],
    }