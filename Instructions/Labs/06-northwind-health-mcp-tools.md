---
lab:
  title: 'Build an enterprise MCP tool ecosystem'
  description: 'Implement, discover, invoke, and govern clinical tools through a real MCP server and client.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Build an enterprise MCP tool ecosystem

## Customer scenario

Northwind Health is replacing agent-specific integrations with a governed clinical tool catalog. The first release exposes synthetic drug-interaction and appointment-capacity tools through Model Context Protocol (MCP), records correlation-safe telemetry, and gives clients a reliable fallback when a dependency is unavailable.

## Lab scenario

You are the Python developer responsible for the MCP boundary. You will complete a FastMCP server, implement an MCP client that discovers tools at runtime, select a compatible tool from catalog metadata, validate tool results, and exercise fallback behavior. The server uses synthetic data and must not be used for clinical decisions.

<!-- LAB DIAGRAM PLACEHOLDER: Show MCP discovery, catalog selection, tool invocation, result validation, and governed fallback. -->

By the end of this exercise, you will be able to:

- Build a custom MCP server with versioned tools, structured errors, and scrubbed telemetry.
- Use a real MCP client session to initialize a connection, discover tools, and invoke a selected tool.
- Validate tool results and route failures to a safe fallback pipeline.
- Apply catalog versioning, dependency, and deprecation metadata to tool selection.

> **Important**: Azure Container Apps and Log Analytics are billable. Complete the local protocol tasks first, and run `azd down --purge` immediately after lab completion to save on Azure costs.

> **Important - Docker is required:** Install and start [Docker Desktop](https://docs.docker.com/desktop/) on Windows/macOS or Docker Engine on Linux. Local MCP exercises run in Python, but `azd deploy` builds the container locally from the lab's `Dockerfile`. Provisioning alone does not satisfy this requirement.

## Task 1: Prepare the lab

You need [Python 3.11 or later](https://www.python.org/downloads/), [Git](https://git-scm.com/downloads), [Visual Studio Code](https://code.visualstudio.com/download), [Docker Desktop or Docker Engine](https://docs.docker.com/get-docker/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), and the VS Code [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep) extensions. For Azure work, you need a precreated resource group or permission to create one, plus permission to create a Log Analytics workspace, a Container Apps environment, and a Container App. Use only the synthetic assets supplied with this lab.

**Clone and open the repository**

1. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

3. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\06-northwind-health-mcp-tools
az version
azd version
python --version
docker --version
docker info
az account show --output table
```

4. Confirm that `docker --version` finds the client and `docker info` reaches the running engine.
5. If `docker info` fails on Windows or macOS, start Docker Desktop and wait until the engine is ready before continuing.

6. Use your signed-in Azure identity. Every remote client obtains an access token with `DefaultAzureCredential`; the client permits an omitted token only for `localhost` or `127.0.0.1`.
7. Do not add API keys, passwords, patient identifiers, or access tokens to `.env`.

**Architecture checkpoint**

Review `infra/main.bicep`, `azure.yaml`, the JSON assets, and these implementation surfaces:

| File | Learner implementation |
|---|---|
| `src/server.py` | Complete both MCP tool handlers and safe fallback responses. |
| `src/client.py` | Initialize the MCP session, discover tools, and invoke the selected tool. |
| `src/catalog.py` | Filter discovered tools by active lifecycle and matching required major version. |
| `src/result_validation.py` | Validate returned structured content against the catalog schema. |

Before continuing, confirm that the request path is `MCP discovery -> catalog selection -> tool invocation -> result validation -> governed fallback`, and distinguish the local checks from the deployed Container App checks.

## Task 2: Build the virtual environment

1. From the lab root, create and activate the virtual environment:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

## Task 3: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Implement drug-interaction lookup**

1. In `src/server.py`, find the exact marker `# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.`

2. Replace only the `raise NotImplementedError` line beneath it with:

```python
  requested_pair = sorted((drug_a.strip().casefold(), drug_b.strip().casefold()))
  for record in _load_json("drug_interactions.json"):
    stored_pair = sorted(str(drug).casefold() for drug in record["drugs"])
    if requested_pair == stored_pair:
      _log_invocation("lookup_drug_interaction", correlation_id, "ok")
      return {
        "status": "ok",
        "severity": record["severity"],
        "guidance": record["guidance"],
      }
  _log_invocation("lookup_drug_interaction", correlation_id, "not_found")
  return {"status": "not_found", "reason": "pair_not_in_synthetic_catalog"}
```

Sorting makes the pair order-independent. The tool logs no medication values, and an unknown pair returns no invented guidance.

**Implement capacity lookup**

3. In `src/server.py`, find the exact marker `# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.`

4. Replace only the `raise NotImplementedError` line beneath it with:

```python
  normalized_site = site.strip().casefold()
  for record in _load_json("appointment_capacity.json"):
    if str(record["site"]).casefold() == normalized_site and record["date"] == date:
      _log_invocation("get_appointment_capacity", correlation_id, "ok")
      return {"status": "ok", **record}
  _log_invocation("get_appointment_capacity", correlation_id, "not_found")
  return {"status": "not_found", "reason": "capacity_not_in_synthetic_catalog"}
```

The signature has no patient identifier, so patient data stays outside the protocol boundary.

**Select a governed tool**

5. In `src/catalog.py`, find the exact marker `# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.`

6. Replace only the `raise NotImplementedError` line beneath it with:

```python
  candidates = [
    entry
    for entry in load_catalog()["tools"]
    if entry["name"] == requested_name
    and entry["name"] in discovered_names
    and entry["lifecycle"] == "active"
    and int(entry["version"].split(".", maxsplit=1)[0]) == required_major
  ]
  if not candidates:
    raise ValueError(
      f"No active discovered {requested_name!r} tool supports major {required_major}"
    )
  return min(candidates, key=lambda entry: entry["p95_latency_ms"])
```

Protocol discovery proves availability; catalog metadata adds lifecycle, compatibility, and latency policy.

**Discover tools through MCP**

7. In `src/client.py`, find the exact marker `# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.`

8. Replace only the `raise NotImplementedError` line beneath it with:

```python
  async with streamablehttp_client(server_url, headers=headers) as (read, write, _):
    async with ClientSession(read, write) as session:
      await session.initialize()
      discovered = await session.list_tools()
      return [
        {
          "name": tool.name,
          "description": tool.description,
          "inputSchema": tool.inputSchema,
        }
        for tool in discovered.tools
      ]
```

Initialization negotiates the MCP session before `tools/list`, and the returned protocol schemas keep discovery observable.

**Invoke the selected tool**

9. In `src/client.py`, find the exact marker `# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.`

10. Replace only the `raise NotImplementedError` line beneath it with:

```python
  async with streamablehttp_client(server_url, headers=headers) as (read, write, _):
    async with ClientSession(read, write) as session:
      await session.initialize()
      discovered = await session.list_tools()
      catalog_entry = select_compatible_tool(
        {tool.name for tool in discovered.tools},
        request["tool"],
        int(request["required_major"]),
      )
      try:
        tool_result = await session.call_tool(
          catalog_entry["name"], arguments=request["arguments"]
        )
      except httpx.HTTPError:
        return dict(catalog_entry["fallback"])

      structured = getattr(tool_result, "structuredContent", None)
      if structured is None:
        structured = getattr(tool_result, "structured_content", None)
      if structured is None and tool_result.content:
        structured = json.loads(tool_result.content[0].text)
      if not isinstance(structured, dict):
        return dict(catalog_entry["fallback"])
      return validate_or_fallback(structured, catalog_entry)
```

The client prefers structured MCP content, tolerates both SDK field spellings, and uses text decoding only as a compatibility fallback.

**Enforce the output contract**

11. In `src/result_validation.py`, find the exact marker `# LAB PLACEHOLDER 6: Replace this line with the Task 6 sample.`

12. Replace only the `raise NotImplementedError` line beneath it with:

```python
  try:
    validate(instance=result, schema=catalog_entry["output_schema"])
  except ValidationError:
    return dict(catalog_entry["fallback"])
  return result
```

Only schema violations become the governed fallback. Programming and configuration errors remain visible.

## Task 4: Run the solution

1. Start the MCP server in one terminal:

```powershell
python -m src.server
```

2. Open a second terminal at the lab root and activate `.venv` there; on macOS/Linux use `source .venv/bin/activate` before discovery.
3. Discover the server's tools:

```powershell
. ./.venv/Scripts/Activate.ps1
python -m src.main discover --server-url http://127.0.0.1:8000/mcp
```

4. Keep the server terminal running throughout local validation.

5. Invoke each tool through the MCP client:

```powershell
python -m src.main call --server-url http://127.0.0.1:8000/mcp --request assets/request-drug.json
python -m src.main call --server-url http://127.0.0.1:8000/mcp --request assets/request-capacity.json
```

**Understand the output**

Discovery must return `lookup_drug_interaction` and `get_appointment_capacity`, each with `name`, `description`, and `inputSchema`. These contracts come from an initialized MCP session, not just the local catalog.

The drug request selects active major version 1, invokes the synthetic atorvastatin/clarithromycin lookup, and validates against the catalog's `output_schema`:

```json
{
  "status": "ok",
  "severity": "high",
  "guidance": "Synthetic record: pause automated workflow and consult a pharmacist."
}
```

`ok` means a catalog match passed the schema, not clinical approval. Severity and guidance come from the synthetic asset. The response excludes medication arguments and correlation ID; server logs retain only tool name, correlation ID, and status, never medication values or credentials.

The capacity request uses the same governed path:

```json
{
  "status": "ok",
  "site": "northwind-central",
  "date": "2026-09-28",
  "available_slots": 4
}
```

Capacity is synthetic: the schema requires status, site, date, and a nonnegative integer slot count. No appointment is reserved or scheduling system called.

An unknown pair returns handler-level `not_found`, fails the success schema, and becomes the governed fallback:

```json
{
  "status": "unavailable",
  "reason": "result_validation_failed",
  "fallback": "consult_pharmacist"
}
```

The client must not treat absent or invalid data as clinical evidence. Capacity lookup uses `contact_scheduling_desk` as its corresponding fallback. Session and catalog metadata are internal; the CLI prints results and the server logs invocation events.

## Task 5: Validate the local implementation

**Validate the local MCP server**

1. With the server running, execute the local checks:

```powershell
python scripts/preflight.py
python -m src.main discover --server-url http://127.0.0.1:8000/mcp
python -m src.main call --server-url http://127.0.0.1:8000/mcp --request assets/request-drug.json
```

2. Verify the discovery, drug, capacity, and scrubbed-log contracts from Task 4. In `assets/request-drug.json`, temporarily set `arguments.drug_a` to `synthetic-unknown-drug`, rerun the local drug call above, and expect `status: unavailable` with `fallback: consult_pharmacist`. Restore `arguments.drug_a` to `atorvastatin` before continuing.

## Task 6: Deploy the Azure resources

**Set the deployment values**

1. Review the cost warning.
2. Sign in interactively and create an isolated environment.

`azd` provisions hosting and monitoring resources; deployment of the completed MCP server is separate.

3. Set `$azureRegion` to an approved region that supports the required services.
4. Replace the example value `eastus2` if needed.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

**Validate and provision the infrastructure**

5. Run the following commands:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
az login
azd auth login
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab06-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
azd env new lab06-mcp-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
$tenantId = az account show --query tenantId -o tsv
$app = az ad app create --display-name "lab06-mcp-api-$((Get-Random))" | ConvertFrom-Json
$scopeId = [guid]::NewGuid().ToString()
$body = @{ identifierUris = @("api://$($app.appId)"); api = @{ oauth2PermissionScopes = @(@{ adminConsentDescription = 'Call the Northwind MCP lab API'; adminConsentDisplayName = 'Call Northwind MCP API'; id = $scopeId; isEnabled = $true; type = 'User'; userConsentDescription = 'Call the Northwind MCP lab API'; userConsentDisplayName = 'Call Northwind MCP API'; value = 'access_as_user' }) } } | ConvertTo-Json -Depth 8 -Compress
$manifestPath = Join-Path $PWD '.lab06-app-manifest.json'
$body | Set-Content $manifestPath -Encoding utf8
try {
  az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$($app.id)" --headers Content-Type=application/json --body "@$manifestPath"
} finally {
  Remove-Item $manifestPath -ErrorAction SilentlyContinue
}
azd env set MCP_ENTRA_CLIENT_ID $app.appId
azd env set MCP_ENTRA_TENANT_ID $tenantId
azd env set MCP_ENTRA_APP_OBJECT_ID $app.id
azd provision
azd env get-values | Out-File .env -Encoding utf8
```

6. If provisioning fails, inspect the first Azure deployment error. Regional Container Apps availability, Entra application permissions, role assignments, or an invalid environment setting are common causes.
7. Correct the cause, then run `azd provision` again.

**Verify the generated environment**

8. After provisioning succeeds, validate that `.env` includes `MCP_ENTRA_CLIENT_ID`, `MCP_ENTRA_TENANT_ID`, `MCP_SERVER_URL`, and `MCP_TOKEN_SCOPE`. These values allow the completed client to authenticate to the deployed MCP endpoint.
9. Do not add API keys, passwords, patient identifiers, or access tokens to `.env`.

The remote endpoint uses Microsoft Entra authentication. Its bootstrap image listens on port 80; Task 7 changes ingress to port 8000 before deploying the MCP server.

10. Have an administrator grant the signed-in lab users consent to the API scope before remote MCP validation.
11. Do not send credentials in MCP arguments or log payloads.

> **Network access for this lab:** The Bicep template enables native external ingress on the Container App so the local client can validate the deployed MCP endpoint. Microsoft Entra authentication still protects the endpoint. Production environments should use an approved private access path where required.

## Task 7: Validate the deployed MCP server

Remote validation exercises the same protocol contracts; hosting administration is not an additional objective.

1. In the second terminal, confirm that Docker is running.
2. Change ingress from the bootstrap image's port 80 to the MCP server's port 8000, deploy the completed server, and load the endpoint and token scope:

```powershell
docker info
$values = azd env get-values --output json | ConvertFrom-Json
$resourceGroupName = $values.AZURE_RESOURCE_GROUP_NAME
$containerAppName = $values.AZURE_CONTAINER_APP_NAME
az containerapp ingress update `
  --name $containerAppName `
  --resource-group $resourceGroupName `
  --target-port 8000
azd deploy
$env:MCP_SERVER_URL = $values.MCP_SERVER_URL
$env:MCP_TOKEN_SCOPE = $values.MCP_TOKEN_SCOPE
```

The client uses `DefaultAzureCredential` and `MCP_TOKEN_SCOPE` to authenticate.

3. Verify the deployed authentication and identity boundaries before sending an authenticated request:

```powershell
$anonymousStatus = curl.exe -s -o NUL -w "%{http_code}" $env:MCP_SERVER_URL
if ($anonymousStatus -ne '401') { throw "Anonymous request was not rejected: HTTP $anonymousStatus" }
$auth = az containerapp auth show --name $containerAppName --resource-group $resourceGroupName | ConvertFrom-Json
$expectedAudience = "api://$($values.MCP_ENTRA_CLIENT_ID)"
if ($auth.globalValidation.unauthenticatedClientAction -ne 'Return401') { throw 'Anonymous requests are not configured for HTTP 401 rejection' }
if ($auth.identityProviders.azureActiveDirectory.validation.allowedAudiences -notcontains $expectedAudience) { throw 'The configured token audience is incorrect' }
if ($env:MCP_TOKEN_SCOPE -ne "$expectedAudience/.default") { throw 'MCP_TOKEN_SCOPE does not match the protected API audience' }
$managedIdentityPrincipalId = az containerapp identity show --name $containerAppName --resource-group $resourceGroupName --query principalId -o tsv
if ([string]::IsNullOrWhiteSpace($managedIdentityPrincipalId)) { throw 'The Container App managed identity is missing' }
'REMOTE_BOUNDARIES_VALIDATED'
```

Expect `REMOTE_BOUNDARIES_VALIDATED`. These checks prove anonymous rejection, the allowed token audience, the requested scope, and the presence of the workload managed identity. They do not prove that a private network path exists.

4. Do not acquire, paste, or print the token manually.
5. Run discovery and both tool requests against the remote MCP endpoint:

```powershell
python -m src.main discover --server-url $env:MCP_SERVER_URL
python -m src.main call --server-url $env:MCP_SERVER_URL --request assets/request-drug.json
python -m src.main call --server-url $env:MCP_SERVER_URL --request assets/request-capacity.json
```

Compare the remote output with the Task 4 examples. Confirm that discovery returns both tools with their `name`, `description`, and `inputSchema`, and that the drug and capacity requests return the exact synthetic results shown in Task 4. Remote log inspection is not required; you verified the scrubbed-log behavior during local validation in Task 5.

6. If the client reports a consent or authorization error, confirm that an administrator granted the signed-in user access to the API scope created during provisioning. If `MCP_TOKEN_SCOPE` is missing for a non-local URL, the client must fail with `MCP_TOKEN_SCOPE is required for a remote MCP server` before opening an HTTP session.

**Run the final checks**

7. Run the side-effect-free final checks:

```powershell
python scripts/preflight.py
Get-ChildItem src,scripts -Filter *.py -Recurse | ForEach-Object { python -m py_compile $_.FullName }
az bicep build --file infra/main.bicep
```

Expect `Preflight passed` and error-free Python and Bicep compilation. These local checks do not replace the protocol evidence above.

## Optional challenge: Reject an incompatible tool version

Add a second catalog entry with incompatible protocol or schema metadata.

**Expected output:** Selection rejects the entry with a compatibility reason and no tool invocation occurs.

**Failure investigation:** Simulate a dependency timeout and verify bounded retry or circuit-breaker behavior without returning fabricated success evidence.
## Task 8: Review the design

1. Answer these questions:

- Which errors should be retried, and which should immediately return a structured permanent failure?
- What catalog fields are required to support a 90-day deprecation window?
- How would per-user OAuth passthrough change the authorization boundary?
- Which telemetry fields support diagnosis without disclosing clinical inputs?

## Task 9: Clean up

**Remove Azure resources**

1. Delete billable resources and confirm the resource group is removed.

```powershell
$values = azd env get-values --output json | ConvertFrom-Json
$entraAppObjectId = $values.MCP_ENTRA_APP_OBJECT_ID
azd down --purge
if (-not [string]::IsNullOrWhiteSpace($entraAppObjectId)) {
  az ad app delete --id $entraAppObjectId
}
```

2. Confirm that the resource group and the temporary Entra app registration are deleted.
3. Do not retain `.env`, access tokens, or deployment output in source control.

**Deactivate the virtual environment**

4. Stop the local MCP server with **Ctrl+C**.
5. Run this command separately in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

6. Confirm that `(.venv)` no longer appears in any terminal before changing to another lab directory.

## Summary

You implemented and validated local and Entra-authenticated remote MCP discovery, compatibility-aware tool selection, result validation, scrubbed telemetry, and safe fallback behavior.
