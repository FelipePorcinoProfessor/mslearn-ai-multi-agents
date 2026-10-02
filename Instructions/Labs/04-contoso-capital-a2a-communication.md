---
lab:
  title: 'Design enterprise-scale agent communication with A2A in Azure'
  description: 'Implement tenant-isolated A2A discovery, JSON-RPC messaging, Cosmos DB shared state, and conflict audit trails.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Design enterprise-scale agent communication with A2A in Azure

## Customer scenario

Contoso Capital must connect independently deployed research agents without hardcoded endpoints. Discovery must be capability based, tenant context must never cross boundaries, shared state must survive restarts, and contradictory recommendations need a durable resolution record.

## Lab scenario

You will complete an A2A-compatible agent-card endpoint and JSON-RPC message endpoint, register cards in Azure Cosmos DB, route by tenant/capability/health, update task state with ETags, and write conflict decisions to an audit container.

<!-- LAB DIAGRAM PLACEHOLDER: Show tenant-scoped discovery, A2A message routing, Cosmos DB task state, and the conflict audit path. -->

By the end of this exercise, you will be able to:

- Design an A2A discovery registry and dynamic routing policy.
- Persist distributed shared state with optimistic concurrency.
- Enforce tenant-scoped context isolation.
- Detect, resolve, and audit conflicting agent outputs.

> **Important**: Cosmos DB and the model deployment are billable. A2A capabilities may be preview; verify current support before production use. The lab uses local HTTP endpoints and synthetic data only.

## Task 1: Prepare the lab

Use [Python 3.11+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)/[Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install), [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download), and an authenticated subscription. You need permission to create Foundry, Cosmos DB, and data-plane role assignments. The examples use local port 8000; you can select another free port.

1. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Open the cloned repository in Visual Studio Code.
3. From the VS Code terminal, validate the required tools, credentials, and active subscription:

```powershell
cd Allfiles\04-contoso-capital-a2a-communication
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `infra/main.bicep`, `src/a2a_server.py`, `src/registry.py`, and the supplied agent-card assets. Before continuing, confirm that:

- trusted tenant context supplies the `/tenantId` partition key;
- the discovery registry expires stale agent cards while the audit container remains durable;
- ETags protect shared task updates;
- an accepted A2A request can reach the Foundry agent invocation and produce a server-side trace.

## Task 2: Build the virtual environment

1. From the lab directory, create and activate the virtual environment:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

## Task 3: Deploy the Azure resources

Check cost and role access before provisioning Foundry, Cosmos DB, Application Insights, and 30-day Log Analytics retention. Use a unique environment and synthetic tenant data. `azd` provisions infrastructure; the A2A server and protocol tests run locally.

**Set the deployment values**

1. Set `$azureRegion` to an approved region that supports the selected model.
2. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

> **Note:** `AZURE_DEV_USER_AGENT` tags provisioning for attribution and is not exported to `.env`. Remove it afterward to avoid tagging unrelated commands.

**Validate and provision the infrastructure**

3. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab04-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new lab04
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set FOUNDRY_MODEL_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_CATALOG_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_VERSION 2026-03-17
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

4. If provisioning fails, inspect the first Azure deployment error.

Model or region availability, Cosmos DB availability, quota, and role-assignment permissions are common causes.

5. Correct the relevant `azd env` setting or permission, then run `azd provision` again.

**Verify the generated environment**

6. After provisioning succeeds, validate that `.env` includes `COSMOS_ENDPOINT`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_PROJECT_ID`, `FOUNDRY_MODEL_NAME`, `APPLICATIONINSIGHTS_RESOURCE_ID`, and `LOG_ANALYTICS_WORKSPACE_ID`.

The Application Insights connection string is stored in the Foundry project connection and is not written to `.env`.

> **Network access for this lab:** The Bicep template enables native public network access for Foundry and Cosmos DB so the local application can reach both data-plane endpoints. Microsoft Entra authentication and Azure RBAC are still required. After deployment, confirm public access on both resources and confirm that the Foundry default network action is **Allow**. Production environments should use an approved selected-network or private-endpoint design.

7. Do not add a Cosmos key, connection string, or token to `.env`.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

**Register a tenant-owned agent card**

1. Open `src/registry.py` and find **LAB PLACEHOLDER 1** in `Registry.register`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete Registry.register in Task 1")
```

2. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
required_fields = ("id", "url", "capabilities")
if any(not card.get(field) for field in required_fields):
  raise ValueError("Agent card requires id, url, and capabilities")
if not isinstance(card["capabilities"], list):
  raise ValueError("Agent card capabilities must be a list")

entry = {
  **card,
  "tenantId": tenant_id,
  "health": "healthy",
  "heartbeat": int(time.time()),
  "ttl": int(os.getenv("REGISTRY_TTL_SECONDS", "300")),
}
return self.registry.upsert_item(entry)
```

The trusted caller supplies `tenant_id`; a card cannot choose its own partition. Health and heartbeat fields make stale instances filterable before the container TTL removes abandoned registrations.

**Discover a fresh healthy agent**

3. Find **LAB PLACEHOLDER 2** in `Registry.discover`:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete Registry.discover in Task 2")
```

4. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
cutoff = int(time.time()) - int(os.getenv("HEARTBEAT_MAX_AGE_SECONDS", "120"))
query = """
SELECT * FROM c
WHERE c.tenantId = @tenant
  AND ARRAY_CONTAINS(c.capabilities, @capability)
  AND c.health = "healthy"
  AND c.heartbeat >= @cutoff
"""
parameters = [
  {"name": "@tenant", "value": tenant_id},
  {"name": "@capability", "value": capability},
  {"name": "@cutoff", "value": cutoff},
]
candidates = list(
  self.registry.query_items(
    query=query,
    parameters=parameters,
    partition_key=tenant_id,
    enable_cross_partition_query=False,
  )
)
return sorted(candidates, key=lambda item: float(item.get("load", 1.0)))[:1]
```

Partition-scoped, parameterized discovery filters by capability, health, and heartbeat freshness, then returns the lowest-load eligible agent. Freshness filtering takes effect before TTL deletion.

**Update shared task state with ETags**

5. Find **LAB PLACEHOLDER 3** in `Registry.update_task`:

```python
# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
raise NotImplementedError("Complete Registry.update_task in Task 3")
```

6. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
for _ in range(3):
  try:
    current = self.tasks.read_item(item=task_id, partition_key=tenant_id)
  except exceptions.CosmosResourceNotFoundError:
    initial = {
      "id": task_id,
      "tenantId": tenant_id,
      "contributions": {agent_id: contribution},
      "updatedAt": int(time.time()),
    }
    try:
      return self.tasks.create_item(initial)
    except exceptions.CosmosResourceExistsError:
      continue

  current.setdefault("contributions", {})[agent_id] = contribution
  current["updatedAt"] = int(time.time())
  try:
    return self.tasks.replace_item(
      item=current["id"],
      body=current,
      etag=current["_etag"],
      match_condition=MatchConditions.IfNotModified,
    )
  except exceptions.CosmosHttpResponseError as exc:
    if exc.status_code != 412:
      raise

raise RuntimeError("Task update failed after three ETag attempts")
```

Creation handles competing writers without overwriting them. Later updates use ETags; a 412 triggers a reread and reapplies only the caller's contribution, with a three-attempt limit.

**Resolve and audit conflicting outputs**

7. Find **LAB PLACEHOLDER 4** in `Registry.resolve_and_audit`:

```python
# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
raise NotImplementedError("Complete resolve_and_audit in Task 4")
```

8. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
candidates = conflict.get("candidates", [])
if len(candidates) < 2:
  raise ValueError("A conflict requires at least two candidates")

priority = {"compliance": 3, "risk": 2, "analysis": 1}
highest = max(priority.get(item.get("role", ""), 0) for item in candidates)
winners = [
  item
  for item in candidates
  if priority.get(item.get("role", ""), 0) == highest
]
if highest == 0 or len(winners) != 1:
  resolution = "escalated"
  chosen_agent = None
else:
  resolution = "priority"
  chosen_agent = winners[0]["agent_id"]

audit_record = {
  "id": str(uuid.uuid4()),
  "tenantId": tenant_id,
  "taskId": conflict["task_id"],
  "timestamp": int(time.time()),
  "resolution": resolution,
  "chosenAgent": chosen_agent,
  "candidates": [
    {"agent_id": item["agent_id"], "role": item["role"]}
    for item in candidates
  ],
}
self.audit.create_item(audit_record)
return {
  "status": resolution,
  "chosen_agent": chosen_agent,
  "audit_id": audit_record["id"],
}
```

Compliance outranks risk, which outranks analysis; tied winners or no recognized priority escalate. The audit retains participants and the decision, not model content, endpoints, or credentials.

**Handle a tenant-scoped JSON-RPC message**

9. Open `src/a2a_server.py` and find **LAB PLACEHOLDER 5** in `handle_message`:

```python
# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.
raise NotImplementedError("Complete handle_message in Task 5")
```

10. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
if payload.get("jsonrpc") != "2.0" or payload.get("method") != "message/send":
  raise ValueError("Expected JSON-RPC 2.0 method message/send")
if "id" not in payload:
  raise ValueError("JSON-RPC request id is required")

params = payload.get("params", {})
tenant_id = params.get("tenantId")
trusted_tenant = os.getenv("A2A_TENANT_ID", "contoso")
if tenant_id != trusted_tenant:
  raise ValueError("Tenant is unavailable")

parts = params.get("message", {}).get("parts", [])
text = "\n".join(
  str(part.get("text", ""))
  for part in parts
  if part.get("kind") == "text" and part.get("text")
).strip()
if not text:
  raise ValueError("At least one text message part is required")

project = AIProjectClient(
  endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
  credential=DefaultAzureCredential(),
)
agent = project.agents.create_version(
  agent_name=CARD["name"],
  definition=PromptAgentDefinition(
    model=os.environ["FOUNDRY_MODEL_NAME"],
    instructions=(
      "Analyze only synthetic portfolio risk. State assumptions, "
      "identify missing evidence, and do not provide investment advice."
    ),
  ),
)
openai = project.get_openai_client(agent_name=agent.name)
response = openai.responses.create(
  input=text,
)
return {
  "jsonrpc": "2.0",
  "id": payload["id"],
  "result": {
    "tenantId": tenant_id,
    "response_id": response.id,
    "text": extract_text(response),
  },
}
```

The endpoint validates protocol shape before making a model call and compares message context with the trusted local tenant setting. The agent-bound OpenAI client uses the agent's dedicated endpoint, so the response request does not carry a shared-endpoint `agent_reference`. In production, authenticated middleware would derive that tenant value from verified identity claims rather than request JSON.

**Check the completed code**

11. Run side-effect-free checks before starting the local server or accessing Azure:

```powershell
python -m py_compile src/main.py src/registry.py src/a2a_server.py scripts/preflight.py
python scripts/preflight.py
```

12. Confirm that preflight reports four `PASS` lines, both starter files retain all five `LAB PLACEHOLDER` markers, and neither file contains `NotImplementedError`.

## Task 5: Run the solution

Use two terminals at the lab root, each with the virtual environment activated. Terminal 1 runs Uvicorn; Terminal 2 runs clients and validation. Temporary environment variables are terminal-local. Keep Uvicorn running until Task 7.

**Start the A2A server**

1. In **Terminal 1**, activate the environment, register the card, and start the server:

```powershell
. ./.venv/Scripts/Activate.ps1
$port = 8000
$env:A2A_TENANT_ID = 'contoso'
$env:A2A_BASE_URL = "http://127.0.0.1:$port"
python -m src.main register --card assets/risk-agent-card.json
python -m uvicorn src.a2a_server:app --host 127.0.0.1 --port $port
```

2. Wait for `Uvicorn running on http://127.0.0.1:8000` (or your chosen port). If using another port, update all client URLs below.

**Run the A2A client commands**

3. Open **Terminal 2** at `Allfiles\04-contoso-capital-a2a-communication`. If activation fails because the environment is missing, run `./scripts/setup.ps1` on Windows or `bash scripts/setup.sh` on macOS/Linux before continuing.
4. Activate the environment with `. ./.venv/Scripts/Activate.ps1`. On macOS/Linux, use `source .venv/bin/activate` instead. Then run the client commands:

```powershell
. ./.venv/Scripts/Activate.ps1
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/.well-known/agent-card.json
python -m src.main discover --tenant contoso --capability risk-analysis
python -m src.main send --url http://127.0.0.1:8000/a2a --message assets/a2a-request.json
```

**Check the responses**

5. Compare the output with these criteria:

| Operation | Expected evidence |
|---|---|
| `register` (Terminal 1) | `id: risk-east-v1`, `tenantId: contoso`, `health: healthy`, `ttl: 300`, and a recent integer `heartbeat`. Cosmos system fields such as `_etag` vary. |
| HTTP access log (Terminal 1) | `/`, `/.well-known/agent-card.json`, and `/a2a` return `200 OK`. Inspect bodies in Terminal 2; HTTP success alone is insufficient. |
| Readiness | `status: ready` and the agent-card and message endpoint paths. |
| Agent card | `name: contoso-risk-agent` and `url: http://127.0.0.1:8000/a2a`; no Cosmos or Foundry endpoint, key, or token. |
| Discovery | One selected document for `contoso`, with `health: healthy` and capability `risk-analysis`. |
| Send | JSON-RPC `2.0`, `id: request-001`, `result.tenantId: contoso`, a populated `result.response_id`, and synthetic portfolio-risk text. |

6. If discovery returns an empty array, rerun `python -m src.main register --card assets/risk-agent-card.json` in Terminal 2 and retry immediately. Registrations become ineligible after 120 seconds without a heartbeat.

Task ETags and `audit_id` are generated by the shared-state checks below, not by these initial commands.

## Task 6: Validate the implementation

1. Keep the Uvicorn server running in **Terminal 1**.
2. Run all validation commands in **Terminal 2**, from the lab root with `(.venv)` visible in the prompt:

The syntax check is local; the next two commands call Uvicorn.

```powershell
python -m py_compile src/main.py src/registry.py src/a2a_server.py scripts/preflight.py
Invoke-RestMethod http://127.0.0.1:8000/.well-known/agent-card.json
python -m src.main send --url http://127.0.0.1:8000/a2a --message assets/a2a-request.json
```

3. Confirm that the syntax command returns to the prompt without an error, the agent-card request shows `contoso-risk-agent`, and the `send` command returns JSON-RPC `2.0` with `id: "request-001"` and a populated `result.response_id`.

**Exercise durable shared state and conflict audit**

4. Continue in **Terminal 2** while Terminal 1 keeps the server running.

The following test accesses Cosmos DB directly through `DefaultAzureCredential`, not through Uvicorn.

5. Run these checks first:

```powershell
Test-Path .env
Get-Content .env | Select-String '^COSMOS_(ENDPOINT|DATABASE_NAME)='
az account show --output table
```

`Test-Path` must return `True`, and the next command must display populated `COSMOS_ENDPOINT` and `COSMOS_DATABASE_NAME` lines.

6. If `.env` is missing or either value is empty, rerun `azd env get-values | Out-File .env -Encoding utf8` from the lab root before continuing.
7. Confirm that `az account show` displays the account used to provision the lab.

8. Run the entire block, including `@'` and `'@ | python -`, to pass the Python script to the active environment:

```powershell
@'
import os
from pathlib import Path

from azure.core import MatchConditions
from azure.cosmos import exceptions
from dotenv import load_dotenv
from src.registry import Registry

load_dotenv(Path.cwd() / ".env")
if not os.getenv("COSMOS_ENDPOINT"):
  raise RuntimeError("COSMOS_ENDPOINT is missing from the lab-root .env file")

registry = Registry()
first = registry.update_task("contoso", "task-001", "risk-agent", {"status": "review"})
stale = registry.tasks.read_item(item="task-001", partition_key="contoso")
second = registry.update_task("contoso", "task-001", "compliance-agent", {"status": "hold"})
stale["stale_writer"] = "must-not-persist"
try:
  registry.tasks.replace_item(
    item=stale["id"],
    body=stale,
    etag=stale["_etag"],
    match_condition=MatchConditions.IfNotModified,
  )
  raise AssertionError("The stale ETag write unexpectedly succeeded")
except exceptions.CosmosAccessConditionFailedError as exc:
  print("stale_write_rejected:", exc.status_code)
recovered = registry.update_task(
  "contoso", "task-001", "supervisor-agent", {"status": "conflict-observed"}
)
decision = registry.resolve_and_audit("contoso", {
  "task_id": "task-001",
  "candidates": [
    {"agent_id": "risk-agent", "role": "risk"},
    {"agent_id": "compliance-agent", "role": "compliance"},
  ],
})
print("first_etag:", first["_etag"])
print("second_etag:", second["_etag"])
print("recovered_etag:", recovered["_etag"])
print("decision:", decision)
'@ | python -
```

The script captures a task version, advances the document with a second writer, proves Cosmos DB rejects the stale conditional replacement with HTTP 412, then uses the lab's normal merge path from a fresh read and persists the deterministic conflict decision in `audit`.

9. In Terminal 2, confirm `stale_write_rejected: 412` appears and that `first_etag`, `second_etag`, and `recovered_etag` are populated and pairwise different.

The `stale_writer` field must not persist. `supervisor-agent` demonstrates recovery after the rejected stale write; the A2A implementation itself remains unchanged.

The `decision` value must contain `status: "priority"`, `chosen_agent: "compliance-agent"`, and a populated `audit_id` UUID.

10. Save the printed `audit_id` for the portal check.

11. In Terminal 2, read the task from a new Python process to verify persistence beyond the first process:

```powershell
@'
import os
from pathlib import Path

from dotenv import load_dotenv
from src.registry import Registry

load_dotenv(Path.cwd() / ".env")
if not os.getenv("COSMOS_ENDPOINT"):
  raise RuntimeError("COSMOS_ENDPOINT is missing from the lab-root .env file")

registry = Registry()
task = registry.tasks.read_item(item="task-001", partition_key="contoso")
print("task_id:", task["id"])
print("tenant_id:", task["tenantId"])
print("contributions:", task["contributions"])
print("current_etag:", task["_etag"])
'@ | python -
```

12. Confirm that `task_id` is `task-001`, `tenant_id` is `contoso`, `contributions` contains `risk-agent`, `compliance-agent`, and `supervisor-agent`, and no `stale_writer` field exists.

13. In the [Foundry portal](https://ai.azure.com), open the provisioned project and confirm a current `contoso-risk-agent` version.
14. Select **Agents** > **Traces**.
15. Set the time range to include the valid Contoso request.
16. Search for the `result.response_id` value printed by the `send` command.
17. Open the matching trace and confirm the agent name, version, successful response operation, and timing.
18. In the Azure portal, open the provisioned Cosmos DB account and select **Data Explorer** > **agent-ecosystem** > **registry** > **Items**.

The registry container deliberately deletes inactive cards after five minutes because its default TTL is 300 seconds.

19. If **Items** is empty, run the following command in Terminal 2, then immediately select **Refresh** in Data Explorer:

   ```powershell
   python -m src.main register --card assets/risk-agent-card.json
   ```

20. Open `risk-east-v1` and confirm its `tenantId`, health, heartbeat, TTL, and A2A URL.

The durable `tasks` and `audit` containers use TTL `-1`, so their documents remain until explicitly deleted.

21. Select **Data Explorer** > **agent-ecosystem** > **tasks** > **Items**.
22. Open `task-001` and confirm that `contributions` contains `risk-agent`, `compliance-agent`, and `supervisor-agent`, and that `stale_writer` is absent.

Its current `_etag` should match `recovered_etag` until another write changes the document.

23. Select **Data Explorer** > **agent-ecosystem** > **audit** > **Items**.
24. Find the item whose `id` matches the printed `audit_id`; confirm that `resolution` is `priority` and `chosenAgent` is `compliance-agent`.

**Test cross-tenant rejection**

25. Keep Uvicorn running in Terminal 1.
26. In Terminal 2, create a temporary copy of the supplied request, change its request ID and tenant with PowerShell's JSON support, and send it:

```powershell
$request = Get-Content assets/a2a-request.json -Raw | ConvertFrom-Json
$request.id = 'request-fabrikam-001'
$request.params.tenantId = 'fabrikam'
$request | ConvertTo-Json -Depth 10 | Set-Content artifacts-a2a-request-fabrikam.json -Encoding utf8
python -m src.main send --url http://127.0.0.1:8000/a2a --message artifacts-a2a-request-fabrikam.json
```

27. Confirm that Terminal 2 prints this error body and no `response_id`:

```json
{
  "detail": "Tenant is unavailable"
}
```

28. Confirm that Terminal 1 logs `POST /a2a` with `400 Bad Request`.
29. Confirm that the rejected request does not create a Foundry trace or return a cross-tenant Cosmos DB result.
30. Remove the temporary request after the check:

```powershell
Remove-Item artifacts-a2a-request-fabrikam.json
```

Foundry traces prove accepted model calls, not local discovery, JSON-RPC validation, tenant checks, ETag updates, or conflict resolution. Use HTTP and Cosmos DB evidence for those boundaries. Allow several minutes for trace ingestion. Client-side tracing, KQL, sampling, and alerts are covered in Lab 13.

## Optional challenge: Resolve a concurrent update

Send two synthetic updates with the same starting ETag but different proposed values.

**Expected output:** Exactly one update succeeds, one returns a conflict decision, and the audit evidence records both proposed versions without exposing unrelated tenant context.

**Failure investigation:** Submit a stale ETag and trace the rejection through protocol validation, state access, conflict handling, and audit logging.

## Task 7: Review the design

Record brief answers:

- Why does tenant ownership come from the trusted caller rather than the agent card?
- Why can the discovery registry expire while the audit container remains durable?
- How do ETags prevent one agent from silently overwriting another agent's contribution?
- Which conflict decisions must remain deterministic rather than being delegated to an agent?

## Task 8: Clean up

**Remove Azure resources**

1. Stop Uvicorn in Terminal 1 by pressing **Ctrl+C**.
2. Run the following commands in either terminal:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge --force
Remove-Item Env:AZURE_DEV_USER_AGENT
```

**Deactivate the virtual environment**

3. Run this command separately in Terminal 1 and Terminal 2 if `(.venv)` appears in their prompts:

```powershell
deactivate
```

4. Confirm that `(.venv)` no longer appears in either terminal before changing to another lab directory.

## Summary

You implemented live A2A discovery and messaging, Cosmos DB shared state, tenant isolation, optimistic concurrency, and durable conflict audits.
