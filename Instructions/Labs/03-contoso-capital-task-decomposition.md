---
lab:
  title: 'Apply task decomposition and agent collaboration strategies in Microsoft Foundry'
  description: 'Implement a live meta-agent planner, validated task DAG, and context-preserving specialist handoffs.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Apply task decomposition and agent collaboration strategies in Microsoft Foundry

## Customer scenario

Contoso Capital receives research questions ranging from lookups to multi-source investment analyses. Fixed chains overprocess simple work and miss dependencies in complex work. The firm needs inspectable model-generated plans with bounded handoffs and measurable coordination overhead.

## Lab scenario

You will complete an Agents v2 meta-agent planner and executor. The planner returns a JSON DAG; application code validates it, invokes specialists only when dependencies are complete, transfers concise context envelopes, and permits one evidence-driven replan.

<!-- LAB DIAGRAM PLACEHOLDER: Show the planner, validated task DAG, dependency-ready specialists, handoff envelopes, and final synthesis. -->

By the end of this exercise, you will be able to:

- Design prompt chains for multi-step analysis.
- Generate adaptive decomposition with a meta-agent.
- Implement reliable, context-preserving handoffs.
- Balance plan depth against latency and token overhead.

> **Important**: Planning and every specialist invocation consume model quota. The model may propose a plan, but application code must validate and bound it.

## Task 1: Prepare the lab

Use [Python 3.11+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)/[Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install), [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download), a supported model, and an authenticated subscription. You need Foundry resource creation and data-plane access. Use only `assets/research-query.json`.

**Clone and open the repository**

1. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

3. From the VS Code terminal, validate the required tools, credentials, and active subscription:

```powershell
cd Allfiles\03-contoso-capital-task-decomposition
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `infra/main.bicep`, `assets/research-query.json`, and `src/main.py`. Before continuing, confirm that you can locate:

- the planner input and capability registry;
- deterministic DAG validation and dependency-ready scheduling;
- the bounded handoff envelope;
- the evidence-driven replan signal and final synthesis task.

## Task 2: Build the virtual environment

1. From the lab directory, create and activate the virtual environment:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

## Task 3: Deploy the Azure resources

Check model quota and access before provisioning. Planning, specialist execution, replanning, Application Insights ingestion, and 30-day Log Analytics retention are billable. Use the bounded synthetic input and a unique disposable environment. `azd` provisions the Bicep resources; you run the application separately.

**Set the deployment values**

1. Set `$azureRegion` to an approved region that supports your selected model.
2. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

> **Note:** `AZURE_DEV_USER_AGENT` tags provisioning for attribution and is not exported to `.env`. Remove it afterward to avoid tagging unrelated commands.

**Validate and provision the infrastructure**

3. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab03-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new lab03
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

Model quota, model-version availability, regional service availability, and role-assignment permissions are common causes.

5. Correct the relevant `azd env` setting or permission, then run `azd provision` again.

**Verify the generated environment**

6. After provisioning succeeds, validate that `.env` includes `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_PROJECT_ID`, `FOUNDRY_MODEL_NAME`, `APPLICATIONINSIGHTS_RESOURCE_ID`, and `LOG_ANALYTICS_WORKSPACE_ID`.

The Application Insights connection string is stored in the Foundry project connection and is not written to `.env`.

> **Network access for this lab:** The Bicep template enables the Foundry account's native public network access and sets the default network action to **Allow** so the local application can reach the project endpoint. Microsoft Entra authentication and Azure RBAC are still required. After deployment, confirm these settings on the Foundry account **Networking** page. Production environments should use an approved selected-network or private-endpoint design.

7. Do not add keys or tokens to `.env`.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Validate the model-generated task DAG**

1. Open `src/main.py` and find **LAB PLACEHOLDER 1** in `validate_plan`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete validate_plan in Task 1")
```

2. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
tasks = plan.get("tasks")
if not isinstance(tasks, list) or not 1 <= len(tasks) <= 6:
  raise ValueError("Plan must contain between 1 and 6 tasks")

task_ids = [task.get("id") for task in tasks]
if any(not isinstance(task_id, str) or not task_id for task_id in task_ids):
  raise ValueError("Every task requires a nonempty string ID")
if len(task_ids) != len(set(task_ids)):
  raise ValueError("Task IDs must be unique")

known_ids = set(task_ids)
for task in tasks:
  if task.get("agent") not in registry:
    raise ValueError(f"Unknown agent for task {task['id']}")
  dependencies = task.get("depends_on", [])
  if not isinstance(dependencies, list):
    raise ValueError(f"depends_on must be a list for task {task['id']}")
  if task["id"] in dependencies or not set(dependencies) <= known_ids:
    raise ValueError(f"Invalid dependency for task {task['id']}")

remaining = {
  task["id"]: set(task.get("depends_on", []))
  for task in tasks
}
resolved: set[str] = set()
while remaining:
  ready = {
    task_id
    for task_id, dependencies in remaining.items()
    if dependencies <= resolved
  }
  if not ready:
    raise ValueError("Plan dependencies contain a cycle")
  resolved.update(ready)
  remaining = {
    task_id: dependencies
    for task_id, dependencies in remaining.items()
    if task_id not in ready
  }

synthesis_tasks = [
  task for task in tasks if task["agent"] == "thesis-synthesis"
]
if len(synthesis_tasks) != 1:
  raise ValueError("The plan must contain exactly one thesis-synthesis task")
synthesis = synthesis_tasks[0]
non_synthesis_dependency_ids = {
  dependency
  for task in tasks
  if task["id"] != synthesis["id"]
  for dependency in task.get("depends_on", [])
}
terminal_evidence_ids = {
  task["id"]
  for task in tasks
  if task["id"] not in non_synthesis_dependency_ids and task["id"] != synthesis["id"]
}
if set(synthesis.get("depends_on", [])) != terminal_evidence_ids:
  raise ValueError(
    "The thesis-synthesis task must depend on every terminal evidence task"
  )
if any(synthesis["id"] in task.get("depends_on", []) for task in tasks):
  raise ValueError("No task can depend on the thesis-synthesis task")
```

Application code validates the proposed graph before any specialist call: bounded plan depth, known capabilities, acyclic dependencies, and exactly one synthesis task that consumes every terminal evidence branch.

**Select dependency-ready tasks**

3. Find **LAB PLACEHOLDER 2** in `ready_tasks`:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete ready_tasks in Task 2")
```

4. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
unfinished = [task for task in tasks if task["id"] not in completed]
ready = [
  task
  for task in unfinished
  if all(
    completed.get(dependency, {}).get("status") == "success"
    for dependency in task.get("depends_on", [])
  )
]
if unfinished and not ready:
  blocked = ", ".join(task["id"] for task in unfinished)
  raise RuntimeError(f"Plan deadlock: blocked tasks: {blocked}")
return ready
```

Only successful prerequisites unlock a task. A blocked graph raises an error rather than looping indefinitely.

**Build a bounded handoff envelope**

5. Find **LAB PLACEHOLDER 3** in `build_handoff`:

```python
# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
raise NotImplementedError("Complete build_handoff in Task 3")
```

6. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
max_chars = int(os.getenv("MAX_HANDOFF_CHARS", "6000"))
dependencies = task.get("depends_on", [])
summary_limit = max(256, max_chars // max(2, len(dependencies) + 1))
dependency_context = [
  {
    "task_id": dependency,
    "response_id": completed[dependency]["response_id"],
    "summary": completed[dependency]["summary"][:summary_limit],
  }
  for dependency in dependencies
]
envelope = {
  "task_id": task["id"],
  "objective": task["objective"],
  "dependency_context": dependency_context,
  "source_response_ids": [
    item["response_id"] for item in dependency_context
  ],
  "expected_schema": task["expected_schema"],
  "deadline_seconds": int(os.getenv("HANDOFF_DEADLINE_SECONDS", "45")),
  "correlation_id": correlation_id,
}
if len(json.dumps(envelope)) > max_chars:
  raise ValueError("Handoff envelope exceeds MAX_HANDOFF_CHARS")
return envelope
```

The envelope separates the objective from dependency evidence, retains source response IDs, and bounds context size. The correlation ID links tasks without logging research content.

**Signal one evidence-driven replan**

7. Find **LAB PLACEHOLDER 4** in `should_replan`:

```python
# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
raise NotImplementedError("Complete should_replan in Task 4")
```

8. Replace only the `raise NotImplementedError` line beneath it with this code:

```python
if replan_count >= 1:
  return False
if result.get("status") != "success":
  return True

try:
  payload = json.loads(result.get("summary", "{}"))
except json.JSONDecodeError:
  return False

status = str(payload.get("status", "")).lower()
confidence = payload.get("confidence")
low_confidence = isinstance(confidence, (int, float)) and confidence < 0.5
return (
  status in {"missing_evidence", "capability_unavailable"}
  or bool(payload.get("missing_evidence"))
  or low_confidence
)
```

The policy records at most one evidence-driven signal in `replan_count`; it does not execute a replan. A production coordinator would submit the evidence to the planner and validate a replacement for only the remaining DAG.

**Check the completed code**

The supplied runner already records planner and specialist response IDs, task and handoff counts, the bounded replan signal, elapsed time, and a coordination ratio without logging prompt or response content.

9. Run the local checks before making billable model calls:

```powershell
python -m py_compile src/main.py scripts/preflight.py
python scripts/preflight.py
```

10. Confirm that preflight reports four `PASS` lines, `src/main.py` retains all four `LAB PLACEHOLDER` markers, and it no longer contains `NotImplementedError`.

## Task 5: Run the solution

1. Run the application:

```powershell
python -m src.main --input assets/research-query.json
```

2. Run the complex query.
3. Then change `complexity_hint` to `simple`.

The live planner should reduce task depth while preserving the final synthesis task.

**Understand the output**

| Field | What it reflects |
|---|---|
| `planner_response_id` | The live structured plan returned by the planner agent. |
| `plan` | The validated task IDs, owners, objectives, schemas, and dependencies used for dispatch. |
| `task_count` | Validated plan depth, bounded to one through six tasks. |
| `handoff_count` | Number of specialist dispatch envelopes created. |
| `replan_count` | Zero or one evidence-driven signal for an outer replanning coordinator. |
| `coordination_ratio` | Handoffs divided by completed tasks; compare this with quality and latency rather than treating it as a score. |
| `elapsed_ms` | End-to-end planner, validation, specialist, and synthesis wall-clock time. |
| `results` | Per-task status, live response ID, and visible structured summary. |

For a valid run, every dependency task appears in `results` before its consumer, and the final entry belongs to `thesis-synthesis`. The planner contract requires a simple-query run to contain exactly one evidence task plus final synthesis, while a complex run contains three through six tasks. Both plans must satisfy the same deterministic DAG invariants.

## Task 6: Validate the implementation

**Inspect the captured plan**

1. Run the following commands:

```powershell
python -m py_compile src/main.py scripts/preflight.py
python -m src.main --input assets/research-query.json *> artifacts-lab03.txt
Select-String artifacts-lab03.txt -Pattern 'planner_response_id|task_count|handoff_count|replan_count|coordination_ratio'
```

2. Inspect the captured plan: every dependency must refer to an earlier completed task, every specialist must exist in the registry, and all task results must have live Foundry response IDs.
3. Demonstrate one simple and one complex plan.

Offline DAG checks alone do not satisfy the live objective.

**Validate the agents in Foundry**

4. Open the [Foundry portal](https://ai.azure.com).
5. Select the project named in `FOUNDRY_PROJECT_ENDPOINT`.
6. Open **Agents** and confirm current versions for `research-planner` and each specialist named in `assets/research-query.json`.

**Validate the response traces**

7. Select **Agents** > **Traces**.
8. Set the time range to include the complex run.
9. Search for `planner_response_id`.
10. Open the matching trace and confirm the planner agent name, version, successful response operation, and timestamp.
11. Then search for each response ID in `results`.
12. Confirm that dependency-consuming specialist traces start only after the traces for their prerequisite results complete.

13. Repeat the trace search for the simple run.
14. Compare the number and sequence of specialist traces with the complex run; the trace count should reflect the smaller validated plan.

Trace ingestion can take several minutes.

## Optional challenge: Compare two decompositions

Create two valid DAGs for the same synthetic query: one coarse-grained and one fine-grained. Select one using explicit quality, latency, and handoff-context constraints.

**Expected output:** The selected plan lists bounded task IDs, owners, dependencies, and preserved artifacts, and its synthesis task depends on every terminal evidence branch.

**Failure investigation:** Reduce the handoff size limit until one envelope is rejected, then classify the cause as decomposition granularity, artifact size, or dispatch validation.
## Task 7: Review the design

1. Answer these questions:

- Which plan invariants must never be delegated to a model?
- When is a fixed chain cheaper and safer?
- What context can be summarized without breaking downstream evidence?
- Which signal justifies the single replan budget?

## Task 8: Clean up

**Remove Azure resources**

1. Run the following commands:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge --force
Remove-Item Env:AZURE_DEV_USER_AGENT
```

**Deactivate the virtual environment**

2. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

3. Confirm that `(.venv)` no longer appears before changing to another lab directory.

## Summary

You built adaptive planning, validated a task DAG, executed dependency-aware specialists, preserved handoff context, and measured decomposition overhead with live Foundry responses.
