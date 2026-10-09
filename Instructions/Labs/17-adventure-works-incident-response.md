---
lab:
  title: 'Depurar um incidente de produção multiagente com evidência de trace'
  description: 'Use Application Insights, KQL, snapshots de trace, replay seguro, hipóteses estruturadas e postmortems vinculados a evidências para diagnosticar um incidente da Adventure Works.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Depurar um incidente de produção multiagente com evidência de trace

## Cenário do cliente

Adventure Works observa uma queda na conclusão de checkout, mas o span de pagamento com falha pode ser apenas um sintoma. A equipe on-call precisa de uma forma repetível de reconstruir traces distribuídos, preservar entradas de replay, comparar caminhos com falha e bem-sucedidos, testar hipóteses concorrentes e documentar uma causa raiz suportada por evidência.

## Cenário do laboratório

Você irá emitir um incidente sintético multiagente através do OpenTelemetry, recuperá-lo do Application Insights com KQL, salvar um snapshot sanitizado no Blob Storage, executar um replay sem efeitos colaterais e avaliar hipóteses estruturadas. Você produzirá um postmortem sem atribuição de culpa somente depois que a evidência suportar ou rejeitar cada hipótese.

<!-- MARCADOR DE DIAGRAMA DO LAB: Mostrar emissão de telemetria, investigação KQL, captura de snapshot sanitizado, replay seguro, avaliação de hipóteses, remediação e evidências do postmortem. -->

Ao final deste exercício, você será capaz de:

- Consultar traces multiagente e latência com Application Insights KQL.
- Capturar artifacts de replay: modelo, prompt-hash, resposta de ferramenta e timeline de spans.
- Testar hipóteses sobre modelo, prompt, ferramenta, orquestração e configuração de forma sistemática.
- Conectar detecção, remediação, escalonamento e ações de postmortem à evidência.

> **Importante**: Application Insights e Log Analytics têm ingestão faturável. Emita apenas o trace sintético delimitado. Snapshots devem conter resultados de ferramenta mockados e não conter PII de clientes nem raciocínio de modelo oculto.

## Tarefa 1: Preparar o laboratório

1. Instale [Python 3.10 or later](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), e [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).

Você precisa de permissão para criar Log Analytics, Application Insights, Storage e atribuições de função. Autentique-se com sua identidade logada.

**Clone e abra o repositório**

2. Se ainda não fez, clone o [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

3. Abra o repositório clonado no Visual Studio Code.

**Verifique as ferramentas e a autenticação**

4. Valide as ferramentas necessárias, credenciais e assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\17-adventure-works-incident-response
az version
azd version
python --version
az account show --output table
```

**Checkpoint de arquitetura**

Revise `scripts/emit_synthetic_trace.py`, os schemas de snapshot e hipótese, as consultas KQL, `src/main.py`, `src/replay.py`, `src/remediation.py`, `.env.example` e `infra/main.bicep`. Antes de continuar, confirme que o caminho do incidente é `synthetic trace -> KQL investigation -> sanitized snapshot -> safe replay -> hypothesis decision -> bounded remediation -> evidence-linked postmortem`.

## Tarefa 2: Construa o ambiente virtual

1. No Windows, crie e ative o ambiente virtual e inicialize `.env`:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
Copy-Item .env.example .env
```

> No macOS/Linux, execute `bash scripts/setup.sh`, `source .venv/bin/activate` e `cp .env.example .env` em vez disso.

## Tarefa 3: Faça o deploy dos recursos Azure

1. Revise ingestão e retenção do Log Analytics, Application Insights, Storage, Event Hubs, custos de alertas e acesso de função requerido antes de provisionar.
2. Use um ambiente único e traces sintéticos delimitados.

`azd` provisiona a infraestrutura; emissão de trace e remediação executam separadamente.

**Defina os valores de deployment**

3. Defina `$azureRegion` para uma região aprovada que suporte os serviços requeridos.
4. Substitua o valor de exemplo `eastus2` se necessário.
> **Resource group:** Se seu ambiente de laboratório fornecer um resource group pré-criado, defina `$resourceGroupName` com seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group único em sua assinatura.

> **Nota:** `AZURE_DEV_USER_AGENT` marca o provisioning para atribuição e não é exportado para `.env`. Remova-o depois para evitar taguear comandos não relacionados.

**Valide e provisione a infraestrutura**

5. Execute os comandos a seguir:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab17-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-incident-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
$principalId = az ad signed-in-user show --query id --output tsv
azd env set AZURE_PRINCIPAL_ID $principalId
az bicep build --file infra/main.bicep
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> **Nota:** Se o provisionamento falhar, inspecione o primeiro erro de deployment. Verifique disponibilidade de monitoramento e mensageria, nomes de recursos, principal ID, restrições de policy e permissões de role-assignment. Corrija a causa e execute novamente `azd provision`.

**Verifique o ambiente gerado**

6. Após o provisionamento ter sucesso, valide que `.env` inclui os identificadores do Application Insights e Log Analytics, endpoint e nomes de container do Storage, nomes do namespace e hubs do Event Hubs, e valores de principal necessários pela aplicação.
7. Não adicione chaves de storage, connection strings, shared-access keys ou tokens.
8. Verifique a fronteira de rede efetiva do Event Hubs e a autorização do receiver:

```powershell
$values = azd env get-values --output json | ConvertFrom-Json
$namespaceName = $values.ALERT_EVENTHUB_NAMESPACE -replace '\.servicebus\.windows\.net$', ''
$networkBoundary = az eventhubs namespace network-rule-set show --namespace-name $namespaceName --resource-group $resourceGroupName --query "{publicNetworkAccess:publicNetworkAccess,defaultAction:defaultAction}" | ConvertFrom-Json
if ($networkBoundary.publicNetworkAccess -ne 'Enabled' -or $networkBoundary.defaultAction -ne 'Allow') { throw 'Unexpected Event Hubs network configuration' }
$eventHubId = az eventhubs eventhub show --name $values.ALERT_EVENTHUB_NAME --namespace-name $namespaceName --resource-group $resourceGroupName --query id -o tsv
$receiverRoles = @(az role assignment list --assignee $principalId --scope $eventHubId --query "[?roleDefinitionName=='Azure Event Hubs Data Receiver'].{role:roleDefinitionName,scope:scope}" | ConvertFrom-Json)
if ($receiverRoles.Count -ne 1 -or $receiverRoles[0].scope -ne $eventHubId) { throw 'Expected one Event Hubs Data Receiver assignment at the exact hub scope' }
$dataPlaneRoles = @(az role assignment list --assignee $principalId --all --query "[?starts_with(scope, '$eventHubId') && (roleDefinitionName=='Azure Event Hubs Data Sender' || roleDefinitionName=='Azure Event Hubs Data Owner')].{role:roleDefinitionName,scope:scope}" | ConvertFrom-Json)
if ($dataPlaneRoles.Count -ne 0) { throw 'The remediation receiver must not inherit Event Hubs Data Sender or Data Owner on this hub' }
[pscustomobject]@{
  publicNetworkAccess = $networkBoundary.publicNetworkAccess
  defaultAction = $networkBoundary.defaultAction
  receiverRole = $receiverRoles[0].role
  receiverScope = $receiverRoles[0].scope
  broaderDataPlaneRoles = $dataPlaneRoles.Count
} | Format-List
'EVENT_HUB_BOUNDARIES_VALIDATED'
```

Espere `EVENT_HUB_BOUNDARIES_VALIDATED`, `Enabled`/`Allow`, uma role exata **Azure Event Hubs Data Receiver**, e zero roles mais amplas de sender/owner no plano de dados. O template Bicep habilita o acesso de rede público nativo do namespace Event Hubs e a ação padrão **Allow** para que o consumidor local possa receber eventos de alerta. Autenticação Microsoft Entra e a role exata de receiver do hub ainda são requeridas. Ambientes de produção devem fornecer e validar um caminho de acesso privado aprovado.

## Tarefa 4: Implemente a solução

Cada placeholder marca código incompleto. Copie cada snippet fornecido para sua localização placeholder, remova o comentário `LAB PLACEHOLDER`, substitua apenas a linha ou bloco incompleto indicado, e preserve a indentação circundante.

> **Dica:** Depois de copiar e colar cada snippet Python, valide sua indentação em relação à função ou classe circundante antes de executar o código.

**Construa um snapshot de replay sanitizado**

1. Em `src/main.py`, localize `# LAB PLACEHOLDER 1`.
2. Substitua apenas as seis declarações de coleção vazias abaixo dele por:

```python
  spans = []
  deployments = {}
  configurations = {}
  prompts = {}
  prompt_hashes = {}
  tool_mocks = {}
  for row in rows:
    properties = row.get("Properties") or {}
    if isinstance(properties, str):
      properties = json.loads(properties)
    span = {
      "time_generated": row.get("TimeGenerated"),
      "span_id": row.get("Id"),
      "parent_id": row.get("ParentId"),
      "span_name": row.get("SpanName"),
      "duration_ms": row.get("DurationMs"),
      "success": row.get("Success"),
      "result_code": row.get("ResultCode"),
      "model_version": properties.get("gen_ai.request.model"),
      "configuration_version": properties.get("agent.configuration.version"),
      "prompt_hash": properties.get("gen_ai.prompt.hash"),
      "error_type": properties.get("incident.error.type"),
      "tool_name": properties.get("tool.name"),
      "tool_mock_id": properties.get("tool.mock_id"),
      "tool_mock_response_available": properties.get("tool.mock_response") is not None,
    }
    spans.append(span)
    if span["model_version"]:
      deployments[span["span_name"]] = {
        "agent": span["span_name"], "version": span["model_version"]
      }
    if span["configuration_version"]:
      configurations[span["span_name"]] = {
        "component": span["span_name"], "version": span["configuration_version"]
      }
    if properties.get("gen_ai.prompt.hash"):
      prompt_hashes[span["span_name"]] = properties["gen_ai.prompt.hash"]
    if properties.get("gen_ai.prompt.template"):
      prompts[span["span_name"]] = properties["gen_ai.prompt.template"]
    if span["tool_name"]:
      mock_response = properties.get("tool.mock_response")
      tool_success = properties.get("tool.response.success")
      if isinstance(tool_success, str) and tool_success.lower() in {"true", "false"}:
        tool_success = tool_success.lower() == "true"
      tool_mocks[span["tool_name"]] = {
        "mock_id": span["tool_mock_id"],
        "response": json.loads(mock_response) if isinstance(mock_response, str) else mock_response,
        "success": tool_success,
        "synthetic": True,
      }
```

Apenas os campos nomeados cruzam a fronteira de telemetria. Corpos de mensagens, credenciais e raciocínio oculto nunca são copiados.

**Resolva caminhos genéricos de evidência**

3. Em `src/analysis.py`, localize `# LAB PLACEHOLDER 2`.
4. Substitua apenas a função incompleta `values_at_path()` associada por:

```python
def values_at_path(document: Any, path: str) -> list[Any]:
  values = [document]
  for segment in path.split("."):
    expanded = []
    for value in values:
      if segment == "*" and isinstance(value, list):
        expanded.extend(value)
      elif segment == "*" and isinstance(value, dict):
        expanded.extend(value.values())
      elif isinstance(value, dict) and segment in value:
        expanded.append(value[segment])
    values = expanded
  return values
```

A travessia com coringa permite que hipóteses abordem coleções observadas sem embutir IDs específicos do incidente.

**Adicione o predicado menor-que**

5. Encontre `# LAB PLACEHOLDER 3`.
6. Adicione este ramo diretamente abaixo dele:

```python
    elif operator == "less_than":
      passed = any(float(value) < float(expected) for value in values)
```

A função existente ainda registra predicados falhos como evidência contraditória e caminhos ausentes como evidência faltante.

**Reconstrua o trace com mocks capturados**

7. Em `src/replay.py`, localize `# LAB PLACEHOLDER 4`.
8. Substitua apenas a função incompleta `reconstruct_trace()` associada por:

```python
def reconstruct_trace(snapshot: dict[str, Any]) -> dict[str, Any]:
  if snapshot.get("replay_mode") is not True:
    raise ValueError("Snapshot must explicitly enable replay mode")
  prompt_checks = []
  for agent, prompt in snapshot.get("prompts", {}).items():
    actual = hashlib.sha256(prompt.encode()).hexdigest()
    expected = snapshot.get("prompt_hashes", {}).get(agent)
    prompt_checks.append({
      "agent": agent, "expected_hash": expected,
      "actual_hash": actual, "matches": actual == expected,
    })
  steps = []
  for index, span in enumerate(snapshot.get("spans", []), start=1):
    tool_name = span.get("tool_name")
    mock = snapshot.get("tool_mocks", {}).get(tool_name) if tool_name else None
    status = span.get("success", span.get("status", span.get("Success")))
    duration_ms = span.get("duration_ms", span.get("DurationMs"))
    steps.append({
      "sequence": index,
      "span_name": span.get("span_name") or span.get("Name"),
      "status": status,
      "mock_used": mock is not None,
      "mock_response": mock.get("response") if mock else None,
      "duration_ms": duration_ms,
    })
  divergences = [check for check in prompt_checks if not check["matches"]]
  tool_steps = [step for step in steps if step["mock_used"]]
  metrics = {
    "prompt_count": len(prompt_checks),
    "prompt_match_rate": round(
      sum(check["matches"] for check in prompt_checks) / len(prompt_checks), 4
    ) if prompt_checks else 0.0,
    "tool_step_count": len(tool_steps),
    "tool_mock_response_count": sum(step["mock_response"] is not None for step in tool_steps),
    "failed_step_count": sum(step["status"] is False for step in steps),
    "divergence_count": len(divergences),
  }
  return {
    "operation_id": snapshot["operation_id"],
    "side_effects_enabled": False,
    "prompt_checks": prompt_checks,
    "steps": steps,
    "divergences": divergences,
    "comparison_metrics": metrics,
  }
```

Esta reconstrução controlada verifica hashes de prompt e substitui respostas sintéticas de ferramenta capturadas. Ela não reexecuta comportamento de modelo ou aplicação e não pode chamar uma ferramenta de produção.

**Sintetize somente evidência suportada**

9. Em `src/postmortem.py`, localize `# LAB PLACEHOLDER 5`.
10. Substitua apenas a função incompleta `summarize_evidence()` associada por:

```python
def summarize_evidence(analysis: list[dict[str, Any]], replay: dict[str, Any]) -> tuple[str, str]:
  metrics = replay["comparison_metrics"]
  supported = sorted(
    (item for item in analysis if item["status"] == "supported"),
    key=lambda item: item["priority"],
  )
  leading = supported[0] if supported else None
  observed = leading["supporting"] if leading else []
  evidence_summary = "; ".join(
    f"{item['path']} observed {json.dumps(item['observed'], sort_keys=True)}"
    for item in observed[:3]
  ) or "No causal observation has enough supporting evidence."
  if metrics["divergence_count"]:
    agents = ", ".join(item["agent"] for item in replay["divergences"])
    root_cause = (
      f"Replay detected {metrics['divergence_count']} prompt divergence(s) for {agents}; "
      "the causal statement remains bounded to the observed comparison evidence."
    )
  elif (
    leading and metrics["prompt_match_rate"] == 1.0
    and metrics["tool_step_count"] > 0
    and metrics["tool_mock_response_count"] == metrics["tool_step_count"]
  ):
    root_cause = (
      f"{leading['statement']} Evidence: {evidence_summary}. Replay matched "
      f"{metrics['prompt_count']} prompt(s), used {metrics['tool_mock_response_count']}/"
      f"{metrics['tool_step_count']} captured tool response(s), and preserved "
      f"{metrics['failed_step_count']} failed step(s)."
    )
  else:
    root_cause = "Root cause is not yet established because replay or comparison evidence is incomplete."
  return root_cause, evidence_summary
```

O relatório seleciona somente a hipótese suportada de maior prioridade e se recusa a exagerar evidência de replay incompleta.

**Verifique o código completado**

11. Verifique o código completado localmente:

```console
python -m py_compile src/main.py src/analysis.py src/replay.py src/postmortem.py src/remediation.py
python scripts/preflight.py --require-complete
```

12. Confirme que a compilação não retorna saída.
13. Antes do provisionamento, confirme que o preflight valida o schema, hipóteses e os três arquivos KQL; checagens de configuração do Azure podem permanecer `not ready`.

Nenhuma verificação preflight envia telemetria ou lê dados do Azure.

## Tarefa 5: Execute a solução

1. Execute os comandos de investigação do incidente:

```console
python scripts/emit_synthetic_trace.py
python -m src.main candidates --query kql/01-find-candidates.kql
python -m src.main capture --operation-id <operation-id> --query kql/02-trace-detail.kql
python -m src.analysis --snapshot reports/<operation-id>.snapshot.json --hypotheses assets/hypotheses.json
python -m src.replay --snapshot reports/<operation-id>.snapshot.json --output reports/replay-comparison.json
python -m src.remediation --max-wait-seconds 30 --max-events 10
python -m src.postmortem --snapshot reports/<operation-id>.snapshot.json --analysis reports/hypothesis-results.json --replay reports/replay-comparison.json
```

O emissor sintético exporta o checkout raiz como uma server request, usa uma razão de amostragem lab determinística `1.0`, e realiza um flush de telemetria delimitado antes de sair. Essas configurações mantêm a execução one-shot do laboratório alinhada com o contrato KQL `AppRequests`/`AppDependencies` em vez do timing de encerramento de processo ou amostragem de produção.

**Entenda a saída**

Um snapshot contém campos de span em lowercase, versões de deployment e configuração, prompt hashes, templates de prompt sintético e respostas mockadas de ferramentas. Resultados de hipótese separam evidência `supporting`, `contradicting` e `missing`. A reconstrução de trace relata fidelidade de prompt, passos falhos, cobertura de mock de ferramentas e divergências com `side_effects_enabled: false`; não é reexecução comportamental. O postmortem cita essas medições; a remediação registra uma ação proposta sem gravações em produção.

`kql/01-find-candidates.kql` é a consulta de descoberta ampla; use seu operation ID e colunas de falha para escolher um trace delimitado. `kql/02-trace-detail.kql` filtra esse ID e projeta os campos consumidos por `sanitize_rows()`. `kql/03-hypothesis-comparison.kql` compara coortes bem-sucedidas e com falha para que uma diferença de versão ou tipo de erro não seja inferida a partir de um único trace.

## Tarefa 6: Valide a implementação

**Valide captura de trace**

1. Confirme que a query candidata retorna operações sintéticas tanto bem-sucedidas quanto com falha.
2. Confirme que o detalhe do trace preserva a ordem pai-filho e as durações.
3. Confirme que o snapshot foi enviado para o container Blob configurado.
4. Delete o arquivo local do snapshot.
5. Baixe o snapshot novamente.
6. Confirme que o snapshot baixado permanece utilizável.

**Valide hipóteses e replay**

7. Para cada hipótese, registre evidência de suporte, contraditória e ausente.
8. Confirme que o snapshot contém `configuration_versions`, `model_deployments`, spans em lowercase `success`, `prompts`, prompt hashes e objetos de resposta sintética reais com flags de sucesso sob `tool_mocks`.
9. Confirme que o cenário com falha enviado suporta a afirmação de modelo de preço-versão a partir dos valores observados `synthetic-pricing-v2`, `SyntheticPriceFormatError` e `success: false`.
10. Confirme que as outras hipóteses enviadas avaliam sem caminhos faltantes.
11. Confirme que o replay preserva `status: false` e relata cobertura de passos falhos e respostas mock de ferramenta.
12. Altere o texto do prompt.
13. Confirme que o texto do prompt alterado causa uma divergência de hash.

**Compare coortes de trace**

14. Execute `kql/03-hypothesis-comparison.kql`.
15. Confirme que a coorte com falha reporta `synthetic-pricing-v2` além de `SyntheticPriceFormatError`, enquanto a coorte bem-sucedida reporta `synthetic-pricing-v1` sem aquele tipo de erro.

**Valide a remediação de alerta**

16. No Azure Monitor, confirme que `aw-synthetic-pricing-failure` está habilitado, avalia a cada minuto sobre uma janela de 15 minutos, e seu Action Group tem como alvo `incident-alerts`.
17. Após ativação do alerta, inspecione mensagens recebidas pelo Event Hubs.
18. Execute o consumidor de remediação delimitado.
19. Verifique que ele retorna após a espera configurada.
20. Confirme que imprime uma contagem processada não maior que `--max-events`.
21. Confirme que persiste um Blob de evidência de remediação por cada evento processado.

O receiver delimitado do laboratório inicia explicitamente a partir do início retido de cada partição e registra uma ação de contenção proposta, mas não pode realizar uma gravação em produção.

**Raciocine sobre checkpoints duráveis**

22. O receiver delimitado do laboratório demonstra tratamento seguro de eventos, mas um processador de eventos de produção deve usar checkpointing no Blob Storage.
23. Use um container de checkpoint Blob dedicado para cada Event Hubs consumer group, e coloque a storage account na mesma região Azure do namespace Event Hubs para reduzir latência de checkpoint e dependências cross-region.
24. Confirme que checkpoints são mantidos de forma independente por partição do Event Hubs. Um reinício pode, portanto, retomar cada partição em uma posição de evento diferente; se fragmentos de trace atravessarem partições, um conjunto de checkpoints parcialmente avançado pode produzir uma reconstrução incompleta até que as partições restantes alcancem o mesmo ponto.
25. Projete a reconstrução para tolerar duplicatas, fragments tardios e progresso local por partição. Persista evidência idempotente antes de avançar o checkpoint da partição correspondente.
26. O lab usa `$Default` e grava evidência de remediação em vez de reconstruir traces a partir do stream de alertas. Se você adicionar um checkpoint store, provisione um container dedicado para `$Default`; se adicionar outro consumer group, dê a ele um container de checkpoint diferente. Veja [Troubleshoot Blob Storage checkpoint store issues](https://learn.microsoft.com/azure/event-hubs/troubleshoot-checkpoint-store-issues) e [Partition load balancing for event processing](https://learn.microsoft.com/azure/event-hubs/event-processor-balance-partition-load).

**Valide o postmortem**

27. Abra o postmortem gerado e seu Blob correspondente em `incident-reports`.
28. Confirme que a declaração de causa raiz usa a afirmação causal suportada de maior prioridade, cita seus valores de predicado observados, e inclui métricas de prompt-match, passos falhos e resposta de ferramenta do replay.
29. Confirme que ele nunca infere causa a partir de um ID de hipótese ou nome de evento.

**Valide os recursos Azure**

30. No portal do Azure, valide apenas o Log Analytics workspace provisionado, o componente Application Insights, a storage account e dois containers Blob, o namespace e hub do Event Hubs, a scheduled query rule e o Action Group.

Nenhum projeto Foundry ou modelo é provisionado neste laboratório.

**Revise a cobertura de objetivos**

| Objetivo | Evidência necessária | Resultado esperado |
|---|---|---|
| Consultar traces e latência | Resultados das consultas candidato, detalhe e coorte | Ambos os resultados sintéticos aparecem e o trace selecionado preserva as relações entre spans. |
| Capturar artefatos de replay | Snapshots locais e no Blob válidos conforme o schema | Versões requeridas, hashes, spans e mocks sintéticos estão presentes; conteúdo sensível está ausente. |
| Testar hipóteses concorrentes | Relatório de resultados de hipótese | Todo predicado é suportado, contradito ou explicitamente ausente. |
| Conectar detecção através do postmortem | Alerta, evidência de remediação, replay e relatório | O processamento é limitado, efeitos colaterais permanecem desativados, e afirmações causais citam evidência observada. |

## Desafio opcional: Falsificar uma hipótese concorrente

Adicione uma hipótese concorrente que explique um sintoma, mas não o trace completo.

**Saída esperada:** O postmortem ranqueia a hipótese suportada em primeiro lugar e cita a observação que falsifica a alternativa.

**Investigação de falha:** Adicione um sintoma sintético enganoso e use as três etapas KQL para isolar o verdadeiro mecanismo de falha.

## Tarefa 7: Revisar o design

1. Responda a estas perguntas:

- Qual falha observável diferiu mais entre as coortes bem-sucedidas e com falha?
- Qual evidência falsificaria sua hipótese principal?
- Qual ação preventiva altera o sistema em vez de apenas tratar o sintoma?

## Tarefa 8: Limpeza

**Remova recursos Azure**

1. Execute `azd down --purge`.
2. Confirme que Application Insights, Log Analytics e Storage foram deletados.
3. Remova `.env` além dos snapshots gerados, a menos que seu instrutor os exija.

**Desative o ambiente virtual**

4. Execute este comando em todo terminal onde `(.venv)` aparece no prompt:

```powershell
deactivate
```

5. Confirme que `(.venv)` não aparece mais antes de mudar para outro diretório de laboratório.

## Sumário

Você diagnosticou um incidente multiagente a partir de evidência do Application Insights, preservou um snapshot de replay seguro, testou hipóteses concorrentes e produziu um postmortem sem atribuição de culpa baseado em evidências.
