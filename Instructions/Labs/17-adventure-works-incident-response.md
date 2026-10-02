---
lab:
  title: 'Debug a multi-agent production incident with trace evidence'
  description: 'Use Application Insights, KQL, trace snapshots, safe replay, structured hypotheses, and evidence-linked postmortems to diagnose an Adventure Works incident.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Debug a multi-agent production incident with trace evidence

## Customer scenario

Adventure Works observes a drop in checkout completion, but the failing payment span may be only a symptom. The on-call team needs a repeatable way to reconstruct distributed traces, preserve replay inputs, compare failed and successful paths, test competing hypotheses, and document a root cause supported by evidence.

## Lab scenario

You will emit a synthetic multi-agent incident through OpenTelemetry, retrieve it from Application Insights with KQL, save a sanitized snapshot to Blob Storage, run side-effect-free replay, and evaluate structured hypotheses. You will produce a blameless postmortem only after the evidence supports or rejects each hypothesis.

<!-- LAB DIAGRAM PLACEHOLDER: Show telemetry emission, KQL investigation, sanitized snapshot capture, safe replay, hypothesis evaluation, remediation, and postmortem evidence. -->

By the end of this exercise, you will be able to:

- Query multi-agent traces and latency with Application Insights KQL.
- Capture model, prompt-hash, tool-response, and span-timeline replay artifacts.
- Test model, prompt, tool, orchestration, and configuration hypotheses systematically.
- Connect detection, remediation, escalation, and postmortem actions to evidence.

> **Important**: Application Insights and Log Analytics ingestion are billable. Emit only the bounded synthetic trace. Snapshots must contain mocked tool results and no customer PII or hidden model reasoning.

## Task 1: Prepare the lab

1. Install [Python 3.10 or later](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), and [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).

You need permission to create Log Analytics, Application Insights, Storage, and role assignments. Authenticate with your signed-in identity.

**Clone and open the repository**

2. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

3. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

4. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\17-adventure-works-incident-response
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `scripts/emit_synthetic_trace.py`, the snapshot and hypothesis schemas, the KQL queries, `src/main.py`, `src/replay.py`, `src/remediation.py`, `.env.example`, and `infra/main.bicep`. Before continuing, confirm that the incident path is `synthetic trace -> KQL investigation -> sanitized snapshot -> safe replay -> hypothesis decision -> bounded remediation -> evidence-linked postmortem`.

## Task 2: Build the virtual environment

1. On Windows, create and activate the virtual environment and initialize `.env`:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
Copy-Item .env.example .env
```

> On macOS/Linux, run `bash scripts/setup.sh`, `source .venv/bin/activate`, and `cp .env.example .env` instead.

## Task 3: Deploy Azure resources

1. Review Log Analytics ingestion and retention, Application Insights, Storage, Event Hubs, alerting costs, and required role access before provisioning.
2. Use a unique environment and bounded synthetic traces.

`azd` provisions infrastructure; trace emission and remediation run separately.

**Set the deployment values**

3. Set `$azureRegion` to an approved region that supports the required services.
4. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

> **Note:** `AZURE_DEV_USER_AGENT` tags provisioning for attribution and is not exported to `.env`. Remove it afterward to avoid tagging unrelated commands.

**Validate and provision the infrastructure**

5. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab17-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-incident-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
$principalId = az ad signed-in-user show --query id --output tsv
azd env set AZURE_PRINCIPAL_ID $principalId
az bicep build --file infra/main.bicep
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> **Note:** If provisioning fails, inspect the first deployment error. Check monitoring and messaging availability, resource naming, principal ID, policy restrictions, and role-assignment permissions. Correct the cause and rerun `azd provision`.

**Verify the generated environment**

6. After provisioning succeeds, validate that `.env` includes the Application Insights and Log Analytics identifiers, Storage endpoint and container names, Event Hubs namespace and hub names, and principal values required by the application.
7. Do not add storage keys, connection strings, shared-access keys, or tokens.
8. Verify the effective Event Hubs network boundary and receiver authorization:

```powershell
$values = azd env get-values --output json | ConvertFrom-Json
$namespaceName = $values.ALERT_EVENTHUB_NAMESPACE -replace '\.servicebus\.windows\.net$', ''
$networkBoundary = az eventhubs namespace network-rule-set show --namespace-name $namespaceName --resource-group $resourceGroupName --query "{publicNetworkAccess:publicNetworkAccess,defaultAction:defaultAction}" | ConvertFrom-Json
if ($networkBoundary.publicNetworkAccess -ne 'Enabled' -or $networkBoundary.defaultAction -ne 'Allow') { throw 'Unexpected Event Hubs network configuration' }
$eventHubId = az eventhubs eventhub show --name $values.ALERT_EVENTHUB_NAME --namespace-name $namespaceName --resource-group $resourceGroupName --query id -o tsv
$receiverRoles = @(az role assignment list --assignee $principalId --scope $eventHubId --query "[?roleDefinitionName=='Azure Event Hubs Data Receiver'].{role:roleDefinitionName,scope:scope}" | ConvertFrom-Json)
if ($receiverRoles.Count -ne 1 -or $receiverRoles[0].scope -ne $eventHubId) { throw 'Expected one Event Hubs Data Receiver assignment at the exact hub scope' }
$dataPlaneRoles = @(az role assignment list --assignee $principalId --all --query "[?starts_with(scope, '$eventHubId') && (roleDefinitionName=='Azure Event Hubs Data Sender' || roleDefinitionName=='Azure Event Hubs Data Owner')].{role:roleDefinitionName,scope:scope}" | ConvertFrom-Json)
if ($dataPlaneRoles.Count -ne 0) { throw 'The remediation receiver must not inherit Event Hubs Data Sender or Data Owner on this hub' }
[pscustomobject]@{
  publicNetworkAccess = $networkBoundary.publicNetworkAccess
  defaultAction = $networkBoundary.defaultAction
  receiverRole = $receiverRoles[0].role
  receiverScope = $receiverRoles[0].scope
  broaderDataPlaneRoles = $dataPlaneRoles.Count
} | Format-List
'EVENT_HUB_BOUNDARIES_VALIDATED'
```

Expect `EVENT_HUB_BOUNDARIES_VALIDATED`, `Enabled`/`Allow`, one exact-hub **Azure Event Hubs Data Receiver** role, and zero broader sender/owner data-plane roles. The Bicep template enables the Event Hubs namespace's native public network access and default **Allow** action so the local consumer can receive alert events. Microsoft Entra authentication and the exact-hub receiver role are still required. Production environments should provide and validate an approved private access path.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, remove the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Build a sanitized replay snapshot**

1. In `src/main.py`, find `# LAB PLACEHOLDER 1`.
2. Replace only the six empty collection declarations beneath it with:

```python
  spans = []
  deployments = {}
  configurations = {}
  prompts = {}
  prompt_hashes = {}
  tool_mocks = {}
  for row in rows:
    properties = row.get("Properties") or {}
    if isinstance(properties, str):
      properties = json.loads(properties)
    span = {
      "time_generated": row.get("TimeGenerated"),
      "span_id": row.get("Id"),
      "parent_id": row.get("ParentId"),
      "span_name": row.get("SpanName"),
      "duration_ms": row.get("DurationMs"),
      "success": row.get("Success"),
      "result_code": row.get("ResultCode"),
      "model_version": properties.get("gen_ai.request.model"),
      "configuration_version": properties.get("agent.configuration.version"),
      "prompt_hash": properties.get("gen_ai.prompt.hash"),
      "error_type": properties.get("incident.error.type"),
      "tool_name": properties.get("tool.name"),
      "tool_mock_id": properties.get("tool.mock_id"),
      "tool_mock_response_available": properties.get("tool.mock_response") is not None,
    }
    spans.append(span)
    if span["model_version"]:
      deployments[span["span_name"]] = {
        "agent": span["span_name"], "version": span["model_version"]
      }
    if span["configuration_version"]:
      configurations[span["span_name"]] = {
        "component": span["span_name"], "version": span["configuration_version"]
      }
    if properties.get("gen_ai.prompt.hash"):
      prompt_hashes[span["span_name"]] = properties["gen_ai.prompt.hash"]
    if properties.get("gen_ai.prompt.template"):
      prompts[span["span_name"]] = properties["gen_ai.prompt.template"]
    if span["tool_name"]:
      mock_response = properties.get("tool.mock_response")
      tool_success = properties.get("tool.response.success")
      if isinstance(tool_success, str) and tool_success.lower() in {"true", "false"}:
        tool_success = tool_success.lower() == "true"
      tool_mocks[span["tool_name"]] = {
        "mock_id": span["tool_mock_id"],
        "response": json.loads(mock_response) if isinstance(mock_response, str) else mock_response,
        "success": tool_success,
        "synthetic": True,
      }
```

Only the named fields cross the telemetry boundary. Message bodies, credentials, and hidden reasoning are never copied.

**Resolve generic evidence paths**

3. In `src/analysis.py`, find `# LAB PLACEHOLDER 2`.
4. Replace only the incomplete `values_at_path()` function associated with it with:

```python
def values_at_path(document: Any, path: str) -> list[Any]:
  values = [document]
  for segment in path.split("."):
    expanded = []
    for value in values:
      if segment == "*" and isinstance(value, list):
        expanded.extend(value)
      elif segment == "*" and isinstance(value, dict):
        expanded.extend(value.values())
      elif isinstance(value, dict) and segment in value:
        expanded.append(value[segment])
    values = expanded
  return values
```

Wildcard traversal lets hypotheses address observed collections without embedding incident-specific IDs.

**Add the less-than predicate**

5. Find `# LAB PLACEHOLDER 3`.
6. Add this branch directly beneath it:

```python
    elif operator == "less_than":
      passed = any(float(value) < float(expected) for value in values)
```

The existing function still records failed predicates as contradictory evidence and absent paths as missing evidence.

**Reconstruct the trace with captured mocks**

7. In `src/replay.py`, find `# LAB PLACEHOLDER 4`.
8. Replace only the incomplete `reconstruct_trace()` function associated with it with:

```python
def reconstruct_trace(snapshot: dict[str, Any]) -> dict[str, Any]:
  if snapshot.get("replay_mode") is not True:
    raise ValueError("Snapshot must explicitly enable replay mode")
  prompt_checks = []
  for agent, prompt in snapshot.get("prompts", {}).items():
    actual = hashlib.sha256(prompt.encode()).hexdigest()
    expected = snapshot.get("prompt_hashes", {}).get(agent)
    prompt_checks.append({
      "agent": agent, "expected_hash": expected,
      "actual_hash": actual, "matches": actual == expected,
    })
  steps = []
  for index, span in enumerate(snapshot.get("spans", []), start=1):
    tool_name = span.get("tool_name")
    mock = snapshot.get("tool_mocks", {}).get(tool_name) if tool_name else None
    status = span.get("success", span.get("status", span.get("Success")))
    duration_ms = span.get("duration_ms", span.get("DurationMs"))
    steps.append({
      "sequence": index,
      "span_name": span.get("span_name") or span.get("Name"),
      "status": status,
      "mock_used": mock is not None,
      "mock_response": mock.get("response") if mock else None,
      "duration_ms": duration_ms,
    })
  divergences = [check for check in prompt_checks if not check["matches"]]
  tool_steps = [step for step in steps if step["mock_used"]]
  metrics = {
    "prompt_count": len(prompt_checks),
    "prompt_match_rate": round(
      sum(check["matches"] for check in prompt_checks) / len(prompt_checks), 4
    ) if prompt_checks else 0.0,
    "tool_step_count": len(tool_steps),
    "tool_mock_response_count": sum(step["mock_response"] is not None for step in tool_steps),
    "failed_step_count": sum(step["status"] is False for step in steps),
    "divergence_count": len(divergences),
  }
  return {
    "operation_id": snapshot["operation_id"],
    "side_effects_enabled": False,
    "prompt_checks": prompt_checks,
    "steps": steps,
    "divergences": divergences,
    "comparison_metrics": metrics,
  }
```

This controlled reconstruction verifies prompt hashes and substitutes captured synthetic tool responses. It does not re-execute model or application behavior and cannot call a production tool.

**Synthesize only supported evidence**

9. In `src/postmortem.py`, find `# LAB PLACEHOLDER 5`.
10. Replace only the incomplete `summarize_evidence()` function associated with it with:

```python
def summarize_evidence(analysis: list[dict[str, Any]], replay: dict[str, Any]) -> tuple[str, str]:
  metrics = replay["comparison_metrics"]
  supported = sorted(
    (item for item in analysis if item["status"] == "supported"),
    key=lambda item: item["priority"],
  )
  leading = supported[0] if supported else None
  observed = leading["supporting"] if leading else []
  evidence_summary = "; ".join(
    f"{item['path']} observed {json.dumps(item['observed'], sort_keys=True)}"
    for item in observed[:3]
  ) or "No causal observation has enough supporting evidence."
  if metrics["divergence_count"]:
    agents = ", ".join(item["agent"] for item in replay["divergences"])
    root_cause = (
      f"Replay detected {metrics['divergence_count']} prompt divergence(s) for {agents}; "
      "the causal statement remains bounded to the observed comparison evidence."
    )
  elif (
    leading and metrics["prompt_match_rate"] == 1.0
    and metrics["tool_step_count"] > 0
    and metrics["tool_mock_response_count"] == metrics["tool_step_count"]
  ):
    root_cause = (
      f"{leading['statement']} Evidence: {evidence_summary}. Replay matched "
      f"{metrics['prompt_count']} prompt(s), used {metrics['tool_mock_response_count']}/"
      f"{metrics['tool_step_count']} captured tool response(s), and preserved "
      f"{metrics['failed_step_count']} failed step(s)."
    )
  else:
    root_cause = "Root cause is not yet established because replay or comparison evidence is incomplete."
  return root_cause, evidence_summary
```

The report selects only the highest-priority supported hypothesis and refuses to overstate incomplete replay evidence.

**Check the completed code**

11. Check the completed code locally:

```console
python -m py_compile src/main.py src/analysis.py src/replay.py src/postmortem.py src/remediation.py
python scripts/preflight.py --require-complete
```

12. Confirm that compilation returns no output.
13. Before provisioning, confirm that preflight validates the schema, hypotheses, and three KQL files; Azure configuration checks can remain `not ready`.

No preflight check sends telemetry or reads Azure data.

## Task 5: Run the solution

1. Run the incident investigation commands:

```console
python scripts/emit_synthetic_trace.py
python -m src.main candidates --query kql/01-find-candidates.kql
python -m src.main capture --operation-id <operation-id> --query kql/02-trace-detail.kql
python -m src.analysis --snapshot reports/<operation-id>.snapshot.json --hypotheses assets/hypotheses.json
python -m src.replay --snapshot reports/<operation-id>.snapshot.json --output reports/replay-comparison.json
python -m src.remediation --max-wait-seconds 30 --max-events 10
python -m src.postmortem --snapshot reports/<operation-id>.snapshot.json --analysis reports/hypothesis-results.json --replay reports/replay-comparison.json
```

The synthetic emitter exports the root checkout as a server request, uses a deterministic `1.0` lab sampling ratio, and performs a bounded telemetry flush before it exits. These settings keep the one-shot lab run aligned with the `AppRequests`/`AppDependencies` KQL contract rather than process-shutdown timing or production sampling.

**Understand the output**

A snapshot contains lowercase span fields, deployment and configuration versions, prompt hashes, synthetic prompt templates, and mock tool responses. Hypothesis results separate `supporting`, `contradicting`, and `missing` evidence. Trace reconstruction reports prompt fidelity, failed steps, mock coverage, and divergences with `side_effects_enabled: false`; it is not behavioral re-execution. The postmortem cites those measurements; remediation records a proposed action without production writes.

`kql/01-find-candidates.kql` is the broad discovery query; use its operation ID and failure columns to choose one bounded trace. `kql/02-trace-detail.kql` filters that ID and projects the fields consumed by `sanitize_rows()`. `kql/03-hypothesis-comparison.kql` compares successful and failed cohorts so a version or error-type difference is not inferred from a single trace.

## Task 6: Validate the implementation

**Validate trace capture**

1. Confirm the candidate query returns both successful and failed synthetic operations.
2. Confirm that the trace detail preserves parent-child order and durations.
3. Confirm that the snapshot is uploaded to the configured Blob container.
4. Delete the local snapshot file.
5. Download the snapshot again.
6. Confirm that the downloaded snapshot remains usable.

**Validate hypotheses and replay**

7. For each hypothesis, record supporting, contradicting, and missing evidence.
8. Confirm the snapshot contains `configuration_versions`, `model_deployments`, lowercase span `success`, `prompts`, prompt hashes, and actual synthetic response objects with success flags under `tool_mocks`.
9. Confirm that the failed shipped scenario supports the pricing model-version statement from observed `synthetic-pricing-v2`, `SyntheticPriceFormatError`, and `success: false` values.
10. Confirm that the other shipped hypotheses evaluate without missing paths.
11. Confirm replay preserves `status: false` and reports failed-step and tool mock response coverage.
12. Change the prompt text.
13. Confirm that the changed prompt text causes a hash divergence.

**Compare trace cohorts**

14. Run `kql/03-hypothesis-comparison.kql`.
15. Confirm the failed cohort reports `synthetic-pricing-v2` plus `SyntheticPriceFormatError`, while the successful cohort reports `synthetic-pricing-v1` without that error type.

**Validate alert remediation**

16. In Azure Monitor, confirm `aw-synthetic-pricing-failure` is enabled, evaluates every minute over a 15-minute window, and its Action Group targets `incident-alerts`.
17. After alert activation, inspect Event Hubs incoming messages.
18. Run the bounded remediation consumer.
19. Verify it returns after the configured wait.
20. Confirm it prints a processed count no greater than `--max-events`.
21. Confirm it persists one remediation evidence Blob per processed event.

The bounded lab receiver starts explicitly from the retained beginning of every partition and records a proposed containment action, but it cannot perform a production write.

**Reason about durable checkpoints**

22. The bounded lab receiver demonstrates safe event handling, but a production event processor should use Blob Storage checkpointing.
23. Use one dedicated Blob checkpoint container for each Event Hubs consumer group, and place the storage account in the same Azure region as the Event Hubs namespace to reduce checkpoint latency and cross-region dependencies.
24. Confirm that checkpoints are maintained independently per Event Hubs partition. A restart can therefore resume each partition at a different event position; if trace fragments span partitions, a partially advanced checkpoint set can produce an incomplete reconstruction until the remaining partitions catch up.
25. Design reconstruction to tolerate duplicates, late fragments, and partition-local progress. Persist idempotent evidence before advancing the corresponding partition checkpoint.
26. The lab uses `$Default` and writes remediation evidence rather than reconstructing traces from the alert stream. If you add a checkpoint store, provision a dedicated container for `$Default`; if you add another consumer group, give it a different checkpoint container. See [Troubleshoot Blob Storage checkpoint store issues](https://learn.microsoft.com/azure/event-hubs/troubleshoot-checkpoint-store-issues) and [Partition load balancing for event processing](https://learn.microsoft.com/azure/event-hubs/event-processor-balance-partition-load).

**Validate the postmortem**

27. Open the generated postmortem and its matching Blob in `incident-reports`.
28. Confirm that its root-cause statement uses the highest-priority supported causal statement, cites its observed predicate values, and includes prompt-match, failed-step, and tool-response replay metrics.
29. Confirm that it never infers cause from a hypothesis ID or event name.

**Validate the Azure resources**

30. In the Azure portal, validate only the provisioned Log Analytics workspace, Application Insights component, Storage account and two Blob containers, Event Hubs namespace and hub, scheduled query rule, and Action Group.

No Foundry project or model is provisioned in this lab.

**Review objective coverage**

| Objective | Required evidence | Passing outcome |
|---|---|---|
| Query traces and latency | Candidate, detail, and cohort query results | Both synthetic outcomes appear and the selected trace preserves span relationships. |
| Capture replay artifacts | Schema-valid local and Blob snapshots | Required versions, hashes, spans, and synthetic mocks are present; sensitive content is absent. |
| Test competing hypotheses | Hypothesis result report | Every predicate is supported, contradicted, or explicitly missing. |
| Connect detection through postmortem | Alert, remediation evidence, replay, and report | Processing is bounded, side effects remain disabled, and causal claims cite observed evidence. |

## Optional challenge: Falsify a competing hypothesis

Add a competing hypothesis that explains one symptom but not the complete trace.

**Expected output:** The postmortem ranks the supported hypothesis first and cites the observation that falsifies the alternative.

**Failure investigation:** Add a misleading synthetic symptom and use the three KQL stages to isolate the actual failure mechanism.
## Task 7: Review the design

1. Answer these questions:

- Which observable failure differed most between successful and failed cohorts?
- What evidence would falsify your leading hypothesis?
- Which preventive action changes the system rather than only treating the symptom?

## Task 8: Clean up

**Remove Azure resources**

1. Run `azd down --purge`.
2. Confirm Application Insights, Log Analytics, and Storage are deleted.
3. Remove `.env` plus generated snapshots unless your instructor requires them.

**Deactivate the virtual environment**

4. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

5. Confirm that `(.venv)` no longer appears before changing to another lab directory.

## Summary

You diagnosed a multi-agent incident from Application Insights evidence, preserved a safe replay snapshot, tested competing hypotheses, and produced an evidence-linked blameless postmortem.
