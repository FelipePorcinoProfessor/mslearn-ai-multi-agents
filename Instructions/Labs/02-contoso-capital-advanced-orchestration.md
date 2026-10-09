---
lab:
  title: 'Implementar padrões avançados de orquestração multiagente no Microsoft Foundry'
  description: 'Construir e validar um workflow de pesquisa v2 fan-out/fan-in com quórum e tratamento de falhas parciais.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Implementar padrões avançados de orquestração multiagente no Microsoft Foundry

## Cenário do cliente

A Contoso Capital precisa que especialistas em mercado, risco e conformidade contribuam para um único informe de investimento. Trabalhos independentes devem ser executados concorrentemente, trabalhos dependentes devem permanecer ordenados, e um especialista opcional com falha não deve invalidar silenciosamente o relatório.

## Cenário do laboratório

Complete um orquestrador hub-and-spoke que cria Agents v2 versionados especialistas, faz fan-out de chamadas de resposta ao vivo, aplica um quórum configurável e envia as evidências aceitas para um supervisor. A solicitação fornecida trata de um portfólio balanceado sintético sob um choque de taxa de juros fictício. Nenhum agente recebe dados reais de clientes ou recomenda transações.

<!-- MARCADOR DO DIAGRAMA DO LAB: Mostrar o hub-and-spoke fan-out, decisão de quórum e fan-in do supervisor. -->

### Responsabilidades dos agentes

Cada spoke recebe a mesma solicitação mais sua atribuição e retorna JSON conciso baseado apenas no cenário fornecido.

| Agente | Contribuição | Política de quórum |
|---|---|---|
| `market-spoke` | Pressupostos de mercado, incertezas e lacunas de evidência. | Obrigatório. |
| `risk-spoke` | Drivers de risco, limites de exposição e incerteza, sem conselho de investimento. | Obrigatório. |
| `compliance-spoke` | Divulgações, ressalvas de política e limites de uso da pesquisa. | Opcional; lacunas de evidência devem ser divulgadas. |
| `research-supervisor` | Um breve do pedido original, evidências aceitas dos spokes e lista de agentes faltantes; sem fatos inventados ou aconselhamento de investimento. | Executa somente após ambos os spokes obrigatórios terem sucesso. |

### Como os agentes colaboram

`src/main.py` cria versões de agente a partir de `assets/portfolio-request.json`, invoca spokes independentes atrás de um semáforo limitado, normaliza seus resultados e avalia o quórum antes da síntese. Spokes não compartilham uma conversa, não veem saídas de irmãos nem invocam uns aos outros. O código da aplicação é responsável por concorrência e política de falha; os agentes são responsáveis pela análise e síntese.

Ao final deste exercício, você será capaz de:

- Justificar quando a coordenação multiagente compensa seu custo.
- Implementar um hub central com spokes especialistas.
- Fazer fan-out de chamadas independentes e sincronizar resultados.
- Aplicar políticas de supervisor, quórum, timeout e falha parcial.
- Comparar o comportamento da orquestração entre entradas normais e com falha opcional.

> **Importante**: Chamadas concorrentes de modelo consomem cota mais rapidamente do que chamadas sequenciais. Use apenas o portfólio sintético e remova recursos após a validação.

## Tarefa 1: Preparar o laboratório

Use [Python 3.11+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)/[Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install), [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download) e uma assinatura Azure autenticada. Você precisa de um deployment de modelo suportado e permissão para criar recursos do Foundry. Confirme se a cota suporta três chamadas concorrentes.

1. Se ainda não fez, clone o [repositório de código-fonte do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.
3. Pelo terminal do VS Code, valide as ferramentas requeridas, credenciais e assinatura ativa:

```powershell
cd Allfiles\02-contoso-capital-advanced-orchestration
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação da arquitetura**

Revise `infra/main.bicep`, `assets/portfolio-request.json` e `src/main.py`. Antes de continuar, confirme que:

- o ativo do portfólio define a atribuição de cada especialista e o status obrigatório ou opcional;
- as três chamadas especialistas vinculadas ao agente podem ser executadas concorrentemente;
- evidência de mercado e risco são obrigatórias enquanto evidência de conformidade é opcional;
- código determinístico avalia o quórum antes da síntese do supervisor.

## Tarefa 2: Construir o ambiente virtual

1. A partir do diretório do laboratório, crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

## Tarefa 3: Provisionar os recursos Azure

Verifique custo, cota e acesso antes do provisionamento. Chamadas de modelo, ingestão do Application Insights e retenção de 30 dias do Log Analytics são cobradas. Use um ambiente único e cenários limitados. `azd` provisiona os recursos Bicep; a aplicação é executada separadamente.

**Defina os valores de implantação**

1. Defina `$azureRegion` para uma região aprovada que suporte o modelo selecionado; substitua `eastus2` se necessário.

> **Grupo de recursos:** Se seu ambiente de laboratório fornecer um grupo de recursos pré-criado, defina `$resourceGroupName` com seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um grupo de recursos único na sua assinatura.

> **Nota:** `AZURE_DEV_USER_AGENT` marca o provisionamento para atribuição e não é exportado para `.env`. Remova-o depois para evitar marcar comandos não relacionados.

**Validar e provisionar a infraestrutura**

2. Valide o Bicep, provisione os recursos e exporte o ambiente:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab02-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new lab02
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set FOUNDRY_MODEL_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_CATALOG_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_VERSION 2026-03-17
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

3. Se o provisionamento falhar, inspecione o primeiro erro de deployment. Verifique cota de modelo, disponibilidade de model-version e regional, e permissões de role-assignment. Corrija a configuração ou permissão relevante e reexecute `azd provision`.

**Verifique o ambiente gerado**

4. Confirme que `.env` inclui `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_PROJECT_ID`, `FOUNDRY_MODEL_NAME`, `APPLICATIONINSIGHTS_RESOURCE_ID` e `LOG_ANALYTICS_WORKSPACE_ID`.

A connection string do Application Insights é armazenada na conexão do projeto Foundry e não é escrita em `.env`.

> **Acesso de rede para este laboratório:** O template Bicep habilita o acesso público nativo da conta Foundry e define a ação de rede padrão para **Allow** para que a aplicação local possa alcançar o endpoint do projeto. A autenticação Microsoft Entra e o Azure RBAC ainda são exigidos. Após o deployment, confirme essas configurações na página **Rede (Networking)** da conta Foundry. Ambientes de produção devem usar um selected-network aprovado ou design de private-endpoint.

5. Não adicione chaves ou tokens em `.env`.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada trecho fornecido para seu local de placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco incompleto indicado e preserve a indentação ao redor.

**Selecione um padrão de execução seguro**

1. Abra `src/main.py` e localize **LAB PLACEHOLDER 1** em `select_execution_pattern`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete select_execution_pattern in Task 1")
```

```python
task_names = {task["name"] for task in tasks}
has_in_round_dependency = any(
  task_names.intersection(task.get("depends_on", []))
  for task in tasks
)
return "sequential" if has_in_round_dependency else "parallel"
```

Uma dependência in-batch seleciona execução sequencial; spokes independentes permanecem elegíveis para fan-out paralelo.

**Aplicar quórum de agente crítico**

2. Localize **LAB PLACEHOLDER 2** em `evaluate_quorum`:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete evaluate_quorum in Task 2")
```

```python
successful = {
  result["agent"]: result
  for result in results
  if isinstance(result, dict) and result.get("status") == "success"
}
all_agents = [
  result.get("agent", "unknown")
  for result in results
  if isinstance(result, dict)
]
missing_agents = [name for name in all_agents if name not in successful]
missing_required = [name for name in required if name not in successful]
accepted_evidence = [
  {
    "agent": name,
    "response_id": result["response_id"],
    "text": result["text"],
    "elapsed_ms": result["elapsed_ms"],
  }
  for name, result in successful.items()
]
return {
  "status": "ready" if not missing_required else "insufficient_quorum",
  "required_agents": required,
  "successful_count": len(successful),
  "missing_agents": missing_agents,
  "missing_required": missing_required,
  "accepted_evidence": accepted_evidence,
}
```

Quórum separa omissões opcionais de evidências obrigatórias ausentes. Apenas resultados normalizados bem-sucedidos avançam; exceções, credenciais, endpoints e estado oculto do agente são excluídos do payload do supervisor.

**Sintetizar evidência aceita**

3. Localize **LAB PLACEHOLDER 3** em `synthesize`:

```python
# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
raise NotImplementedError("Complete synthesize in Task 3")
```

```python
if quorum["status"] != "ready":
  missing = ", ".join(quorum["missing_required"])
  raise RuntimeError(f"Critical quorum was not met: {missing}")

payload = {
  "request": request,
  "accepted_evidence": quorum["accepted_evidence"],
  "missing_agents": quorum["missing_agents"],
}
return openai.responses.create(
  input=(
    "Synthesize the supplied specialist evidence. State a caveat for "
    "every missing agent, do not invent facts, and do not provide "
    "investment advice.\n"
    + json.dumps(payload)
  ),
)
```

Esta barreira de fan-in bloqueia a síntese quando o quórum é insuficiente e exige ressalvas explícitas para evidência opcional ausente.

**Verificar isolamento de falhas e controles de concorrência**

O runner fornecido respeita o padrão de execução selecionado. Spokes independentes usam `asyncio.gather(...)`, enquanto spokes dependentes são aguardados sequencialmente. `invoke` captura cada falha de spoke e retorna a mesma forma de resultado normalizado antes da lógica de quórum executar, de modo que objetos de exceção brutos nunca entram em `evaluate_quorum`. O `asyncio.Semaphore` limita chamadas paralelas, e cada timeout inclui tempo de espera por capacidade além da chamada de modelo.

4. Execute as verificações locais antes de fazer uma chamada de modelo cobrável:

```powershell
python -m py_compile src/main.py scripts/preflight.py
python scripts/preflight.py
```

5. Confirme que o preflight reporta quatro linhas `PASS`, que os três marcadores permanecem, e que `src/main.py` não contém `NotImplementedError`.

## Tarefa 5: Executar a solução

**Capturar ambos os cenários**

1. Execute a entrada normal uma vez e capture sua saída:

```powershell
python -m py_compile src/main.py scripts/preflight.py
python -m src.main --input assets/portfolio-request.json *> artifacts-normal.txt
Select-String artifacts-normal.txt -Pattern 'pattern|quorum|elapsed_ms|missing_agents|supervisor_response_id'
```

2. Execute a entrada com falha opcional e capture sua saída separadamente:

```powershell
python -m src.main --input assets/portfolio-request-optional-failure.json *> artifacts-optional-failure.txt
```

As entradas diferem apenas em `simulate_optional_failure`. A segunda execução marca `compliance-spoke` como falhado **após sua chamada ao vivo**; ela não simula uma queda de serviço Azure. Não edite a entrada normal.

3. Exiba os campos de orquestração de ambas as execuções:

```powershell
Select-String -Path artifacts-normal.txt,artifacts-optional-failure.txt -Pattern 'pattern|"agent"|"status"|missing_agents|missing_required|accepted_evidence|supervisor_response_id'
```

4. Preserve ambos os artefatos e seus response IDs para validação de rastreio. IDs, redação e tempos variam entre execuções ao vivo; essas diferenças não são mudanças de política.

## Tarefa 6: Validar a implementação

**Comparar resultados da orquestração**

1. Compare as saídas salvas contra estes critérios de aceitação:

| Campo | Entrada normal | Entrada com falha opcional |
|---|---|---|
| `pattern` | `parallel` | `parallel` |
| `compliance-spoke.status` | `success` | `failed`; market e risk ainda têm sucesso |
| `quorum.status` | `ready` | `ready` |
| `quorum.missing_agents` | Vazio | Contém `compliance-spoke` |
| `quorum.missing_required` | Vazio | Vazio |
| `quorum.accepted_evidence` | Três resultados de spoke | Apenas resultados de market e risk |
| `supervisor_response_id` | Presente | Presente |
| Resposta do Supervisor | Usa apenas evidência aceita | Declara explicitamente que evidência de conformidade está ausente |

2. Na saída normal, confirme que `spokes` contém três resultados normalizados bem-sucedidos com response IDs, texto visível e durações, além de um response ID separado do supervisor.
3. Compare `elapsed_ms` com a soma das durações dos spokes. O valor de wall-clock inclui a barreira dos spokes e a chamada do supervisor; use a sobreposição de trace abaixo para verificar concorrência.
4. Revise o caminho de falha obrigatória em `evaluate_quorum` e `synthesize`: um `market-spoke` ou `risk-spoke` falhado deve produzir `insufficient_quorum` e bloquear a chamada do supervisor. A execução com falha opcional não exerce esse caminho.

Verificações locais de schema não substituem evidência de respostas ao vivo.

**Validar definições de agente e comportamento de papéis**

5. Encontre o nome do projeto no segmento final de `FOUNDRY_PROJECT_ENDPOINT` em `.env`. Abra o [portal Microsoft Foundry](https://ai.azure.com), habilite **Novo Foundry (New Foundry)**, e selecione esse projeto.
6. Selecione **Criar (Build)** > **Agentes (Agents)**. Confirme que `market-spoke`, `risk-spoke`, `compliance-spoke` e `research-supervisor` existem como prompt agents.
7. Abra a versão mais nova de cada agente e confirme que seu modelo corresponde a `FOUNDRY_MODEL_NAME` e suas instruções correspondem a `assets/portfolio-request.json`. Cada execução da aplicação cria novas versões.
8. Abra a versão mais nova de cada spoke no **Playground (Playground)** e submeta o prompt mostrado para esse agente:

**`market-spoke`**

  ```text
  Request: Assess a synthetic balanced portfolio under a fictional rate shock.
  Assignment: Return market assumptions and evidence gaps.
  ```

**`risk-spoke`**

  ```text
  Request: Assess a synthetic balanced portfolio under a fictional rate shock.
  Assignment: Return risk drivers and limits.
  ```

**`compliance-spoke`**

  ```text
  Request: Assess a synthetic balanced portfolio under a fictional rate shock.
  Assignment: Return compliance caveats.
  ```

9. Verifique os limites de função:
   - `market-spoke` identifica pressupostos e evidência de mercado faltante.
   - `risk-spoke` identifica drivers de risco e limites de análise sem fornecer conselho de investimento.
   - `compliance-spoke` identifica ressalvas de política sem realizar a análise de mercado ou risco.
10. Abra `research-supervisor` no **Playground (Playground)** e submeta este payload completo de fan-in sintético:

  ```json
  {
    "request": "Assess a synthetic balanced portfolio under a fictional rate shock.",
    "accepted_evidence": [
      {
        "agent": "market-spoke",
        "response_id": "playground-market-001",
        "text": "Assumption: the fictional scenario includes a rate increase. Evidence gaps: no holdings, duration, rate-shock magnitude, or market data were supplied.",
        "elapsed_ms": 0
      },
      {
        "agent": "risk-spoke",
        "response_id": "playground-risk-001",
        "text": "Potential drivers include duration and concentration, but exposure cannot be quantified without portfolio data. This is risk analysis, not investment advice.",
        "elapsed_ms": 0
      }
    ],
    "missing_agents": [
      "compliance-spoke"
    ]
  }
  ```

11. Confirme que o supervisor:
    - Usa apenas os dois registros de evidência fornecidos.
    - Declara explicitamente que a evidência de conformidade está ausente.
    - Não inventa uma conclusão de conformidade, participações do portfólio, valores de exposição ou a magnitude do choque de taxa.

Chamadas no Playground testam agentes independentemente. Elas não reproduzem orquestração paralela nem provam quais agentes uma execução salva no console invocou.

**Correlacione traces de serviço com evidência da aplicação**

12. Selecione **Agentes (Agents)** > **Rastreamentos (Traces)**, defina o intervalo de tempo para cobrir a execução normal, e busque pelos response IDs salvos. Aguarde vários minutos para ingestão.
13. Compare os três traces de spoke: tempos de início e durações sobrepostos demonstram chamadas concorrentes. Confirme que o trace do supervisor inicia após a conclusão das respostas dos spokes.
14. Repita para a execução com falha opcional. Um trace de conformidade ainda pode existir porque a injeção de falha ocorre após a chamada ao vivo. Use o JSON final para verificar a exclusão da evidência aceita, a decisão de quórum e a ressalva do supervisor.

Traces de serviço mostram chamadas Foundry e tempos, não o semáforo Python, `asyncio.gather`, injeção de falha ou código de quórum. Correlacione-os com o JSON salvo; não espere uma única span pai de ponta a ponta. Instrumentação do lado cliente, KQL, sampling e alertas são abordados no Lab 13.

## Tarefa 7: Revisar o design

Registre respostas breves:

- Por que `pattern` permanece `parallel` em ambas as execuções?
- Por que a falha opcional deve deixar o quórum pronto enquanto remove a evidência de conformidade e adiciona uma ressalva?
- Quais decisões pertencem a código determinístico em vez de julgamento do agente?
- Quando esses especialistas justificariam seu custo de coordenação em vez de um único agente, e quais medições adicionais suportariam essa decisão?

## Desafio opcional: Adicionar uma rota protegida

Adicione uma solicitação sintética de alto risco que selecione execução sequencial e exija o spoke de conformidade antes da atribuição dependente restante.

**Saída esperada:** `pattern` é `sequential`, o resultado de conformidade completa antes do início do spoke dependente, e a resposta final identifica a rota selecionada.

**Investigação de falha:** Force um spoke opcional a falhar e explique a partir da saída de quórum se o orquestrador continuou, fez fallback ou falhou fechado.

## Tarefa 8: Limpeza

**Remover recursos Azure**

1. Execute os seguintes comandos:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge --force
Remove-Item Env:AZURE_DEV_USER_AGENT
```

2. Confirme que o grupo de recursos foi excluído.
3. Remova artefatos de response gerados.

**Desativar o ambiente virtual**

4. Execute este comando em cada terminal onde `(.venv)` apareça no prompt:

```powershell
deactivate
```

5. Confirme que `(.venv)` não aparece mais antes de mudar para outro diretório de laboratório.

## Resumo

Você implementou chamadas especialistas paralelas ao vivo, sincronização, política de quórum, isolamento de falhas e síntese de supervisor no Microsoft Foundry.
