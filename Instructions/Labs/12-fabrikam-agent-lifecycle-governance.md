---
lab:
  title: 'Govern a multi-agent topology lifecycle'
  description: 'Use Microsoft Foundry and Cosmos DB interfaces to govern agent versions, quotas, rate limits, metering, chargeback, and retirement.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Govern a multi-agent topology lifecycle

## Customer scenario

Fabrikam must govern releases of a code-review topology containing a scanner, reviewer, and orchestrator. The team must know which Foundry versions belong to each logical release, prove why the topology was approved, control tenant usage, and retire obsolete component versions without breaking consumers.

## Lab scenario

You will provision a Foundry project, model deployment, and Cosmos DB usage registry. You will inventory Foundry agents through `AIProjectClient`, implement a release gate, create versioned prompt agents for the scanner, reviewer, and orchestrator, enforce concrete usage controls, and execute a governed version retirement.

<!-- LAB DIAGRAM PLACEHOLDER: Show topology promotion, logical-to-Foundry version mapping, usage metering, and gated retirement. -->

By the end of this exercise, you will be able to:

- Enumerate prompt agents and immutable versions from the Foundry registry.
- Promote one approved three-agent topology as a governed release.
- Preserve a reproducible mapping between logical topology versions and Foundry versions.
- Enforce a 60-request-per-minute limit and 1,000,000-token monthly quota atomically.
- Meter usage and allocate estimated USD charges to a tenant and cost center.
- Retire one disposable prompt-agent version through explicit governance controls.

> **Important**: Use only the synthetic prompt-agent versions created during this exercise. Never point the retirement command at any other agent or version.

## Task 1: Prepare the lab

1. Install [Python 3.10+](https://www.python.org/downloads/), [Azure CLI 2.80+](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI 1.23+](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), and the [`azure.ai.agents` azd extension](https://learn.microsoft.com/azure/foundry/agents/how-to/install-cli-foundry-extensions).
2. Use a subscription with Foundry availability, permission to create an account and project, permission to deploy the selected model, and project access that allows prompt-agent version management.

3. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

4. Open the cloned repository in Visual Studio Code.
5. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\12-fabrikam-agent-lifecycle-governance
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `infra/main.bicep`, the approved version manifest, `src/lifecycle.py`, and `src/usage.py`, then use this table to locate each operation that can create, meter, or delete state:

| Function | Control to inspect |
|---|---|
| `promote_topology` | `validate_promotion` runs before `create_version`; a later creation failure removes versions created by that attempt. |
| `retire_version` | All retirement gates precede `delete_version`. The target is one lab-created Foundry version, not a logical topology version. |
| `enforce_and_meter_usage` | Placeholder 2 becomes one retry loop for rate/quota checks, charge calculation, and conditional meter replacement. It does not mutate Foundry versions. |

Before continuing, confirm that promotion, usage metering, and retirement have separate mutation boundaries and fail-closed controls.

## Task 2: Build the virtual environment

1. On Windows, run:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

2. Review `registry/fabrikam-review-topology-v2.4.0.yaml`. It defines the three agents, instructions, logical versions, compatibility declarations, evaluation results, and approval evidence used in this exercise.

## Task 3: Deploy Azure resources

1. Check Foundry and Cosmos DB costs and lifecycle/data-plane access. `azd` provisions infrastructure; the application creates agent versions later.
2. Set `$azureRegion` to an approved region that supports the required model and services.
3. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

> **Note:** `AZURE_DEV_USER_AGENT` tags provisioning for attribution and is not exported to `.env`. Remove it afterward to avoid tagging unrelated commands.

4. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
$modelDeploymentName = 'gpt-5.4-mini'
$modelName = 'gpt-5.4-mini'
$modelVersion = '2026-03-17'
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab12-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new lab12-agent-lifecycle
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set FOUNDRY_MODEL_NAME $modelDeploymentName
azd env set FOUNDRY_MODEL_CATALOG_NAME $modelName
azd env set FOUNDRY_MODEL_VERSION $modelVersion
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> Note: If provisioning fails, inspect the first Azure deployment error. Model or region availability, extension compatibility, quota, and role-assignment permissions are common causes. Correct the cause, then run `azd provision` again.

5. After provisioning succeeds, validate that `.env` includes the Foundry project endpoint and ID, `FOUNDRY_MODEL_NAME`, `FOUNDRY_MODEL_VERSION`, the Cosmos DB endpoint and container values, and `USAGE_IDENTITY_CLIENT_ID`. The file contains resource identifiers and parameterized settings, not keys or tokens.
6. Assign your development identity the minimum Foundry role required to manage prompt agents at project scope and the Cosmos DB Built-in Data Contributor role at the provisioned account scope.
7. Do not add keys, connection strings, or client secrets.

> **Network access for this lab:** The Bicep template enables native public network access for Foundry and Cosmos DB so the local application can reach both data-plane endpoints. Microsoft Entra authentication and Azure RBAC are still required. After deployment, confirm public access on both resources and confirm that the Foundry default network action is **Allow**. Production environments should use an approved selected-network or private-endpoint design.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

**Implement the promotion gate**

1. Open `src/lifecycle.py` and find **LAB PLACEHOLDER 1** in `validate_promotion`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete validate_promotion in Task 1")
```

2. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
failures: list[str] = []
evaluation = manifest.get("evaluation") or {}
approval = manifest.get("approval") or {}
compliance = manifest.get("compliance") or {}
topology = manifest.get("topology") or {}
agent_specs = {
  str(item.get("agent_id")): item
  for item in topology.get("agents") or []
}
compatibility = topology.get("compatibility") or {}

if manifest.get("status") != "approved":
  failures.append("manifest status is not approved")
if approval.get("status") != "approved":
  failures.append("approval status is not approved")
if set(agent_specs) != {"scanner", "reviewer", "orchestrator"}:
  failures.append("topology must contain scanner, reviewer, and orchestrator")

try:
  scanner_schema = Version(str(compatibility["scanner_output_schema"]))
  reviewer_requirement = SpecifierSet(
    str(compatibility["reviewer_requires_scanner_schema"])
  )
  if scanner_schema not in reviewer_requirement:
    failures.append("scanner output schema is incompatible with reviewer")
except (KeyError, TypeError, ValueError):
  failures.append("scanner-to-reviewer compatibility evidence is invalid")

try:
  reviewer_version = Version(str(agent_specs["reviewer"]["version"]))
  orchestrator_requirement = SpecifierSet(
    str(compatibility["orchestrator_requires_reviewer_version"])
  )
  if reviewer_version not in orchestrator_requirement:
    failures.append("reviewer version is incompatible with orchestrator")
except (KeyError, TypeError, ValueError):
  failures.append("reviewer-to-orchestrator compatibility evidence is invalid")

try:
  if float(evaluation["precision"]) < float(evaluation["minimum_precision"]):
    failures.append("precision is below its minimum")
except (KeyError, TypeError, ValueError):
  failures.append("precision evidence is missing or invalid")

try:
  if float(evaluation["recall"]) < float(evaluation["minimum_recall"]):
    failures.append("recall is below its minimum")
except (KeyError, TypeError, ValueError):
  failures.append("recall evidence is missing or invalid")

if compliance.get("material_change_assessment") is not True:
  failures.append("material change assessment is missing")
technical_file = str(compliance.get("technical_file_reference", "")).strip()
if not technical_file or not Path(technical_file).is_file():
  failures.append("technical file reference is missing or unavailable")

if failures:
  raise PermissionError("Promotion denied: " + "; ".join(failures))
```

The gate collects all failures: required roles, compatibility, evaluation thresholds, explicit material-change approval, and an existing technical file. Invalid or missing evidence denies promotion before version creation.

3. Leave `promote_topology` unchanged. It applies the gate once for all three agents and returns the logical-to-Foundry version map.

**Enforce and meter usage atomically**

4. Open `src/usage.py` and find **LAB PLACEHOLDER 2** in `enforce_and_meter_usage`:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete enforce_and_meter_usage in Task 2")
```

5. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
controls = policy["usage_governance"]
token_count = int(request["token_count"])
if token_count <= 0:
  raise ValueError("token_count must be positive")
tenant_id = str(request["tenant_id"])
cost_center = str(request["cost_center"])
if not tenant_id or not cost_center:
  raise ValueError("tenant_id and cost_center are required")

now = datetime.now(timezone.utc)
month = now.strftime("%Y-%m")
rate_window = now.strftime("%Y-%m-%dT%H:%M")
allocation_key = f"{tenant_id}:{cost_center}"
meter_id = f"{allocation_key}:{month}"

for _ in range(max_attempts):
  try:
    meter = container.read_item(item=meter_id, partition_key=allocation_key)
  except CosmosResourceNotFoundError:
    meter = {
      "id": meter_id,
      "allocation_key": allocation_key,
      "tenant_id": tenant_id,
      "cost_center": cost_center,
      "month": month,
      "monthly_tokens": 0,
      "request_count": 0,
      "estimated_charge": 0.0,
      "rate_window": rate_window,
      "rate_window_requests": 0,
    }
    try:
      container.create_item(meter)
    except CosmosResourceExistsError:
      continue
    meter = container.read_item(item=meter_id, partition_key=allocation_key)

  window_requests = (
    int(meter["rate_window_requests"])
    if meter["rate_window"] == rate_window
    else 0
  )
  if window_requests + 1 > int(controls["requests_per_minute"]):
    raise PermissionError("Per-minute request limit exceeded")
  new_monthly_tokens = int(meter["monthly_tokens"]) + token_count
  if new_monthly_tokens > int(controls["monthly_token_quota"]):
    raise PermissionError("Monthly token quota exceeded")

  charge = token_count / 1000 * float(controls["price_per_1000_tokens"])
  meter.update(
    {
      "monthly_tokens": new_monthly_tokens,
      "request_count": int(meter["request_count"]) + 1,
      "estimated_charge": round(
        float(meter["estimated_charge"]) + charge,
        6,
      ),
      "rate_window": rate_window,
      "rate_window_requests": window_requests + 1,
      "last_metered_at": now.isoformat(),
      "currency": str(controls["currency"]),
      "agent_id": str(request["agent_id"]),
      "agent_version": str(request["agent_version"]),
    }
  )
  try:
    saved = container.replace_item(
      item=meter_id,
      body=meter,
      etag=meter["_etag"],
      match_condition=MatchConditions.IfNotModified,
    )
    return {
      "decision": "allow",
      "meter_id": saved["id"],
      "allocation_key": allocation_key,
      "monthly_tokens": saved["monthly_tokens"],
      "monthly_token_quota": int(controls["monthly_token_quota"]),
      "rate_window_requests": saved["rate_window_requests"],
      "requests_per_minute": int(controls["requests_per_minute"]),
      "estimated_charge": saved["estimated_charge"],
      "currency": saved["currency"],
      "metered_at": saved["last_metered_at"],
    }
  except CosmosHttpResponseError as error:
    if error.status_code != 412:
      raise

raise RuntimeError("Usage meter update conflicted too many times")
```

The limit checks occur before the item mutation. `IfNotModified` binds the replacement to the `_etag` read by this attempt; a concurrent writer causes HTTP 412 and a retry instead of a lost increment. The 60 requests per UTC minute, 1,000,000 monthly tokens, and USD 0.005 per 1,000 tokens remain parameterized in `policy/promotion-policy.yaml`. They are application governance values, not Azure model prices.

**Check the completed code**

6. Run the following checks:

```powershell
python -m py_compile src/main.py src/lifecycle.py src/usage.py scripts/preflight.py
python scripts/preflight.py
Get-ChildItem src -Filter *.py | Select-String -Pattern 'NotImplementedError'
```

Preflight must end with `READY (local)`, and the final command must return no matches. Project and Cosmos configuration can remain `INFO` before provisioning.

## Task 5: Run the solution

1. Record the Foundry inventory before promotion:

```powershell
python -m src.main inventory
```

In a fresh project, expect an empty list. Retain the inventory as your baseline.

2. Promote the approved topology:

```powershell
$promotion = python -m src.main promote | ConvertFrom-Json
$promotion
$scannerVersion = $promotion.versions.scanner.foundry_version
$reviewerVersion = $promotion.versions.reviewer.foundry_version
$orchestratorVersion = $promotion.versions.orchestrator.foundry_version
```

3. Inspect release `2.4.0` and its `scanner`, `reviewer`, and `orchestrator` logical-to-Foundry version mappings:

```powershell
$promotion | ConvertTo-Json -Depth 10
$scannerVersion
$reviewerVersion
$orchestratorVersion
```

Expected logical versions are `scanner: 1.2.0`, `reviewer: 1.1.0`, and `orchestrator: 1.3.0`. Each Foundry version value must be present; do not assume it matches the logical semantic version.

4. Inventory the project again:

```powershell
python -m src.main inventory
```

5. Confirm all three captured versions appear in inventory. In the Foundry portal, select the project > **Agents** and match each version to its PowerShell variable.

If version creation fails, promotion attempts rollback in reverse creation order. When rollback succeeds, the original promotion exception and traceback are preserved. When any cleanup fails, the terminal error reports both the original promotion error and every exact `agent:version` cleanup failure; retain those targets for reconciliation.

**Test a denied promotion**

6. Snapshot inventory before testing denials:

```powershell
$inventoryBeforeDeniedPromotion = python -m src.main inventory | ConvertFrom-Json
$inventoryBeforeDeniedPromotion | ConvertTo-Json -Depth 10
```

7. In `registry/fabrikam-review-topology-v2.4.0.yaml`, change `evaluation.precision` from `0.96` to `0.94`, below `minimum_precision: 0.95`.

8. Attempt promotion without overwriting `$promotion`:

```powershell
python -m src.main promote
```

Expect `PermissionError: Promotion denied: precision is below its minimum`, before any version creation.

9. Capture inventory after the denial:

```powershell
$inventoryAfterDeniedPromotion = python -m src.main inventory | ConvertFrom-Json
$inventoryAfterDeniedPromotion | ConvertTo-Json -Depth 10
```

10. Compare the snapshots:

```powershell
Compare-Object ($inventoryBeforeDeniedPromotion | ConvertTo-Json -Depth 10) ($inventoryAfterDeniedPromotion | ConvertTo-Json -Depth 10)
```

11. Expect no differences. Refresh all three portal version lists to confirm no new versions, then restore `precision: 0.96`.
12. Under `topology.compatibility`, change `reviewer_requires_scanner_schema` from `'>=2.0,<3.0'` to `'>=3.0,<4.0'`.
13. Attempt promotion:

```powershell
python -m src.main promote
```

14. Expect `PermissionError: Promotion denied: scanner output schema is incompatible with reviewer`.
15. Capture inventory again:

```powershell
$inventoryAfterCompatibilityDenial = python -m src.main inventory | ConvertFrom-Json
```

16. Compare with the pre-denial snapshot:

```powershell
Compare-Object ($inventoryBeforeDeniedPromotion | ConvertTo-Json -Depth 10) ($inventoryAfterCompatibilityDenial | ConvertTo-Json -Depth 10)
```

17. Expect no differences, then restore `reviewer_requires_scanner_schema` to `'>=2.0,<3.0'`.

**Reconcile versions left by a failed rollback**

Use this administrative operation only for exact `agent:version` targets reported in a promotion cleanup failure. Never pass a version from the successful `$promotion` mapping.

```powershell
python -m src.main reconcile --orphan-version scanner:<foundry-version> --orphan-version reviewer:<foundry-version> --confirm-delete-orphans
```

The result separates `deleted` from `already_absent`. Run the same command again and confirm that every target moves to `already_absent`, demonstrating idempotent reconciliation. If any delete fails, the error reports versions already deleted, versions already absent, and every remaining cleanup failure so the command can be safely retried.

**Verify metering and usage controls**

18. Run the metering command once:

```powershell
python -m src.main meter
```

In the terminal output, confirm:

- `decision` is `allow`.
- `allocation_key` is `synthetic-tenant-a:FAB-SEC-042`.
- `monthly_tokens` increased by `1250` and `monthly_token_quota` is `1000000`.
- `rate_window_requests` increased by `1` and `requests_per_minute` is `60`.
- `estimated_charge` increased by `0.00625`, `currency` is `USD`, and `metered_at` contains a UTC timestamp.

19. Run it a second time:

```powershell
python -m src.main meter
```

For the first two requests in one UTC minute, expect `monthly_tokens: 2500`, `rate_window_requests: 2`, and `estimated_charge: 0.0125`. Otherwise, compare increments of 1250 tokens and USD 0.00625 in the same monthly meter; the rate count resets when the UTC minute changes.

20. In the Azure portal, open Cosmos DB > **Data Explorer** > **lifecycle** > **usage-meters** > **Items**. Open the item beginning `synthetic-tenant-a:FAB-SEC-042` and confirm that partition key. Record `monthly_tokens`, `request_count`, `rate_window_requests`, `estimated_charge`, and `_ts`; keep the item open for denial tests.

**Test the per-minute request limit**

21. In `policy/promotion-policy.yaml`, change `requests_per_minute` from `60` to `1`. Wait for a new UTC minute if you have already metered a request in the current one.
22. Run the first request:

```powershell
python -m src.main meter
```

23. Expect `decision: allow` and `rate_window_requests: 1`. Refresh and reopen the Data Explorer item; record its counters, charge, and `_ts`.
24. Run a second request before the UTC minute changes:

```powershell
python -m src.main meter
```

25. Expect `PermissionError: Per-minute request limit exceeded`. Refresh the item and confirm all five recorded values are unchanged. Restore `requests_per_minute: 60`.

**Test the monthly token quota**

26. In `assets/usage-request.json`, change `token_count` from `1250` to `1000001`.
27. Run:

```powershell
python -m src.main meter
```

28. Expect `PermissionError: Monthly token quota exceeded`. Refresh the item and confirm the five recorded values remain unchanged. Verify `scanner`, logical version `1.2.0`, tenant `synthetic-tenant-a`, and cost center `FAB-SEC-042`, with no credentials or request content. Restore `token_count: 1250`.

Meter counters are post-update values. Estimated charges are application allocations, not Azure invoices; denied requests must leave counters and charge unchanged.

## Task 6: Validate the implementation

1. Use the Foundry portal and SDK output to verify that all three prompt-agent versions in the promoted release exist and match `$scannerVersion`, `$reviewerVersion`, and `$orchestratorVersion`.
2. Run inventory again and compare it with the original evidence.
3. Review the technical file, topology compatibility declarations, and manifest diff as the approval record.

4. For retirement practice, use the disposable `scanner` version created by this lab.
5. Open `assets/retirement-request.json` and replace its `version` value with the value shown in `$scannerVersion`.
6. Review the request and confirm that it records at least 90 days between deprecation and deletion, zero consumers, zero pins, archive completion, deprecation registration, and governance approval.
7. Immediately before running a retirement command, confirm that the command targets agent `scanner` and the exact disposable version stored in `$scannerVersion`. Stop if either value differs.

8. Test each gate separately: consumers or pins set to `1`, archive or deprecation registration set to `false`, approval set to `pending`, a mismatched request version, a shorter notice interval, and a future deletion date. Keep the CLI target fixed to this lab's `$scannerVersion`. After each denial and inventory check below, restore the changed field before testing the next gate.
9. For each change, run:

```powershell
python -m src.main retire --agent-name scanner --agent-version $scannerVersion --confirm-delete-version
```

10. Confirm that the terminal shows `Retirement denied` and names the failed gate.
11. Run inventory after each denial and confirm that the `scanner` version in `$scannerVersion` still exists.
12. Restore the approved synthetic request.
13. Run:

```powershell
python -m src.main retire --agent-name scanner --agent-version $scannerVersion --confirm-delete-version
```

14. Confirm that the success output shows `retired: true` and repeats the enforced gate evidence.
15. Run inventory again and confirm that `$scannerVersion` is absent while the `reviewer` and `orchestrator` versions remain. This demonstrates component retirement within a topology.

16. Retain the Cosmos DB snapshots and both usage-denial messages alongside the release mapping, approval record, and retirement evidence.

## Optional challenge: Block an incompatible promotion

Create a synthetic reviewer version whose output contract is incompatible with an active orchestrator consumer.

**Expected output:** Promotion is blocked and the evidence names the failed compatibility rule and affected consumer.

**Failure investigation:** Attempt to retire a version still referenced by the topology and explain the lifecycle-policy rejection.

## Task 7: Review the design

1. Answer these questions:

- Why is a prompt hash part of an agent version?
- Which changes require manual or customer approval?
- Why should deprecation and consumer migration precede deletion of one topology component?
- What proves a retired version has no remaining consumers?
- Why must quota enforcement and meter increments use one conditional update?
- How does chargeback evidence differ from an Azure invoice?

## Task 8: Clean up

**Remove Azure resources**

1. Reconcile any exact orphan targets reported by failed promotion rollback, then delete any remaining `scanner`, `reviewer`, and `orchestrator` versions created by this lab.
2. Run `azd down --purge`.
3. Confirm that the Foundry project, model deployment, and Cosmos DB account are removed.
4. Keep only synthetic manifests and evidence; remove `.env` and local caches.

**Deactivate the virtual environment**

5. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

6. Confirm that `(.venv)` no longer appears before leaving the working directory.

## Summary

You used real Foundry and Cosmos DB interfaces to govern a three-agent topology release, immutable prompt-agent versions, quotas, rate limits, usage allocation, estimated chargeback, and fail-closed retirement.
