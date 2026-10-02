---
lab:
  title: 'Govern a Foundry multi-agent code review'
  description: 'Apply content safety, fairness, transparency, privacy, and accountability controls to a Microsoft Foundry multi-agent workflow.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Govern a Foundry multi-agent code review

## Customer scenario

Fabrikam uses specialized AI agents to review customer code. A security reviewer identifies vulnerabilities, a fairness auditor checks whether equivalent technology stacks receive consistent outcomes, and a governance orchestrator combines their evidence. Because the recommendation can delay a deployment, Fabrikam must screen the request, minimize every handoff, preserve attribution, and require human review when a policy threshold is exceeded.

## Lab scenario

You will deploy a Microsoft Foundry project, a model with Foundry-native guardrails, and workspace-based Application Insights by using Bicep. You will then complete a deterministic policy gate and run a three-agent governance workflow:

1. Foundry applies its default safety guardrails to model prompts and completions.
1. The **security-reviewer** receives only the source fragment and external evidence reference needed for its task.
1. The **fairness-auditor** receives only calculated group rates, disparity, and the policy threshold.
1. The **governance-orchestrator** receives minimized specialist results and the deterministic policy decision.
1. The application records response IDs, hashes, policy metadata, and the human-review result without logging raw source code, tenant identity, prompts, or hidden reasoning.

By the end of this exercise, you will be able to:

- Identify where Foundry-native guardrails protect model prompts and completions.
- Measure fairness disparity with paired synthetic probes.
- Restrict each agent handoff to purpose-specific data.
- Preserve agent attribution with Foundry response IDs.
- Query minimized accountability evidence in Application Insights.

> **Important**: The model deployment, Log Analytics, and Application Insights are billable. Use only the supplied synthetic data and delete the resources after validation.

## Task 1: Prepare the lab

1. Install [Python 3.10+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download), and the VS Code [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep) extensions.

2. Use an Azure identity that can create Microsoft Foundry, model deployment, and monitoring resources and can assign roles.
3. Select a region where the required model is available.
4. Do not use customer code, personal data, credentials, or secrets.

5. If you haven't already done so, clone the lab repository:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

6. Open the repository in Visual Studio Code.
7. In a PowerShell terminal, go to the lab directory and verify the tools and active subscription:

```powershell
cd Allfiles\11-fabrikam-responsible-ai-governance
az version
azd version
python --version
az account show --output table
```

**Architecture checkpoint**

Review these components before editing:

| Component | What to locate |
|---|---|
| `assets/governance-scenario.json` and `policy/governance-policy.yaml` | Synthetic inputs, fairness threshold, and human-review policy |
| `src/governance.py` | Fairness calculations, minimized payloads, identifier hashing, and evidence |
| `src/main.py` | Deterministic local orchestration and the `--live` Foundry path |
| `kql/governance-evidence.kql` | Minimized accountability evidence |
| `infra/main.bicep` | Foundry, model, monitoring, and least-privilege role assignments |

Before continuing, confirm that the default workflow is local and deterministic and that only the `--live` path invokes Foundry agents.

## Task 2: Build the virtual environment

1. On Windows, run:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

## Task 3: Deploy Azure resources

1. Set the deployment values.
2. Replace the model name and version if they are not available in your approved region.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.
3. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
$modelDeploymentName = 'gpt-5.4-mini'
$modelName = 'gpt-5.4-mini'
$modelVersion = '2026-03-17'
$principalId = az ad signed-in-user show --query id --output tsv

if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab11-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}

az bicep build --file infra/main.bicep
azd env new lab11-rai-governance
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set FOUNDRY_MODEL_NAME $modelDeploymentName
azd env set FOUNDRY_MODEL_CATALOG_NAME $modelName
azd env set FOUNDRY_MODEL_VERSION $modelVersion
azd env set AZURE_PRINCIPAL_ID $principalId
azd provision
azd env get-values | Out-File .env -Encoding utf8
```

> **Note**: If `azd env new` reports that the environment exists, select another environment name or use the existing environment. If provisioning fails, inspect the first deployment error. Model availability, quota, Azure Policy, and role-assignment permissions are common causes.

4. Confirm that the generated `.env` contains identifiers, endpoints, and an Application Insights connection string; it contains no model keys or tokens. `DefaultAzureCredential` uses your Azure sign-in.

> **Network access for this lab:** The Bicep template enables the Foundry account's native public network access and sets the default network action to **Allow** so the local application can reach the project endpoint. Microsoft Entra authentication and Azure RBAC are still required. After deployment, confirm these settings on the Foundry account **Networking** page. Production environments should use an approved selected-network or private-endpoint design.

## Task 4: Implement the policy gate

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete requires_human_review in Task 1")
```

1. Replace only the `raise NotImplementedError(...)` line beneath the retained marker with this implementation, preserving indentation:

```python
fairness = evidence.get("fairness")
if not isinstance(fairness, dict) or "max_disparity" not in fairness:
    return True

try:
    return (
        float(fairness["max_disparity"])
        > float(policy["thresholds"]["max_fairness_disparity"])
    )
except (KeyError, TypeError, ValueError):
    return True
```

This decision is fail-closed: incomplete or malformed evidence requires human review. Thresholds come from the versioned policy instead of being duplicated in code.

2. Check the completed code:

```powershell
& .\.venv\Scripts\python.exe -m py_compile src/main.py src/governance.py scripts/preflight.py
& .\.venv\Scripts\python.exe scripts/preflight.py
Select-String -Path src/governance.py -Pattern 'NotImplementedError'
```

Preflight must show `PASS` for the Foundry project, model, and Application Insights configuration checks and end with `READY (Azure configured)`. The final command must return no matches.

**Inspect the privacy boundaries**

3. Open `policy/governance-policy.yaml` and compare `agent_inputs` with `build_agent_payload` in `src/governance.py`.

| Agent | Allowed input | Deliberately excluded |
|---|---|---|
| `security-reviewer` | Request ID, synthetic source fragment, CWE reference | Tenant identity, fairness probes, policy internals |
| `fairness-auditor` | Request ID, group rates, disparity, threshold | Source code, tenant identity, security output |
| `governance-orchestrator` | Request ID, policy version, control results, specialist results | Raw source code, tenant identity, hidden reasoning |

4. Check that the application doesn't record raw prompts or hidden reasoning:

```powershell
Select-String -Path src/governance.py,src/main.py -Pattern 'chain_of_thought|raw_prompt'
```

The command must return no matches.

5. Locate the fields used for hashed values and Foundry agent attribution:

```powershell
Select-String -Path src/governance.py -Pattern 'tenant_id_hash|input_sha256|agent_response_ids'
```

The command should show that raw values are replaced by hashes and that Foundry response IDs provide agent attribution.

## Task 5: Run the solution

**Run the deterministic workflow**

1. Run the workflow without Azure calls:

```powershell
& .\.venv\Scripts\python.exe -m src.main
```

The output must show:

- `mode` equal to `deterministic`.
- Python positive-outcome rate `1.0` and Node positive-outcome rate `0.5`.
- Maximum fairness disparity `0.5`.
- `human_review_required` equal to `true` because `0.5` exceeds the policy threshold of `0.1`.
- Three local response IDs, one for each agent role.
- Purpose-specific field names under `payloadFields`.

2. Inspect the latest evidence record:

```powershell
$evidence = Get-Content evidence/governance-evidence.jsonl | Select-Object -Last 1 | ConvertFrom-Json
$evidence | ConvertTo-Json -Depth 10
```

3. Confirm that it includes `evidence_scope` equal to `single_process_local_jsonl`, the policy ID and version, fairness rates, hashes, human-review result, and three response IDs. It must not include the raw tenant value or source fragment from `assets/governance-scenario.json`.

The JSONL file is local, single-process exercise evidence. It is not a concurrency-safe or centralized production evidence store; use Application Insights or another governed central sink when multiple processes can write.

**Run the live multi-agent workflow**

The live command creates a version of each Foundry prompt agent and invokes them in this order. Foundry's native guardrails evaluate the prompts and completions inline:

- `security-reviewer`
- `fairness-auditor`
- `governance-orchestrator`

4. Run it once:

```powershell
& .\.venv\Scripts\python.exe -m src.main --live
```

The command prints each agent's `responseId` and text, appends one minimized local evidence record, and emits one `fabrikam.governance.evidence` trace to Application Insights. Azure Monitor telemetry is configured once per Python process and reused for subsequent emissions in that process. The model can vary its wording, but the fairness calculation and human-review decision remain deterministic.

> **Note**: Role assignments can take several minutes to propagate. If the first live run returns an authorization error, wait briefly, sign in again with `az login` if needed, and rerun the command.

## Task 6: Validate the implementation

**Validate in Microsoft Foundry**

1. Open [Microsoft Foundry](https://ai.azure.com/) and select the project named `lab11-<environment-name>`.
2. In the left navigation, select **Agents**.
3. Confirm that `security-reviewer`, `fairness-auditor`, and `governance-orchestrator` exist and each has a version.
4. Review each agent's instructions.
5. Confirm that its role is narrow and that the orchestrator is instructed not to request raw source, tenant identity, or hidden reasoning.
6. At the top of the **Agents** page, select **Traces**. There is no separate **Observability** navigation item in the current Foundry portal.
7. Search by **Response ID** using an ID from `agentResponses` in the terminal output or `agent_response_ids` in the latest local evidence record.
8. Open each matching trace and compare its response ID with the corresponding security reviewer, fairness auditor, or governance orchestrator response.
9. Inspect the inputs.
10. Confirm that only the security reviewer receives `sourceCode`; the fairness auditor and governance orchestrator do not.

> **Note**: If **Traces** isn't visible or a trace can't be opened, confirm that you selected the correct project, completed a live run, and allowed time for telemetry and role assignments to propagate. The Bicep template assigns the learner `Log Analytics Reader` on the connected Application Insights resource, which Microsoft Foundry requires for viewing trace data.

**Review Foundry-native guardrails**

This lab doesn't deploy a standalone Azure AI Content Safety resource. The model deployment uses the default guardrails that Foundry applies to prompts and completions.

11. In the Foundry project, select **Build** in the top menu, and then select **Models**.
12. Open the deployment named `gpt-5.4-mini`.
13. Review the deployment's guardrail or content-filter setting.
14. Confirm that the deployment uses Foundry's default safety policy and isn't configured with an unfiltered custom policy.
15. Return to **Agents** and review the latest traces.
16. Confirm that each successful specialist and orchestrator response came from the guarded model deployment.

Default guardrails block supported prompt or completion risks above their configured threshold. Use only the supplied neutral synthetic scenario; don't introduce harmful test content.

**Test the fairness boundary**

17. Change only the final `node-b` probe in `assets/governance-scenario.json` from `0` to `1`.
18. Run:

```powershell
& .\.venv\Scripts\python.exe -m src.main
$updated = Get-Content evidence/governance-evidence.jsonl | Select-Object -Last 1 | ConvertFrom-Json
$updated.fairness | ConvertTo-Json -Depth 5
$updated.human_review_required
```

Both rates should now be `1.0`, disparity should be `0.0`, and human review should be `false` because no fairness threshold is exceeded.

19. Restore `node-b` to `0` before continuing.

**Query accountability evidence**

20. Wait several minutes for the live trace to reach Application Insights.
21. In the Azure portal, open the Application Insights resource whose name starts with `appi-lab11-`.
22. Select **Logs**.
23. Switch to KQL mode if needed.
24. Run the contents of `kql/governance-evidence.kql`.

The result should show policy version `1.0.0`, at least one review and escalation, maximum disparity `0.5`, and the serialized response IDs for the three Foundry agents.

25. Run this privacy query and confirm it returns zero rows:

```kusto
AppTraces
| where Message == "fabrikam.governance.evidence"
| where Properties has_any ("tenant_id", "source_code", "raw_prompt", "chain_of_thought")
```

26. Capture the following as the governance evidence set:

- The Foundry model deployment's default guardrail assignment.
- Fairness rates, disparity, and human-review decision.
- The three Foundry agent versions and matching response IDs.
- Trace inputs demonstrating purpose-specific data minimization.
- The Application Insights policy summary and zero-row privacy result.

## Optional challenge: Trigger human review

Add a synthetic fairness probe that crosses a configured governance threshold.

**Expected output:** The release gate changes to `human review required` and records both the measured value and policy threshold.

**Failure investigation:** Remove one required evidence field and confirm that the policy gate fails closed with a specific missing-evidence reason.
## Task 7: Review the design

1. Answer these questions:

- Why is the human-review gate deterministic instead of delegated to the orchestrator agent?
- How could bias compound if the fairness auditor received a security review framed with developer metadata?
- Which additional controls would be required before processing real customer source code?
- When should an audit store retain full specialist output instead of response IDs and minimized policy evidence?

## Task 8: Clean up

1. Delete the Azure resources:

```powershell
azd down --purge
```

2. If you used a precreated resource group, verify which resources the command will remove before confirming.
3. Delete local evidence and environment values:

```powershell
Remove-Item evidence/governance-evidence.jsonl -ErrorAction SilentlyContinue
Remove-Item .env -ErrorAction SilentlyContinue
```

4. Deactivate the virtual environment in every terminal where `(.venv)` appears:

```powershell
deactivate
```

## Summary

You deployed a Bicep-defined Microsoft Foundry project and governed a three-agent code review with native model guardrails, paired fairness probes, minimized handoffs, attributable response IDs, deterministic human oversight, and queryable Application Insights evidence.
