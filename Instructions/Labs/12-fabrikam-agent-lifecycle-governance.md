---
lab:
  title: 'Governar o ciclo de vida de uma topologia de múltiplos agentes'
  description: 'Use as interfaces do Microsoft Foundry e do Cosmos DB para governar versões de agentes, cotas, limites de taxa, medição, rateio de custos e desativação.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Governar o ciclo de vida de uma topologia de múltiplos agentes

## Cenário do cliente

Fabrikam deve governar lançamentos de uma topologia de revisão de código contendo um scanner, um reviewer e um orchestrator. A equipe precisa saber quais versões do Foundry pertencem a cada release lógica, comprovar por que a topologia foi aprovada, controlar o uso por tenant e aposentar versões de componentes obsoletas sem quebrar consumidores.

## Cenário do laboratório

Você irá provisionar um projeto Foundry, model deployment e um registry de uso no Cosmos DB. Você fará inventário de agentes Foundry através de `AIProjectClient`, implementará um gate de release, criará prompt agents versionados para o scanner, reviewer e orchestrator, aplicará controles de uso concretos e executará uma aposentadoria de versão governada.

<!-- PLACEHOLDER DO DIAGRAMA DO LAB: Mostrar promoção da topologia, mapeamento de versão lógica para Foundry, medição de uso e aposentadoria com gate. -->

Ao final deste exercício, você será capaz de:

- Enumerar prompt agents e versões imutáveis do registro do Foundry.
- Promover uma topologia aprovada de três agentes como um release governado.
- Preservar um mapeamento reproduzível entre versões lógicas de topologia e versões Foundry.
- Aplicar atomicamente um limite de 60 requisições por minuto e uma cota mensal de 1.000.000 tokens.
- Medir uso e alocar estimativas em USD para um tenant e centro de custo.
- Aposentar uma versão descartável de prompt-agent através de controles explícitos de governança.

> **Importante**: Use somente as versões sintéticas de prompt-agent criadas durante este exercício. Nunca aponte o comando de aposentadoria para qualquer outro agente ou versão.

## Tarefa 1: Preparar o laboratório

1. Instale [Python 3.10+](https://www.python.org/downloads/), [Azure CLI 2.80+](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI 1.23+](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) e a extensão [`azure.ai.agents` azd](https://learn.microsoft.com/azure/foundry/agents/how-to/install-cli-foundry-extensions).
2. Use uma subscription com disponibilidade do Foundry, permissão para criar uma account e project, permissão para implantar o modelo selecionado e acesso ao projeto que permita gerenciamento de versões de prompt-agent.

3. Se ainda não fez, clone o [repositório de origem do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

4. Abra o repositório clonado no Visual Studio Code.
5. Valide as ferramentas necessárias, credenciais e subscription ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\12-fabrikam-agent-lifecycle-governance
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação arquitetural**

Revise `infra/main.bicep`, o manifesto de versão aprovado, `src/lifecycle.py` e `src/usage.py`, então use esta tabela para localizar cada operação que pode criar, medir ou deletar estado:

| Função | Controle a inspecionar |
|---|---|
| `promote_topology` | `validate_promotion` é executado antes de `create_version`; uma falha de criação posterior remove versões criadas por essa tentativa. |
| `retire_version` | Todos os gates de aposentadoria precedem `delete_version`. O alvo é uma versão Foundry criada neste laboratório, não uma versão lógica da topologia. |
| `enforce_and_meter_usage` | Placeholder 2 se torna um único laço de retry para checagens de taxa/cota, cálculo de cobrança e substituição condicional do medidor. Ele não muta versões do Foundry. |

Antes de continuar, confirme que promoção, medição de uso e aposentadoria têm fronteiras de mutação separadas e controles em modo 'falhar-fechado'.

## Tarefa 2: Construir o ambiente virtual

1. No Windows, execute:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

2. Revise `registry/fabrikam-review-topology-v2.4.0.yaml`. Ele define os três agentes, instruções, versões lógicas, declarações de compatibilidade, resultados de avaliação e evidência de aprovação usados neste exercício.

## Tarefa 3: Implantar recursos do Azure

1. Verifique custos do Foundry e do Cosmos DB e acesso ao plano de dados/lifecycle. `azd` provisiona a infraestrutura; a aplicação cria versões de agente posteriormente.
2. Defina `$azureRegion` para uma região aprovada que suporte o modelo e serviços necessários.
3. Substitua o valor de exemplo `eastus2` se necessário.
> **Grupo de recursos:** Se o ambiente do laboratório fornecer um resource group pré-criado, defina `$resourceGroupName` com seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group único na sua subscription.

> **Observação:** `AZURE_DEV_USER_AGENT` marca o provisionamento para atribuição e não é exportado para `.env`. Remova-o depois para evitar taguear comandos não relacionados.

4. Execute os seguintes comandos:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
$modelDeploymentName = 'gpt-5.4-mini'
$modelName = 'gpt-5.4-mini'
$modelVersion = '2026-03-17'
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab12-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new lab12-agent-lifecycle
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set FOUNDRY_MODEL_NAME $modelDeploymentName
azd env set FOUNDRY_MODEL_CATALOG_NAME $modelName
azd env set FOUNDRY_MODEL_VERSION $modelVersion
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> Observação: Se o provisionamento falhar, inspecione o primeiro erro de implantação do Azure. Disponibilidade de modelo ou região, compatibilidade de extensão, cota e permissões de role-assignment são causas comuns. Corrija a causa e então execute `azd provision` novamente.

5. Após o provisionamento ter sucesso, valide que `.env` inclui o endpoint e ID do projeto Foundry, `FOUNDRY_MODEL_NAME`, `FOUNDRY_MODEL_VERSION`, os valores do endpoint e container do Cosmos DB, e `USAGE_IDENTITY_CLIENT_ID`. O arquivo contém identificadores de recurso e configurações parametrizadas, não chaves ou tokens.
6. Atribua à sua identidade de desenvolvimento o papel mínimo do Foundry necessário para gerenciar prompt agents no escopo do projeto e o papel Cosmos DB Built-in Data Contributor no escopo da conta provisionada.
7. Não adicione chaves, connection strings ou client secrets.

> **Acesso de rede para este laboratório:** O template Bicep habilita o acesso público nativo para Foundry e Cosmos DB para que a aplicação local possa alcançar ambos endpoints do plano de dados. Autenticação Microsoft Entra e Azure RBAC ainda são exigidas. Após a implantação, confirme o acesso público em ambos os recursos e confirme que a ação de rede padrão do Foundry está em **Permitir (Allow)**. Ambientes de produção devem usar um design selected-network aprovado ou private-endpoint.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada trecho fornecido para sua localização de placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco indicado como incompleto e preserve a indentação ao redor.

**Implemente a verificação de promoção**

1. Abra `src/lifecycle.py` e encontre **LAB PLACEHOLDER 1** em `validate_promotion`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete validate_promotion in Task 1")
```

2. Substitua apenas a linha `raise NotImplementedError` logo abaixo por este código:

```python
failures: list[str] = []
evaluation = manifest.get("evaluation") or {}
approval = manifest.get("approval") or {}
compliance = manifest.get("compliance") or {}
topology = manifest.get("topology") or {}
agent_specs = {
  str(item.get("agent_id")): item
  for item in topology.get("agents") or []
}
compatibility = topology.get("compatibility") or {}

if manifest.get("status") != "approved":
  failures.append("manifest status is not approved")
if approval.get("status") != "approved":
  failures.append("approval status is not approved")
if set(agent_specs) != {"scanner", "reviewer", "orchestrator"}:
  failures.append("topology must contain scanner, reviewer, and orchestrator")

try:
  scanner_schema = Version(str(compatibility["scanner_output_schema"]))
  reviewer_requirement = SpecifierSet(
    str(compatibility["reviewer_requires_scanner_schema"])
  )
  if scanner_schema not in reviewer_requirement:
    failures.append("scanner output schema is incompatible with reviewer")
except (KeyError, TypeError, ValueError):
  failures.append("scanner-to-reviewer compatibility evidence is invalid")

try:
  reviewer_version = Version(str(agent_specs["reviewer"]["version"]))
  orchestrator_requirement = SpecifierSet(
    str(compatibility["orchestrator_requires_reviewer_version"])
  )
  if reviewer_version not in orchestrator_requirement:
    failures.append("reviewer version is incompatible with orchestrator")
except (KeyError, TypeError, ValueError):
  failures.append("reviewer-to-orchestrator compatibility evidence is invalid")

try:
  if float(evaluation["precision"]) < float(evaluation["minimum_precision"]):
    failures.append("precision is below its minimum")
except (KeyError, TypeError, ValueError):
  failures.append("precision evidence is missing or invalid")

try:
  if float(evaluation["recall"]) < float(evaluation["minimum_recall"]):
    failures.append("recall is below its minimum")
except (KeyError, TypeError, ValueError):
  failures.append("recall evidence is missing or invalid")

if compliance.get("material_change_assessment") is not True:
  failures.append("material change assessment is missing")
technical_file = str(compliance.get("technical_file_reference", "")).strip()
if not technical_file or not Path(technical_file).is_file():
  failures.append("technical file reference is missing or unavailable")

if failures:
  raise PermissionError("Promotion denied: " + "; ".join(failures))
```

O gate coleta todas as falhas: papéis exigidos, compatibilidade, limiares de avaliação, aprovação explícita de material-change e um arquivo técnico existente. Evidência inválida ou ausente nega a promoção antes da criação de versões.

3. Deixe `promote_topology` inalterado. Ele aplica o gate uma vez para os três agentes e retorna o mapa lógico-para-Foundry das versões.

**Aplicar e medir uso atomicamente**

4. Abra `src/usage.py` e encontre **LAB PLACEHOLDER 2** em `enforce_and_meter_usage`:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete enforce_and_meter_usage in Task 2")
```

5. Substitua apenas a linha `raise NotImplementedError` logo abaixo por este código:

```python
controls = policy["usage_governance"]
token_count = int(request["token_count"])
if token_count <= 0:
  raise ValueError("token_count must be positive")
tenant_id = str(request["tenant_id"])
cost_center = str(request["cost_center"])
if not tenant_id or not cost_center:
  raise ValueError("tenant_id and cost_center are required")

now = datetime.now(timezone.utc)
month = now.strftime("%Y-%m")
rate_window = now.strftime("%Y-%m-%dT%H:%M")
allocation_key = f"{tenant_id}:{cost_center}"
meter_id = f"{allocation_key}:{month}"

for _ in range(max_attempts):
  try:
    meter = container.read_item(item=meter_id, partition_key=allocation_key)
  except CosmosResourceNotFoundError:
    meter = {
      "id": meter_id,
      "allocation_key": allocation_key,
      "tenant_id": tenant_id,
      "cost_center": cost_center,
      "month": month,
      "monthly_tokens": 0,
      "request_count": 0,
      "estimated_charge": 0.0,
      "rate_window": rate_window,
      "rate_window_requests": 0,
    }
    try:
      container.create_item(meter)
    except CosmosResourceExistsError:
      continue
    meter = container.read_item(item=meter_id, partition_key=allocation_key)

  window_requests = (
    int(meter["rate_window_requests"])
    if meter["rate_window"] == rate_window
    else 0
  )
  if window_requests + 1 > int(controls["requests_per_minute"]):
    raise PermissionError("Per-minute request limit exceeded")
  new_monthly_tokens = int(meter["monthly_tokens"]) + token_count
  if new_monthly_tokens > int(controls["monthly_token_quota"]):
    raise PermissionError("Monthly token quota exceeded")

  charge = token_count / 1000 * float(controls["price_per_1000_tokens"])
  meter.update(
    {
      "monthly_tokens": new_monthly_tokens,
      "request_count": int(meter["request_count"]) + 1,
      "estimated_charge": round(
        float(meter["estimated_charge"]) + charge,
        6,
      ),
      "rate_window": rate_window,
      "rate_window_requests": window_requests + 1,
      "last_metered_at": now.isoformat(),
      "currency": str(controls["currency"]),
      "agent_id": str(request["agent_id"]),
      "agent_version": str(request["agent_version"]),
    }
  )
  try:
    saved = container.replace_item(
      item=meter_id,
      body=meter,
      etag=meter["_etag"],
      match_condition=MatchConditions.IfNotModified,
    )
    return {
      "decision": "allow",
      "meter_id": saved["id"],
      "allocation_key": allocation_key,
      "monthly_tokens": saved["monthly_tokens"],
      "monthly_token_quota": int(controls["monthly_token_quota"]),
      "rate_window_requests": saved["rate_window_requests"],
      "requests_per_minute": int(controls["requests_per_minute"]),
      "estimated_charge": saved["estimated_charge"],
      "currency": saved["currency"],
      "metered_at": saved["last_metered_at"],
    }
  except CosmosHttpResponseError as error:
    if error.status_code != 412:
      raise

raise RuntimeError("Usage meter update conflicted too many times")
```

As checagens de limite ocorrem antes da mutação do item. `IfNotModified` vincula a substituição ao `_etag` lido por esta tentativa; um escritor concorrente causa HTTP 412 e um retry ao invés de um incremento perdido. O limite de 60 requisições por minuto UTC, 1.000.000 tokens mensais e USD 0.005 por 1.000 tokens permanecem parametrizados em `policy/promotion-policy.yaml`. Eles são valores de governança da aplicação, não preços de modelo do Azure.

**Verifique o código completo**

6. Execute as seguintes checagens:

```powershell
python -m py_compile src/main.py src/lifecycle.py src/usage.py scripts/preflight.py
python scripts/preflight.py
Get-ChildItem src -Filter *.py | Select-String -Pattern 'NotImplementedError'
```

A checagem preliminar deve terminar com `READY (local)`, e o comando final deve retornar sem correspondências. A configuração de projeto e do Cosmos pode permanecer `INFO` antes do provisionamento.

## Tarefa 5: Executar a solução

1. Registre o inventário do Foundry antes da promoção:

```powershell
python -m src.main inventory
```

Em um projeto novo, espere uma lista vazia. Mantenha o inventário como sua linha de base.

2. Promova a topologia aprovada:

```powershell
$promotion = python -m src.main promote | ConvertFrom-Json
$promotion
$scannerVersion = $promotion.versions.scanner.foundry_version
$reviewerVersion = $promotion.versions.reviewer.foundry_version
$orchestratorVersion = $promotion.versions.orchestrator.foundry_version
```

3. Inspecione o release `2.4.0` e seus mapeamentos lógico-para-Foundry `scanner`, `reviewer` e `orchestrator`:

```powershell
$promotion | ConvertTo-Json -Depth 10
$scannerVersion
$reviewerVersion
$orchestratorVersion
```

As versões lógicas esperadas são `scanner: 1.2.0`, `reviewer: 1.1.0` e `orchestrator: 1.3.0`. Cada valor de versão Foundry deve estar presente; não presuma que corresponda à versão semântica lógica.

4. Faça o inventário do projeto novamente:

```powershell
python -m src.main inventory
```

5. Confirme que todas as três versões capturadas aparecem no inventário. No portal do Foundry, selecione o projeto > **Agentes (Agents)** e compare cada versão com sua variável do PowerShell.

Se a criação de versão falhar, tentativas de promoção fazem reversão na ordem inversa de criação. Quando a reversão tem sucesso, a exceção original de promoção e traceback são preservados. Quando qualquer limpeza falha, o erro no terminal relata tanto o erro de promoção original quanto cada falha exata de limpeza `agent:version`; retenha esses alvos para reconciliação.

**Testar uma promoção negada**

6. Faça um instantâneo do inventário antes de testar negações:

```powershell
$inventoryBeforeDeniedPromotion = python -m src.main inventory | ConvertFrom-Json
$inventoryBeforeDeniedPromotion | ConvertTo-Json -Depth 10
```

7. Em `registry/fabrikam-review-topology-v2.4.0.yaml`, altere `evaluation.precision` de `0.96` para `0.94`, abaixo de `minimum_precision: 0.95`.

8. Tente promover sem sobrescrever `$promotion`:

```powershell
python -m src.main promote
```

Espere `PermissionError: Promotion denied: precision is below its minimum`, antes de qualquer criação de versão.

9. Capture o inventário após a negação:

```powershell
$inventoryAfterDeniedPromotion = python -m src.main inventory | ConvertFrom-Json
$inventoryAfterDeniedPromotion | ConvertTo-Json -Depth 10
```

10. Compare os instantâneos:

```powershell
Compare-Object ($inventoryBeforeDeniedPromotion | ConvertTo-Json -Depth 10) ($inventoryAfterDeniedPromotion | ConvertTo-Json -Depth 10)
```

11. Não espere diferenças. Atualize as três listas de versão no portal para confirmar que não há novas versões, então restaure `precision: 0.96`.
12. Em `topology.compatibility`, altere `reviewer_requires_scanner_schema` de `'>=2.0,<3.0'` para `'>=3.0,<4.0'`.
13. Tente promover:

```powershell
python -m src.main promote
```

14. Espere `PermissionError: Promotion denied: scanner output schema is incompatible with reviewer`.
15. Capture o inventário novamente:

```powershell
$inventoryAfterCompatibilityDenial = python -m src.main inventory | ConvertFrom-Json
```

16. Compare com o instantâneo pré-negação:

```powershell
Compare-Object ($inventoryBeforeDeniedPromotion | ConvertTo-Json -Depth 10) ($inventoryAfterCompatibilityDenial | ConvertTo-Json -Depth 10)
```

17. Não espere diferenças, então restaure `reviewer_requires_scanner_schema` para `'>=2.0,<3.0'`.

**Reconcilie versões deixadas por uma reversão com falha**

Use esta operação administrativa somente para alvos exatos `agent:version` reportados em uma falha de limpeza de promoção. Nunca passe uma versão do mapeamento bem-sucedido `$promotion`.

```powershell
python -m src.main reconcile --orphan-version scanner:<foundry-version> --orphan-version reviewer:<foundry-version> --confirm-delete-orphans
```

O resultado separa `deleted` de `already_absent`. Execute o mesmo comando novamente e confirme que cada alvo passa para `already_absent`, demonstrando reconciliação idempotente. Se alguma exclusão falhar, o erro relata versões já deletadas, versões já ausentes e cada falha de limpeza remanescente para que o comando possa ser tentado novamente com segurança.

**Verificar medição e controles de uso**

18. Execute o comando de medição uma vez:

```powershell
python -m src.main meter
```

Na saída do terminal, confirme:

- `decision` é `allow`.
- `allocation_key` é `synthetic-tenant-a:FAB-SEC-042`.
- `monthly_tokens` aumentou em `1250` e `monthly_token_quota` é `1000000`.
- `rate_window_requests` aumentou em `1` e `requests_per_minute` é `60`.
- `estimated_charge` aumentou em `0.00625`, `currency` é `USD`, e `metered_at` contém um timestamp UTC.

19. Execute-o uma segunda vez:

```powershell
python -m src.main meter
```

Para as primeiras duas requisições dentro de um minuto UTC, espere `monthly_tokens: 2500`, `rate_window_requests: 2` e `estimated_charge: 0.0125`. Caso contrário, compare incrementos de 1250 tokens e USD 0.00625 no mesmo medidor mensal; o contador de taxa reseta quando o minuto UTC muda.

20. No portal do Azure, abra Cosmos DB > **Explorador de Dados (Data Explorer)** > **lifecycle** > **usage-meters** > **Itens (Items)**. Abra o item que começa com `synthetic-tenant-a:FAB-SEC-042` e confirme sua partition key. Registre `monthly_tokens`, `request_count`, `rate_window_requests`, `estimated_charge` e `_ts`; mantenha o item aberto para testes de negação.

**Testar o limite de requisições por minuto**

21. Em `policy/promotion-policy.yaml`, altere `requests_per_minute` de `60` para `1`. Aguarde um novo minuto UTC se você já tiver medido uma requisição no minuto atual.
22. Execute a primeira requisição:

```powershell
python -m src.main meter
```

23. Espere `decision: allow` e `rate_window_requests: 1`. Atualize e reabra o item no Explorador de Dados; registre seus contadores, cobrança e `_ts`.
24. Execute uma segunda requisição antes de o minuto UTC mudar:

```powershell
python -m src.main meter
```

25. Espere `PermissionError: Per-minute request limit exceeded`. Atualize o item e confirme que todos os cinco valores registrados permanecem inalterados. Restaure `requests_per_minute: 60`.

**Testar a cota mensal de tokens**

26. Em `assets/usage-request.json`, altere `token_count` de `1250` para `1000001`.
27. Execute:

```powershell
python -m src.main meter
```

28. Espere `PermissionError: Monthly token quota exceeded`. Atualize o item e confirme que os cinco valores registrados permanecem inalterados. Verifique `scanner`, versão lógica `1.2.0`, tenant `synthetic-tenant-a` e centro de custo `FAB-SEC-042`, sem credenciais ou conteúdo de requisição. Restaure `token_count: 1250`.

Os contadores do medidor são valores pós-atualização. Cobranças estimadas são alocações da aplicação, não faturas do Azure; requisições negadas devem deixar contadores e cobrança inalterados.

## Tarefa 6: Validar a implementação

1. Use o portal do Foundry e o output do SDK para verificar que as três versões de prompt-agent no release promovido existem e correspondem a `$scannerVersion`, `$reviewerVersion` e `$orchestratorVersion`.
2. Execute o inventário novamente e compare com a evidência original.
3. Revise o arquivo técnico, declarações de compatibilidade da topologia e o diff do manifesto como registro de aprovação.

4. Para prática de aposentadoria, utilize a versão descartável `scanner` criada por este laboratório.
5. Abra `assets/retirement-request.json` e substitua seu valor `version` pelo valor mostrado em `$scannerVersion`.
6. Revise a solicitação e confirme que ela registra pelo menos 90 dias entre descontinuação e exclusão, zero consumidores, zero pins, conclusão de arquivamento, registro de descontinuação e aprovação de governança.
7. Imediatamente antes de executar um comando de aposentadoria, confirme que o comando tem como alvo o agente `scanner` e a versão descartável exata armazenada em `$scannerVersion`. Pare se qualquer um desses valores diferir.

8. Teste cada gate separadamente: consumidores ou pins definidos para `1`, arquivamento ou registro de descontinuação definidos para `false`, aprovação definida para `pending`, uma versão de solicitação que não corresponde, um intervalo de aviso mais curto, e uma data de exclusão futura. Mantenha o alvo do CLI fixo para o `$scannerVersion` deste laboratório. Após cada negação e verificação de inventário abaixo, restaure o campo alterado antes de testar o próximo gate.
9. Para cada alteração, execute:

```powershell
python -m src.main retire --agent-name scanner --agent-version $scannerVersion --confirm-delete-version
```

10. Confirme que o terminal mostra `Retirement denied` e nomeia o gate que falhou.
11. Execute o inventário após cada negação e confirme que a versão `scanner` em `$scannerVersion` ainda existe.
12. Restaure a solicitação sintética aprovada.
13. Execute:

```powershell
python -m src.main retire --agent-name scanner --agent-version $scannerVersion --confirm-delete-version
```

14. Confirme que o output de sucesso mostra `retired: true` e repete a evidência dos gates aplicados.
15. Execute o inventário novamente e confirme que `$scannerVersion` está ausente enquanto as versões `reviewer` e `orchestrator` permanecem. Isto demonstra a aposentadoria de um componente dentro de uma topologia.

16. Preserve os instantâneos do Cosmos DB e ambas as mensagens de negação de uso junto com o mapeamento do release, o registro de aprovação e a evidência de aposentadoria.

## Desafio opcional: Bloquear uma promoção incompatível

Crie uma versão sintética do reviewer cuja contract de saída é incompatível com um consumer orchestrator ativo.

**Saída esperada:** A promoção é bloqueada e a evidência nomeia a regra de compatibilidade que falhou e o consumer afetado.

**Investigação de falha:** Tente aposentar uma versão ainda referenciada pela topologia e explique a rejeição pela política de ciclo de vida.

## Tarefa 7: Revisar o design

1. Responda a estas perguntas:

- Por que um hash do prompt faz parte de uma versão de agente?
- Quais mudanças exigem aprovação manual ou do cliente?
- Por que a descontinuação e migração de consumidores devem preceder a exclusão de um componente de topologia?
- O que prova que uma versão aposentada não tem consumidores remanescentes?
- Por que a aplicação de cota e os incrementos do medidor devem usar uma única atualização condicional?
- Como a evidência de rateio de custos difere de uma fatura do Azure?

## Tarefa 8: Limpeza

**Remover recursos do Azure**

1. Reconcile quaisquer alvos órfãos exatos reportados por reversão de promoção com falha, então delete quaisquer versões `scanner`, `reviewer` e `orchestrator` remanescentes criadas por este laboratório.
2. Execute `azd down --purge`.
3. Confirme que o projeto Foundry, o model deployment e a conta Cosmos DB foram removidos.
4. Mantenha apenas manifests sintéticos e evidências; remova `.env` e caches locais.

**Desativar o ambiente virtual**

5. Execute este comando em todo terminal onde `(.venv)` aparece no prompt:

```powershell
deactivate
```

6. Confirme que `(.venv)` não aparece mais antes de sair do diretório de trabalho.

## Resumo

Você usou interfaces reais do Foundry e do Cosmos DB para governar um release de topologia de três agentes, versões imutáveis de prompt-agent, cotas, limites de taxa, alocação de uso, rateio de custos estimado e aposentadoria com fail-closed.
