---
lab:
  title: 'Trace multi-agent workflows with OpenTelemetry'
  description: 'Create correlated OpenTelemetry spans, W3C context propagation, structured logs, anomaly signals, and Azure Monitor evidence for Adventure Works agents.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Trace multi-agent workflows with OpenTelemetry

## Customer scenario

Adventure Works operates a customer intelligence platform whose router, recommendation, and inventory agents cross service boundaries. Operators need one trace waterfall, privacy-aware decision logs, latency evidence, and alerts that identify the responsible agent before customers report failures.

## Lab scenario

You will create real spans for a synthetic three-agent flow, explicitly propagate W3C `traceparent` context, activate latency, error-rate, and token anomaly policy, export queryable telemetry through Microsoft Entra authentication, and validate an Azure Monitor scheduled-query alert and action group.

By the end of this exercise, you will be able to:

- Create OpenTelemetry spans at agent semantic boundaries.
- Inject and extract W3C Trace Context across agent calls.
- Emit structured, privacy-aware logs correlated to spans.
- Export to Application Insights and query agent health and a trace waterfall.
- Trigger and observe an actionable alert for latency, error-rate, or token anomalies.

> **Important**: Application Insights and Log Analytics ingestion are billable. The lab sleeps for milliseconds and uses synthetic metadata only. Delete monitoring resources after validation.

## Task 1: Prepare the lab

1. Install [Python 3.10+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download) with the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) extension, and [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).
2. Use an identity with permission to create monitoring resources and assign `Monitoring Metrics Publisher`.
3. Use only the included synthetic scenario.
4. Never put prompts, personal identifiers, payment data, or credentials into logs or span attributes.

5. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

6. Open the cloned repository in Visual Studio Code.
7. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\13-adventure-works-distributed-observability
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `src/telemetry.py`, `config/telemetry-policy.yaml`, `assets/trace-scenario.json`, `kql/anomaly-alert.kql`, and `infra/main.bicep`. The lab export ratio is `1.0` so one learner run produces a complete waterfall; the policy separately records a `0.05` production head-sampling example for design discussion. Before continuing, confirm that `traceparent` flows across all three agents and that flattened latency, token, and error-rate decisions are queryable by the scheduled alert.

## Task 2: Build the virtual environment

1. On Windows, run:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

2. Review `config/telemetry-policy.yaml`.
3. Confirm prohibited fields are absent from `assets/trace-scenario.json`.

## Task 3: Deploy Azure resources

1. Before provisioning with `azd`, check monitoring role access and costs for Log Analytics ingestion and retention, Application Insights, scheduled-query alerts, and action groups.

2. Set `$azureRegion` to an approved region that supports the required services.
3. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.
4. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab13-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
azd env new lab13-distributed-observability
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set ALERT_EMAIL <lab-operator-email>
azd provision
azd env get-values | Out-File .env -Encoding utf8
```

> Note: If provisioning fails, inspect the first Azure deployment error. Regional monitoring availability, invalid alert email, policy restrictions, and role-assignment permissions are common causes. Correct the cause, then run `azd provision` again.

The scheduled-query rule uses a typed, empty fallback and skips deployment-time query validation because a new workspace does not expose the `AppTraces` table until its first telemetry arrives. The fallback returns no rows; Azure evaluates the real `AppTraces` signals normally after ingestion begins.

5. After provisioning succeeds, validate that `.env` includes the Application Insights connection string, `APPLICATIONINSIGHTS_RESOURCE_ID`, the Log Analytics workspace ID, identity client ID, and alert resource IDs.
6. Confirm that it contains no token or key. The Bicep identity receives `Monitoring Metrics Publisher` for deployed execution.
7. For local live validation, assign your signed-in development identity the same role on `APPLICATIONINSIGHTS_RESOURCE_ID`.
8. Do not enable local-key ingestion.
9. Confirm the action group subscription email before expecting notifications.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Inject the active trace context**

1. Open `src/telemetry.py` and find **LAB PLACEHOLDER 1** in `build_next_carrier`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete build_next_carrier in Task 1")
```

2. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
carrier: dict[str, str] = {}
propagator.inject(carrier)
return carrier
```

The propagator serializes the active context into `traceparent`. `execute_agent` extracts it before `start_as_current_span`, making the next agent a child in the same trace.

**Review structured decision telemetry**

3. Inspect `_structured_log` and `execute_agent`. Both surfaces include `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.agent.id`, `gen_ai.provider.name`, `gen_ai.conversation.id`, `gen_ai.usage.input_tokens`, and `gen_ai.usage.output_tokens`; failed spans and logs also include `error.type`.
4. List the domain-specific attributes retained alongside the semantic attributes: `agent.version`, latency, anomaly flags, policy status, and the hashed session ID. Semantic conventions improve interoperability; they do not replace useful bounded business telemetry.
5. Do not add raw request text or model reasoning. The conversation ID in this synthetic scenario is noncustomer test data; apply your organization's identifier policy before using the same attribute with production conversations.
6. Inspect `execute_agent`.
7. Identify the three policy decisions: latency uses a strict threshold, token anomaly uses the scenario mean plus the configured sigma multiple, and chain error rate is calculated after all agents complete. These decisions remain parameterized in `config/telemetry-policy.yaml`.

**Check the completed code**

8. Run the following checks:

```powershell
python -m py_compile src/main.py src/telemetry.py scripts/preflight.py
python scripts/preflight.py
Select-String -Path src/telemetry.py -Pattern 'NotImplementedError'
```

Preflight must end with `READY (local)`, and the final command must return no matches. Azure Monitor configuration can remain `INFO` for the console-only run.

## Task 5: Run the solution

1. Temporarily leave the Azure Monitor connection string blank.
2. Run `python -m src.main`.
3. Inspect the console span JSON.
4. Confirm three unique span IDs share one 32-character trace ID and form a parent-child chain. The recommendation span contains latency and token anomaly events: 85 ms exceeds 60 ms, and 516 tokens exceed the `350 + (3 x 50) = 500` token boundary. The inventory error produces a chain error rate of `1/3`, above 0.05.

5. Restore the Azure Monitor connection string.
6. Run the command again. The command writes `evidence/trace-evidence.json` and exports spans and logs.
7. Record the printed trace ID.

**Understand the output**

`correlation_complete: true` means all three records share one trace ID. `span_count: 3` is the number of agent semantic spans, not every SDK or exporter span. `anomalies` names agents whose status is not success. `error_rate` is the observed chain error fraction, while `error_rate_anomaly` is the policy comparison result.

The default `records` exercise all three signals: recommendation latency and tokens, plus the inventory error that produces a chain error rate of approximately 0.3333.

## Task 6: Validate the implementation

1. Open the Application Insights **Agents (Preview)** view as the built-in baseline. Use it to inspect per-agent requests, latency, token usage, errors, and individual agent details when the emitted semantic attributes are recognized. See [Monitor AI agents with Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/agents-view).
2. Open Application Insights **Transaction search**.
3. Find the recorded trace ID and inspect the transaction details waterfall.
4. Confirm router, recommendation, and inventory appear under one operation.
5. Open **Logs**.
6. Paste the trace ID into `kql/trace-waterfall.kql` and run it.
7. Run `kql/agent-health.kql` and verify recommendation has the highest P95 latency and a token anomaly, while inventory has error status. Treat these custom queries and dashboards as extensions for domain policy and cross-agent analysis, not replacements for the built-in Agents view.

8. Validate each active setting independently and restore the asset after each run:

9. Set recommendation latency to exactly 60 ms and output tokens to 80.
10. Confirm neither boundary is anomalous because both comparisons use greater-than.
11. Restore output tokens to 96 and confirm the token anomaly returns while latency remains at 60 ms.
12. Set every `error` field to `false` and confirm `error_rate_anomaly` is false.
13. Restore the inventory error.
14. Change `latency_threshold_ms`, `error_rate_threshold`, and `token_anomaly_sigma` in the YAML one at a time and confirm runtime decisions change without editing KQL.

15. Inspect the provisioned resources:

```console
az monitor action-group show --ids <ANOMALY_ACTION_GROUP_ID> --query "{enabled:enabled,receivers:emailReceivers[].emailAddress}"
az monitor scheduled-query show --ids <ANOMALY_ALERT_RULE_ID> --query "{enabled:enabled,severity:severity,frequency:evaluationFrequency,actions:actions.actionGroups}"
```

16. Run the restored default scenario with Azure export enabled.
17. After ingestion and the next five-minute evaluation, open Azure Monitor **Alerts**.
18. Filter by the scheduled-query rule.
19. Confirm that a fired severity-2 alert links to the workspace that stores the Application Insights telemetry and to the action group.
20. Confirm the email uses the common alert schema.
21. Run a no-anomaly scenario and observe auto-mitigation after the configured five-minute healthy period.
22. Capture the Agents view baseline, waterfall, correlated property rows, three policy decisions, rule/action linkage, fired alert, notification, and resolved state as live evidence.

## Optional challenge: Add a cross-agent attribute

Add a synthetic request-classification span attribute and propagate it through the chain.

**Expected output:** The value appears on the correlated agent spans and can be selected in KQL without exposing request content.

**Failure investigation:** Break context propagation at one handoff and locate the first span that leaves the original trace.
## Task 7: Review the design

1. Answer these questions:

- What breaks when context injection is omitted at one boundary?
- Which structured fields are useful without exposing customer content?
- Why would errors and slow traces require collector-side tail sampling rather than the head-sampling ratio used by this lab?
- How would you correlate simultaneous anomalies into one incident?
- Why does the alert consume emitted policy decisions instead of repeating thresholds in KQL?

## Task 8: Clean up

**Remove Azure resources**

1. Run `azd down --purge`.
2. Confirm the workspace and Application Insights resource are deleted.
3. Remove `.env` and local evidence. Leaving telemetry export active continues ingestion charges.

**Deactivate the virtual environment**

4. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

5. Confirm that `(.venv)` no longer appears before changing to another lab directory.

## Summary

You created real OpenTelemetry spans, propagated W3C context, activated latency, error-rate, and token anomaly policy, exported queryable properties through secure Azure Monitor configuration, and validated an actionable scheduled-query alert lifecycle.
