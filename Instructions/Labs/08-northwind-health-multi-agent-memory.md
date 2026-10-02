---
lab:
  title: 'Build persistent shared memory for Foundry agents'
  description: 'Build a Microsoft Foundry Hosted Agent that recalls patient-scoped vector memory from Azure Cosmos DB with retention, context budgeting, audit, and consistency controls.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Build persistent shared memory for Foundry agents

## Customer scenario

Northwind Health's scheduling, care-navigation, and medication-support agents need shared, reviewed patient preferences. A Memory Coordinator must supply bounded, patient-scoped evidence with consistent isolation, read-your-writes behavior, retention, and auditable deletion.

## Lab scenario

You are the memory-platform developer. You will implement the custom memory layer in Azure Cosmos DB for NoSQL, then connect it to a Microsoft Agent Framework agent hosted by Microsoft Foundry. The agent uses a read-only local tool to recall memory for one configured synthetic patient, builds bounded context, and asks a Foundry chat model for a grounded response. Memory writes, reviewed consolidation, and destructive pruning remain explicit administrative CLI operations.

<!-- LAB DIAGRAM PLACEHOLDER: Show the hosted agent, patient-scoped recall tool, Cosmos DB memory and audit containers, and administrative write paths. -->

You build one reusable specialist with a controlled interface for other agents, not a model impersonating several agents.

By the end of this exercise, you will be able to:

- Map working, episodic, and semantic memory to appropriate persistence patterns.
- Implement patient-scoped vector memory with Azure Cosmos DB and `VectorDistance`.
- Apply context budgeting, retention, pruning, and audit policies.
- Compare session and eventual consistency for memory read-after-write behavior.
- Host a Microsoft Agent Framework agent in Foundry and ground its responses in custom Cosmos DB memory.

> **Important**: Live Azure validation is required because vector indexing, RU charge, partition behavior, TTL, and consistency are service behaviors. The serverless account is billable. Use only synthetic data and run `azd down --purge` after validation.

## Task 1: Prepare the lab

Install [Python 3.13](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI 1.27.1 or later](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Git](https://git-scm.com/downloads), [Visual Studio Code](https://code.visualstudio.com/download), and the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python), [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep), and [Foundry Toolkit](https://marketplace.visualstudio.com/items?itemName=ms-windows-ai-studio.windows-ai-studio) extensions. You need permission to create a Cosmos DB account, Foundry account and project, model deployments, hosted agent, and role assignments. Vector search and model availability vary by region.

**Clone and open the repository**

1. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

3. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\08-northwind-health-multi-agent-memory
az version
azd version
python --version
az account show --output table
```

4. Use `DefaultAzureCredential`.
5. Do not use account keys, connection strings, real patient data, or globally shared memory partitions.

**Architecture checkpoint**

Review these boundaries before editing:

| Boundary | Component |
|---|---|
| Hosted conversation and read-only recall tool | `agent.py` |
| Durable patient-scoped memory | `src/memory_store.py` and the memory container |
| Bounded model context | `src/context_budget.py` |
| Session consistency transfer | `src/consistency.py` |
| Retention and deletion | `src/retention.py` |
| Durable audit evidence | Audit container |
| Azure resources and synthetic input | `infra/main.bicep` and `assets/memories.json` |

Before continuing, confirm that Cosmos DB—not conversation history—is the durable memory authority and that memory and audit records use separate containers.

> Do not replace Cosmos operations with an in-memory list or local vector calculation.

## Task 2: Build the virtual environment

1. Create and activate the virtual environment:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

2. Inspect `assets/memories.json`; the patient IDs and observations are synthetic. The starter generates embeddings at ingestion time rather than storing fixed vectors.

## Task 3: Deploy the Azure resources

**Set the deployment values**

1. Review cost, model quota, and access before provisioning.

Cosmos DB vector operations, both Foundry model deployments, and Hosted Agent compute are billable.

2. Use a unique environment.
3. Use synthetic data only.
4. Remove the resources after validation.

`azd` provisions the Bicep resources. Memory ingestion and recall run separately.

5. Specify an approved region where Cosmos DB vector search, Microsoft Foundry, and both model deployments are available.
6. The following example uses `eastus2`; change it if your subscription has different model availability or quota.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

**Validate and provision the infrastructure**

7. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
az login
azd auth login
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab08-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
azd env new lab08-memory-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd provision
azd env get-values | Out-File .env -Encoding utf8
```

8. If provisioning fails, inspect the first Azure deployment error. Cosmos DB or model regional availability, `GlobalStandard` quota, and role-assignment permissions are common causes.
9. Correct the relevant setting or permission, then run `azd provision` again.

**Verify the generated environment**

10. Confirm that `.env` includes `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL_NAME`, `AZURE_COSMOS_ENDPOINT`, the database and memory/audit container names, `AZURE_OPENAI_ENDPOINT`, and the embedding deployment name. `AZURE_OPENAI_ENDPOINT` points to the Foundry `AIServices` account, not a separate `kind: OpenAI` account.
11. Allow data-plane RBAC to propagate.
12. Do not add account keys, connection strings, or tokens.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

The constructor already creates one reusable async `CosmosClient` with `DefaultAzureCredential` and session consistency. Keep that client for the lifetime of the store.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Persist an embedded memory**

1. In `src/memory_store.py`, find the exact marker `# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.`

2. Replace only the `raise NotImplementedError` line beneath it with:

```python
    patient_id = str(memory["patientId"])
    self._authorize(patient_id)
    item = {
      **memory,
      "embedding": self._embeddings.embed(str(memory["content"])),
    }
    response = await self._memories.upsert_item(item)
    headers = response.get_response_headers()
    return {
      "id": response["id"],
      "patientId": response["patientId"],
      "request_charge": float(headers.get("x-ms-request-charge", 0)),
      "session_token": headers.get("x-ms-session-token"),
    }
```

Authorization happens before embedding or I/O. The returned diagnostics expose RU cost and the session token without returning memory content.

The container sets `defaultTtl` to 2,592,000 seconds. An item without `ttl` inherits that container default, a positive item `ttl` overrides it, and item `ttl: -1` disables expiration for that item while TTL remains enabled on the container.

**Run partition-scoped vector recall**

3. In `src/memory_store.py`, find the exact marker `# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.`

4. Replace only the `raise NotImplementedError` line beneath it with:

```python
    self._authorize(patient_id)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 20:
      raise ValueError("top_k must be an integer from 1 through 20")
    embedding = self._embeddings.embed(query_text)
    query = f"""
      SELECT TOP {top_k}
        c.id, c.patientId, c.content, c.importance, c.memoryType,
        c.critical, c.timestamp, c.ttl,
        VectorDistance(c.embedding, @embedding) AS vector_distance
      FROM c
      WHERE c.patientId = @patientId
      ORDER BY VectorDistance(c.embedding, @embedding)
    """
    response_headers: dict[str, str] = {}
    iterator = self._memories.query_items(
      query=query,
      parameters=[
        {"name": "@patientId", "value": patient_id},
        {"name": "@embedding", "value": embedding},
      ],
      partition_key=patient_id,
      response_hook=lambda headers, _: response_headers.update(headers),
    )
    results = [item async for item in iterator]
    request_charge = float(response_headers.get("x-ms-request-charge", 0))
    for item in results:
      item["request_charge"] = request_charge
    return results
```

Only the validated integer is interpolated into `TOP`; patient ID and embedding remain parameters. The partition key enforces a single physical patient partition.

The lab uses a `quantizedFlat` vector index, but meaningful index-performance testing requires a meaningfully large vector population. Use at least 1,000 vectors before drawing performance conclusions; the six synthetic starter records validate query behavior, not vector-index scale or latency.

**Write content-free audit evidence**

5. In `src/memory_store.py`, find the exact marker `# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.`

6. Replace only the `raise NotImplementedError` line beneath it with:

```python
    self._authorize(patient_id)
    await self._audit.upsert_item(
      {
        "id": event_id or str(uuid4()),
        "patientId": patient_id,
        "operation": operation,
        "memoryIds": sorted(set(memory_ids)),
        "reason": reason,
        "timestamp": event_timestamp or datetime.now(UTC).isoformat(),
      }
    )
```

The audit event identifies the operation and affected records but deliberately excludes memory content and embeddings.

**Prove read-your-writes consistency**

7. In `src/consistency.py`, find the exact marker `# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.`

8. Replace only the `raise NotImplementedError` line beneath it with:

```python
  diagnostics = await store.upsert_memory(memory)
  session_token = diagnostics.get("session_token")
  if not session_token:
    raise RuntimeError("The write response did not include a session token")
  item = await store._memories.read_item(
    item=memory["id"],
    partition_key=memory["patientId"],
    session_token=session_token,
  )
  return {
    "write_id": diagnostics["id"],
    "read_id": item["id"],
    "patientId": item["patientId"],
    "session_token_transferred": True,
    "request_charge": diagnostics["request_charge"],
  }
```

The immediate point read uses both the same partition key and the write token. An eventual-consistency client cannot provide this explicit read-your-writes boundary.

**Build bounded memory context**

9. In `src/context_budget.py`, find the exact marker `# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.`

10. Replace only the `raise NotImplementedError` line beneath it with:

```python
  if token_budget < 1:
    raise ValueError("token_budget must be positive")
  recent_count = max(1, (len(memories) * 3 + 9) // 10) if memories else 0
  recent = sorted(memories, key=lambda item: str(item["timestamp"]), reverse=True)[:recent_count]
  ranked = sorted(
    memories,
    key=lambda item: (
      float(item.get("importance", 0)) * 0.5
      + (1.0 / (1.0 + float(item.get("vector_distance", 1)))) * 0.5
    ),
    reverse=True,
  )
  ordered = recent + [item for item in ranked if item not in recent]
  selected: list[dict[str, Any]] = []
  blocks: list[str] = []
  used = estimate_tokens("<patient_memory>\n</patient_memory>")
  for item in ordered:
    block = f"<memory id=\"{item['id']}\">{item['content']}</memory>"
    cost = estimate_tokens(block)
    if used + cost <= token_budget:
      selected.append(item)
      blocks.append(block)
      used += cost
  return {
    "selected_ids": [item["id"] for item in selected],
    "token_count": used,
    "context": "<patient_memory>\n" + "\n".join(blocks) + "\n</patient_memory>",
  }
```

Recent records receive a 30% reservation before the remaining candidates are ranked by importance and vector distance. Explicit delimiters separate stored memory from instructions.

**Apply retention and audit deletion**

11. In `src/retention.py`, find the exact marker `# LAB PLACEHOLDER 6: Replace this line with the Task 6 sample.`

12. Replace only the `raise NotImplementedError` line beneath it with:

```python
  store._authorize(patient_id)
  eligible_ids = sorted(
    str(memory["id"])
    for memory in memories
    if memory.get("patientId") == patient_id
    and not bool(memory.get("critical"))
    and int(memory.get("ttl", -1)) > 0
    and datetime.fromisoformat(
      str(memory["timestamp"]).replace("Z", "+00:00")
    ) + timedelta(seconds=int(memory["ttl"])) <= datetime.now(UTC)
    and float(memory.get("importance", 0)) <= 4.0
  )
  if dry_run:
    return {"status": "dry_run", "eligible_ids": eligible_ids, "deleted_count": 0}
  for memory_id in eligible_ids:
    await store._memories.delete_item(item=memory_id, partition_key=patient_id)
  if eligible_ids:
    await store.write_audit(
      patient_id,
      "retention_prune",
      eligible_ids,
      "expired noncritical memory with finite TTL and importance at or below 4.0",
    )
  return {
    "status": "applied",
    "eligible_ids": eligible_ids,
    "deleted_count": len(eligible_ids),
  }
```

Dry run and apply use the same deterministic eligibility rule. The stored timestamp plus the Cosmos DB TTL must be in the past before a record is eligible. Every delete remains partition-scoped, and critical, unexpired, or indefinite-TTL records are preserved.

**Review guarded consolidation**

No code replacement is required.

13. Review episodic records `mem-100-3`, `mem-100-4`, and `mem-100-5`.
14. Run consolidation first with `--dry-run`.
15. Verify that the three sources support one repeated reminder preference.
16. Then apply it.

The completed method point-reads every source from the patient partition, derives TTL from the sources, then sends the semantic-memory create and every ETag-conditional source patch in one Cosmos DB transactional batch. Because all records use the same `patientId` partition key, the batch either commits all lineage changes or none. The deterministic semantic ID and audit event ID make retries idempotent; the audit remains in its separate container and is safely retried after the memory batch commits.

**Check the completed code**

17. Run the following command:

```powershell
python scripts/preflight.py
```

Preflight must end with `Preflight passed`.

18. Run it only after completing all six coding placeholders so it validates the learner implementation rather than the untouched starter.

## Task 5: Run the solution

**Run the memory operations**

1. Load the synthetic memories and capture write diagnostics:

```powershell
python -m src.main ingest --file assets/memories.json
```

2. Recall memory for one patient and build context:

```powershell
python -m src.main recall --patient-id synthetic-patient-100 --query "medication tolerance and appointment preferences" --top 5 --budget 500
```

3. Validate read-your-writes consistency:

```powershell
python -m src.main consistency --patient-id synthetic-patient-100
```

4. Run a dry-run prune before allowing deletion:

```powershell
python -m src.main prune --patient-id synthetic-patient-100 --dry-run
```

5. Consolidate repeated episodic evidence into a reviewed semantic pattern.
6. Never infer a clinical pattern from these reminder examples.

```powershell
python -m src.main consolidate --patient-id synthetic-patient-100 --source-id mem-100-3 --source-id mem-100-4 --source-id mem-100-5 --summary "Repeatedly requests written reminders before synthetic follow-ups." --reviewer-id reviewer-07 --dry-run
python -m src.main consolidate --patient-id synthetic-patient-100 --source-id mem-100-3 --source-id mem-100-4 --source-id mem-100-5 --summary "Repeatedly requests written reminders before synthetic follow-ups." --reviewer-id reviewer-07
```

**Understand the output**

Ingestion reports each memory ID, patient partition, RU charge, and whether Cosmos returned a session token; it does not echo content. Recall returns a `retrieved_memories` array containing the authorized patient's records in ascending `vector_distance` order and their query RU charge. Its `bounded_context` object lists selected IDs, estimated token count, and a delimited `<patient_memory>` block. Prune output separates eligible IDs from `deleted_count`, while consolidation distinguishes `dry_run` from `consolidated` and records retained source lineage.

**Run the Memory Coordinator locally**

7. Open a second terminal in the lab folder.
8. Activate the same virtual environment and start the Responses server.
9. Keep this terminal running:

```powershell
. ./.venv/Scripts/Activate.ps1
azd ai agent run memory-coordinator --no-client
```

10. In the first terminal, invoke the local agent with a patient-specific question:

```powershell
azd ai agent invoke memory-coordinator --local --new-session "What reminder and appointment preferences should the care team consider? Cite the supporting memory IDs."
```

`AGENT_PATIENT_ID` binds the recall tool to `synthetic-patient-100` for authorization and partition scoping; the model cannot choose a patient ID.

11. Confirm that the response cites retrieved memory IDs and does not invent details outside the bounded context.
12. Press **Ctrl+C** in the server terminal when local validation is complete.

**Deploy and invoke the Hosted Agent**

13. Deploy the same tested code to Foundry, then invoke the remote agent:

```powershell
azd deploy memory-coordinator
azd ai agent invoke memory-coordinator --new-session "What reminder and appointment preferences should the care team consider? Cite the supporting memory IDs."
```

Foundry hosts the Responses endpoint and model call. The tool queries Cosmos DB using the project managed identity; patient memory remains in Cosmos DB.

## Task 6: Validate the implementation

Inspect the live output from **Run the solution**, then complete the portal and additional live checks below. Local preflight alone does not validate these service behaviors.

**Review evidence from the commands already run**

1. Use the terminal output from **Run the solution** to confirm:

- `ingest` reports each written ID, `patientId`, RU charge, and a session token without echoing memory content.
- `recall` returns only records for `synthetic-patient-100`. Confirm that `vector_distance` values in `retrieved_memories` are ascending, each record reports the same query `request_charge`, and `bounded_context.token_count` is no greater than 500.
- `consistency` reports matching `write_id` and `read_id`, `session_token_transferred: true`, and the write RU charge.
- `prune --dry-run` reports `status: dry_run`, `deleted_count: 0`, and the eligible IDs while preserving the critical record.
- The consolidation dry run reports three source records and performs no writes. The applied run reports `status: consolidated`, one semantic memory ID, the three retained source IDs, and transactional-batch diagnostics.
- Both local and deployed agent invocations call `recall_patient_memory`, cite supporting memory IDs, and limit their claims to the bounded context.

**Inspect the persisted records in the Azure portal**

2. In the [Microsoft Foundry portal](https://ai.azure.com), open the project provisioned for this lab. Confirm that the `gpt-5.4-mini` and `text-embedding-3-small` deployments exist and that `northwind-health-memory-coordinator` has a deployed version.
3. In the [Azure portal](https://portal.azure.com), open the Cosmos DB account provisioned for this lab.
4. Select **Data Explorer** > **clinical-memory-db** > **patient-memories** > **Items**.
5. Open an ingested memory and confirm it contains `patientId`, `schemaVersion`, `memoryType`, `importance`, `timestamp`, `ttl`, and an `embedding` array. The vector embedding policy in the container requires 1,536 dimensions.
6. Open `mem-100-3`, `mem-100-4`, and `mem-100-5`. After applied consolidation, confirm that all three source documents remain and contain the same `consolidatedInto` semantic memory ID.
7. Open the corresponding `semantic_pattern` document and confirm that `sourceMemoryIds` contains the three source IDs and `reviewerId` is `reviewer-07`.

These portal checks validate persistence and lineage. They do not replace the terminal checks for vector ordering, RU charge, context budgeting, or session-token transfer.

**Complete the remaining live checks**

8. First, rerun the applied consolidation command **before pruning**:

```powershell
python -m src.main consolidate --patient-id synthetic-patient-100 --source-id mem-100-3 --source-id mem-100-4 --source-id mem-100-5 --summary "Repeatedly requests written reminders before synthetic follow-ups." --reviewer-id reviewer-07
```

9. Expect `status: already_consolidated` with the same semantic memory and source IDs, confirming that retry reconciliation does not create a duplicate semantic memory and safely restores the deterministic audit event if needed.

10. Next, apply the retention policy. This command deletes the eligible noncritical, finite-TTL records, so run it only after completing the consolidation and lineage checks above:

```powershell
python -m src.main prune --patient-id synthetic-patient-100
```

11. Confirm that the output reports `status: applied` and a nonzero `deleted_count`.
12. Then, in Data Explorer, select **clinical-memory-db** > **memory-audit** > **Items**.
13. Confirm that the `retention_prune` audit event contains the patient ID, operation, affected memory IDs, reason, and timestamp, but no memory content or embedding.

The cross-patient authorization boundary is a code-level safeguard rather than a separate CLI scenario.

14. Review `_authorize` in `src/memory_store.py` and confirm that it raises `PermissionError` before embedding or Cosmos DB I/O when the requested patient differs from the patient bound to the store.

## Optional challenge: Gate memory consolidation

Add a synthetic confidence field and consolidate only evidence at or above a documented threshold.

**Expected output:** Low-confidence evidence remains in source history but does not appear in the consolidated reminder; accepted evidence records the threshold and reviewer.

**Failure investigation:** Repeat the same consolidation request and determine whether idempotency or deduplication prevents a duplicate semantic memory.
## Task 7: Review the design

1. Answer these questions:

- Which memory fields should be immutable after creation?
- How should a contradiction supersede an older memory without destroying audit history?
- When is explicit session-token transfer required instead of client-local token management?
- What would a right-to-deletion verification query need to prove?

## Task 8: Clean up

**Remove Azure resources**

1. Run the following command:

```powershell
azd down --purge --force
```

2. Confirm that the Cosmos DB account, Foundry account and project, model deployments, and Hosted Agent are deleted.
3. Remove `.env`.

**Deactivate the virtual environment**

4. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

5. Confirm that `(.venv)` no longer appears before changing to another lab directory.

## Summary

You implemented live vector memory persistence, patient isolation, read-your-writes consistency, context budgeting, retention, and audit patterns with Azure Cosmos DB for NoSQL.
