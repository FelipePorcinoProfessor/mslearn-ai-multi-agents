---
lab:
  title: 'Construir um ecossistema corporativo de ferramentas MCP'
  description: 'Implemente, descubra, invoque e governe ferramentas clínicas por meio de um servidor e cliente MCP real.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Construir um ecossistema corporativo de ferramentas MCP

## Cenário do cliente

Northwind Health está substituindo integrações específicas de agentes por um catálogo de ferramentas clínicas governado. A primeira versão expõe ferramentas sintéticas de interação medicamentosa e capacidade de agendamento por meio do Model Context Protocol (MCP), registra telemetria segura para correlação e fornece aos clientes um fallback confiável quando uma dependência não está disponível.

## Cenário do laboratório

Você é o desenvolvedor Python responsável pela fronteira MCP. Você completará um servidor FastMCP, implementará um cliente MCP que descobre ferramentas em tempo de execução, selecionará uma ferramenta compatível a partir dos metadados do catálogo, validará os resultados da ferramenta e exercitará o comportamento de fallback. O servidor usa dados sintéticos e não deve ser usado para decisões clínicas.

<!-- DIAGRAMA DO LAB - ESPAÇO RESERVADO: Mostrar descoberta MCP, seleção de catálogo, invocação de ferramenta, validação de resultados e fallback governado. -->

Ao final deste exercício, você será capaz de:

- Construir um servidor MCP personalizado com ferramentas versionadas, erros estruturados e telemetria depurada.
- Usar uma sessão real de cliente MCP para inicializar uma conexão, descobrir ferramentas e invocar uma ferramenta selecionada.
- Validar resultados de ferramentas e direcionar falhas para um pipeline de fallback seguro.
- Aplicar versionamento de catálogo, dependência e metadados de descontinuação à seleção de ferramentas.

> **Importante**: Azure Container Apps e Log Analytics geram cobrança. Complete primeiro as tarefas do protocolo local e execute `azd down --purge` imediatamente após a conclusão do laboratório para economizar custos no Azure.

> **Importante - Docker é necessário:** Instale e inicie [Docker Desktop](https://docs.docker.com/desktop/) no Windows/macOS ou Docker Engine no Linux. Os exercícios MCP locais são executados em Python, mas `azd deploy` constrói o contêiner localmente a partir do `Dockerfile` do laboratório. Somente o provisionamento não satisfaz este requisito.

## Tarefa 1: Preparar o laboratório

Você precisa de [Python 3.11 or later](https://www.python.org/downloads/), [Git](https://git-scm.com/downloads), [Visual Studio Code](https://code.visualstudio.com/download), [Docker Desktop or Docker Engine](https://docs.docker.com/get-docker/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) e as extensões do VS Code [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) e [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep). Para trabalho no Azure, você precisa de um resource group pré-criado ou permissão para criar um, além de permissão para criar um Log Analytics workspace, um Container Apps environment e um Container App. Use apenas os artefatos sintéticos fornecidos com este laboratório.

**Clonar e abrir o repositório**

1. Se ainda não fez, clone o [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.

**Verificar ferramentas e autenticação**

3. Valide as ferramentas necessárias, credenciais e assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\06-northwind-health-mcp-tools
az version
azd version
python --version
docker --version
docker info
az account show --output table
```

4. Confirme que `docker --version` encontra o cliente e `docker info` alcança o engine em execução.
5. Se `docker info` falhar no Windows ou macOS, inicie o Docker Desktop e aguarde até que o engine esteja pronto antes de continuar.

6. Use sua identidade Azure autenticada. Todo cliente remoto obtém um token de acesso com `DefaultAzureCredential`; o cliente permite um token omitido apenas para `localhost` ou `127.0.0.1`.
7. Não adicione chaves de API, senhas, identificadores de pacientes ou tokens de acesso em `.env`.

**Ponto de verificação de arquitetura**

Revise `infra/main.bicep`, `azure.yaml`, os ativos JSON e estas superfícies de implementação:

| Arquivo | Implementação do aluno |
|---|---|
| `src/server.py` | Complete ambos os MCP tool handlers e as respostas de fallback seguras. |
| `src/client.py` | Inicialize a sessão MCP, descubra ferramentas e invoque a ferramenta selecionada. |
| `src/catalog.py` | Filtre as ferramentas descobertas por lifecycle ativo e pelo major version requerido correspondente. |
| `src/result_validation.py` | Valide o conteúdo estruturado retornado contra o schema do catálogo. |

Antes de continuar, confirme que o caminho da requisição é `MCP discovery -> catalog selection -> tool invocation -> result validation -> governed fallback` e distinga as verificações locais das verificações do Container App implantado.

## Tarefa 2: Criar o ambiente virtual

1. A partir do root do laboratório, crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

## Tarefa 3: Implementar a solução

Cada placeholder marca código incompleto. Copie cada trecho fornecido para o local do placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua apenas a linha ou bloco indicado como incompleto e preserve a indentação circundante.

> **Dica:** Depois de copiar e colar cada trecho Python, valide sua indentação em relação à função ou classe circundante antes de executar o código.

**Implemente a busca de interação medicamentosa**

1. Em `src/server.py`, encontre o marcador exato `# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.`

2. Substitua apenas a linha `raise NotImplementedError` logo abaixo por:

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

A ordenação torna a ordem dos pares independente. A ferramenta não registra valores de medicação, e um par desconhecido não retorna orientação inventada.

**Implemente a busca de capacidade**

3. Em `src/server.py`, encontre o marcador exato `# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.`

4. Substitua apenas a linha `raise NotImplementedError` logo abaixo por:

```python
  normalized_site = site.strip().casefold()
  for record in _load_json("appointment_capacity.json"):
    if str(record["site"]).casefold() == normalized_site and record["date"] == date:
      _log_invocation("get_appointment_capacity", correlation_id, "ok")
      return {"status": "ok", **record}
  _log_invocation("get_appointment_capacity", correlation_id, "not_found")
  return {"status": "not_found", "reason": "capacity_not_in_synthetic_catalog"}
```

A assinatura não possui identificador de paciente, portanto dados do paciente permanecem fora da fronteira do protocolo.

**Selecione uma ferramenta governada**

5. Em `src/catalog.py`, encontre o marcador exato `# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.`

6. Substitua apenas a linha `raise NotImplementedError` logo abaixo por:

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

A descoberta do protocolo prova disponibilidade; os metadados do catálogo adicionam lifecycle, compatibilidade e política de latência.

**Descubra ferramentas por meio do MCP**

7. Em `src/client.py`, encontre o marcador exato `# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.`

8. Substitua apenas a linha `raise NotImplementedError` logo abaixo por:

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

A inicialização negocia a sessão MCP antes de `tools/list`, e os schemas de protocolo retornados mantém a descoberta observável.

**Invoque a ferramenta selecionada**

9. Em `src/client.py`, encontre o marcador exato `# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.`

10. Substitua apenas a linha `raise NotImplementedError` logo abaixo por:

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

O cliente prefere conteúdo MCP estruturado, tolera ambas as grafias de campo do SDK e usa decodificação de texto apenas como fallback de compatibilidade.

**Imponha o contrato de saída**

11. Em `src/result_validation.py`, encontre o marcador exato `# LAB PLACEHOLDER 6: Replace this line with the Task 6 sample.`

12. Substitua apenas a linha `raise NotImplementedError` logo abaixo por:

```python
  try:
    validate(instance=result, schema=catalog_entry["output_schema"])
  except ValidationError:
    return dict(catalog_entry["fallback"])
  return result
```

Apenas violações de schema tornam-se o fallback governado. Erros de programação e configuração permanecem visíveis.

## Tarefa 4: Executar a solução

1. Inicie o servidor MCP em um terminal:

```powershell
python -m src.server
```

2. Abra um segundo terminal no root do laboratório e ative `.venv` ali; no macOS/Linux use `source .venv/bin/activate` antes da descoberta.
3. Descubra as ferramentas do servidor:

```powershell
. ./.venv/Scripts/Activate.ps1
python -m src.main discover --server-url http://127.0.0.1:8000/mcp
```

4. Mantenha o terminal do servidor em execução durante toda a validação local.

5. Invoque cada ferramenta por meio do cliente MCP:

```powershell
python -m src.main call --server-url http://127.0.0.1:8000/mcp --request assets/request-drug.json
python -m src.main call --server-url http://127.0.0.1:8000/mcp --request assets/request-capacity.json
```

**Entenda a saída**

A descoberta deve retornar `lookup_drug_interaction` e `get_appointment_capacity`, cada um com `name`, `description` e `inputSchema`. Esses contratos vêm de uma sessão MCP inicializada, não apenas do catálogo local.

A requisição de interação medicamentosa seleciona major version 1 ativo, invoca a busca sintética por atorvastatina/claritromicina e valida contra o `output_schema` do catálogo:

```json
{
  "status": "ok",
  "severity": "high",
  "guidance": "Synthetic record: pause automated workflow and consult a pharmacist."
}
```

`ok` significa que a correspondência do catálogo passou no schema, não aprovação clínica. Severidade e orientação vêm do asset sintético. A resposta exclui argumentos de medicação e o correlation ID; os logs do servidor retêm apenas nome da ferramenta, correlation ID e status, nunca valores de medicação ou credenciais.

A requisição de capacidade usa o mesmo caminho governado:

```json
{
  "status": "ok",
  "site": "northwind-central",
  "date": "2026-09-28",
  "available_slots": 4
}
```

A capacidade é sintética: o schema requer status, site, date e um número inteiro não negativo de vagas. Nenhum agendamento é reservado nem sistema de agendamento é chamado.

Um par desconhecido retorna `not_found` em nível de handler, falha no schema de sucesso e torna-se o fallback governado:

```json
{
  "status": "unavailable",
  "reason": "result_validation_failed",
  "fallback": "consult_pharmacist"
}
```

O cliente não deve tratar dados ausentes ou inválidos como evidência clínica. A busca de capacidade usa `contact_scheduling_desk` como seu fallback correspondente. Metadados de sessão e catálogo são internos; o CLI imprime resultados e o servidor registra eventos de invocação.

## Tarefa 5: Validar a implementação local

**Validar o servidor MCP local**

1. Com o servidor em execução, execute as verificações locais:

```powershell
python scripts/preflight.py
python -m src.main discover --server-url http://127.0.0.1:8000/mcp
python -m src.main call --server-url http://127.0.0.1:8000/mcp --request assets/request-drug.json
```

2. Verifique os contratos de discovery, drug, capacity e scrubbed-log da Tarefa 4. Em `assets/request-drug.json`, temporariamente defina `arguments.drug_a` para `synthetic-unknown-drug`, execute novamente a chamada local de drug acima e espere `status: unavailable` com `fallback: consult_pharmacist`. Restaure `arguments.drug_a` para `atorvastatin` antes de continuar.

## Tarefa 6: Implantar os recursos no Azure

**Defina os valores de implantação**

1. Revise o aviso de custo.
2. Faça login interativamente e crie um ambiente isolado.

`azd` provisiona recursos de hospedagem e monitoramento; a implantação do servidor MCP concluído é separada.

3. Defina `$azureRegion` para uma região aprovada que suporte os serviços necessários.
4. Substitua o valor de exemplo `eastus2` se necessário.
> **Resource group:** Se seu ambiente de laboratório fornecer um resource group pré-criado, defina `$resourceGroupName` para seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group único na sua assinatura.

**Validar e provisionar a infraestrutura**

5. Execute os seguintes comandos:

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

6. Se o provisionamento falhar, inspecione o primeiro erro da implantação do Azure. Disponibilidade regional do Container Apps, permissões da aplicação Entra, atribuições de função ou uma configuração de environment inválida são causas comuns.
7. Corrija a causa e então execute `azd provision` novamente.

**Verifique o environment gerado**

8. Após o provisionamento ser bem-sucedido, valide que `.env` inclui `MCP_ENTRA_CLIENT_ID`, `MCP_ENTRA_TENANT_ID`, `MCP_SERVER_URL` e `MCP_TOKEN_SCOPE`. Esses valores permitem que o cliente completo se autentique no endpoint MCP implantado.
9. Não adicione chaves de API, senhas, identificadores de pacientes ou tokens de acesso em `.env`.

O endpoint remoto usa autenticação Microsoft Entra. Sua imagem bootstrap escuta na porta 80; a Tarefa 7 altera o ingress para a porta 8000 antes de implantar o servidor MCP.

10. Peça a um administrador para conceder consentimento aos usuários do laboratório autenticados para o escopo da API antes da validação remota do MCP.
11. Não envie credenciais em argumentos MCP ou payloads de log.

> **Acesso de rede para este laboratório:** O template Bicep habilita ingress externo nativo no Container App para que o cliente local possa validar o endpoint MCP implantado. A autenticação Microsoft Entra ainda protege o endpoint. Ambientes de produção devem usar um caminho de acesso privado aprovado quando necessário.

## Tarefa 7: Validar o servidor MCP implantado

A validação remota exercita os mesmos contratos de protocolo; administração de hospedagem não é um objetivo adicional.

1. No segundo terminal, confirme que o Docker está em execução.
2. Altere o ingress da imagem bootstrap da porta 80 para a porta 8000 do servidor MCP, implante o servidor concluído e carregue o endpoint e o scope de token:

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

O cliente usa `DefaultAzureCredential` e `MCP_TOKEN_SCOPE` para autenticar.

3. Verifique as fronteiras de autenticação e identidade implantadas antes de enviar uma requisição autenticada:

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

Espere `REMOTE_BOUNDARIES_VALIDATED`. Essas verificações provam rejeição anônima, a audiência permitida do token, o scope solicitado e a presença da workload managed identity. Elas não provam que um caminho de rede privado existe.

4. Não adquira, cole ou imprima o token manualmente.
5. Execute discovery e ambas as requisições de ferramenta contra o endpoint MCP remoto:

```powershell
python -m src.main discover --server-url $env:MCP_SERVER_URL
python -m src.main call --server-url $env:MCP_SERVER_URL --request assets/request-drug.json
python -m src.main call --server-url $env:MCP_SERVER_URL --request assets/request-capacity.json
```

Compare a saída remota com os exemplos da Tarefa 4. Confirme que a discovery retorna ambas as ferramentas com seus `name`, `description` e `inputSchema`, e que as requisições de drug e capacity retornam exatamente os resultados sintéticos mostrados na Tarefa 4. A inspeção remota de logs não é necessária; você já verificou o comportamento de logs depurados durante a validação local na Tarefa 5.

6. Se o cliente relatar um erro de consentimento ou autorização, confirme que um administrador concedeu ao usuário autenticado acesso ao scope da API criado durante o provisionamento. Se `MCP_TOKEN_SCOPE` estiver ausente para uma URL não-local, o cliente deve falhar com `MCP_TOKEN_SCOPE is required for a remote MCP server` antes de abrir uma sessão HTTP.

**Execute as verificações finais**

7. Execute as verificações finais sem efeitos colaterais:

```powershell
python scripts/preflight.py
Get-ChildItem src,scripts -Filter *.py -Recurse | ForEach-Object { python -m py_compile $_.FullName }
az bicep build --file infra/main.bicep
```

Espere `Preflight passed` e compilação sem erros de Python e Bicep. Essas verificações locais não substituem as evidências de protocolo acima.

## Desafio opcional: Rejeitar uma versão de ferramenta incompatível

Adicione uma segunda entrada de catálogo com metadata de protocolo ou schema incompatível.

**Saída esperada:** A seleção rejeita a entrada com uma razão de compatibilidade e nenhuma invocação da ferramenta ocorre.

**Investigação de falha:** Simule um timeout de dependência e verifique comportamento de retry limitado ou circuit-breaker sem retornar evidência de sucesso fabricada.
## Tarefa 8: Revisar o design

1. Responda a estas perguntas:

- Quais erros devem ser re-tentados e quais devem imediatamente retornar uma falha permanente estruturada?
- Quais campos do catálogo são necessários para suportar uma janela de descontinuação de 90 dias?
- Como o passthrough OAuth por usuário alteraria a fronteira de autorização?
- Quais campos de telemetria suportam diagnóstico sem divulgar entradas clínicas?

## Tarefa 9: Limpeza

**Remover recursos do Azure**

1. Exclua recursos faturáveis e confirme que o resource group foi removido.

```powershell
$values = azd env get-values --output json | ConvertFrom-Json
$entraAppObjectId = $values.MCP_ENTRA_APP_OBJECT_ID
azd down --purge
if (-not [string]::IsNullOrWhiteSpace($entraAppObjectId)) {
  az ad app delete --id $entraAppObjectId
}
```

2. Confirme que o resource group e o registro de aplicação Entra temporário foram excluídos.
3. Não retenha `.env`, tokens de acesso ou saída de implantação no controle de versão.

**Desativar o ambiente virtual**

4. Pare o servidor MCP local com **Ctrl+C**.
5. Execute este comando separadamente em cada terminal onde `(.venv)` aparecer no prompt:

```powershell
deactivate
```

6. Confirme que `(.venv)` não aparece mais em nenhum terminal antes de mudar para outro diretório do laboratório.

## Resumo

Você implementou e validou discovery MCP local e remoto autenticado por Entra, seleção de ferramenta sensível à compatibilidade, validação de resultados, telemetria depurada e comportamento de fallback seguro.
