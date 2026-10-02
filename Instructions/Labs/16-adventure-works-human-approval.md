---
lab:
  title: 'Implement durable human approval workflows'
  description: 'Build a resumable Adventure Works approval workflow with calibrated escalation, Service Bus events, Cosmos DB state, and immutable audit evidence.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Implement durable human approval workflows

## Customer scenario

Adventure Works agents can recommend refunds and policy exceptions, but high-impact actions must pause for meaningful human review. An in-memory pending flag is not sufficient: approval can take hours, processes restart, duplicate decisions arrive, and overdue work must escalate without losing history.

## Lab scenario

You will implement a durable approval state machine. Cosmos DB stores current workflow state and append-only audit events. Service Bus carries approval requests and reviewer decisions. The CLI submits work, receives approve or reject events, resumes exactly once with optimistic concurrency, and escalates expired approvals.

<!-- LAB DIAGRAM PLACEHOLDER: Show request submission, risk decision, durable pending state, Service Bus review events, resume processing, and audit evidence. -->

By the end of this exercise, you will be able to:

- Combine calibrated confidence, business impact, exceptions, and ambiguity into escalation decisions.
- Persist approval state outside the process and resume after restart.
- Handle approve, reject, duplicate, and overdue paths safely.
- Produce structured feedback and immutable audit evidence.

> **Important**: Cosmos DB and Service Bus are billable. The synthetic payloads contain no customer PII. Do not place connection strings or keys in `.env`.

## Task 1: Prepare the lab

1. Install [Python 3.10 or later](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), and [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).

You need an Azure subscription and permission to create Cosmos DB, Service Bus, and role assignments. Use your signed-in identity through `DefaultAzureCredential`.

**Clone and open the repository**

2. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

3. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

4. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\16-adventure-works-human-approval
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `infra/main.bicep`, the synthetic refund request, `assets/workflow-state.schema.json`, `assets/adaptive-card.json`, `src/workflow.py`, and `src/reviewer_webhook.py`. Before continuing, confirm that a high-risk request moves from calibrated risk to durable pending state, authenticated reviewer submission, exactly-once resume processing, and idempotent audit evidence.

## Task 2: Build the virtual environment

1. On Windows, create and activate the virtual environment:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

## Task 3: Deploy Azure resources

1. Review Cosmos DB and Service Bus costs plus data-plane and messaging role access before provisioning.
2. Use only the supplied synthetic payloads and a unique environment.

`azd` provisions infrastructure; the approval workflow runs separately.

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
  $resourceGroupName = "rg-lab16-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-approval-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
$principalId = az ad signed-in-user show --query id --output tsv
azd env set AZURE_PRINCIPAL_ID $principalId
az bicep build --file infra/main.bicep
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> **Note:** If provisioning fails, inspect the first deployment error. Check Cosmos DB and Service Bus regional availability, namespace naming, principal ID, and role-assignment permissions. Correct the cause and rerun `azd provision`.

**Verify the generated environment**

6. After provisioning succeeds, validate that `.env` includes the Cosmos DB endpoint, database and container names, Service Bus namespace and queue names, and the principal values required by the application.
7. Keep only endpoints and resource names; do not add connection strings, keys, or tokens.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, remove the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Calibrate raw confidence**

1. In `src/workflow.py`, find `# LAB PLACEHOLDER 1`.
2. Replace only the incomplete `calibrate_confidence()` function associated with it with:

```python
def calibrate_confidence(raw_confidence: float, curve_path: Path) -> float:
  """Map raw confidence to observed accuracy using the nearest calibration point."""
  curve = json.loads(curve_path.read_text(encoding="utf-8"))
  nearest = min(
    curve["points"],
    key=lambda point: abs(float(point["raw_confidence"]) - raw_confidence),
  )
  return float(nearest["observed_accuracy"])
```

Observed accuracy, rather than an uncalibrated model confidence, drives review thresholds.

**Use calibrated confidence in risk assessment**

3. Find `# LAB PLACEHOLDER 2`.
4. Replace only the following `calibrated` assignment with:

```python
  calibrated = calibrate_confidence(
    float(request["raw_confidence"]),
    Path("assets/calibration-curve.json"),
  )
```

This derives confidence from the versioned curve instead of trusting a value copied into the request.

**Append immutable audit evidence**

5. Find `# LAB PLACEHOLDER 3`.
6. Replace only the following `raise NotImplementedError` statement with:

```python
    actor_hash = hashlib.sha256(actor.encode()).hexdigest()
    record = {
      "id": event_id,
      "event_id": event_id,
      "workflow_id": workflow_id,
      "event_type": event_type,
      "timestamp": utc_now(),
      "actor_hash": actor_hash,
      "previous_state": previous_state,
      "new_state": new_state,
      "policy_version": policy_version,
      "trace_id": trace_id,
      "rationale_category": rationale_category,
      "state_etag": state_etag,
      "state_version": state_version,
      "details": details,
    }
    try:
      self._audit.create_item(record)
    except exceptions.CosmosResourceExistsError:
      existing = self._audit.read_item(
        item=event_id,
        partition_key=workflow_id,
      )
      identity_fields = ("event_id", "workflow_id", "policy_version", "trace_id")
      if any(existing.get(field) != record.get(field) for field in identity_fields):
        raise RuntimeError(
          f"Audit event ID {event_id} already belongs to different evidence"
        )
```

The audit record uses the event ID as its document ID. A redelivery accepts an existing record only after verifying its workflow, policy, and trace identity; conflicting evidence fails closed. The record links a transition to persisted state without storing a reviewer identity in clear text. The workflow state also stores `last_transition` in the same optimistic-concurrency write, so a failed audit replication remains detectable and recoverable.

**Add cancellation compensation**

7. Find `# LAB PLACEHOLDER 4`.
8. Add this branch directly beneath it, keeping the existing final `else` block:

```python
    elif decision == "CANCELLED":
      new_state = "CANCELLED"
      execution = {
        "mode": "synthetic",
        "status": "cancelled_before_execution",
        "executed_at": None,
      }
```

Cancellation is a terminal, nonexecuting transition. The supplied `replace_item()` call still enforces the original ETag.

**Expose cancellation through the CLI**

9. In `src/main.py`, find `# LAB PLACEHOLDER 5`.
10. Replace only the following `decide.add_argument()` call with:

```python
  decide.add_argument(
    "--decision",
    choices=["approved", "rejected", "overridden", "cancelled"],
    required=True,
  )
```

The command surface and workflow state machine now accept the same decision vocabulary.

**Escalate expired reviews durably**

11. In `src/workflow.py`, find `# LAB PLACEHOLDER 6`.
12. Replace only the incomplete `escalate_expired()` method associated with it with:

```python
  def escalate_expired(self) -> list[str]:
    now = utc_now()
    query = "SELECT * FROM c WHERE c.state = 'WAITING_FOR_REVIEW' AND c.review_deadline < @now"
    expired = self._state.query_items(
      query=query,
      parameters=[{"name": "@now", "value": now}],
      enable_cross_partition_query=True,
    )
    escalated = []
    for item in expired:
      previous = item["state"]
      item["state"] = "ESCALATED"
      item["version"] += 1
      item["updated_at"] = now
      escalation_event_id = str(uuid.uuid4())
      item["last_transition"] = {
        "event_id": escalation_event_id,
        "event_type": "escalated",
        "actor_hash": hashlib.sha256(b"scheduler").hexdigest(),
        "previous_state": previous,
        "new_state": "ESCALATED",
        "timestamp": now,
      }
      updated = self._state.replace_item(
        item=item["id"],
        body=item,
        etag=item["_etag"],
        match_condition=MatchConditions.IfNotModified,
      )
      self.append_audit(
        item["id"], "escalated", "scheduler", previous, "ESCALATED", {},
        policy_version=updated["policy_version"],
        trace_id=updated["trace_id"],
        rationale_category="review_deadline_expired",
        event_id=escalation_event_id,
        state_etag=updated["_etag"],
        state_version=updated["version"],
      )
      with self._bus.get_queue_sender(self._request_queue) as sender:
        sender.send_messages(
          ServiceBusMessage(json.dumps(updated), message_id=str(uuid.uuid4()))
        )
      escalated.append(item["id"])
    return escalated
```

The same optimistic-concurrency and audit requirements apply to scheduler-driven transitions.

**Check the completed code**

13. Check the completed code locally:

```console
python -m py_compile src/workflow.py src/main.py src/reviewer_webhook.py src/active_learning.py
python scripts/preflight.py --require-complete
```

14. Confirm that compilation returns no output.
15. Before provisioning, confirm that preflight validates the synthetic request and schema; endpoint checks can remain `not ready`.
16. After provisioning and `.env` setup, confirm that every check reports `ready`.

## Task 5: Run the solution

1. Run the approval workflow commands:

```console
python -m src.main submit --input assets/refund-request.json
python -m src.main status --workflow-id <workflow-id>
python -m src.main decide --workflow-id <workflow-id> --decision approved --reviewer SYN-REVIEWER-01 --comment "Within exception authority"
python -m src.main resume
python -m src.main escalate
python -m src.reviewer_webhook --port 8080
python -m src.active_learning --output reports/active-learning.jsonl --evaluation reports/active-learning-evaluation.json
```

**Test the HTTP adapter**

2. Test the HTTP adapter locally before connecting a hosted reviewer surface.
3. Start the webhook in one terminal.
4. Submit synthetic card data from another:

```powershell
$body = @{
  workflow_id = '<workflow-id>'
  decision = 'APPROVED'
  comment = 'Synthetic local reviewer test'
  category = 'within_authority'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8080/api/reviewer-decisions' `
  -Headers @{'X-MS-CLIENT-PRINCIPAL-ID'='SYN-REVIEWER-01'} `
  -ContentType 'application/json' -Body $body
```

5. Confirm that the local response is HTTP 202 with `status: queued`.
6. Only after this works, configure an optional Teams or Power Automate flow to post the same fields through a host protected by Microsoft Entra authentication.

The decision producer connects only to Service Bus. Cosmos DB is initialized by the state-transition commands that submit, inspect, resume, escalate, or export workflows.

**Understand the output**

`submit` returns durable state with `WAITING_FOR_REVIEW` or `READY_TO_EXECUTE`, risk evidence, and an ETag. `decide` only queues an event. `resume` applies it, increments `version`, writes `human_review`, and appends a linked audit record. Duplicate terminal decisions return `duplicate: true`. `escalate` returns workflow IDs moved to `ESCALATED`. Active-learning output contains only rejected or overridden examples plus aggregate decision, rationale, and trace coverage.

## Task 6: Validate the implementation

**Validate durable state and audit evidence**

1. Query Cosmos DB and confirm current state survives restarts.
2. Verify every audit record, including submitted, duplicate, decision, and escalation events, has workflow ID, event ID, UTC timestamp, actor hash, previous and new state, rationale category, policy version, trace ID, `state_etag`, and `state_version`.
3. Inspect Service Bus incoming, active, and completed message metrics before and after a webhook POST to prove the reviewer path is asynchronous and observable.

**Validate the reviewer path**

4. For a local observable check, start the webhook.
5. POST synthetic Adaptive Card data with `Invoke-RestMethod`, including `X-MS-CLIENT-PRINCIPAL-ID: SYN-REVIEWER-01`.
6. Confirm HTTP 202.
7. Observe the decision queue count increase.
8. Run `resume`.
9. Observe the queue count decrease and a linked Cosmos audit event.
10. In a hosted environment, accept that header only from the platform's Microsoft Entra authentication layer.

**Validate workflow outcomes**

11. Demonstrate approved and executed, rejected and closed, overridden and executed, and overdue and escalated synthetic records.
12. Inspect both active-learning files and confirm their counts match the rejected and overridden Cosmos records.
13. Confirm that no action executes from a pending or rejected state.

**Validate the Azure resources**

14. In the Azure portal, validate only the provisioned Cosmos DB account, `approvals` database and two containers, Service Bus namespace and two queues, and their metrics.

Teams and Power Automate are optional external reviewer surfaces and are not provisioned by this lab.

**Compare with the canonical durable human-interaction pattern**

15. Compare this lab's hand-rolled design with the Durable Functions/Durable Task human-interaction pattern in [Human interaction in Durable Functions](https://learn.microsoft.com/azure/durable-task/common/durable-task-human-interaction).
16. In the canonical pattern, an orchestration waits for a named external approval event and creates a durable timer for the deadline. It races those durable tasks, cancels the timer when the approval wins, and follows the timeout or escalation path when the timer wins.
17. Map those concepts to this lab: Service Bus carries the external decision, Cosmos DB stores resumable state and the deadline, `resume` applies an event exactly once, and `escalate` performs the timer-equivalent deadline scan.
18. Record one tradeoff. The current architecture exposes queue and state mechanics for learning and works without replacing the application with Durable Functions, but the application owns replay safety, scheduling, duplicate handling, and race resolution that a durable orchestrator framework normally coordinates.

This is an optional conceptual comparison. Do not replace the lab's Service Bus/Cosmos DB architecture.

## Optional challenge: Add a reviewer band

Add a second confidence band that routes to a different synthetic reviewer group.

**Expected output:** A request in that band records the selected threshold and reviewer group and enters the correct durable approval state.

**Failure investigation:** Resume the same decision after a simulated timeout and prove that the protected action and audit event are not duplicated.
## Task 7: Review the design

1. Answer these questions:

- Which signal should override high model confidence?
- Why does the resume worker own execution rather than the reviewer endpoint?
- How would you prove that human oversight is substantive rather than rubber-stamping?

## Task 8: Clean up

**Remove Azure resources**

1. Run `azd down --purge`.
2. Confirm Cosmos DB and Service Bus are deleted.
3. Remove `.env`.
4. Retain only the instructor-requested synthetic report.

**Deactivate the virtual environment**

5. Run this command separately in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

6. Confirm that `(.venv)` no longer appears in any terminal before changing to another lab directory.

## Summary

You implemented a durable human approval workflow with risk-based escalation, asynchronous events, restart-safe resume, rejection feedback, timeout escalation, and immutable audit evidence.
