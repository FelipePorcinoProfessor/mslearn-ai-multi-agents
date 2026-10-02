from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from azure.cosmos import ConsistencyLevel
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

from .embeddings import EmbeddingService


class PatientMemoryStore:
    def __init__(
        self,
        endpoint: str,
        database_name: str,
        memory_container: str,
        audit_container: str,
        session_patient_id: str,
        embedding_service: EmbeddingService,
    ) -> None:
        self._credential = DefaultAzureCredential()
        self._client = CosmosClient(endpoint, credential=self._credential, consistency_level=ConsistencyLevel.Session)
        database = self._client.get_database_client(database_name)
        self._memories = database.get_container_client(memory_container)
        self._audit = database.get_container_client(audit_container)
        self._session_patient_id = session_patient_id
        self._embeddings = embedding_service

    def _authorize(self, patient_id: str) -> None:
        if patient_id != self._session_patient_id:
            raise PermissionError(f"Session is not authorized for patient {patient_id}")

    async def upsert_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        """Persist one memory and return request diagnostics including session token."""
        # LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
        raise NotImplementedError("Complete upsert_memory in Task 1")

    async def vector_recall(self, patient_id: str, query_text: str, top_k: int) -> list[dict[str, Any]]:
        """Run a partition-scoped vector query ordered by VectorDistance."""
        # LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
        raise NotImplementedError("Complete vector_recall in Task 2")

    async def write_audit(
        self,
        patient_id: str,
        operation: str,
        memory_ids: list[str],
        reason: str,
        event_id: str | None = None,
        event_timestamp: str | None = None,
    ) -> None:
        """Write content-free audit metadata for a memory operation."""
        # LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
        raise NotImplementedError("Complete write_audit in Task 3")

    async def consolidate_episodic_memories(
        self,
        patient_id: str,
        source_ids: list[str],
        semantic_content: str,
        reviewer_id: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Consolidate reviewed episodic records into one persisted semantic pattern."""
        self._authorize(patient_id)
        unique_ids = sorted(set(source_ids))
        if len(unique_ids) < 2:
            raise ValueError("Consolidation requires at least two distinct episodic memories")
        if len(unique_ids) > 99:
            raise ValueError("Consolidation supports at most 99 sources in one transactional batch")
        if not semantic_content.strip() or len(semantic_content) > 1000:
            raise ValueError("Semantic content must contain 1-1000 characters")
        if not reviewer_id.strip():
            raise ValueError("A reviewer ID is required")

        digest = hashlib.sha256(f"{patient_id}:{':'.join(unique_ids)}".encode()).hexdigest()[:16]
        semantic_id = f"semantic-{digest}"
        sources = [
            await self._memories.read_item(item=memory_id, partition_key=patient_id)
            for memory_id in unique_ids
        ]
        if any(source.get("memoryType") != "episodic" for source in sources):
            raise ValueError("Every consolidation source must be episodic")
        consolidation_targets = {
            str(source["consolidatedInto"])
            for source in sources
            if source.get("consolidatedInto")
        }
        if all(
            source.get("consolidatedInto") == semantic_id
            for source in sources
        ):
            semantic = await self._memories.read_item(
                item=semantic_id,
                partition_key=patient_id,
            )
            if semantic.get("sourceMemoryIds") != unique_ids:
                raise RuntimeError("Existing semantic memory has inconsistent source lineage")
            if (
                semantic.get("content") != semantic_content.strip()
                or semantic.get("reviewerId") != reviewer_id
            ):
                raise ValueError(
                    "Retry input does not match the completed semantic consolidation"
                )
            await self.write_audit(
                patient_id,
                "consolidate_episodic_to_semantic",
                [*unique_ids, semantic_id],
                f"reviewed pattern consolidation by {reviewer_id}",
                event_id=f"audit-{semantic_id}",
                event_timestamp=str(semantic["timestamp"]),
            )
            return {
                "status": "already_consolidated",
                "semantic_memory_id": semantic_id,
                "source_memory_ids": unique_ids,
                "source_records_retained": True,
                "ttl": int(semantic["ttl"]),
            }
        if consolidation_targets:
            raise ValueError("A source memory has already been consolidated")

        critical = any(bool(source.get("critical")) for source in sources)
        positive_ttls = [int(source["ttl"]) for source in sources if int(source.get("ttl", 0)) > 0]
        ttl = -1 if critical else max(positive_ttls, default=2592000)
        semantic = {
            "id": semantic_id,
            "patientId": patient_id,
            "content": semantic_content.strip(),
            "importance": round(sum(float(source.get("importance", 0)) for source in sources) / len(sources), 2),
            "memoryType": "semantic_pattern",
            "critical": critical,
            "timestamp": datetime.now(UTC).isoformat(),
            "ttl": ttl,
            "schemaVersion": "1.0",
            "sourceMemoryIds": unique_ids,
            "reviewerId": reviewer_id,
            "retentionPolicy": "preserve-source-lineage",
        }
        if dry_run:
            return {"status": "dry_run", "semantic_memory": semantic, "source_count": len(sources)}

        semantic["embedding"] = self._embeddings.embed(str(semantic["content"]))
        batch_operations: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = [
            ("create", (semantic,), {}),
        ]
        for source in sources:
            batch_operations.append(
                (
                    "patch",
                    (
                        source["id"],
                        [
                            {"op": "add", "path": "/consolidatedInto", "value": semantic_id},
                            {"op": "add", "path": "/consolidatedAt", "value": semantic["timestamp"]},
                        ],
                    ),
                    {"if_match_etag": source["_etag"]},
                )
            )
        batch_results = await self._memories.execute_item_batch(
            batch_operations=batch_operations,
            partition_key=patient_id,
        )
        await self.write_audit(
            patient_id,
            "consolidate_episodic_to_semantic",
            [*unique_ids, semantic_id],
            f"reviewed pattern consolidation by {reviewer_id}",
            event_id=f"audit-{semantic_id}",
            event_timestamp=str(semantic["timestamp"]),
        )
        return {
            "status": "consolidated",
            "semantic_memory_id": semantic_id,
            "source_memory_ids": unique_ids,
            "source_records_retained": True,
            "ttl": ttl,
            "write_diagnostics": {
                "transactional_batch": True,
                "operation_count": len(batch_results),
            },
        }

    async def close(self) -> None:
        await self._client.close()
        await self._credential.close()