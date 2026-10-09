---
lab:
  title: 'Rastreie fluxos de trabalho multiagente com OpenTelemetry'
  description: 'Crie spans correlacionados OpenTelemetry, propagação de contexto W3C, logs estruturados, sinais de anomalia e evidência no Azure Monitor para agentes Adventure Works.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Rastreie fluxos de trabalho multiagente com OpenTelemetry

## Cenário do cliente

A Adventure Works opera uma plataforma de inteligência do cliente cujos agentes router, recommendation e inventory atravessam limites de serviço. Os operadores precisam de uma única waterfall de trace, logs de decisão com privacidade, evidência de latência e alertas que identifiquem o agente responsável antes que os clientes relatem falhas.

## Cenário do laboratório

Você irá criar spans reais para um fluxo sintético de três agentes, propagar explicitamente o contexto W3C `traceparent`, ativar políticas de latência, taxa de erro e anomalia de tokens, exportar telemetria consultável através da Microsoft Entra authentication, e validar um alerta agendado do Azure Monitor (scheduled-query) e action group.

Ao final deste exercício, você será capaz de:

- Criar spans OpenTelemetry em fronteiras semânticas de agentes.
- Injete e extraia W3C Trace Context através de chamadas entre agentes.
- Emitir logs estruturados e com privacidade correlacionados aos spans.
- Exportar para Application Insights e consultar a integridade dos agentes e uma waterfall de trace.
- Acionar e observar um alerta acionável por latência, taxa de erro ou anomalia de token.

> **Importante**: Application Insights e Log Analytics ingestion são cobrados. O laboratório dorme por milissegundos e usa apenas metadados sintéticos. Exclua os recursos de monitoramento após a validação.

## Tarefa 1: Prepare o laboratório

1. Instale [Python 3.10+](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Visual Studio Code](https://code.visualstudio.com/download) com a extensão [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) e [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).
2. Use uma identidade com permissão para criar recursos de monitoramento e atribuir `Monitoring Metrics Publisher`.
3. Use apenas o cenário sintético incluído.
4. Nunca coloque prompts, identificadores pessoais, dados de pagamento ou credenciais em logs ou atributos de span.

5. Se você ainda não fez, clone o [repositório fonte do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

6. Abra o repositório clonado no Visual Studio Code.
7. Valide as ferramentas necessárias, as credenciais e a assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\13-adventure-works-distributed-observability
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação de arquitetura**

Revise `src/telemetry.py`, `config/telemetry-policy.yaml`, `assets/trace-scenario.json`, `kql/anomaly-alert.kql` e `infra/main.bicep`. A razão de exportação do laboratório é `1.0` de modo que uma execução do aluno produz uma waterfall completa; a política registra separadamente um exemplo de head-sampling de produção `0.05` para discussão de design. Antes de continuar, confirme que `traceparent` flui por todos os três agentes e que decisões flattenadas de latência, token e taxa de erro são consultáveis pelo alerta agendado.

## Tarefa 2: Construa o ambiente virtual

1. No Windows, execute:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

2. Revise `config/telemetry-policy.yaml`.
3. Confirme que campos proibidos estão ausentes de `assets/trace-scenario.json`.

## Tarefa 3: Implemente os recursos do Azure

1. Antes de provisionar com `azd`, verifique o acesso ao papel de monitoramento e os custos para Log Analytics ingestion e retention, Application Insights, scheduled-query alerts e action groups.

2. Defina `$azureRegion` para uma região aprovada que suporte os serviços necessários.
3. Substitua o valor de exemplo `eastus2` se necessário.
> **Resource group:** Se seu ambiente de laboratório fornecer um resource group pré-criado, defina `$resourceGroupName` com seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group único na sua assinatura.
4. Execute os seguintes comandos:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab13-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
azd env new lab13-distributed-observability
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd env set ALERT_EMAIL <lab-operator-email>
azd provision
azd env get-values | Out-File .env -Encoding utf8
```

> Observação: Se o provisionamento falhar, inspecione o primeiro erro de implantação do Azure. Disponibilidade regional de monitoramento, e-mail inválido no alerta, restrições de política e permissões de atribuição de função são causas comuns. Corrija a causa e execute `azd provision` novamente.

A regra scheduled-query usa um fallback tipado e vazio e pula a validação de query em tempo de implantação porque um workspace novo não expõe a tabela `AppTraces` até que sua primeira telemetria chegue. O fallback retorna nenhuma linha; o Azure avalia os sinais reais `AppTraces` normalmente após o início da ingestão.

5. Após o provisionamento ser bem-sucedido, valide que `.env` inclua a connection string do Application Insights, `APPLICATIONINSIGHTS_RESOURCE_ID`, o ID do Log Analytics workspace, client ID da identidade e os IDs de recurso do alerta.
6. Confirme que não contém nenhum token ou chave. A identidade Bicep recebe `Monitoring Metrics Publisher` para execução implantada.
7. Para validação local ao vivo, atribua à sua identidade de desenvolvimento logada a mesma função em `APPLICATIONINSIGHTS_RESOURCE_ID`.
8. Não habilite ingestão com chave local.
9. Confirme o e-mail do action group antes de esperar por notificações.

## Tarefa 4: Implemente a solução

Cada placeholder marca código incompleto. Copie cada trecho fornecido para sua localização placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco incompleto indicado e preserve a indentação ao redor.

> **Dica:** Depois de copiar e colar cada snippet Python, valide sua indentação em relação à função ou classe circundante antes de executar o código.

**Injetar o contexto de trace ativo**

1. Abra `src/telemetry.py` e encontre **LAB PLACEHOLDER 1** em `build_next_carrier`:

```python
# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.
raise NotImplementedError("Complete build_next_carrier in Task 1")
```

2. Substitua somente a linha `raise NotImplementedError` logo abaixo por este código:

```python
carrier: dict[str, str] = {}
propagator.inject(carrier)
return carrier
```

O propagador serializa o contexto ativo em `traceparent`. `execute_agent` o extrai antes de `start_as_current_span`, fazendo com que o próximo agente seja filho no mesmo trace.

**Revise a telemetria de decisão estruturada**

3. Inspecione `_structured_log` e `execute_agent`. Ambos exibem `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.agent.id`, `gen_ai.provider.name`, `gen_ai.conversation.id`, `gen_ai.usage.input_tokens` e `gen_ai.usage.output_tokens`; spans e logs com falha também incluem `error.type`.
4. Liste os atributos específicos do domínio retidos ao lado dos atributos semânticos: `agent.version`, latency, anomaly flags, policy status e o hashed session ID. Convenções semânticas melhoram a interoperabilidade; elas não substituem telemetria útil e limitada ao negócio.
5. Não adicione texto de requisição cru nem raciocínio de modelo. O conversation ID neste cenário sintético é dado de teste não relacionado a clientes; aplique a política de identificador da sua organização antes de usar o mesmo atributo com conversas de produção.
6. Inspecione `execute_agent`.
7. Identifique as três decisões de política: latência usa um limiar estrito, anomalia de token usa a média do cenário mais o múltiplo de sigma configurado, e a taxa de erro da cadeia é calculada após todos os agentes completarem. Essas decisões permanecem parametrizadas em `config/telemetry-policy.yaml`.

**Verifique o código concluído**

8. Execute as seguintes checagens:

```powershell
python -m py_compile src/main.py src/telemetry.py scripts/preflight.py
python scripts/preflight.py
Select-String -Path src/telemetry.py -Pattern 'NotImplementedError'
```

O preflight deve terminar com `READY (local)`, e o comando final deve retornar nenhuma correspondência. A configuração do Azure Monitor pode permanecer `INFO` para a execução apenas no console.

## Tarefa 5: Execute a solução

1. Temporariamente deixe a connection string do Azure Monitor em branco.
2. Execute `python -m src.main`.
3. Inspecione o JSON do span no console.
4. Confirme que três IDs de span únicos compartilham um único trace ID de 32 caracteres e formam uma cadeia pai-filho. O span de recommendation contém eventos de latência e anomalia de token: 85 ms excede 60 ms, e 516 tokens excedem o limite de token `350 + (3 x 50) = 500`. O erro de inventory produz uma chain error rate de `1/3`, acima de 0.05.

5. Restaure a connection string do Azure Monitor.
6. Execute o comando novamente. O comando grava `evidence/trace-evidence.json` e exporta spans e logs.
7. Registre o trace ID impresso.

**Entenda a saída**

`correlation_complete: true` significa que os três registros compartilham o mesmo trace ID. `span_count: 3` é o número de agent semantic spans, não de cada span do SDK ou exporter. `anomalies` nomeia agentes cujo status não é success. `error_rate` é a fração observada de erro da cadeia, enquanto `error_rate_anomaly` é o resultado da comparação da política.

O exercício padrão `records` exercita todos os três sinais: latência e tokens da recommendation, mais o erro de inventory que produz uma chain error rate de aproximadamente 0.3333.

## Tarefa 6: Valide a implementação

1. Abra a visualização Application Insights **Agentes (Preview)** como baseline embutida. Use-a para inspecionar requests por agente, latência, uso de tokens, erros e detalhes de agente individuais quando os atributos semânticos emitidos são reconhecidos. Veja [Monitor AI agents with Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/agents-view).
2. Abra Application Insights **Busca de transações (Transaction search)**.
3. Encontre o trace ID registrado e inspecione os detalhes da transaction waterfall.
4. Confirme que router, recommendation e inventory aparecem sob uma única operação.
5. Abra **Logs**.
6. Cole o trace ID em `kql/trace-waterfall.kql` e execute.
7. Execute `kql/agent-health.kql` e verifique que recommendation tem a maior latência P95 e uma anomalia de token, enquanto inventory tem status de erro. Trate essas queries e dashboards customizados como extensões para política de domínio e análise entre agentes, não como substitutos da visualização Agents embutida.

8. Valide cada configuração ativa de forma independente e restaure o ativo após cada execução:

9. Defina a latência de recommendation exatamente para 60 ms e tokens de saída para 80.
10. Confirme que nenhum dos limites é anômalo porque ambas as comparações usam greater-than.
11. Restaure tokens de saída para 96 e confirme que a anomalia de token retorna enquanto a latência permanece em 60 ms.
12. Defina todos os campos `error` para `false` e confirme que `error_rate_anomaly` é false.
13. Restaure o erro de inventory.
14. Altere `latency_threshold_ms`, `error_rate_threshold` e `token_anomaly_sigma` no YAML um por vez e confirme que decisões em runtime mudam sem editar KQL.

15. Inspecione os recursos provisionados:

```console
az monitor action-group show --ids <ANOMALY_ACTION_GROUP_ID> --query "{enabled:enabled,receivers:emailReceivers[].emailAddress}"
az monitor scheduled-query show --ids <ANOMALY_ALERT_RULE_ID> --query "{enabled:enabled,severity:severity,frequency:evaluationFrequency,actions:actions.actionGroups}"
```

16. Execute o cenário padrão restaurado com exportação para Azure habilitada.
17. Após a ingestão e a próxima avaliação de cinco minutos, abra Azure Monitor **Alerts**.
18. Filtre pela regra scheduled-query.
19. Confirme que um alerta fired de severidade-2 está vinculado ao workspace que armazena a telemetria do Application Insights e ao action group.
20. Confirme que o e-mail usa o common alert schema.
21. Execute um cenário sem anomalia e observe a mitigação automática após o período saudável configurado de cinco minutos.
22. Capture a baseline da visualização Agents, a waterfall, linhas de propriedade correlacionadas, as três decisões de política, ligação regra/ação, alerta disparado, notificação e estado resolvido como evidência ao vivo.

## Desafio opcional: Adicione um atributo cross-agent

Adicione um atributo sintético de classificação de requisição (request-classification) e propague-o pela cadeia.

Resultado esperado: O valor aparece nos spans correlacionados dos agentes e pode ser selecionado em KQL sem expor o conteúdo da requisição.

Investigação de falha: Quebre a propagação de contexto em uma das passagens e localize o primeiro span que sai do trace original.

## Tarefa 7: Revise o design

1. Responda a estas perguntas:

- O que quebra quando a injeção de contexto é omitida em uma fronteira?
- Quais campos estruturados são úteis sem expor conteúdo do cliente?
- Por que erros e traces lentos exigiriam tail sampling no collector em vez da razão de head-sampling usada por este laboratório?
- Como você correlacionaria anomalias simultâneas em um único incidente?
- Por que o alerta consome decisões de política emitidas em vez de repetir thresholds em KQL?

## Tarefa 8: Limpeza

**Remova recursos do Azure**

1. Execute `azd down --purge`.
2. Confirme que o workspace e o recurso Application Insights foram deletados.
3. Remova `.env` e evidência local. Deixar a exportação de telemetria ativa continua gerando custos de ingestão.

**Desative o ambiente virtual**

4. Execute este comando em todo terminal onde `(.venv)` apareça no prompt:

```powershell
deactivate
```

5. Confirme que `(.venv)` não aparece mais antes de mudar para outro diretório de laboratório.

## Resumo

Você criou spans OpenTelemetry reais, propagou W3C context, ativou políticas de latência, taxa de erro e anomalia de token, exportou propriedades consultáveis através de configuração segura do Azure Monitor e validou o ciclo de vida de um alerta acionável scheduled-query.
