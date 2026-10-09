---
lab:
  title: 'Projetar comunicação de agentes em escala empresarial com A2A no Azure'
  description: 'Implemente descoberta A2A isolada por locatário, mensagens JSON-RPC, estado compartilhado no Cosmos DB e trilhas de auditoria de conflitos.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Projetar comunicação de agentes em escala empresarial com A2A no Azure

## Cenário do cliente

A Contoso Capital precisa conectar agentes de pesquisa implantados de forma independente sem endpoints codados. A descoberta deve ser baseada em capacidades, o contexto do locatário nunca deve cruzar limites, o estado compartilhado deve sobreviver a reinicializações e recomendações contraditórias precisam de um registro de resolução durável.

## Cenário do laboratório

Você completará um endpoint compatível com A2A para agent-card e um endpoint de mensagens JSON-RPC, registrará cards no Azure Cosmos DB, roteará por locatário/capacidade/saúde, atualizará o estado de tarefas com ETags e gravará decisões de conflito em um contêiner de auditoria.

<!-- ESPAÇO RESERVADO DO DIAGRAMA DO LAB: Mostrar descoberta com escopo de locatário, roteamento de mensagens A2A, estado de tarefas no Cosmos DB e o caminho de auditoria de conflitos. -->

Ao final deste exercício, você será capaz de:

- Projetar um registro de descoberta A2A e uma política de roteamento dinâmica.
- Persistir estado distribuído compartilhado com concorrência otimista.
- Aplicar isolamento de contexto com escopo de locatário.
- Detectar, resolver e auditar saídas conflitantes de agentes.

> **Importante**: Cosmos DB e a implantação do modelo são cobráveis. Capacidades A2A podem estar em preview; verifique o suporte atual antes do uso em produção. O laboratório usa endpoints HTTP locais e dados sintéticos apenas.

## Tarefa 1: Preparar o laboratório

Use [Python 3.11+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)/[Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install), [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download) e uma subscription autenticada. Você precisa de permissão para criar Foundry, Cosmos DB e atribuições de função no plano de dados. Os exemplos usam a porta local 8000; você pode escolher outra porta livre.

1. Se ainda não fez, clone o [repositório de origem do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork e clone do seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.
3. Pelo terminal do VS Code, valide as ferramentas requeridas, as credenciais e a subscription ativa:

```powershell
cd Allfiles\04-contoso-capital-a2a-communication
az version
azd version
python --version
az account show --output table
```

**Checkpoint de arquitetura**

Revise `infra/main.bicep`, `src/a2a_server.py`, `src/registry.py` e os assets de agent-card fornecidos. Antes de continuar, confirme que:

- o contexto de locatário confiável fornece a chave de partição `/tenantId`;
- o registro de descoberta expira agent cards inativos enquanto o contêiner de auditoria permanece durável;
- ETags protegem atualizações compartilhadas de tarefas;
- uma requisição A2A aceita pode alcançar a invocação do agente no Foundry e produzir uma trace no servidor.

## Tarefa 2: Construir o ambiente virtual

1. Do diretório do laboratório, crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

## Tarefa 3: Implantar os recursos do Azure

Verifique custo e acesso por função antes de provisionar Foundry, Cosmos DB, Application Insights e retenção de Log Analytics de 30 dias. Use um ambiente único e dados de locatário sintéticos. `azd` provisiona a infraestrutura; o servidor A2A e os testes de protocolo rodam localmente.

**Defina os valores de implantação**

1. Defina `$azureRegion` para uma região aprovada que suporte o modelo selecionado.
2. Substitua o valor de exemplo `eastus2` se necessário.
> **Grupo de recursos:** Se seu ambiente de laboratório fornecer um resource group pré-criado, defina `$resourceGroupName` para o seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group exclusivo na sua subscription.

> **Nota:** `AZURE_DEV_USER_AGENT` marca a provisão para atribuição e não é exportado para `.env`. Remova-o depois para evitar marcar comandos não relacionados.

**Validar e provisionar a infraestrutura**

3. Execute os comandos a seguir:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab04-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new lab04
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set FOUNDRY_MODEL_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_CATALOG_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_VERSION 2026-03-17
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

4. Se o provisionamento falhar, inspecione o primeiro erro de implantação do Azure.

Disponibilidade de modelo ou região, disponibilidade do Cosmos DB, cota e permissões de atribuição de função são causas comuns.

5. Corrija a `azd env` ou permissão relevante e então execute `azd provision` novamente.

**Verifique o ambiente gerado**

6. Após o provisionamento bem-sucedido, valide que `.env` inclui `COSMOS_ENDPOINT`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_PROJECT_ID`, `FOUNDRY_MODEL_NAME`, `APPLICATIONINSIGHTS_RESOURCE_ID` e `LOG_ANALYTICS_WORKSPACE_ID`.

A connection string do Application Insights está armazenada na conexão do projeto Foundry e não é gravada em `.env`.

> **Acesso de rede para este laboratório:** O template Bicep habilita acesso de rede público nativo para Foundry e Cosmos DB para que a aplicação local possa alcançar ambos endpoints do plano de dados. Microsoft Entra authentication e Azure RBAC ainda são exigidos. Após a implantação, confirme o acesso público em ambos os recursos e confirme que a ação de rede padrão do Foundry é **Allow**. Ambientes de produção devem usar um design aprovado com selected-network ou private-endpoint.

7. Não adicione uma key, connection string ou token do Cosmos em `.env`.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada snippet fornecido para seu local de placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua apenas a linha ou bloco incompleto indicado e preserve a indentação ao redor.

**Registrar um agent card pertencente ao locatário**

1. Abra `src/registry.py` e encontre **LAB PLACEHOLDER 1** em `Registry.register`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete Registry.register in Task 1")
```

2. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

```python
required_fields = ("id", "url", "capabilities")
if any(not card.get(field) for field in required_fields):
  raise ValueError("Agent card requires id, url, and capabilities")
if not isinstance(card["capabilities"], list):
  raise ValueError("Agent card capabilities must be a list")

entry = {
  **card,
  "tenantId": tenant_id,
  "health": "healthy",
  "heartbeat": int(time.time()),
  "ttl": int(os.getenv("REGISTRY_TTL_SECONDS", "300")),
}
return self.registry.upsert_item(entry)
```

O chamador confiável fornece `tenant_id`; um card não pode escolher sua própria partição. Campos de health e heartbeat tornam instâncias obsoletas filtráveis antes que o TTL do contêiner remova registros abandonados.

**Descobrir um agente saudável e recente**

3. Encontre **LAB PLACEHOLDER 2** em `Registry.discover`:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete Registry.discover in Task 2")
```

4. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

```python
cutoff = int(time.time()) - int(os.getenv("HEARTBEAT_MAX_AGE_SECONDS", "120"))
query = """
SELECT * FROM c
WHERE c.tenantId = @tenant
  AND ARRAY_CONTAINS(c.capabilities, @capability)
  AND c.health = "healthy"
  AND c.heartbeat >= @cutoff
"""
parameters = [
  {"name": "@tenant", "value": tenant_id},
  {"name": "@capability", "value": capability},
  {"name": "@cutoff", "value": cutoff},
]
candidates = list(
  self.registry.query_items(
    query=query,
    parameters=parameters,
    partition_key=tenant_id,
    enable_cross_partition_query=False,
  )
)
return sorted(candidates, key=lambda item: float(item.get("load", 1.0)))[:1]
```

Com escopo de partição, a descoberta parametrizada filtra por capability, health e freshness do heartbeat, então retorna o agente elegível com menor carga. O filtro de freshness vale antes da exclusão por TTL.

**Atualizar estado compartilhado da tarefa com ETags**

5. Encontre **LAB PLACEHOLDER 3** em `Registry.update_task`:

```python
# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
raise NotImplementedError("Complete Registry.update_task in Task 3")
```

6. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

```python
for _ in range(3):
  try:
    current = self.tasks.read_item(item=task_id, partition_key=tenant_id)
  except exceptions.CosmosResourceNotFoundError:
    initial = {
      "id": task_id,
      "tenantId": tenant_id,
      "contributions": {agent_id: contribution},
      "updatedAt": int(time.time()),
    }
    try:
      return self.tasks.create_item(initial)
    except exceptions.CosmosResourceExistsError:
      continue

  current.setdefault("contributions", {})[agent_id] = contribution
  current["updatedAt"] = int(time.time())
  try:
    return self.tasks.replace_item(
      item=current["id"],
      body=current,
      etag=current["_etag"],
      match_condition=MatchConditions.IfNotModified,
    )
  except exceptions.CosmosHttpResponseError as exc:
    if exc.status_code != 412:
      raise

raise RuntimeError("Task update failed after three ETag attempts")
```

A criação lida com escritores concorrentes sem sobrescrevê-los. Atualizações posteriores usam ETags; um 412 aciona uma releitura e reaplica apenas a contribuição do chamador, com limite de três tentativas.

**Resolver e auditar saídas conflitantes**

7. Encontre **LAB PLACEHOLDER 4** em `Registry.resolve_and_audit`:

```python
# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
raise NotImplementedError("Complete resolve_and_audit in Task 4")
```

8. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

```python
candidates = conflict.get("candidates", [])
if len(candidates) < 2:
  raise ValueError("A conflict requires at least two candidates")

priority = {"compliance": 3, "risk": 2, "analysis": 1}
highest = max(priority.get(item.get("role", ""), 0) for item in candidates)
winners = [
  item
  for item in candidates
  if priority.get(item.get("role", ""), 0) == highest
]
if highest == 0 or len(winners) != 1:
  resolution = "escalated"
  chosen_agent = None
else:
  resolution = "priority"
  chosen_agent = winners[0]["agent_id"]

audit_record = {
  "id": str(uuid.uuid4()),
  "tenantId": tenant_id,
  "taskId": conflict["task_id"],
  "timestamp": int(time.time()),
  "resolution": resolution,
  "chosenAgent": chosen_agent,
  "candidates": [
    {"agent_id": item["agent_id"], "role": item["role"]}
    for item in candidates
  ],
}
self.audit.create_item(audit_record)
return {
  "status": resolution,
  "chosen_agent": chosen_agent,
  "audit_id": audit_record["id"],
}
```

Compliance tem precedência sobre risk, que por sua vez tem precedência sobre analysis; empates entre vencedores ou ausência de prioridade reconhecida escalonam. A auditoria retém participantes e a decisão, não o conteúdo do modelo, endpoints ou credenciais.

**Lidar com uma mensagem JSON-RPC com escopo de locatário**

9. Abra `src/a2a_server.py` e encontre **LAB PLACEHOLDER 5** em `handle_message`:

```python
# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.
raise NotImplementedError("Complete handle_message in Task 5")
```

10. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

```python
if payload.get("jsonrpc") != "2.0" or payload.get("method") != "message/send":
  raise ValueError("Expected JSON-RPC 2.0 method message/send")
if "id" not in payload:
  raise ValueError("JSON-RPC request id is required")

params = payload.get("params", {})
tenant_id = params.get("tenantId")
trusted_tenant = os.getenv("A2A_TENANT_ID", "contoso")
if tenant_id != trusted_tenant:
  raise ValueError("Tenant is unavailable")

parts = params.get("message", {}).get("parts", [])
text = "\n".join(
  str(part.get("text", ""))
  for part in parts
  if part.get("kind") == "text" and part.get("text")
).strip()
if not text:
  raise ValueError("At least one text message part is required")

project = AIProjectClient(
  endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
  credential=DefaultAzureCredential(),
)
agent = project.agents.create_version(
  agent_name=CARD["name"],
  definition=PromptAgentDefinition(
    model=os.environ["FOUNDRY_MODEL_NAME"],
    instructions=(
      "Analyze only synthetic portfolio risk. State assumptions, "
      "identify missing evidence, and do not provide investment advice."
    ),
  ),
)
openai = project.get_openai_client(agent_name=agent.name)
response = openai.responses.create(
  input=text,
)
return {
  "jsonrpc": "2.0",
  "id": payload["id"],
  "result": {
    "tenantId": tenant_id,
    "response_id": response.id,
    "text": extract_text(response),
  },
}
```

O endpoint valida a forma do protocolo antes de fazer uma chamada ao modelo e compara o contexto da mensagem com a configuração local confiável do locatário. O cliente OpenAI vinculado ao agente usa o endpoint dedicado do agente, então a requisição de resposta não carrega um `agent_reference` de endpoint compartilhado. Em produção, middleware autenticado derivaria esse valor de locatário a partir de claims de identidade verificadas em vez do JSON da requisição.

**Verificar o código completado**

11. Execute verificações sem efeitos colaterais antes de iniciar o servidor local ou acessar o Azure:

```powershell
python -m py_compile src/main.py src/registry.py src/a2a_server.py scripts/preflight.py
python scripts/preflight.py
```

12. Confirme que o preflight reporta quatro linhas `PASS`, que ambos os arquivos iniciais retêm todas as cinco marcações `LAB PLACEHOLDER` e que nenhum dos arquivos contém `NotImplementedError`.

## Tarefa 5: Executar a solução

Use dois terminais na raiz do laboratório, cada um com o ambiente virtual ativado. Terminal 1 executa Uvicorn; Terminal 2 executa clientes e validação. Variáveis de ambiente temporárias são locais ao terminal. Mantenha o Uvicorn em execução até a Tarefa 7.

**Iniciar o servidor A2A**

1. No **Terminal 1**, ative o ambiente, registre o card e inicie o servidor:

```powershell
. ./.venv/Scripts/Activate.ps1
$port = 8000
$env:A2A_TENANT_ID = 'contoso'
$env:A2A_BASE_URL = "http://127.0.0.1:$port"
python -m src.main register --card assets/risk-agent-card.json
python -m uvicorn src.a2a_server:app --host 127.0.0.1 --port $port
```

2. Aguarde `Uvicorn running on http://127.0.0.1:8000` (ou a porta escolhida). Se estiver usando outra porta, atualize todas as URLs dos clientes abaixo.

**Executar os comandos do cliente A2A**

3. Abra o **Terminal 2** em `Allfiles\04-contoso-capital-a2a-communication`. Se a ativação falhar porque o ambiente está ausente, execute `./scripts/setup.ps1` no Windows ou `bash scripts/setup.sh` no macOS/Linux antes de continuar.
4. Ative o ambiente com `. ./.venv/Scripts/Activate.ps1`. No macOS/Linux, use `source .venv/bin/activate` em vez disso. Então execute os comandos do cliente:

```powershell
. ./.venv/Scripts/Activate.ps1
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/.well-known/agent-card.json
python -m src.main discover --tenant contoso --capability risk-analysis
python -m src.main send --url http://127.0.0.1:8000/a2a --message assets/a2a-request.json
```

**Verificar as respostas**

5. Compare a saída com estes critérios:

| Operação | Evidência esperada |
|---|---|
| `register` (Terminal 1) | `id: risk-east-v1`, `tenantId: contoso`, `health: healthy`, `ttl: 300`, e um inteiro recente `heartbeat`. Campos de sistema do Cosmos como `_etag` variam. |
| HTTP access log (Terminal 1) | `/`, `/.well-known/agent-card.json`, e `/a2a` retornam `200 OK`. Inspecione bodies no Terminal 2; sucesso HTTP sozinho é insuficiente. |
| Readiness | `status: ready` e os caminhos de endpoint de agent-card e message. |
| Agent card | `name: contoso-risk-agent` e `url: http://127.0.0.1:8000/a2a`; sem endpoint, key ou token do Cosmos ou Foundry. |
| Discovery | Um documento selecionado para `contoso`, com `health: healthy` e capability `risk-analysis`. |
| Send | JSON-RPC `2.0`, `id: request-001`, `result.tenantId: contoso`, um `result.response_id` preenchido, e texto sintético de portfolio-risk. |

6. Se a descoberta retornar um array vazio, execute `python -m src.main register --card assets/risk-agent-card.json` novamente no Terminal 2 e tente novamente imediatamente. Registros ficam inelegíveis após 120 segundos sem heartbeat.

As ETags das Tarefas e `audit_id` são geradas pelas verificações de estado compartilhado abaixo, não por esses comandos iniciais.

## Tarefa 6: Validar a implementação

1. Mantenha o servidor Uvicorn em execução no **Terminal 1**.
2. Execute todos os comandos de validação no **Terminal 2**, a partir da raiz do laboratório com `(.venv)` visível no prompt:

A verificação de sintaxe é local; os dois próximos comandos chamam o Uvicorn.

```powershell
python -m py_compile src/main.py src/registry.py src/a2a_server.py scripts/preflight.py
Invoke-RestMethod http://127.0.0.1:8000/.well-known/agent-card.json
python -m src.main send --url http://127.0.0.1:8000/a2a --message assets/a2a-request.json
```

3. Confirme que o comando de sintaxe retorna ao prompt sem erro, a requisição de agent-card mostra `contoso-risk-agent` e o comando `send` retorna JSON-RPC `2.0` com `id: "request-001"` e um `result.response_id` preenchido.

**Exercitar estado compartilhado durável e auditoria de conflitos**

4. Continue no **Terminal 2** enquanto o Terminal 1 mantém o servidor em execução.

O teste a seguir acessa o Cosmos DB diretamente através de `DefaultAzureCredential`, não através do Uvicorn.

5. Execute estas checagens primeiro:

```powershell
Test-Path .env
Get-Content .env | Select-String '^COSMOS_(ENDPOINT|DATABASE_NAME)='
az account show --output table
```

`Test-Path` deve retornar `True`, e o próximo comando deve exibir linhas `COSMOS_ENDPOINT` e `COSMOS_DATABASE_NAME` preenchidas.

6. Se `.env` estiver ausente ou qualquer valor vazio, execute `azd env get-values | Out-File .env -Encoding utf8` a partir da raiz do laboratório antes de continuar.
7. Confirme que `az account show` exibe a conta usada para provisionar o laboratório.

8. Execute todo o bloco, incluindo `@'` e `'@ | python -`, para passar o script Python ao ambiente ativo:

```powershell
@'
import os
from pathlib import Path

from azure.core import MatchConditions
from azure.cosmos import exceptions
from dotenv import load_dotenv
from src.registry import Registry

load_dotenv(Path.cwd() / ".env")
if not os.getenv("COSMOS_ENDPOINT"):
  raise RuntimeError("COSMOS_ENDPOINT is missing from the lab-root .env file")

registry = Registry()
first = registry.update_task("contoso", "task-001", "risk-agent", {"status": "review"})
stale = registry.tasks.read_item(item="task-001", partition_key="contoso")
second = registry.update_task("contoso", "task-001", "compliance-agent", {"status": "hold"})
stale["stale_writer"] = "must-not-persist"
try:
  registry.tasks.replace_item(
    item=stale["id"],
    body=stale,
    etag=stale["_etag"],
    match_condition=MatchConditions.IfNotModified,
  )
  raise AssertionError("The stale ETag write unexpectedly succeeded")
except exceptions.CosmosAccessConditionFailedError as exc:
  print("stale_write_rejected:", exc.status_code)
recovered = registry.update_task(
  "contoso", "task-001", "supervisor-agent", {"status": "conflict-observed"}
)
decision = registry.resolve_and_audit("contoso", {
  "task_id": "task-001",
  "candidates": [
    {"agent_id": "risk-agent", "role": "risk"},
    {"agent_id": "compliance-agent", "role": "compliance"},
  ],
})
print("first_etag:", first["_etag"])
print("second_etag:", second["_etag"])
print("recovered_etag:", recovered["_etag"])
print("decision:", decision)
'@ | python -
```

O script captura uma versão da tarefa, avança o documento com um segundo escritor, prova que o Cosmos DB rejeita a substituição condicional obsoleta com HTTP 412, então usa o caminho normal de merge do laboratório a partir de uma leitura fresca e persiste a decisão determinística de conflito em `audit`.

9. No Terminal 2, confirme que `stale_write_rejected: 412` aparece e que `first_etag`, `second_etag` e `recovered_etag` estão preenchidos e são diferentes entre si.

O campo `stale_writer` não deve persistir. `supervisor-agent` demonstra recuperação após a escrita obsoleta rejeitada; a implementação A2A em si permanece inalterada.

O valor `decision` deve conter `status: "priority"`, `chosen_agent: "compliance-agent"` e um UUID `audit_id` preenchido.

10. Salve o `audit_id` impresso para a verificação no portal.

11. No Terminal 2, leia a tarefa a partir de um novo processo Python para verificar persistência além do primeiro processo:

```powershell
@'
import os
from pathlib import Path

from dotenv import load_dotenv
from src.registry import Registry

load_dotenv(Path.cwd() / ".env")
if not os.getenv("COSMOS_ENDPOINT"):
  raise RuntimeError("COSMOS_ENDPOINT is missing from the lab-root .env file")

registry = Registry()
task = registry.tasks.read_item(item="task-001", partition_key="contoso")
print("task_id:", task["id"])
print("tenant_id:", task["tenantId"])
print("contributions:", task["contributions"])
print("current_etag:", task["_etag"])
'@ | python -
```

12. Confirme que `task_id` é `task-001`, `tenant_id` é `contoso`, `contributions` contém `risk-agent`, `compliance-agent` e `supervisor-agent`, e que nenhum campo `stale_writer` existe.

13. No [portal do Foundry](https://ai.azure.com), abra o projeto provisionado e confirme uma versão atual `contoso-risk-agent`.
14. Selecione **Agentes (Agents)** > **Traces (Traces)**.
15. Defina o intervalo de tempo para incluir a requisição válida da Contoso.
16. Procure pelo valor `result.response_id` impresso pelo comando `send`.
17. Abra a trace correspondente e confirme o nome do agente, versão, operação de resposta bem-sucedida e o tempo.
18. No portal do Azure, abra a conta provisionada do Cosmos DB e selecione **Explorador de Dados (Data Explorer)** > **agent-ecosystem** > **registry** > **Itens (Items)**.

O contêiner registry deliberadamente deleta cards inativos após cinco minutos porque seu TTL padrão é de 300 segundos.

19. Se **Itens (Items)** estiver vazio, execute o seguinte comando no Terminal 2 e então selecione **Atualizar (Refresh)** em Explorador de Dados (Data Explorer) imediatamente:

   ```powershell
   python -m src.main register --card assets/risk-agent-card.json
   ```

20. Abra `risk-east-v1` e confirme seu `tenantId`, health, heartbeat, TTL e A2A URL.

Os contêineres duráveis `tasks` e `audit` usam TTL `-1`, então seus documentos permanecem até serem excluídos explicitamente.

21. Selecione **Explorador de Dados (Data Explorer)** > **agent-ecosystem** > **tasks** > **Itens (Items)**.
22. Abra `task-001` e confirme que `contributions` contém `risk-agent`, `compliance-agent` e `supervisor-agent`, e que `stale_writer` está ausente.

Seu `_etag` atual deve combinar com `recovered_etag` até que outra escrita altere o documento.

23. Selecione **Explorador de Dados (Data Explorer)** > **agent-ecosystem** > **audit** > **Itens (Items)**.
24. Encontre o item cujo `id` corresponda ao `audit_id` impresso; confirme que `resolution` é `priority` e `chosenAgent` é `compliance-agent`.

**Testar rejeição entre locatários (cross-tenant)**

25. Mantenha o Uvicorn em execução no Terminal 1.
26. No Terminal 2, crie uma cópia temporária da requisição fornecida, altere seu request ID e tenant com o suporte JSON do PowerShell, e envie-a:

```powershell
$request = Get-Content assets/a2a-request.json -Raw | ConvertFrom-Json
$request.id = 'request-fabrikam-001'
$request.params.tenantId = 'fabrikam'
$request | ConvertTo-Json -Depth 10 | Set-Content artifacts-a2a-request-fabrikam.json -Encoding utf8
python -m src.main send --url http://127.0.0.1:8000/a2a --message artifacts-a2a-request-fabrikam.json
```

27. Confirme que o Terminal 2 imprime este corpo de erro e nenhum `response_id`:

```json
{
  "detail": "Tenant is unavailable"
}
```

28. Confirme que o Terminal 1 registra `POST /a2a` com `400 Bad Request`.
29. Confirme que a requisição rejeitada não cria uma trace no Foundry nem retorna um resultado do Cosmos DB entre locatários.
30. Remova a requisição temporária após a verificação:

```powershell
Remove-Item artifacts-a2a-request-fabrikam.json
```

Traces do Foundry provam chamadas aceitas ao modelo, não validação local de descoberta, JSON-RPC, checagens de locatário, atualizações com ETag ou resolução de conflitos. Use evidências HTTP e Cosmos DB para esses limites. Permita alguns minutos para ingestão de trace. Tracing do lado do cliente, KQL, amostragem e alertas são cobertos no Lab 13.

## Desafio opcional: Resolver uma atualização concorrente

Envie duas atualizações sintéticas com o mesmo ETag inicial mas valores propostos diferentes.

**Saída esperada:** Exatamente uma atualização deve ter sucesso, uma deve retornar uma decisão de conflito, e a evidência de auditoria deve registrar ambas as versões propostas sem expor contexto de locatário não relacionado.

**Investigação de falha:** Envie um ETag obsoleto e trace a rejeição através da validação de protocolo, acesso ao estado, tratamento de conflitos e logging de auditoria.

## Tarefa 7: Revisar o design

Registre respostas breves:

- Por que a propriedade do locatário vem do chamador confiável em vez do agent card?
- Por que o registro de descoberta pode expirar enquanto o contêiner de auditoria permanece durável?
- Como ETags impedem que um agente sobrescreva silenciosamente a contribuição de outro agente?
- Quais decisões de conflito devem permanecer determinísticas em vez de serem delegadas a um agente?

## Tarefa 8: Limpeza

**Remover recursos do Azure**

1. Pare o Uvicorn no Terminal 1 pressionando **Ctrl+C**.
2. Execute os seguintes comandos em qualquer um dos terminais:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge --force
Remove-Item Env:AZURE_DEV_USER_AGENT
```

**Desativar o ambiente virtual**

3. Execute este comando separadamente no Terminal 1 e no Terminal 2 se `(.venv)` aparecer em seus prompts:

```powershell
deactivate
```

4. Confirme que `(.venv)` não aparece mais em nenhum dos terminais antes de mudar para outro diretório de laboratório.

## Resumo

Você implementou descoberta e mensagens A2A ativas, estado compartilhado no Cosmos DB, isolamento por locatário, concorrência otimista e auditorias duráveis de conflito.
