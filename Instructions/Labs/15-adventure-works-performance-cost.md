---
lab:
  title: 'Optimize multi-agent performance and cost with measured evidence'
  description: 'Measure live model usage, then implement model routing, caching, token budgets, and quality-floor escalation for Adventure Works.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Optimize multi-agent performance and cost with measured evidence

## Customer scenario

Adventure Works routes every Customer Intelligence Platform request to its premium model and repeatedly sends oversized context. The platform team needs evidence that a cheaper design meets each customer segment's quality, latency, and budget envelope.

## Lab scenario

You will run synthetic requests against live Microsoft Foundry deployments, capture actual latency and token usage, and implement routing, result caching, context budgets, and quality-floor escalation. You will compare a premium control run with the optimized policy and recommend a configuration from evidence.

By the end of this exercise, you will be able to:

- Route simple, moderate, and high-risk requests to appropriate model tiers.
- Apply stable prompt prefixes, distributed result caching, and explicit invalidation metadata.
- Enforce token budgets before model invocation.
- Compare quality, cost, latency, retries, and cache behavior with measured evidence.

> **Important**: Live model calls and Azure Managed Redis are billable. Confirm model pricing for your region, cap the supplied synthetic workload, and clean up immediately.

## Task 1: Prepare the lab

1. Install [Python 3.10 or later](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), and [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).

You need an Azure subscription, permission to create Foundry and Redis resources, two or three instructor-approved chat deployments, and current input/output token prices. Use your signed-in identity and never store access keys.

**Clone and open the repository**

2. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

3. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

4. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\15-adventure-works-performance-cost
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `assets/requests.jsonl`, `assets/optimization-config.json`, `src/main.py`, `src/cache.py`, `.env.example`, and `infra/main.bicep`. Before continuing, confirm that one request passes through deterministic tier selection, context budgeting, cache lookup, model invocation or cache return, quality-floor evaluation, and evidence recording.

## Task 2: Build the virtual environment

1. On Windows, create and activate the virtual environment and initialize `.env`:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
Copy-Item .env.example .env
```

> On macOS/Linux, run `bash scripts/setup.sh`, `source .venv/bin/activate`, and `cp .env.example .env` instead.

## Task 3: Deploy Azure resources

1. Review Foundry model usage and Azure Managed Redis costs, model quota, and role access before provisioning.
2. Cap the supplied synthetic workload and use a unique environment.

`azd` provisions infrastructure; the benchmark runs separately and incurs model charges.

**Set the deployment values**

3. Set `$azureRegion` to an approved region that supports the required models and services.
4. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

> **Note:** `AZURE_DEV_USER_AGENT` tags provisioning for attribution and is not exported to `.env`. Remove it afterward to avoid tagging unrelated commands.

**Validate and provision the infrastructure**

5. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab15-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-optimize-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
$principalId = az ad signed-in-user show --query id --output tsv
azd env set AZURE_PRINCIPAL_ID $principalId
azd env set FOUNDRY_MODEL_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_CATALOG_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_VERSION 2026-03-17
az bicep build --file infra/main.bicep
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> **Note:** If provisioning fails, inspect the first deployment error. Check model and region availability, quota, Redis availability, principal ID, and role-assignment permissions. Correct the cause and rerun `azd provision`.

**Verify the generated environment**

6. After provisioning succeeds, validate that `.env` includes the Foundry project endpoint, all three model deployment names, the Redis host, and the principal ID required by the application.
7. Do not add keys, tokens, or connection strings; Redis authentication uses an Entra token obtained at runtime.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, remove the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

The supplied Global Standard `gpt-5.4-mini` prices are versioned evidence for this lab run. Verify and update them if the model, deployment type, currency, or pricing date changes.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Classify request complexity**

1. In `src/main.py`, find `# LAB PLACEHOLDER 1`.
2. Replace only the incomplete `classify_tier()` function associated with it with:

```python
def classify_tier(request: dict[str, Any]) -> int:
  """Classify request complexity without spending model tokens."""
  message = request["message"].lower()
  if (
    request.get("policy_exception")
    or float(request.get("transaction_amount", 0)) > 200
    or any(term in message for term in ("legal", "regulatory", "chargeback"))
  ):
    return 3
  if "compare" in message or len(request.get("dependencies", [])) > 1:
    return 2
  return 1
```

The router spends no model tokens and sends exception, high-value, and legal work directly to the highest tier.

**Build priority-based context**

3. Find `# LAB PLACEHOLDER 2`.
4. Replace only the incomplete `apply_context_budget()` function associated with it with:

```python
def apply_context_budget(request: dict[str, Any], budget: int) -> str:
  """Build context that preserves required facts within a character proxy budget."""
  context = request["context"]
  required = set(request.get("required_context_fields", context.keys())) - {"unused_fields"}
  selected = {key: context[key] for key in context if key in required}
  rendered = json.dumps(selected, sort_keys=True, separators=(",", ":"))
  character_limit = budget * 4
  if len(rendered) > character_limit:
    raise ValueError(
      f"Required context needs {len(rendered)} characters; tier budget allows {character_limit}."
    )
  return rendered
```

Required facts are preserved or the request fails before invocation; silent truncation cannot remove an authorization or order detail.

**Version exact-result cache keys**

5. In `src/cache.py`, find `# LAB PLACEHOLDER 3`.
6. Replace only the incomplete `result_key()` method associated with it with:

```python
  def result_key(cls, request: dict[str, Any], agent_version: str, policy_version: str) -> str:
    signature = {
      "request": request["message"].strip().lower(),
      "segment": request["segment"],
      "context": request["context"],
      "dependencies": sorted(request["dependencies"]),
      "agent_version": agent_version,
      "policy_version": policy_version,
    }
    return f"aw:result:{cls._digest(signature)}"
```

Context, version, and dependency inputs prevent reuse after facts, behavior, or sources change, while the `aw:result` namespace keeps exact responses distinct.

**Version prompt-context cache keys**

7. Find `# LAB PLACEHOLDER 4`.
8. Replace only the incomplete `prompt_key()` method associated with it with:

```python
  def prompt_key(
    cls,
    request: dict[str, Any],
    tier: int,
    input_budget: int,
    agent_version: str,
    policy_version: str,
  ) -> str:
    signature = {
      "context": request["context"],
      "dependencies": sorted(request["dependencies"]),
      "tier": tier,
      "input_budget": input_budget,
      "agent_version": agent_version,
      "policy_version": policy_version,
    }
    return f"aw:prompt:{cls._digest(signature)}"
```

Tier and budget affect prompt construction, so they must participate in the prompt-cache identity.

**Check the completed code**

9. Check the completed code locally:

```console
python -m py_compile src/main.py src/cache.py scripts/compare_runs.py
python scripts/preflight.py --require-complete
```

10. Confirm that compilation returns no output.
11. Confirm that preflight reports the local files and implementation checks as `ready`; it must remain nonzero until current prices, three deployment names, the project endpoint, Redis host, and principal ID are configured.

## Task 5: Run the solution

1. Run the benchmark commands in order.

The control establishes the premium baseline. The first optimized run uses a cold cache, the second demonstrates exact-result hits, invalidation removes only `SYN-LOOKUP-001`'s exact result, and the final run demonstrates prompt-context reuse for that request.

```console
python -m src.main --policy control --output reports/control-summary.json
python -m src.main --policy optimized --output reports/optimized-summary.json
python -m src.main --policy optimized --output reports/optimized-cached-summary.json
python -m src.main --invalidate-exact SYN-LOOKUP-001
python -m src.main --policy optimized --output reports/optimized-prompt-cached-summary.json
python scripts/compare_runs.py reports/control-summary.json reports/optimized-summary.json reports/optimized-cached-summary.json
```

**Understand the output**

Each evidence row records `initial_tier`, `final_tier`, deployment, measured tokens, latency, versioned price, quality, retries, and `cache_level`. `miss` means a model call built fresh context, `prompt` means cached context was reused but the model was called, and `exact_result` means no model call occurred. Summary cost includes every retry attempt. `needs_human_review` is set only when tier 3 remains below its quality floor.

## Task 6: Validate the implementation

**Inspect the measured evidence**

1. Confirm that every evidence row, including an exact-result cache hit, contains deployment, price version, initial and final tiers, `cache_level`, prompt-cache status, retry count, cost, and quality score.
2. Confirm that noncached rows also contain measured elapsed milliseconds and actual input and output tokens from the service response.
3. Inspect the second optimized run for `cache_level: exact_result`.
4. Run `python -m src.main --invalidate-exact SYN-LOOKUP-001` and record the reported `exact_result_key` and `deleted` count.
5. Rerun the optimized policy and confirm request `SYN-LOOKUP-001` reports `cache_level: prompt`.
6. Confirm that the summary `cache_hit_rate` counts both exact-result and prompt hits; use `exact_result_cache_hit_rate` and `prompt_cache_hit_rate` for the per-level breakdown.
7. Verify Redis contains only the supplied synthetic context and responses, and contains no credentials or real customer data.

Base the recommendation on measured evidence, excluding savings from failed requests or unobserved cache hits.

**Validate the Azure resources**

8. In the Microsoft Foundry portal, validate the provisioned account, project, and deployment named by `TIER1_DEPLOYMENT`, `TIER2_DEPLOYMENT`, and `TIER3_DEPLOYMENT`.
9. In Azure Managed Redis, validate the provisioned `default` database and Entra `default` access policy assignment.

The standalone lab maps all three routing tiers to one current deployment so that measured differences come from budgets, retries, and caching. In a production experiment, use separately priced and benchmarked deployments when the routing comparison requires model-quality tradeoffs.

**Review objective coverage**

| Objective | Required evidence | Passing outcome |
|---|---|---|
| Route requests by complexity | Evidence tier fields | Exception/high-risk cases start at tier 3; simpler cases use lower tiers. |
| Apply cache separation and invalidation | Cache levels and invalidation output | Exact and prompt keys differ; invalidation removes only the selected exact result. |
| Enforce context budgets | Completed function and successful runs | Required fields fit the tier budget or fail before a model call. |
| Compare measured performance and cost | Three summaries and comparison report | Recommendation uses actual tokens, latency, retries, quality, and cache hits. |

## Optional challenge: Isolate cache entries by tenant

Add a synthetic tenant identifier to the request and both cache signatures.

**Expected output:** Identical requests from two tenants create distinct cache entries, and targeted invalidation removes only the selected tenant''s result.

**Failure investigation:** Use stale invalidation metadata and determine whether the defect is key construction or invalidation scope.
## Task 7: Review the design

1. Answer these questions:

- When did a cheaper initial route cost more because it retried?
- Which context fields consumed tokens without changing quality?
- What evidence would justify adding semantic caching rather than exact result caching?

## Task 8: Clean up

**Remove Azure resources**

1. Run `azd down --purge` with `AZURE_DEV_USER_AGENT=microsoft_foundry_skill`.
2. Remove the local `.env`.
3. Confirm the resource group and Redis instance are deleted.

**Deactivate the virtual environment**

4. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

5. Confirm that `(.venv)` no longer appears before changing to another lab directory.

## Summary

You optimized a live multi-agent workload with routing, caching, token budgets, and quality floors, then selected a policy from actual token, latency, quality, and cost evidence.
