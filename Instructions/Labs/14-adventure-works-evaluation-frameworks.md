---
lab:
  title: 'Build a multi-agent evaluation quality gate'
  description: 'Evaluate Adventure Works multi-agent journeys with Microsoft Foundry evaluators, synthetic data, calibration evidence, and regression thresholds.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Build a multi-agent evaluation quality gate

## Customer scenario

Adventure Works must detect regressions in its Customer Intelligence Platform before a new agent configuration reaches customers. Individual agents can return plausible answers while the complete journey fails through poor intent resolution, incomplete handoffs, or contradictory responses.

## Lab scenario

You are the platform engineer responsible for a repeatable Microsoft Foundry evaluation run. You will complete an evaluator factory, evaluate a privacy-safe JSONL dataset, calibrate judge output against human labels, and apply deterministic regression thresholds to the measured results.

By the end of this exercise, you will be able to:

- Define component, journey, and system-level success metrics.
- Run current Responses-based model judges through the Azure AI Evaluation SDK batch framework.
- Use synthetic canary, regression, and historical-failure cases.
- Convert evaluation output into an auditable deployment recommendation.

> **Important**: The live run uses a deployed model and incurs token charges. Use only the supplied synthetic data. Confirm quota and run cleanup when finished.

## Task 1: Prepare the lab

You need [Python 3.10 or later](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), an Azure subscription, and permission to create a Microsoft Foundry account, project, and model deployment. Use a region with quota for the instructor-approved chat model. Authenticate locally with `DefaultAzureCredential`; do not place keys in files.

**Clone and open the repository**

1. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

3. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\14-adventure-works-evaluation-frameworks
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review `assets/evaluation-data.jsonl`, `assets/evaluation-config.json`, `src/evaluators.py`, `src/main.py`, and `infra/main.bicep`. Before continuing, confirm that one dataset row produces deterministic and model-based metrics, row-level evidence, judge calibration, and a deterministic release decision.

Complete the evaluator set, calibration, batch run, and deterministic gate. The model judge supplies quality signals; application code owns the release decision.

## Task 2: Build the virtual environment

1. On Windows, create and activate the virtual environment:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

## Task 3: Deploy Azure resources

1. Use an isolated environment and the inline user-agent required for Foundry workflows.

2. Review Foundry model-judge cost, quota, and role access before provisioning.

`azd` provisions the Foundry account, project, and model deployment; evaluation runs separately and incurs model charges.

**Set the deployment values**

3. Set `$azureRegion` to an approved region that supports your selected model.
4. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

> **Note:** `AZURE_DEV_USER_AGENT` tags provisioning for attribution and is not exported to `.env`. Remove it afterward to avoid tagging unrelated commands.

**Validate and provision the infrastructure**

5. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab14-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-eval-dev
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

> **Note:** If provisioning fails, inspect the first deployment error. Check model and region availability, quota, principal ID, and role-assignment permissions. Correct the cause and rerun `azd provision`.

**Verify the generated environment**

6. After provisioning succeeds, validate that `.env` includes `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL_NAME`, and the project and principal values required by the evaluator.
7. Do not add keys, tokens, or connection strings; the application uses your signed-in identity.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, remove the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Create the evaluator set**

1. In `src/evaluators.py`, find `# LAB PLACEHOLDER 1`.
2. Replace the incomplete `create_evaluators()` function associated with it with:

```python
def create_evaluators(
  model_config: dict[str, str], credential: TokenCredential
) -> dict[str, Any]:
  """Create Responses-based evaluators for the batch run."""
  judge_options = {
    "project_endpoint": model_config["project_endpoint"],
    "deployment_name": model_config["azure_deployment"],
    "credential": credential,
  }
  return {
    "intent_resolution": IntentResolutionEvaluator(**judge_options),
    "task_adherence": TaskAdherenceEvaluator(**judge_options),
    "response_completeness": ResponseCompletenessEvaluator(**judge_options),
    "journey_coherence": JourneyCoherenceEvaluator(**judge_options),
  }
```

This combines component metrics with the journey-level model judge while reusing the parameterized deployment and passwordless credential.

> **Preview note:** The Foundry agent evaluators and composite **Output Quality** and **Tool Use Quality** evaluators are preview features. APIs, score definitions, supported judge models, and package names can change. This lab keeps individual evaluators because their row-level signals support the calibration exercise. Check [Agent evaluators](https://learn.microsoft.com/azure/foundry-classic/concepts/evaluation-evaluators/agent-evaluators) before using them in a production release gate.

**Calculate calibration agreement**

3. In `src/main.py`, find `# LAB PLACEHOLDER 2`.
4. Replace the incomplete `calibration_agreement()` function associated with it with:

```python
def calibration_agreement(rows: list[dict[str, Any]]) -> float:
  """Return exact agreement between rounded judge scores and human labels."""
  labeled = []
  for row in rows:
    human_label = (
      row.get("human_label")
      or row.get("data.human_label")
      or row.get("inputs.human_label")
    )
    judge_score = row.get("outputs.journey_coherence.journey_coherence")
    if human_label is not None and judge_score is not None:
      labeled.append(int(human_label) == round(float(judge_score)))
  return sum(labeled) / len(labeled) if labeled else 0.0
```

Calibration keeps judge disagreement visible instead of treating a model score as ground truth.

**Apply deterministic regression gates**

5. Find `# LAB PLACEHOLDER 3`.
6. Replace the incomplete `apply_regression_gate()` function associated with it with:

```python
def apply_regression_gate(
  metrics: dict[str, float], agreement: float, config: dict[str, Any]
) -> dict[str, Any]:
  """Compare measured metrics with absolute, delta, and calibration gates."""
  comparisons = []
  failed_gates = []
  for name, policy in config["metrics"].items():
    measured = metrics.get(name)
    if measured is None:
      failed_gates.append(f"{name}: missing measured metric")
      comparisons.append({"metric": name, "status": "missing"})
      continue
    delta = measured - float(policy["baseline"])
    passed = measured >= float(policy["minimum"]) and delta >= -float(policy["maximum_drop"])
    comparisons.append({
      "metric": name,
      "measured": measured,
      "baseline": policy["baseline"],
      "delta": round(delta, 4),
      "minimum": policy["minimum"],
      "maximum_drop": policy["maximum_drop"],
      "passed": passed,
    })
    if not passed:
      failed_gates.append(name)
  if agreement < float(config["minimum_calibration_agreement"]):
    failed_gates.append("judge_calibration")
  return {
    "passed": not failed_gates,
    "failed_gates": failed_gates,
    "comparisons": comparisons,
    "calibration_agreement": agreement,
    "minimum_calibration_agreement": config["minimum_calibration_agreement"],
  }
```

The model produces semantic measurements; deterministic code owns the release decision and fails closed when a metric is missing.

**Run the batch evaluation**

7. Find `# LAB PLACEHOLDER 4`.
8. Replace the `evaluation = None` assignment and its following `if` block with:

```python
  evaluation = evaluate(
    data=str(data_path),
    evaluators=evaluators,
    evaluator_config={
      "intent_resolution": {
        "column_mapping": {
          "query": "${data.query}",
          "response": "${data.response}",
        }
      },
      "task_adherence": {
        "column_mapping": {
          "query": "${data.query}",
          "response": "${data.response}",
        }
      },
      "response_completeness": {
        "column_mapping": {
          "response": "${data.response}",
          "ground_truth": "${data.expected_behavior}",
        }
      },
      "journey_coherence": {
        "column_mapping": {
          "query": "${data.query}",
          "response": "${data.response}",
          "context": "${data.context}",
          "expected_behavior": "${data.expected_behavior}",
        }
      }
    },
    output_path=str(output_path.with_suffix(".rows.jsonl")),
  )
```

Each evaluator receives its documented dataset contract. Response completeness compares the candidate with `expected_behavior` as ground truth, while the journey judge also receives context. Row-level evidence remains separate from the summary.

**Guard report generation**

9. Find `# LAB PLACEHOLDER 5`.
10. Insert this guard at the placeholder location:

```python
  if not rows:
    raise RuntimeError("Evaluation returned no rows; no release decision can be made.")
```

An empty evaluation must not produce a plausible-looking deployment recommendation.

**Check the completed code**

11. Check the completed code locally:

```console
python -m py_compile src/evaluators.py src/main.py
python scripts/preflight.py --require-complete
```

12. Confirm that compilation returns no output.
13. Confirm that preflight reports the Python version, dataset, configuration, and Evaluation SDK as `ready`; endpoint and deployment can remain `not ready` until provisioning is complete.

## Task 5: Run the solution

1. Run the batch evaluation:

```console
python -m src.main --data assets/evaluation-data.jsonl --output reports/evaluation-result.json
```

2. Confirm that the command invokes the live evaluator model, preserves row-level evidence, and produces a release recommendation derived from measured metrics.

**Understand the output**

`reports/evaluation-result.rows.jsonl` contains one evidence record per synthetic case, including evaluator scores and reasons. `reports/evaluation-result.json` is the release summary: `metrics` contains aggregates, `gate.comparisons` shows measured values against absolute and delta thresholds, `gate.calibration_agreement` compares the journey judge with human labels, and `gate.passed` is true only when `failed_gates` is empty. `deployment` is the configured deployment name, not a hardcoded model.

## Task 6: Validate the implementation

**Inspect the evaluation evidence**

1. Confirm that `reports/evaluation-result.json` contains dataset metadata, evaluator names, aggregate scores, calibration agreement, threshold comparisons, failed gates, and the model deployment name.
2. Inspect low-scoring rows and explain whether the failure is component-level, handoff-level, or system-level.

**Test the regression gate**

3. Change one synthetic candidate response to contradict an earlier handoff.
4. Re-run the evaluation.
5. Confirm that the evaluation score changes and that the regression gate uses the measured result rather than a hardcoded scenario label.

**Validate the Azure resources**

6. In the Microsoft Foundry portal, validate the provisioned Foundry account, project, and model deployment used by this lab.

**Review objective coverage**

| Objective | Required evidence | Passing outcome |
|---|---|---|
| Define component, journey, and system metrics | Evaluator names and gate comparisons | All configured metrics appear; missing metrics fail closed. |
| Run Responses-based evaluators through the SDK batch framework | Row JSONL and aggregate summary | Every synthetic row has evaluator output and reasons. |
| Use synthetic coverage cases | Dataset metadata and reviewed rows | Only supplied or learner-created synthetic cases are present. |
| Produce an auditable recommendation | Gate result, calibration, and deployment | Recommendation follows measured thresholds and names the configured deployment. |

## Optional challenge: Add a grounding failure

Add one synthetic case that completes the requested task but contradicts or omits supplied grounding evidence.

**Expected output:** The relevant evaluator fails the row, the aggregate report shows the affected metric, and the deterministic quality gate blocks release.

**Failure investigation:** Create judge and human-label disagreement and distinguish calibration failure from task-result failure.
## Task 7: Review the design

1. Answer these questions:

- Which system-level metric would expose a successful agent response followed by a failed handoff?
- What calibration sample size would you require before a judge can block production?
- Which cases belong in canary, regression, and historical-failure partitions?

## Task 8: Clean up

**Remove Azure resources**

1. Run the following commands:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge
Remove-Item Env:AZURE_DEV_USER_AGENT
```

2. Confirm that the resource group is deleted.
3. Keep only synthetic local reports that your instructor requires.

**Deactivate the virtual environment**

4. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

5. Confirm that `(.venv)` no longer appears before changing to another lab directory.

## Summary

You implemented a Microsoft Foundry evaluation workflow that uses synthetic datasets, specialized evaluators, human-label calibration, and deterministic regression gates to produce release evidence.
