---
lab:
  title: 'Projetar ciclos agentivos com estado com Microsoft Foundry Agent Service'
  description: 'Implemente um loop de reflexão limitado do Agents v2, conversa persistente e ramificação retomável para pesquisa de investimentos.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Projetar ciclos agentivos com estado com Microsoft Foundry Agent Service

## Cenário do cliente

A Contoso Capital precisa de um agente de pesquisa de investimentos que retenha contexto multi-turno, execute auto-revisão limitada, reporte conclusão explicitamente e suporte ramos alternativos de pesquisa sem registrar texto confidencial da conversa.

## Cenário do laboratório

Você migrará um padrão fornecido do Agents v1 para Agents v2, implantará os recursos Foundry necessários e capturará evidências de conversa, reflexão, resposta e ramificação.

Ao final deste exercício, você será capaz de:

- Mapear o tratamento de run-status para tratamento de respostas limitado e exceções.
- Implementar planejamento visível e resumos de reflexão sem expor raciocínio oculto.
- Manter estado multi-turno em uma conversa.
- Fazer fork de um caminho de pesquisa com `previous_response_id`.
- Explicar agents, conversations, responses e typed output items.
- Migrar conceitos v1 de thread/run/tool para `azure-ai-projects` 2.x.

> **Importante:** O deployment do modelo, ingestão no Application Insights e retenção do Log Analytics são cobráveis. Use apenas a solicitação sintética em `assets`.

## Tarefa 1: Preparar o laboratório

Você precisará de:

- [Python 3.11 or later](https://www.python.org/downloads/)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) com [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Visual Studio Code](https://code.visualstudio.com/download)
- Uma assinatura do Azure com cota de modelo em uma região suportada
- Contributor e User Access Administrator no grupo de recursos de destino, ou acesso de data-plane do Foundry pré-atribuído equivalente

**Clone e abra o repositório**

1. Clone o [repositório de origem do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents), ou clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.

**Verifique as ferramentas e a autenticação**

3. Abra um terminal PowerShell no Visual Studio Code e execute:

```powershell
cd Allfiles\01-contoso-capital-stateful-agentic-loops
az version
azd version
python --version
az account show --output table
```

4. Confirme que cada comando tem sucesso e que `az account show` exibe a assinatura que você pretende usar.
5. Se necessário, autentique-se com `az login` e `azd auth login`, e então repita as verificações.

**Ponto de verificação da arquitetura**

Revise estes componentes antes de editar:

| Componente | O que localizar |
|---|---|
| `infra/main.bicep` | Foundry resources, model deployment, and project connection for server-side traces |
| `src/main.py` | `build_agent_definition`, `run_reflection_cycle`, and `fork_with_previous_response` |
| `assets/agents-v1-loop.py.txt` | Legacy v1 comparison evidence; do not execute this file |

Antes de continuar, confirme que você consegue localizar o loop de reflexão limitado, o ramo de resposta alternativo e o padrão legado usado apenas para comparação.

## Tarefa 2: Construir o ambiente virtual

1. A partir do diretório do laboratório, crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

2. Confirme que `(.venv)` aparece no prompt do terminal.

## Tarefa 3: Implementar os recursos do Azure

**Defina os valores de deployment**

1. Defina `$azureRegion` para uma região onde o modelo selecionado esteja disponível.
> **Grupo de recursos (Resource group):** Se seu ambiente de laboratório fornecer um resource group pré-criado, defina `$resourceGroupName` com seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group exclusivo na sua assinatura.

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab01-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
```

**Valide e provisione a infraestrutura**

2. Valide o Bicep, provisione os recursos e exporte o ambiente:

```powershell
az bicep build --file infra/main.bicep
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new lab01
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set FOUNDRY_MODEL_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_CATALOG_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_VERSION 2026-03-17
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

3. Se o provisionamento falhar, inspecione o primeiro erro do deployment. Para erros de disponibilidade de modelo ou região, atualize o valor de ambiente relevante e execute novamente `azd provision`.

**Verifique o ambiente gerado**

4. Abra `.env` e confirme que ele contém:

- `FOUNDRY_PROJECT_ENDPOINT`
- `FOUNDRY_MODEL_NAME`
- `FOUNDRY_PROJECT_ID`
- `APPLICATIONINSIGHTS_RESOURCE_ID`
- `LOG_ANALYTICS_WORKSPACE_ID`

A connection string do Application Insights é armazenada na conexão do projeto (project connection) do Foundry e não é gravada em `.env`.

> **Acesso de rede para este laboratório:** O template Bicep habilita o acesso de rede pública nativo da conta Foundry e define a ação de rede padrão como **Allow** para que a aplicação local possa alcançar o endpoint do projeto. Microsoft Entra authentication e Azure RBAC ainda são exigidos. Após o deployment, confirme essas configurações na página Rede (Networking) da conta Foundry. Ambientes de produção devem usar um design de selected-network ou private-endpoint aprovado.

5. Não adicione tokens ou chaves em `.env`.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada snippet fornecido para seu local de placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua apenas a linha ou bloco indicado como incompleto e preserve a indentação circundante.

**Defina o prompt agent**

1. Em `src/main.py`, encontre o placeholder em `build_agent_definition`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete build_agent_definition in Task 1")
```

```python
return PromptAgentDefinition(
  model=config.model_deployment,
  instructions=(
    "You are Contoso Capital's investment research agent. Use only the "
    "evidence provided in the request and conversation. Do not invent facts, "
    "recommend trades, or reveal hidden chain-of-thought. Return concise, "
    "visible planning and review summaries using exactly these headings:\n"
    "PLAN: <brief approach>\n"
    "REFLECTION: <evidence gaps or checks performed>\n"
    "STATUS: <COMPLETE or CONTINUE>\n"
    "ANSWER: <evidence-based answer or the next information needed>\n"
    "Use COMPLETE only when the request is fully answered from supplied "
    "evidence. Otherwise use CONTINUE."
  ),
)
```

Esta definição vincula o agente ao modelo implantado e solicita resumos visíveis mais um sinal de conclusão estável. O código da aplicação ainda controla o limite de iterações.

**Implemente o ciclo de reflexão limitado**

2. Em `run_reflection_cycle`, encontre:

```python
# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.
raise NotImplementedError("Complete run_reflection_cycle in Task 2")
```

```python
if max_iterations <= 0:
  raise ValueError("max_iterations must be greater than zero")

iterations: list[dict[str, Any]] = []
next_input = request
last_response_id = ""

for iteration_number in range(1, max_iterations + 1):
  response = openai_client.responses.create(
    conversation=conversation_id,
    input=next_input,
  )
  visible_text = extract_text(response).strip()
  status = "MISSING"

  for line in visible_text.splitlines():
    label, separator, value = line.partition(":")
    if separator and label.strip().strip("*").upper() == "STATUS":
      status = value.strip().strip("* .").upper()
      break

  last_response_id = response.id
  iterations.append(
    {
      "iteration": iteration_number,
      "response_id": response.id,
      "status": status,
      "visible_summary": visible_text,
    }
  )
  LOGGER.info(
    "Iteration completed iteration=%d response_id=%s status=%s",
    iteration_number,
    response.id,
    status,
  )

  if status == "COMPLETE":
    return {
      "iterations": iterations,
      "last_response_id": last_response_id,
    }

  next_input = (
    "Review the previous visible answer for unsupported claims, missing "
    "evidence, and incomplete coverage. Return a revised response with the "
    "required PLAN, REFLECTION, STATUS, and ANSWER headings."
  )

raise RuntimeError(
  f"Reflection cycle exhausted its {max_iterations}-iteration budget "
  "without STATUS: COMPLETE"
)
```

O loop mantém todas as iterações em uma única conversa, registra IDs de resposta e saída visível, e para após `max_iterations`. O logging é limitado ao número da iteração, response ID e status.

**Crie um ramo alternativo de resposta**

3. Em `fork_with_previous_response`, encontre:

```python
# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.
raise NotImplementedError("Complete fork_with_previous_response in Task 3")
```

```python
if not previous_response_id:
  raise ValueError("previous_response_id is required")

return openai_client.responses.create(
  previous_response_id=previous_response_id,
  input=branch_request,
)
```

Porque a chamada omite `conversation`, `previous_response_id` cria um branch separado sem alterar a conversa original.

**Registre a migração v1-para-v2**

4. Crie `migration-notes.md` na pasta do laboratório com esta comparação:

```markdown
# Agents v1 to v2 migration notes

| Agents v1 construct | Agents v2 replacement |
|---|---|
| `AgentsClient` | `AIProjectClient` plus `get_openai_client(agent_name=agent.name)` |
| Shared project OpenAI endpoint plus `extra_body.agent_reference` | Agent-bound OpenAI client using the agent's dedicated endpoint |
| Thread | A project OpenAI `conversation` |
| Run creation and status polling | Synchronous `responses.create()` calls bounded by application code |
| `requires_action` run state | Typed response output items and tool-call handling when tools are configured |
| GUID agent ID | Stable agent name plus an immutable agent version |
| New thread for an alternate path | `previous_response_id` without a conversation ID |

The migration changes both the client API and the state model. Conversations retain
multi-turn history, while response chaining creates an auditable alternate branch.
Application code, rather than the model, owns the maximum iteration count.
```

5. Compare a tabela com `assets/agents-v1-loop.py.txt`; não execute o arquivo legado.

**Verifique o código completo**

6. Salve `src/main.py` e execute as verificações locais antes de fazer uma chamada ao modelo que gere cobrança:

```powershell
python -m py_compile src/main.py scripts/preflight.py
python scripts/preflight.py
```

7. Confirme que todos os três marcadores permanecem, nenhum `NotImplementedError` permanece, e o preflight reporta `READY (local)`.

## Tarefa 5: Executar a solução

1. Execute a aplicação uma vez e salve sua saída no console:

```powershell
python -m src.main --input assets/research-request.json --retain-resources 2>&1 | Tee-Object -FilePath artifacts-lab01.txt
```

O cenário sintético fornecido contém fatos sobre receita, earnings before interest, taxes, depreciation, and amortization (EBITDA), dívida, liquidez, vencimento, contracted-revenue, e permissões além de lacunas explícitas de evidência. A solicitação de branch adiciona uma suposição de custo de refinancing de 250 basis points para que você possa observar se o caminho alternativo reutiliza a evidência original sem mutar o histórico de conversa.

Mensagens de autenticação podem mostrar tipos de credenciais indisponíveis antes de `DefaultAzureCredential acquired a token from AzureCliCredential`. Essa sequência é esperada quando a aplicação usa seu sign-in do Azure CLI.

Por padrão, a aplicação retém a conversa e a versão exata do agente para que você possa inspecioná-las no portal Foundry. A opção explícita `--retain-resources` no comando torna essa intenção visível e define `resources_retained` para `true`. Se você não precisar de inspeção no portal, use `--cleanup-resources`; a aplicação então exclui a conversa e a versão exata do agente que criou em um bloco `finally`, inclusive quando uma chamada de resposta falha.

## Tarefa 6: Validar a implementação

**Validar a saída capturada**

1. Localize os identificadores e registros de iteração:

```powershell
Select-String -Path artifacts-lab01.txt -Pattern 'agent_version|conversation_id|branch_response_id|iterations'
```

2. Confirme que todos os quatro campos estão presentes, então abra `artifacts-lab01.txt` e verifique:

| Campo | Critérios de aceitação |
|---|---|
| `agent_name` and `agent_version` | Identificam o agent nomeado e sua versão Foundry imutável. |
| `conversation_id` | Começa com `conv_`; todas as iterações de reflexão usam esta conversa. |
| `resources_retained` | É `true` para a execução de inspeção. |
| `iterations` | Contém de uma a três entradas, cada uma com um único `resp_` response ID, um status de topo e um sumário não vazio contendo `PLAN:`, `REFLECTION:`, `STATUS:` e `ANSWER:`. O status final é `COMPLETE`. |
| `branch_response_id` | Começa com `resp_` e difere de todo response ID de iteração; o branch está fora da conversa original. |
| `branch_text` | Aborda a suposição de refinancing de 250 basis points sem inventar dívida ou dados de fluxo de caixa faltantes. |

`STATUS: COMPLETE` significa que a revisão limitada terminou; isso não prova que a questão de investimento teve evidência suficiente. O limite de iterações controlado pela aplicação previne um loop ilimitado.

**Validar o ciclo de vida da versão do agente no Foundry**

3. Abra o [portal Foundry (Foundry portal)](https://ai.azure.com) e selecione o projeto identificado por `FOUNDRY_PROJECT_ENDPOINT` em `.env`.
4. Selecione **Agentes (Agents)** > **contoso-investment-researcher** e abra o histórico de versões.
5. Confirme que o `agent_version` registrado está presente e inspecione sua definição.

Após a inspeção, exclua a conversa retida e a versão do agente no portal Foundry (Foundry portal). Para execuções futuras que não exigem inspeção, passe `--cleanup-resources`. Essa opção limpa apenas os recursos criados por essa execução; não exclui versões retidas por execuções anteriores. Números de versão podem ser maiores que `1` após execuções repetidas.

**Validar os traces de resposta**

6. Selecione **Agentes (Agents)** > **Rastreamentos (Traces)** e defina o intervalo de tempo para incluir a execução.

A ingestão de rastreamentos pode levar vários minutos.

7. Pesquise por cada iteração `response_id` e pelo `branch_response_id`.
8. Confirme que:

- Cada trace mostra o nome do agente, a versão do agente, response ID, timestamp e operação de resposta bem-sucedida esperados.
- Respostas de iteração usam o `conversation_id` registrado quando metadata da conversa está disponível.
- A resposta de branch encadeia a partir da resposta final sem juntar-se à conversa.

Os traces provam as chamadas ao Foundry. `artifacts-lab01.txt` prova o limite de iteração controlado pela aplicação e a decisão de ramificação.

## Desafio opcional: Verificar isolamento de branch

Crie um segundo fork a partir da mesma resposta pai, dê aos dois forks fatos sintéticos de follow-up diferentes e compare seus resumos de estado finais.

**Saída esperada:** Cada fork relata seu próprio fato, nenhum fork relata o fato do outro fork, e a conversa pai permanece inalterada. Registre os response IDs do pai e dos forks como evidência.

**Investigação de falha:** Remova um campo de estado persistido de uma cópia local do registro de sessão, execute a continuação novamente e identifique o primeiro sinal de continuidade ausente. Restaure o campo antes da limpeza.

## Tarefa 7: Revisar o design

1. Responda estas perguntas:

- Quando uma conversation é preferível ao encadeamento `previous_response_id`?
- Qual sinal de conclusão pertence às instruções do modelo, e qual limite deve permanecer controlado pela aplicação?
- Como você migraria o estado histórico de thread do v1 quando a ferramenta de migração move o código mas não os dados?
- Qual metadata de branch deve ser retida para auditoria sem reter texto sensível do prompt?

## Tarefa 8: Limpeza

**Remover os recursos do Azure**

1. Execute os comandos a seguir:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge --force
Remove-Item Env:AZURE_DEV_USER_AGENT
az group show --name (azd env get-value AZURE_RESOURCE_GROUP) --output none
```

2. Confirme que o comando final relata que o resource group não existe mais.

**Remover arquivos gerados localmente**

3. Execute o comando a seguir:

```powershell
Remove-Item .env, artifacts-lab01.txt -ErrorAction SilentlyContinue
```

**Desativar o ambiente virtual**

4. Em todo terminal onde `(.venv)` aparecer, execute:

```powershell
deactivate
```

## Resumo

Você migrou um loop stateful para Agents v2, implementou reflexão limitada, reteve contexto em uma conversa, criou um branch de resposta e validou o comportamento contra um projeto Foundry ativo.
