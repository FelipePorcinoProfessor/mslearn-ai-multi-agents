---
lab:
  title: 'Aplicar estratégias de decomposição de tarefas e de colaboração entre agentes no Microsoft Foundry'
  description: 'Implemente um planner meta-agente ao vivo, um DAG de tarefas validado e handoffs de especialistas que preservam o contexto.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Aplicar estratégias de decomposição de tarefas e de colaboração entre agentes no Microsoft Foundry

## Cenário do cliente

Contoso Capital recebe perguntas de pesquisa que variam desde consultas simples até análises de investimento multi-fonte. Cadeias fixas processam em excesso trabalhos simples e deixam passar dependências em trabalhos complexos. A empresa precisa de planos gerados por modelos que sejam inspecionáveis, com handoffs limitados e overhead de coordenação mensurável.

## Cenário do laboratório

Você completará um planner meta-agente Agents v2 e um executor. O planner retorna um DAG JSON; o código da aplicação o valida, invoca especialistas somente quando as dependências são concluídas, transfere envelopes de contexto concisos e permite um único replanejamento baseado em evidências.

<!-- PLACEHOLDER DO DIAGRAMA DO LAB: Mostre o planner, o DAG de tarefas validado, especialistas prontos para dependências, envelopes de handoff e a síntese final. -->

Ao final deste exercício, você será capaz de:

- Projetar cadeias de prompt para análises em múltiplas etapas.
- Gerar decomposição adaptativa com um meta-agente.
- Implementar handoffs confiáveis que preservam o contexto.
- Balancear profundidade do plano contra latência e overhead de tokens.

> **Importante**: O planejamento e cada invocação de especialista consomem cota de modelo. O modelo pode propor um plano, mas o código da aplicação deve validá-lo e limitá-lo.

## Tarefa 1: Prepare o laboratório

Use [Python 3.11+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)/[Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install), [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download), um modelo suportado e uma assinatura autenticada. Você precisa de criação de recursos do Microsoft Foundry e de acesso ao plano de dados. Use apenas `assets/research-query.json`.

**Clone e abra o repositório**

1. Se ainda não fez isso, clone o [repositório fonte do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.

**Verifique ferramentas e autenticação**

3. No terminal do VS Code, valide as ferramentas necessárias, credenciais e a assinatura ativa:

```powershell
cd Allfiles\03-contoso-capital-task-decomposition
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação de arquitetura**

Revise `infra/main.bicep`, `assets/research-query.json` e `src/main.py`. Antes de continuar, confirme que você consegue localizar:

- a entrada do planner e o registro de capacidades;
- validação determinística do DAG e agendamento pronto para dependências;
- o envelope de handoff limitado;
- o sinal de replanejamento orientado por evidências e a tarefa final de síntese.

## Tarefa 2: Crie o ambiente virtual

1. A partir do diretório do laboratório, crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

## Tarefa 3: Implemente os recursos do Azure

Verifique a cota e o acesso ao modelo antes de provisionar. Planejamento, execução de especialistas, replanejamento, ingestão no Application Insights e retenção de 30 dias do Log Analytics são cobráveis. Use a entrada sintética limitada e um ambiente descartável único. `azd` provisiona os recursos Bicep; você executa a aplicação separadamente.

**Defina os valores de implantação**

1. Defina `$azureRegion` para uma região aprovada que ofereça suporte ao modelo selecionado.
2. Substitua o valor de exemplo `eastus2` se necessário.
> **Resource group:** Se o seu ambiente do laboratório fornecer um resource group pré-criado, defina `$resourceGroupName` com o nome dele. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group único na sua assinatura.

> **Nota:** `AZURE_DEV_USER_AGENT` marca o provisionamento para atribuição e não é exportado para `.env`. Remova-o posteriormente para evitar marcar comandos não relacionados.

**Valide e provisione a infraestrutura**

3. Execute os seguintes comandos:

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

4. Se o provisionamento falhar, inspecione o primeiro erro de implantação do Azure.

Causas comuns incluem cota de modelo, disponibilidade de versão do modelo, disponibilidade regional do serviço e permissões de atribuição de função.

5. Corrija a configuração ou permissão `azd env` relevante e então execute `azd provision` novamente.

**Verifique o ambiente gerado**

6. Depois que o provisionamento for bem-sucedido, valide que `.env` inclui `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_PROJECT_ID`, `FOUNDRY_MODEL_NAME`, `APPLICATIONINSIGHTS_RESOURCE_ID` e `LOG_ANALYTICS_WORKSPACE_ID`.

A connection string do Application Insights é armazenada na conexão do projeto Foundry e não é escrita em `.env`.

> **Acesso à rede para este laboratório:** O template Bicep habilita o acesso de rede pública nativo da conta Foundry e define a ação de rede padrão para **Allow** para que a aplicação local possa alcançar o endpoint do projeto. A autenticação Microsoft Entra e o Azure RBAC ainda são necessários. Após a implantação, confirme essas configurações na página **Rede (Networking)** da conta Foundry. Ambientes de produção devem usar um design de selected-network aprovado ou private-endpoint.

7. Não adicione chaves ou tokens em `.env`.

## Tarefa 4: Implemente a solução

Cada placeholder marca código incompleto. Copie cada trecho fornecido para o local do placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua apenas a linha ou bloco indicado como incompleto e preserve a indentação ao redor.

> **Dica:** Após copiar e colar cada trecho Python, valide a indentação em relação à função ou classe circundante antes de executar o código.

**Valide o DAG de tarefas gerado pelo modelo**

1. Abra `src/main.py` e localize **LAB PLACEHOLDER 1** em `validate_plan`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete validate_plan in Task 1")
```

2. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

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

O código da aplicação valida o grafo proposto antes de qualquer chamada a especialista: profundidade do plano limitada, capacidades conhecidas, dependências acíclicas e exatamente uma tarefa de síntese que consome cada ramo terminal de evidência.

**Selecione tarefas prontas para dependências**

3. Localize **LAB PLACEHOLDER 2** em `ready_tasks`:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete ready_tasks in Task 2")
```

4. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

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

Apenas pré-requisitos bem-sucedidos desbloqueiam uma tarefa. Um grafo bloqueado gera erro em vez de entrar em loop indefinidamente.

**Construa um envelope de handoff limitado**

5. Localize **LAB PLACEHOLDER 3** em `build_handoff`:

```python
# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
raise NotImplementedError("Complete build_handoff in Task 3")
```

6. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

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

O envelope separa o objetivo das evidências de dependência, retém IDs de resposta da fonte e limita o tamanho do contexto. O correlation ID vincula tarefas sem registrar o conteúdo da pesquisa.

**Sinalize um replanejamento orientado por evidências**

7. Localize **LAB PLACEHOLDER 4** em `should_replan`:

```python
# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
raise NotImplementedError("Complete should_replan in Task 4")
```

8. Substitua apenas a linha `raise NotImplementedError` abaixo por este código:

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

A política registra no máximo um sinal orientado por evidências em `replan_count`; ela não executa um replanejamento. Um coordenador de produção enviaria as evidências ao planner e validaria uma substituição apenas para o DAG remanescente.

**Verifique o código concluído**

O executor fornecido já registra IDs de resposta do planner e dos especialistas, contagens de tarefas e handoffs, o sinal de replanejamento limitado, tempo decorrido e uma razão de coordenação sem registrar conteúdo de prompt ou resposta.

9. Execute as verificações locais antes de fazer chamadas de modelo cobráveis:

```powershell
python -m py_compile src/main.py scripts/preflight.py
python scripts/preflight.py
```

10. Confirme que o relatório de verificação prévia mostra quatro linhas `PASS`, `src/main.py` retém todos os quatro marcadores `LAB PLACEHOLDER` e que ele não contém mais `NotImplementedError`.

## Tarefa 5: Execute a solução

1. Execute a aplicação:

```powershell
python -m src.main --input assets/research-query.json
```

2. Execute a consulta complexa.
3. Em seguida, altere `complexity_hint` para `simple` editando o arquivo assets/research-query.json.
4. Salve as alterações.
5. Execute novamente o cmdlet do PowerShell anterior:
```powershell
python -m src.main --input assets/research-query.json
```

O planner ao vivo deve reduzir a profundidade das tarefas enquanto preserva a tarefa final de síntese.

**Entenda a saída**

| Campo | O que reflete |
|---|---|
| `planner_response_id` | O plano estruturado ao vivo retornado pelo agente planner. |
| `plan` | Os IDs de tarefa validados, proprietários, objetivos, schemas e dependências usados para despacho. |
| `task_count` | Profundidade do plano validada, limitada entre um e seis tarefas. |
| `handoff_count` | Número de envelopes de despacho para especialistas criados. |
| `replan_count` | Zero ou um sinal orientado por evidências para um coordenador externo de replanejamento. |
| `coordination_ratio` | Handoffs divididos pelo número de tarefas concluídas; compare isto com qualidade e latência em vez de tratá-lo como uma pontuação. |
| `elapsed_ms` | Tempo de parede end-to-end do planner, validação, especialistas e síntese. |
| `results` | Status por tarefa, ID de resposta ao vivo e resumo estruturado visível. |

Para uma execução válida, toda tarefa dependente aparece em `results` antes de seu consumidor, e a entrada final pertence a `thesis-synthesis`. O contrato do planner exige que uma execução de consulta simples contenha exatamente uma tarefa de evidência mais a síntese final, enquanto uma execução complexa contém de três a seis tarefas. Ambos os planos devem satisfazer as mesmas invariantes determinísticas do DAG.

## Tarefa 6: Valide a implementação

**Inspecione o plano capturado**

1. Execute os seguintes comandos:

```powershell
python -m py_compile src/main.py scripts/preflight.py
python -m src.main --input assets/research-query.json *> artifacts-lab03.txt
Select-String artifacts-lab03.txt -Pattern 'planner_response_id|task_count|handoff_count|replan_count|coordination_ratio'
```

2. Inspecione o plano capturado: toda dependência deve referenciar uma tarefa concluída anteriormente, todo especialista deve existir no registro, e todos os resultados das tarefas devem ter IDs de resposta Foundry ao vivo.
3. Demonstre um plano simples e um complexo.

Verificações offline do DAG por si só não satisfazem o objetivo ao vivo.

**Valide os agentes no Foundry**

4. Abra o [portal Foundry](https://ai.azure.com).
5. Selecione o projeto nomeado em `FOUNDRY_PROJECT_ENDPOINT`.
6. Abra **Agentes (Agents)** e confirme as versões atuais para `research-planner` e cada especialista nomeado em `assets/research-query.json`.

**Valide os rastreamentos de resposta**

7. Selecione **Agentes (Agents)** > **Rastreamentos (Traces)**.
8. Ajuste o intervalo de tempo para incluir a execução complexa.
9. Pesquise por `planner_response_id`.
10. Abra o rastreamento correspondente e confirme o nome do agente planner, a versão, a operação de resposta bem-sucedida e o timestamp.
11. Em seguida, pesquise cada ID de resposta em `results`.
12. Confirme que os rastreamentos (traces) dos especialistas que consomem dependências iniciam somente depois dos rastreamentos de seus resultados pré-requisito serem concluídos.

13. Repita a busca de rastreamentos para a execução simples.
14. Compare o número e a sequência de rastreamentos dos especialistas com a execução complexa; a contagem de rastreamentos deve refletir o plano validado menor.

A ingestão de rastreamentos pode levar vários minutos.

## Desafio opcional: Compare duas decomposições

Crie dois DAGs válidos para a mesma consulta sintética: um coarse-grained e outro fine-grained. Selecione um usando restrições explícitas de qualidade, latência e contexto de handoff.

**Saída esperada:** O plano selecionado lista IDs de tarefa limitados, proprietários, dependências e artefatos preservados, e sua tarefa de síntese depende de cada ramo terminal de evidência.

**Investigação de falha:** Reduza o limite de tamanho do handoff até que um envelope seja rejeitado, então classifique a causa como granularidade da decomposição, tamanho do artefato ou validação de despacho.

## Tarefa 7: Reveja o design

1. Responda estas perguntas:

- Quais invariantes do plano nunca devem ser delegadas a um modelo?
- Quando uma cadeia fixa é mais barata e mais segura?
- Qual contexto pode ser sumarizado sem quebrar a evidência downstream?
- Qual sinal justifica o orçamento único de replanejamento?

## Tarefa 8: Limpeza

**Remova os recursos do Azure**

1. Execute os seguintes comandos:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge --force
Remove-Item Env:AZURE_DEV_USER_AGENT
```

**Desative o ambiente virtual**

2. Execute este comando em todo terminal onde `(.venv)` apareça no prompt:

```powershell
deactivate
```

3. Confirme que `(.venv)` não aparece mais antes de entrar em outro diretório de laboratório.

## Resumo

Você construiu planejamento adaptativo, validou um DAG de tarefas, executou especialistas com consciência de dependências, preservou o contexto de handoff e mediu o overhead de decomposição com respostas Foundry ao vivo.
