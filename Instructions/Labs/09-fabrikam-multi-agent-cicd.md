---
lab:
  title: 'Implement CI/CD for Foundry hosted agents'
  description: 'Release immutable Microsoft Foundry hosted-agent versions with GitHub Actions, then use a thin Container Apps dashboard to demonstrate progressive delivery and compatible-set rollback.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Implement CI/CD for Foundry hosted agents

## Customer scenario

Fabrikam uses three AI agents to review code changes:

- The **scanner** identifies security vulnerabilities.
- The **reviewer** assesses maintainability and release risk.
- The **orchestrator** invokes both specialists and produces one release recommendation.

Scanner, reviewer, and orchestrator are Microsoft Foundry hosted agents v2. Each successful `azd deploy` creates a new immutable Foundry agent version. Calls use the hosted-agent Responses endpoint only after creating a session with a concrete `version_ref`, so the session is bound to the recorded immutable version. They aren't Azure Container Apps.

Fabrikam also operates one deliberately thin traditional web application: a Container Apps release dashboard and gateway. Each dashboard revision targets one exact orchestrator version and displays:

- Its Container App revision and release channel.
- The selected Foundry release-set ID.
- The immutable orchestrator agent name, Foundry version, and Responses endpoint.

The dashboard is the progressive-delivery boundary. During a canary, Container Apps sends 75 percent of requests to the stable dashboard revision and 25 percent to the candidate dashboard revision. The agents don't claim native weighted Foundry routing.

## Lab scenario

Prepare passwordless GitHub access to Azure, activate the supplied workflows, and deploy the initial release to a development environment. Then change the scanner's logical version, review credential-free pull-request evidence, and deploy a candidate release set.

Use the dashboard's weighted URL to observe 75/25 routing. Use the stable and candidate label URLs for deterministic verification. Promote healthy dashboard traffic to 0/100, then exercise a regression profile. Rollback must use a persisted last-verified release manifest, restore the dashboard revision that targets that compatible Foundry release set, and verify the exact restored orchestrator version both through the dashboard and by version-pinned invocation.

<!-- LAB DIAGRAM PLACEHOLDER: Show scanner and reviewer deployment before the orchestrator, the version-bound dashboard revision, canary traffic, promotion, and rollback to a verified release set. -->

By the end of this exercise, you'll be able to:

- Validate strict logical semantic versions, tool contracts, a dependency DAG, model policy, and hosted-agent v2 manifests without Azure credentials.
- Deploy Foundry hosted agents serially in shared azd state and capture immutable names, versions, and Responses endpoints.
- Bind deterministic smoke evaluation evidence to a source commit and Foundry release set.
- Use GitHub environments, OIDC, Bicep, and separate Foundry projects for development, staging, and production.
- Apply canary and blue-green traffic to a traditional Container Apps boundary without misrepresenting Foundry routing.
- Restore a compatible release set from persisted evidence and retain reverse-dependency rollback closure.

> [!IMPORTANT]
> This lab creates billable Azure Container Registry, Log Analytics, Container Apps, and Microsoft Foundry resources, including a `gpt-5.4-mini` model deployment pinned to version `2026-03-17`. Use an isolated training subscription and remove the resource groups when you finish. Model availability and quota vary by region.

## Understand the three version identities

The lab intentionally keeps three version systems separate.

| Identity | Example | Purpose |
|---|---|---|
| Logical semantic version | `scanner 1.2.0` | Source compatibility and dependency ranges |
| Immutable Foundry agent version | `fabrikam-code-scanner`, version `7` | Deployed executable agent, version endpoint, and version-bound session |
| Dashboard Container App revision | `fabrikam-release-dev--abc123` | Traditional-app release channel and 75/25 or 0/100 traffic |

A logical version isn't a Foundry version. A Foundry version isn't a Container App revision. The release-set manifest records all three and prevents the pipeline from treating them as interchangeable.

## Understand the release architecture

The deployment graph is:

```text
scanner  --------+
                  +--> orchestrator --> version-bound hosted-agent session
reviewer --------+                           ^
                                              |
                                   dashboard revision
                                   (stable or candidate)
```

The source has four parts:

- `azure.yaml` and `src/*_agent.py` define the three hosted agents; `dashboard/app.py` is the only Container Apps service.
- `agents/*.yml` defines logical versions, dependencies, model policy, evaluation identity, instructions, and tool contracts.
- `scripts/` captures immutable deployment outputs into a release set, while `assets/evaluation/` and the quality profiles provide validation evidence.
- `infra/` and `assets/workflows/` create the Azure boundary and provide the inactive workflow templates that you activate during the lab.

The captured release set binds the reviewed source and policy metadata to each immutable Foundry agent version and the dashboard revision that invokes the orchestrator.

## Task 1: Prepare the lab

You need:

- An Azure subscription in which an administrator can grant the required roles.
- A GitHub account that can create a private repository, workflows, environments, variables, protection rules, releases, and issues.
- [Python 3.13](https://www.python.org/downloads/), [Git](https://git-scm.com/downloads), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), and [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd).
- Visual Studio Code with the Python, GitHub Actions, and Bicep extensions.

1. Clone the lab source repository, open it in Visual Studio Code, and change to the starter directory:

```powershell
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
cd mslearn-ai-multi-agents\Allfiles\09-fabrikam-multi-agent-cicd
```

2. Sign in and confirm the subscription:

```powershell
az login
az account show --output table
$env:AZURE_DEV_USER_AGENT = 'microsoft_foundry_skill'; azd auth login
```

3. Use synthetic data only. Don't add an Azure client secret or an `AZURE_CREDENTIALS` secret to GitHub.

4. Open `azure.yaml`. Confirm that scanner, reviewer, and orchestrator are hosted agents and dashboard is the only Container Apps service.

5. Open `agents/orchestrator.yml`. Identify its logical version, scanner/reviewer dependency ranges, exact model version, evaluation identity, and hosted Responses manifest.

6. Open `dashboard/app.py`. Find the release-set, release-channel, Container App revision, orchestrator version, and Responses endpoint fields shown to learners.

## Task 2: Validate the starter locally

1. Create the virtual environment and install dependencies:

```powershell
.\scripts\setup.ps1
. .\.venv\Scripts\Activate.ps1
```

2. Run the complete credential-free validation:

```powershell
python scripts\preflight.py
python scripts\validate_workflows.py
python -m unittest discover -s Allfiles\09-fabrikam-multi-agent-cicd\tests -v
python scripts\export_release.py --agents agents --manifest artifacts\release-set.json --contracts artifacts\current-contracts.json --source-commit local-validation --environment pr-validation --status validated
python -m src.main validate --manifest artifacts\release-set.json --baseline assets\contracts\baseline.json --candidate artifacts\current-contracts.json --quality assets\quality-metrics-healthy.json --output artifacts\compatibility-report.json
az bicep build --file infra\main.bicep
```

Expected results:

- Preflight reports three Foundry hosted agents v2 and one dashboard.
- Workflow validation confirms OIDC, serial deployments, version-pinned smoke calls, persisted rollback evidence, and dashboard-only traffic.
- Targeted tests pass.
- The compatibility report has `"compatible": true`.
- Bicep builds without errors.

3. Open `artifacts/release-set.json`. Confirm that remote Foundry names, versions, and endpoints are `null`. Pull-request validation is credential-free and can't invent deployment evidence. The deployment workflow fills those fields only after successful `azd deploy`.

4. Optional: press **F5** and choose a hosted-agent configuration to start the selected entrypoint with the VS Code Python debugger. Foundry Toolkit Agent Inspector can connect to the local hosted-agent server after you supply the required local environment values.

## Task 3: Create the practice repository

1. On GitHub, create a private repository named `fabrikam-agent-cicd`.
2. Don't initialize it with a README, `.gitignore`, or license.
3. Record the exact `<owner>/fabrikam-agent-cicd` value.
4. Copy the starter into a separate practice repository:

```powershell
$labRoot = (Get-Location).Path
$practiceRepo = Join-Path (Split-Path $labRoot -Parent) 'fabrikam-agent-cicd'
New-Item -ItemType Directory -Force $practiceRepo
Get-ChildItem $labRoot -Force |
  Where-Object { $_.Name -notin @('.azure', '.env', '.venv', 'artifacts', '__pycache__') } |
  Copy-Item -Destination $practiceRepo -Recurse -Force
Set-Location $practiceRepo
git init
git branch -M main
git remote add origin '<repository-url>'
```

5. Don't push yet. A push to `main` deploys development.

## Task 4: Configure passwordless GitHub access

GitHub Actions exchanges a short-lived GitHub OIDC token for an Entra token. Don't create a client secret.

1. In the Microsoft Entra admin center, create a single-tenant app registration named `fabrikam-agent-github`.
2. Record:
   - Application (client) ID as `AZURE_CLIENT_ID`.
   - Directory (tenant) ID as `AZURE_TENANT_ID`.
3. Open the linked Enterprise application and record its Object ID as `GITHUB_PRINCIPAL_ID`.
4. Add one federated credential for each GitHub environment:

```text
repo:<owner>/fabrikam-agent-cicd:environment:development
repo:<owner>/fabrikam-agent-cicd:environment:staging
repo:<owner>/fabrikam-agent-cicd:environment:production
```

5. Select or create one resource group per environment:

```powershell
$azureRegion = 'eastus2'
$suffix = (New-Guid).Guid.Substring(0, 8)
@('dev', 'stg', 'prod') | ForEach-Object {
  az group create --name "rg-lab09-$($_)-$suffix" --location $azureRegion | Out-Null
}
```

6. An Azure administrator must assign the Enterprise application these roles on each selected resource group:

- **Contributor**
- **Role Based Access Control Administrator**

These permissions allow the workflow to create environment-specific Foundry projects, model deployments, identities, RBAC assignments, and dashboard resources.

## Task 5: Configure GitHub environments

1. In repository **Settings** > **Environments**, create:
   - `development`
   - `staging`
   - `production`
2. Add these environment variables to each environment:

| Variable | Development example | Requirement |
|---|---|---|
| `AZURE_CLIENT_ID` | `<application-client-id>` | Same OIDC application |
| `AZURE_TENANT_ID` | `<directory-tenant-id>` | Same tenant |
| `AZURE_SUBSCRIPTION_ID` | `<subscription-id>` | Target subscription |
| `AZURE_LOCATION` | `eastus2` | Region with exact model quota |
| `AZURE_ENV_NAME` | `lab09-cicd-dev` | Unique per environment |
| `GITHUB_PRINCIPAL_ID` | `<enterprise-app-object-id>` | Enterprise application Object ID |
| `AZURE_RESOURCE_GROUP_NAME` | `rg-lab09-dev-...` | Unique per environment |

3. Use `lab09-cicd-stg` and `lab09-cicd-prod` plus their distinct resource groups for staging and production.
4. Add required reviewers and restrict deployment branches for staging and production.

Each GitHub environment maps to a separate resource group and Foundry project. The workflow promotes the same reviewed source identity. Production additionally verifies that staging has a persisted verified manifest for the same commit and reviewed release ID.

## Task 6: Activate the workflows

1. Create `.github/workflows`:

```powershell
New-Item -ItemType Directory -Force .github\workflows
```

2. Copy the four supplied templates:

```powershell
Copy-Item assets\workflows\validate-agents.yml .github\workflows\validate-agents.yml
Copy-Item assets\workflows\deploy-environment.yml .github\workflows\deploy-environment.yml
Copy-Item assets\workflows\canary-quality-gate.yml .github\workflows\canary-quality-gate.yml
Copy-Item assets\workflows\rollback-agents.yml .github\workflows\rollback-agents.yml
```

3. Review `.github/workflows/validate-agents.yml`.

It has no Azure login. It validates:

- Contracts and strict logical semantic versions.
- Dependency DAG and reverse-dependency closure.
- Exact `gpt-5.4-mini` / `2026-03-17` model policy.
- Hosted-agent v2 declarations and separate entrypoints.
- Source compilation, targeted tests, workflows, and deterministic dataset shape.

4. Review `.github/workflows/deploy-environment.yml`.

The important deployment order is:

```text
azd deploy scanner
azd ai agent show scanner
azd ai agent invoke scanner --version <captured-version>

azd deploy reviewer
azd ai agent show reviewer
azd ai agent invoke reviewer --version <captured-version>

azd deploy orchestrator
azd ai agent show orchestrator
azd ai agent invoke orchestrator --version <captured-version>

azd deploy dashboard
```

Every azd command sets `AZURE_DEV_USER_AGENT=microsoft_foundry_skill` inline. Scanner and reviewer are serial because concurrent deploys must not mutate the same selected azd state. Orchestrator deploys only after their immutable endpoints exist. Deployment evidence also records a concrete `/versions/<version>` endpoint for CLI verification. Runtime HTTP calls create a session with that same concrete version and reject a mismatched returned version.

5. Find `capture_release_set.py` in the deployment workflow. It captures:

```text
AGENT_SCANNER_NAME
AGENT_SCANNER_VERSION
AGENT_SCANNER_RESPONSES_ENDPOINT
AGENT_REVIEWER_NAME
AGENT_REVIEWER_VERSION
AGENT_REVIEWER_RESPONSES_ENDPOINT
AGENT_ORCHESTRATOR_NAME
AGENT_ORCHESTRATOR_VERSION
AGENT_ORCHESTRATOR_RESPONSES_ENDPOINT
```

6. Review `.github/workflows/canary-quality-gate.yml`.

It refuses promotion unless the candidate artifact contains passing version-bound evaluation evidence. The healthy/regression fixture is secondary evidence used only to exercise the policy branches.

7. Review `.github/workflows/rollback-agents.yml`.

It downloads `release-set.json` from the persistent `verified-<environment>` GitHub release, validates environment, verified status, release-set identity, all agent bindings, dashboard app/revision, and stable label evidence, then restores it. It doesn't infer that the second-newest revision is safe.

The deploy, quality, and rollback workflows share one environment-keyed concurrency group with `cancel-in-progress: false`, so two operations can't race while changing dashboard traffic or persisted release evidence.

8. Validate the activated copies:

```powershell
python scripts\validate_workflows.py
git status --short
```

## Task 7: Deploy the initial development release

1. Commit and push:

```powershell
git add .
git commit -m "Initialize Foundry hosted-agent delivery"
git push -u origin main
```

2. In GitHub Actions, open **Deploy hosted-agent release set**.

Observe:

- Credential-free validation completes first.
- GitHub exchanges its environment OIDC token; no stored client secret is used.
- Bicep creates a development Foundry project, exact model deployment, ACR, Log Analytics, Container Apps environment, and one dashboard Container App.
- Scanner, reviewer, and orchestrator each create an immutable Foundry hosted-agent version.
- Each agent is checked with `azd ai agent show` and a version-pinned smoke invocation.
- The orchestrator's environment points to captured scanner and reviewer Responses endpoints plus exact versions; each call creates and verifies a session pinned to that version.
- The two-record deterministic dataset runs against the pinned orchestrator.
- One dashboard revision is deployed with 100 percent traffic and displays the exact selected release set.
- Because no `verified-development` release exists and Azure reports only the infrastructure bootstrap revision, the workflow treats this as an explicit first release. After smoke, evaluation, stable-label dashboard, and version-evidence checks pass, it persists this release as the first verified baseline.

3. Download `deployment-evidence-development-<run-id>`.
4. Open `release-set.json`. Compare each logical version with the immutable Foundry version.
5. Open `evaluation-evidence.json`. Confirm the source commit, release-set ID, exact orchestrator version, dataset/evaluator identity, and `"status": "passed"`.

## Task 8: Verify the initial resources

1. In the Azure portal, open the development resource group.
2. Open the Microsoft Foundry project.
3. Confirm the `gpt-5.4-mini` deployment is version `2026-03-17`.
4. Open **Agents** and confirm scanner, reviewer, and orchestrator are hosted agents with active immutable versions.
5. Compare the agent names and versions with `release-set.json`.
6. Confirm there aren't scanner, reviewer, or orchestrator Container Apps.
7. Open the single Fabrikam release dashboard Container App.
8. Under **Revision management**, confirm one selected dashboard revision has 100 percent traffic.
9. Open the dashboard URL. Confirm it displays:
   - `STABLE` channel.
   - Its Container App revision.
   - Release-set ID.
   - Exact orchestrator name, Foundry version, and Responses endpoint.
10. Submit the synthetic review form. Confirm the dashboard invokes the selected orchestrator.

## Task 9: Create and review a candidate

1. Create a branch:

```powershell
git checkout -b feature/scanner-release-metadata
```

2. In `agents/scanner.yml`, change:

```yaml
version: 1.2.0
```

to:

```yaml
version: 1.2.1
```

3. Add one instruction sentence that doesn't change the tool contract:

```text
Include a short confidence explanation for each reported finding.
```

4. Run local validation.
5. Commit, push, and create a pull request:

```powershell
git add agents\scanner.yml
git commit -m "Clarify scanner finding confidence"
git push -u origin feature/scanner-release-metadata
```

6. Open the pull-request workflow artifact.
7. Confirm:
   - Scanner logical version is `1.2.1`.
   - Contract digest is present.
   - No breaking contract finding exists.
   - Orchestrator's `>=1.0.0,<2.0.0` dependency accepts scanner `1.2.1`.
   - Hosted manifests remain Responses `2.0.0`, Python `3.13`.
   - Remote Foundry deployment fields remain `null`.

8. Merge the pull request.

## Task 10: Verify 75/25 dashboard exposure

After the merge deployment succeeds:

1. Download its deployment evidence.
2. Confirm the candidate release set has new immutable Foundry versions and a new release-set ID.
3. Confirm its dashboard revision records the candidate orchestrator's exact version endpoint and uses a Responses session pinned to that version.
4. Open the dashboard's normal URL and refresh at least 12 times.
5. Record when the page shows:
   - Stable channel and the last-verified release-set identity.
   - Candidate channel and the candidate release-set identity.

The sample is small, so don't expect exactly nine stable and three candidate responses. The configured weights, not a short random sample, are authoritative.

6. Open the `stable_label_url` from the candidate `release-set.json`. Its hostname begins `stable---`; the workflow obtains the app FQDN from Azure and verifies the label-to-revision mapping before recording it.
7. Refresh it three times. Confirm it always reports the same stable dashboard revision and orchestrator version.
8. Open the `candidate_label_url`.
9. Refresh it three times. Confirm it always reports the candidate dashboard revision and candidate orchestrator version.
10. In the Azure portal, open dashboard **Revision management** and verify the 75/25 weights and `stable`/`candidate` labels.

These direct label routes are deterministic verification. Learners must not rely only on random refreshes.

## Task 11: Promote the candidate across environments

1. In GitHub Actions, run **Assess dashboard canary quality** with:
   - Environment: `development`
   - Deployment run ID: candidate deployment run ID
   - Failed agent: `scanner`
   - Metric profile: `healthy`
2. Confirm:
   - Version-bound evaluation evidence is passing.
   - Policy action is `promote`.
   - Dashboard traffic changes from 75/25 to 0/100.
   - Candidate dashboard revision receives the `stable` label.
   - `verified-development` contains the persisted verified `release-set.json`.
3. Open the stable label URL and verify the promoted release-set and exact orchestrator version.

4. Run **Deploy hosted-agent release set** manually for `staging`.
5. Enter the same reviewed source commit deployed to development.
6. Approve the protected staging environment.
7. Run its healthy canary assessment to create `verified-staging`.
8. Run **Deploy hosted-agent release set** for `production` with the same source commit.
9. Confirm production waits for its protected-environment approval and verifies staging's:
   - Source commit.
   - Reviewed release ID.
   - Verified status.

The Foundry agent version numbers can differ across projects. The reviewed source identity, logical versions, contracts, model policy, and evaluation identity remain the same.

## Task 12: Exercise compatible-set rollback

1. Run **Assess dashboard canary quality** for a candidate with:
   - Metric profile: `regression`
   - Failed agent: `scanner`
2. Confirm policy action is `rollback`.
3. Open **Restore verified Foundry release set**.
4. Confirm it:
   - Downloads the candidate release set from the deployment run.
   - Downloads the persisted last-verified environment manifest.
   - Derives rollback closure `orchestrator, scanner` in reverse dependency order.
   - Restores 100 percent dashboard traffic to the exact revision recorded in the verified manifest.
   - Applies the `stable` label to that revision.
   - Verifies the dashboard reports the persisted release-set ID and exact orchestrator version.
   - Invokes that exact Foundry orchestrator version with `azd ai agent invoke --version`.
   - Creates a GitHub incident issue and uploads rollback evidence.

5. Open `rollback-evidence.json`. Confirm it records:
   - Restored release-set ID.
   - Dashboard revision.
   - Exact orchestrator name, version, and Responses endpoint.
   - 100 percent traffic.
6. Open the stable dashboard URL and verify the same values.

Rollback doesn't delete immutable Foundry versions. It restores traffic to a dashboard revision that is already bound to a known-compatible Foundry release set.

## Task 13: Review the release evidence

Retain:

- Pull-request compatibility report.
- Candidate and verified release-set manifests.
- Version-bound evaluation evidence.
- 75/25 and 0/100 traffic evidence.
- Stable/candidate direct-route responses.
- Rollback closure, restored dashboard metadata, pinned invocation output, and incident link.

### Reflect on the release design

1. Why is a logical semantic version insufficient to identify a deployed Foundry hosted agent?
2. Why must the release set capture an immutable version endpoint and create a version-bound session instead of invoking only a logical agent name?
3. Why does the orchestrator deploy after scanner and reviewer even though the specialist agents are independent?
4. Why is the dashboard, rather than the Foundry agents, the 75/25 traffic boundary?
5. How do direct label URLs make canary verification deterministic?
6. Why can't rollback assume the second-newest Container App revision is safe?
7. Why does reverse-dependency closure include orchestrator when scanner fails?
8. Which release fields must remain identical when promoting reviewed source from staging to production, and which environment-specific Foundry values may differ?
9. Why are healthy/regression fixtures secondary to version-bound smoke evaluation evidence?
10. Which managed identity invokes Foundry from the dashboard, and why is a stored API key unnecessary?

## Optional challenge: Extend the smoke-test dataset

Add a third deterministic smoke record that requires the orchestrator to explain why a release should be held when scanner and reviewer disagree. Increment the dataset version in every agent definition, update the targeted test expectation, and confirm the reviewed release ID changes even though no tool contract changed. Don't weaken the exact model policy or promote without version-bound evidence.

## Task 14: Clean up

Delete each lab resource group:

```powershell
az group delete --name '<development-resource-group>' --yes --no-wait
az group delete --name '<staging-resource-group>' --yes --no-wait
az group delete --name '<production-resource-group>' --yes --no-wait
```

Then:

1. Delete the `development`, `staging`, and `production` GitHub environments.
2. Delete the automation-owned `verified-development`, `verified-staging`, and `verified-production` GitHub releases.
3. Delete the Entra app registration and Enterprise application if they were created only for this lab.
4. Delete the practice repository if you no longer need the evidence.

## Live-only assumptions

No live deployment is required to validate the lab source. During an actual learner deployment:

- The selected region must support `gpt-5.4-mini` version `2026-03-17` with sufficient quota.
- `azd` must return `AGENT_<SERVICE>_NAME`, `AGENT_<SERVICE>_VERSION`, and `AGENT_<SERVICE>_RESPONSES_ENDPOINT` after each hosted-agent deployment.
- Hosted-agent session and Responses endpoints must accept Microsoft Entra bearer tokens obtained by `DefaultAzureCredential`, and session creation must return the concrete requested version.
- GitHub environment protection must enforce staging and production approvals.
- Container Apps revision labels and direct label URLs must be enabled by the current Azure CLI/Container Apps API.
