---
lab:
  title: 'Governar uma revisão de código multiagente do Foundry'
  description: 'Aplicar controles de segurança de conteúdo, equidade, transparência, privacidade e responsabilização a um fluxo de trabalho multiagente do Microsoft Foundry.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Governar uma revisão de código multiagente do Foundry

## Cenário do cliente

A Fabrikam usa agentes de IA especializados para revisar código de clientes. Um revisor de segurança identifica vulnerabilidades, um auditor de equidade verifica se stacks tecnológicos equivalentes recebem resultados consistentes e um orquestrador de governança combina as evidências. Como a recomendação pode atrasar uma implantação, a Fabrikam precisa triagem do pedido, minimizar cada transferência, preservar a atribuição e exigir revisão humana quando um limite de política for excedido.

## Cenário do laboratório

Você implantará um projeto Microsoft Foundry, um modelo com guardrails nativos do Foundry e Application Insights baseado em workspace usando Bicep. Em seguida, você completará um portão determinístico de política e executará um fluxo de trabalho de governança com três agentes:

1. O Foundry aplica seus guardrails de segurança padrão aos prompts e completions do modelo.
1. O **security-reviewer** recebe apenas o fragmento de origem e a referência de evidência externa necessários para sua tarefa.
1. O **fairness-auditor** recebe apenas taxas de grupo calculadas, disparidade e o limite da política.
1. O **governance-orchestrator** recebe resultados minimizados dos especialistas e a decisão determinística da política.
1. A aplicação registra IDs de resposta, hashes, metadados de política e o resultado da revisão humana sem registrar código-fonte bruto, identidade do locatário, prompts ou raciocínio oculto.

Ao fim deste exercício, você será capaz de:

- Identificar onde os guardrails nativos do Foundry protegem prompts e completions do modelo.
- Medir disparidade de equidade com sondas sintéticas pareadas.
- Restringir cada transferência entre agentes a dados específicos para o propósito.
- Preservar a atribuição do agente com IDs de resposta do Foundry.
- Consultar evidências de responsabilização minimizadas no Application Insights.

> **Importante**: A implantação do modelo, o Log Analytics e o Application Insights são passíveis de cobrança. Use apenas os dados sintéticos fornecidos e exclua os recursos após a validação.

## Tarefa 1: Preparar o laboratório

1. Instale [Python 3.10+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download) e as extensões do VS Code [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) e [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep).

2. Use uma identidade do Azure que possa criar recursos do Microsoft Foundry, implantação de modelo e monitoramento e que possa atribuir funções.
3. Selecione uma região onde o modelo necessário esteja disponível.
4. Não use código de cliente, dados pessoais, credenciais ou segredos.

5. Se você ainda não fez, clone o repositório do laboratório:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

6. Abra o repositório no Visual Studio Code.
7. Em um terminal PowerShell, vá para o diretório do laboratório e verifique as ferramentas e a assinatura ativa:

```powershell
cd Allfiles\11-fabrikam-responsible-ai-governance
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação da arquitetura**

Revise estes componentes antes de editar:

| Componente | O que localizar |
|---|---|
| `assets/governance-scenario.json` e `policy/governance-policy.yaml` | Entradas sintéticas, limite de equidade e política de revisão humana |
| `src/governance.py` | Cálculos de equidade, cargas minimizadas, hashing de identificadores e evidências |
| `src/main.py` | Orquestração local determinística e o caminho Foundry `--live` |
| `kql/governance-evidence.kql` | Evidência de responsabilização minimizada |
| `infra/main.bicep` | Foundry, modelo, monitoramento e atribuições de função de menor privilégio |

Antes de continuar, confirme que o fluxo de trabalho padrão é local e determinístico e que apenas o caminho `--live` invoca agentes do Foundry.

## Tarefa 2: Construir o ambiente virtual

1. No Windows, execute:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

## Tarefa 3: Implantar recursos do Azure

1. Defina os valores de implantação.
2. Substitua o nome e a versão do modelo se não estiverem disponíveis na região aprovada.
> **Grupo de recursos:** Se o ambiente do seu laboratório fornecer um grupo de recursos pré-criado, defina `$resourceGroupName` para seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um grupo de recursos exclusivo em sua assinatura.
3. Execute os seguintes comandos:

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

> **Nota**: Se `azd env new` relatar que o ambiente já existe, selecione outro nome de ambiente ou use o ambiente existente. Se o provisionamento falhar, inspecione o primeiro erro de implantação. Disponibilidade de modelo, cota, Azure Policy e permissões de atribuição de função são causas comuns.

4. Confirme que o `.env` gerado contém identificadores, endpoints e uma connection string do Application Insights; ele não contém chaves de modelo ou tokens. `DefaultAzureCredential` usa seu sign-in do Azure.

> **Acesso de rede para este laboratório:** O template Bicep habilita o acesso de rede público nativo da conta Foundry e define a ação de rede padrão como **Allow** para que a aplicação local consiga alcançar o endpoint do projeto. A autenticação Microsoft Entra e o Azure RBAC ainda são exigidos. Após a implantação, confirme essas configurações na página **Rede (Networking)** da conta Foundry. Ambientes de produção devem usar um design aprovado de selected-network ou private-endpoint.

## Tarefa 4: Implementar o portão de política

Cada placeholder marca código incompleto. Copie cada trecho fornecido para seu placeholder correspondente, mantenha o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco incompleto indicado e preserve a indentação ao redor.

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete requires_human_review in Task 1")
```

1. Substitua apenas a linha `raise NotImplementedError(...)` sob o marcador mantido por esta implementação, preservando a indentação:

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

Esta decisão é de fechar em caso de falha: evidência incompleta ou malformada exige revisão humana. Limites vêm da política versionada em vez de serem duplicados no código.

2. Verifique o código concluído:

```powershell
& .\.venv\Scripts\python.exe -m py_compile src/main.py src/governance.py scripts/preflight.py
& .\.venv\Scripts\python.exe scripts/preflight.py
Select-String -Path src/governance.py -Pattern 'NotImplementedError'
```

A verificação prévia deve mostrar `PASS` para os cheques de configuração do projeto Foundry, modelo e Application Insights e terminar com `READY (Azure configured)`. O comando final não deve retornar correspondências.

**Inspecione os limites de privacidade**

3. Abra `policy/governance-policy.yaml` e compare `agent_inputs` com `build_agent_payload` em `src/governance.py`.

| Agente | Entrada permitida | Excluído deliberadamente |
|---|---|---|
| `security-reviewer` | Request ID, fragmento de origem sintético, referência CWE | Identidade do locatário, sondas de equidade, internos da política |
| `fairness-auditor` | Request ID, taxas de grupo, disparidade, limite | Código-fonte, identidade do locatário, saída de segurança |
| `governance-orchestrator` | Request ID, versão da política, resultados de controle, resultados dos especialistas | Código-fonte bruto, identidade do locatário, raciocínio oculto |

4. Verifique que a aplicação não registre prompts brutos ou raciocínio oculto:

```powershell
Select-String -Path src/governance.py,src/main.py -Pattern 'chain_of_thought|raw_prompt'
```

O comando não deve retornar correspondências.

5. Localize os campos usados para valores hashed e atribuição de agente do Foundry:

```powershell
Select-String -Path src/governance.py -Pattern 'tenant_id_hash|input_sha256|agent_response_ids'
```

O comando deve mostrar que valores brutos foram substituídos por hashes e que os IDs de resposta do Foundry fornecem atribuição do agente.

## Tarefa 5: Executar a solução

**Execute o fluxo de trabalho determinístico**

1. Execute o fluxo de trabalho sem chamadas ao Azure:

```powershell
& .\.venv\Scripts\python.exe -m src.main
```

A saída deve mostrar:

- `mode` igual a `deterministic`.
- Taxa de resultado positivo em Python `1.0` e taxa de resultado positivo em Node `0.5`.
- Disparidade máxima de equidade `0.5`.
- `human_review_required` igual a `true` porque `0.5` excede o limite da política de `0.1`.
- Três IDs locais de resposta, um para cada função de agente.
- Nomes de campo específicos para propósito sob `payloadFields`.

2. Inspecione o último registro de evidência:

```powershell
$evidence = Get-Content evidence/governance-evidence.jsonl | Select-Object -Last 1 | ConvertFrom-Json
$evidence | ConvertTo-Json -Depth 10
```

3. Confirme que inclui `evidence_scope` igual a `single_process_local_jsonl`, o ID e versão da política, taxas de equidade, hashes, resultado da revisão humana e três IDs de resposta. Não deve incluir o valor bruto do locatário ou o fragmento de origem de `assets/governance-scenario.json`.

O arquivo JSONL é evidência local de exercício de processo único. Não é um armazenamento de evidência concorrente ou centralizado; use Application Insights ou outro sink central governado quando múltiplos processos puderem escrever.

**Execute o fluxo de trabalho multiagente ao vivo**

O comando ao vivo cria uma versão de cada agente prompt do Foundry e os invoca nesta ordem. Os guardrails nativos do Foundry avaliam os prompts e completions inline:

- `security-reviewer`
- `fairness-auditor`
- `governance-orchestrator`

4. Execute-o uma vez:

```powershell
& .\.venv\Scripts\python.exe -m src.main --live
```

O comando imprime o `responseId` e o texto de cada agente, acrescenta um registro de evidência local minimizado e emite um rastreamento (trace) `fabrikam.governance.evidence` para o Application Insights. A telemetria do Azure Monitor é configurada uma vez por processo Python e reutilizada para emissões subsequentes nesse processo. O modelo pode variar sua redação, mas o cálculo de equidade e a decisão de revisão humana permanecem determinísticos.

> **Nota**: A atribuição de funções pode levar vários minutos para propagar. Se a primeira execução ao vivo retornar um erro de autorização, aguarde brevemente, faça sign in novamente com `az login` se necessário, e execute o comando novamente.

## Tarefa 6: Validar a implementação

**Validar no Microsoft Foundry**

1. Abra [Microsoft Foundry](https://ai.azure.com/) e selecione o projeto nomeado `lab11-<environment-name>`.
2. Na navegação à esquerda, selecione **Agentes (Agents)**.
3. Confirme que `security-reviewer`, `fairness-auditor` e `governance-orchestrator` existem e que cada um tem uma versão.
4. Revise as instruções de cada agente.
5. Confirme que sua função é estreita e que o orquestrador é instruído a não solicitar código-fonte bruto, identidade do locatário ou raciocínio oculto.
6. No topo da página **Agentes (Agents)**, selecione **Rastreamentos (Traces)**. Não há um item separado **Observabilidade (Observability)** no portal atual do Foundry.
7. Pesquise por **ID de resposta (Response ID)** usando um ID de `agentResponses` na saída do terminal ou `agent_response_ids` no último registro local de evidência.
8. Abra cada rastreamento correspondente e compare seu ID de resposta com a resposta correspondente do security reviewer, fairness auditor ou governance orchestrator.
9. Inspecione as entradas.
10. Confirme que apenas o security reviewer recebe `sourceCode`; o fairness auditor e o governance orchestrator não recebem.

> **Nota**: Se **Rastreamentos (Traces)** não estiver visível ou um rastreamento não puder ser aberto, confirme que você selecionou o projeto correto, completou uma execução ao vivo e permitiu tempo para a telemetria e as atribuições de função propagarem. O template Bicep atribui ao aprendiz `Log Analytics Reader` no recurso Application Insights conectado, o que o Microsoft Foundry requer para visualizar dados de rastreamento.

**Revisar os guardrails nativos do Foundry**

Este laboratório não implanta um recurso separado Azure AI Content Safety. A implantação do modelo usa os guardrails padrão que o Foundry aplica a prompts e completions.

11. No projeto Foundry, selecione **Construção (Build)** no menu superior e depois selecione **Modelos (Models)**.
12. Abra a implantação nomeada `gpt-5.4-mini`.
13. Revise o guardrail ou a configuração de filtro de conteúdo da implantação.
14. Confirme que a implantação usa a política de segurança padrão do Foundry e não está configurada com uma política personalizada sem filtragem.
15. Retorne a **Agentes (Agents)** e revise os últimos rastreamentos.
16. Confirme que cada resposta bem-sucedida de especialista e do orquestrador veio da implantação do modelo com guardrail.

Os guardrails padrão bloqueiam riscos de prompt ou completion acima de seus limites configurados. Use apenas o cenário sintético neutro fornecido; não introduza conteúdo de teste prejudicial.

**Testar o limite de equidade**

17. Altere apenas a última sonda `node-b` em `assets/governance-scenario.json` de `0` para `1`.
18. Execute:

```powershell
& .\.venv\Scripts\python.exe -m src.main
$updated = Get-Content evidence/governance-evidence.jsonl | Select-Object -Last 1 | ConvertFrom-Json
$updated.fairness | ConvertTo-Json -Depth 5
$updated.human_review_required
```

Ambas as taxas agora devem ser `1.0`, a disparidade deve ser `0.0` e a revisão humana deve ser `false` porque nenhum limite de equidade foi excedido.

19. Restaure `node-b` para `0` antes de continuar.

**Consultar evidência de responsabilização**

20. Aguarde vários minutos para que o rastreamento ao vivo alcance o Application Insights.
21. No portal do Azure, abra o recurso Application Insights cujo nome começa com `appi-lab11-`.
22. Selecione **Registros (Logs)**.
23. Mude para o modo KQL se necessário.
24. Execute o conteúdo de `kql/governance-evidence.kql`.

O resultado deve mostrar a versão da política `1.0.0`, pelo menos uma revisão e escalonamento, disparidade máxima `0.5` e os IDs de resposta serializados para os três agentes do Foundry.

25. Execute esta consulta de privacidade e confirme que ela retorna zero linhas:

```kusto
AppTraces
| where Message == "fabrikam.governance.evidence"
| where Properties has_any ("tenant_id", "source_code", "raw_prompt", "chain_of_thought")
```

26. Capture o seguinte como o conjunto de evidências de governança:

- A atribuição de guardrail padrão da implantação do modelo do Foundry.
- Taxas de equidade, disparidade e decisão de revisão humana.
- As três versões de agentes do Foundry e os IDs de resposta correspondentes.
- Inputs de rastreamento demonstrando minimização de dados por propósito.
- O resumo da política no Application Insights e o resultado de privacidade com zero linhas.

## Desafio opcional: Acionar revisão humana

Adicione uma sonda sintética de equidade que ultrapasse um limite de governança configurado.

**Resultado esperado:** O portão de liberação muda para `human review required` e registra tanto o valor medido quanto o limite da política.

**Investigação de falha:** Remova um campo de evidência obrigatório e confirme que o portão de política falha fechado com uma razão específica de evidência ausente.

## Tarefa 7: Revisar o design

1. Responda a estas perguntas:

- Por que o portão de revisão humana é determinístico em vez de delegado ao agente orquestrador?
- Como o viés poderia se acumular se o fairness auditor recebesse uma revisão de segurança enquadrada com metadados do desenvolvedor?
- Quais controles adicionais seriam necessários antes de processar código-fonte real de clientes?
- Quando um repositório de auditoria deve reter a saída completa do especialista em vez de IDs de resposta e evidência de política minimizada?

## Tarefa 8: Limpar

1. Exclua os recursos do Azure:

```powershell
azd down --purge
```

2. Se você usou um grupo de recursos pré-criado, verifique quais recursos o comando removerá antes de confirmar.
3. Exclua evidências locais e valores de ambiente:

```powershell
Remove-Item evidence/governance-evidence.jsonl -ErrorAction SilentlyContinue
Remove-Item .env -ErrorAction SilentlyContinue
```

4. Desative o ambiente virtual em todo terminal onde `(.venv)` aparecer:

```powershell
deactivate
```

## Resumo

Você implantou um projeto Microsoft Foundry definido por Bicep e governou uma revisão de código com três agentes com guardrails nativos do modelo, sondas de equidade pareadas, transferências minimizadas, IDs de resposta atribuíveis, supervisão humana determinística e evidência consultável no Application Insights.
