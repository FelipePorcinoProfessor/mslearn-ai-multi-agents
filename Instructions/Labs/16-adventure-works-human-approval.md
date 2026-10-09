---
lab:
  title: 'Implementar fluxos de trabalho de aprovação humana duráveis'
  description: 'Construa um workflow de aprovação resumível para Adventure Works com escalonamento calibrado, eventos do Service Bus, estado no Cosmos DB e evidência de auditoria imutável.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Implementar fluxos de trabalho de aprovação humana duráveis

## Cenário do cliente

Agentes da Adventure Works podem recomendar reembolsos e exceções de política, mas ações de alto impacto devem pausar para uma revisão humana significativa. Uma flag pendente em memória não é suficiente: aprovações podem levar horas, processos reiniciam, decisões duplicadas chegam e trabalhos vencidos devem escalar sem perder o histórico.

## Cenário do laboratório

Você implementará uma máquina de estados de aprovação durável. O Cosmos DB armazena o estado atual do workflow e eventos de auditoria em append-only. O Service Bus transporta solicitações de aprovação e decisões dos revisores. O CLI submete trabalho, recebe eventos de aprovar ou rejeitar, retoma exatamente uma vez com concorrência otimista e escala aprovações expiradas.

<!-- ESPAÇO RESERVADO PARA DIAGRAMA DO LAB: Mostrar submissão de solicitação, decisão de risco, estado pendente durável, eventos de revisão do Service Bus, retomada do processamento e evidência de auditoria. -->

Ao final deste exercício, você será capaz de:

- Combinar confiança calibrada, impacto de negócio, exceções e ambiguidade em decisões de escalonamento.
- Persistir o estado de aprovação fora do processo e retomar após reinício.
- Tratar caminhos de aprovar, rejeitar, duplicado e vencido com segurança.
- Produzir feedback estruturado e evidência de auditoria imutável.

> **Importante**: Cosmos DB e Service Bus são cobráveis. As cargas sintéticas não contêm PII de clientes. Não coloque strings de conexão ou chaves em `.env`.

## Tarefa 1: Preparar o laboratório

1. Instale [Python 3.10 ou posterior](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) e [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).

Você precisa de uma assinatura do Azure e permissão para criar Cosmos DB, Service Bus e atribuições de função. Use sua identidade autenticada via `DefaultAzureCredential`.

**Clonar e abrir o repositório**

2. Se você ainda não fez isso, clone o [repositório de origem do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

3. Abra o repositório clonado no Visual Studio Code.

**Verificar ferramentas e autenticação**

4. Valide as ferramentas necessárias, credenciais e assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\16-adventure-works-human-approval
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação da arquitetura**

Revise `infra/main.bicep`, a solicitação sintética de reembolso `assets/workflow-state.schema.json`, `assets/adaptive-card.json`, `src/workflow.py` e `src/reviewer_webhook.py`. Antes de continuar, confirme que uma solicitação de alto risco se move de risco calibrado para estado pendente durável, envio autenticado do revisor, retomada exatamente-uma vez e evidência de auditoria idempotente.

## Tarefa 2: Construir o ambiente virtual

1. No Windows, crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

## Tarefa 3: Provisionar recursos do Azure

1. Revise os custos do Cosmos DB e Service Bus, além do acesso de plano de dados e de mensagens antes de provisionar.
2. Use apenas as cargas sintéticas fornecidas e um ambiente único.

`azd` provisiona a infraestrutura; o workflow de aprovação roda separadamente.

**Definir os valores de implantação**

3. Defina `$azureRegion` para uma região aprovada que suporte os serviços requeridos.
4. Substitua o valor de exemplo `eastus2` se necessário.
> **Grupo de recursos:** Se seu ambiente de laboratório fornece um resource group pré-criado, defina `$resourceGroupName` com seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um resource group único na sua assinatura.

> **Nota:** `AZURE_DEV_USER_AGENT` marca a provisão para atribuição e não é exportado para `.env`. Remova-o depois para evitar marcar comandos não relacionados.

**Validar e provisionar a infraestrutura**

5. Execute os seguintes comandos:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab16-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-approval-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
$principalId = az ad signed-in-user show --query id --output tsv
azd env set AZURE_PRINCIPAL_ID $principalId
az bicep build --file infra/main.bicep
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> **Nota:** Se a provisão falhar, inspecione o primeiro erro de implantação. Verifique a disponibilidade regional do Cosmos DB e Service Bus, nomes do namespace, ID do principal e permissões de atribuição de função. Corrija a causa e execute `azd provision` novamente.

**Verificar o ambiente gerado**

6. Depois que a provisão for bem-sucedida, valide que `.env` inclui o endpoint do Cosmos DB, nomes do banco de dados e do container, namespace e nomes de filas do Service Bus, e os valores do principal requeridos pela aplicação.
7. Mantenha apenas endpoints e nomes de recursos; não adicione strings de conexão, chaves ou tokens.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada trecho fornecido para seu local placeholder, remova o comentário `LAB PLACEHOLDER`, substitua apenas a linha ou bloco incompleto indicado e preserve a indentação ao redor.

> **Dica:** Depois de colar cada trecho em Python, valide sua indentação em relação à função ou classe ao redor antes de executar o código.

**Calibrar confiança bruta**

1. Em `src/workflow.py`, encontre `# LAB PLACEHOLDER 1`.
2. Substitua apenas a função incompleta `calibrate_confidence()` associada por:

```python
def calibrate_confidence(raw_confidence: float, curve_path: Path) -> float:
  """Map raw confidence to observed accuracy using the nearest calibration point."""
  curve = json.loads(curve_path.read_text(encoding="utf-8"))
  nearest = min(
    curve["points"],
    key=lambda point: abs(float(point["raw_confidence"]) - raw_confidence),
  )
  return float(nearest["observed_accuracy"])
```

Acurácia observada, em vez de uma confiança não calibrada do modelo, dirige os limites de revisão.

**Usar confiança calibrada na avaliação de risco**

3. Encontre `# LAB PLACEHOLDER 2`.
4. Substitua apenas a seguinte atribuição `calibrated` por:

```python
  calibrated = calibrate_confidence(
    float(request["raw_confidence"]),
    Path("assets/calibration-curve.json"),
  )
```

Isso deriva a confiança a partir da curva versionada em vez de confiar em um valor copiado na solicitação.

**Anexar evidência de auditoria imutável**

5. Encontre `# LAB PLACEHOLDER 3`.
6. Substitua apenas a seguinte instrução `raise NotImplementedError` por:

```python
    actor_hash = hashlib.sha256(actor.encode()).hexdigest()
    record = {
      "id": event_id,
      "event_id": event_id,
      "workflow_id": workflow_id,
      "event_type": event_type,
      "timestamp": utc_now(),
      "actor_hash": actor_hash,
      "previous_state": previous_state,
      "new_state": new_state,
      "policy_version": policy_version,
      "trace_id": trace_id,
      "rationale_category": rationale_category,
      "state_etag": state_etag,
      "state_version": state_version,
      "details": details,
    }
    try:
      self._audit.create_item(record)
    except exceptions.CosmosResourceExistsError:
      existing = self._audit.read_item(
        item=event_id,
        partition_key=workflow_id,
      )
      identity_fields = ("event_id", "workflow_id", "policy_version", "trace_id")
      if any(existing.get(field) != record.get(field) for field in identity_fields):
        raise RuntimeError(
          f"Audit event ID {event_id} already belongs to different evidence"
        )
```

O registro de auditoria usa o ID do evento como seu ID de documento. Uma reentrega aceita um registro existente somente depois de verificar seu workflow, política e identidade de trace; evidência conflitante falha fechada. O registro vincula uma transição ao estado persistido sem armazenar a identidade do revisor em texto claro. O estado do workflow também armazena `last_transition` na mesma gravação de concorrência otimista, assim uma replicação de auditoria falha permanece detectável e recuperável.

**Adicionar compensação de cancelamento**

7. Encontre `# LAB PLACEHOLDER 4`.
8. Adicione este ramo diretamente abaixo dele, mantendo o bloco final `else` existente:

```python
    elif decision == "CANCELLED":
      new_state = "CANCELLED"
      execution = {
        "mode": "synthetic",
        "status": "cancelled_before_execution",
        "executed_at": None,
      }
```

Cancelamento é uma transição terminal, não executante. A chamada `replace_item()` fornecida ainda aplica o ETag original.

**Expor cancelamento via CLI**

9. Em `src/main.py`, encontre `# LAB PLACEHOLDER 5`.
10. Substitua apenas a seguinte chamada `decide.add_argument()` por:

```python
  decide.add_argument(
    "--decision",
    choices=["approved", "rejected", "overridden", "cancelled"],
    required=True,
  )
```

A superfície de comando e a máquina de estados agora aceitam o mesmo vocabulário de decisões.

**Escalonar revisões expiradas de forma durável**

11. Em `src/workflow.py`, encontre `# LAB PLACEHOLDER 6`.
12. Substitua apenas o método incompleto `escalate_expired()` associado por:

```python
  def escalate_expired(self) -> list[str]:
    now = utc_now()
    query = "SELECT * FROM c WHERE c.state = 'WAITING_FOR_REVIEW' AND c.review_deadline < @now"
    expired = self._state.query_items(
      query=query,
      parameters=[{"name": "@now", "value": now}],
      enable_cross_partition_query=True,
    )
    escalated = []
    for item in expired:
      previous = item["state"]
      item["state"] = "ESCALATED"
      item["version"] += 1
      item["updated_at"] = now
      escalation_event_id = str(uuid.uuid4())
      item["last_transition"] = {
        "event_id": escalation_event_id,
        "event_type": "escalated",
        "actor_hash": hashlib.sha256(b"scheduler").hexdigest(),
        "previous_state": previous,
        "new_state": "ESCALATED",
        "timestamp": now,
      }
      updated = self._state.replace_item(
        item=item["id"],
        body=item,
        etag=item["_etag"],
        match_condition=MatchConditions.IfNotModified,
      )
      self.append_audit(
        item["id"], "escalated", "scheduler", previous, "ESCALATED", {},
        policy_version=updated["policy_version"],
        trace_id=updated["trace_id"],
        rationale_category="review_deadline_expired",
        event_id=escalation_event_id,
        state_etag=updated["_etag"],
        state_version=updated["version"],
      )
      with self._bus.get_queue_sender(self._request_queue) as sender:
        sender.send_messages(
          ServiceBusMessage(json.dumps(updated), message_id=str(uuid.uuid4()))
        )
      escalated.append(item["id"])
    return escalated
```

As mesmas exigências de concorrência otimista e auditoria se aplicam a transições acionadas pelo agendador.

**Verificar o código completado**

13. Verifique o código completado localmente:

```console
python -m py_compile src/workflow.py src/main.py src/reviewer_webhook.py src/active_learning.py
python scripts/preflight.py --require-complete
```

14. Confirme que a compilação não retorna saída.
15. Antes de provisionar, confirme que o preflight valida a solicitação sintética e o esquema; verificações de endpoint podem permanecer `not ready`.
16. Após a provisão e configuração de `.env`, confirme que cada verificação reporte `ready`.

## Tarefa 5: Executar a solução

1. Execute os comandos do workflow de aprovação:

```console
python -m src.main submit --input assets/refund-request.json
python -m src.main status --workflow-id <workflow-id>
python -m src.main decide --workflow-id <workflow-id> --decision approved --reviewer SYN-REVIEWER-01 --comment "Within exception authority"
python -m src.main resume
python -m src.main escalate
python -m src.reviewer_webhook --port 8080
python -m src.active_learning --output reports/active-learning.jsonl --evaluation reports/active-learning-evaluation.json
```

**Testar o adaptador HTTP**

2. Teste o adaptador HTTP localmente antes de conectar uma superfície de revisor hospedada.
3. Inicie o webhook em um terminal.
4. Envie os dados sintéticos do card a partir de outro:

```powershell
$body = @{
  workflow_id = '<workflow-id>'
  decision = 'APPROVED'
  comment = 'Synthetic local reviewer test'
  category = 'within_authority'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8080/api/reviewer-decisions' `
  -Headers @{'X-MS-CLIENT-PRINCIPAL-ID'='SYN-REVIEWER-01'} `
  -ContentType 'application/json' -Body $body
```

5. Confirme que a resposta local é HTTP 202 com `status: queued`.
6. Somente depois que isso funcionar, configure um fluxo opcional do Teams ou Power Automate para postar os mesmos campos através de um host protegido pela autenticação Microsoft Entra.

O produtor de decisão conecta-se somente ao Service Bus. O Cosmos DB é inicializado pelos comandos de transição de estado que submetem, inspecionam, retomam, escalam ou exportam workflows.

**Entender a saída**

`submit` retorna estado durável com `WAITING_FOR_REVIEW` ou `READY_TO_EXECUTE`, evidência de risco e um ETag. `decide` apenas enfileira um evento. `resume` o aplica, incrementa `version`, grava `human_review` e anexa um registro de auditoria vinculado. Decisões terminais duplicadas retornam `duplicate: true`. `escalate` retorna IDs de workflow movidos para `ESCALATED`. A saída de active-learning contém apenas exemplos rejeitados ou sobrescritos mais decisão agregada, justificativa e cobertura de trace.

## Tarefa 6: Validar a implementação

**Validar estado durável e evidência de auditoria**

1. Consulte o Cosmos DB e confirme que o estado atual sobrevive a reinícios.
2. Verifique que cada registro de auditoria, incluindo submetido, duplicado, decisão e eventos de escalonamento, contenha ID do workflow, ID do evento, timestamp UTC, hash do ator, estado anterior e novo, categoria da justificativa, versão da política, trace ID, `state_etag` e `state_version`.
3. Inspecione métricas de mensagens do Service Bus (incoming, active e completed) antes e depois de um POST ao webhook para provar que o caminho do revisor é assíncrono e observável.

**Validar o caminho do revisor**

4. Para uma verificação observável local, inicie o webhook.
5. POST com dados sintéticos do Adaptive Card com `Invoke-RestMethod`, incluindo `X-MS-CLIENT-PRINCIPAL-ID: SYN-REVIEWER-01`.
6. Confirme HTTP 202.
7. Observe o aumento na contagem da fila de decisões.
8. Execute `resume`.
9. Observe a diminuição da contagem da fila e um evento de auditoria vinculado no Cosmos.
10. Em um ambiente hospedado, aceite esse cabeçalho somente a partir da camada de autenticação Microsoft Entra da plataforma.

**Validar resultados do workflow**

11. Demonstre registros sintéticos aprovados e executados, rejeitados e fechados, sobrescritos e executados, e vencidos e escalados.
12. Inspecione os arquivos de active-learning e confirme que suas contagens correspondem aos registros rejeitados e sobrescritos no Cosmos.
13. Confirme que nenhuma ação é executada a partir de um estado pendente ou rejeitado.

**Validar os recursos do Azure**

14. No portal do Azure, valide apenas a conta do Cosmos DB provisionada, o banco de dados `approvals` e dois containers, o namespace do Service Bus e duas filas, e suas métricas.

Teams e Power Automate são superfícies externas opcionais de revisor e não são provisionados por este laboratório.

**Comparar com o padrão canônico de interação humana durável**

15. Compare o design manual deste laboratório com o padrão de interação humana do Durable Functions/Durable Task em [Human interaction in Durable Functions](https://learn.microsoft.com/azure/durable-task/common/durable-task-human-interaction).
16. No padrão canônico, uma orquestração espera por um evento externo nomeado de aprovação e cria um timer durável para o prazo. Ela faz uma corrida entre essas tarefas duráveis, cancela o timer quando a aprovação vence e segue o caminho de timeout ou escalonamento quando o timer vence.
17. Mapeie esses conceitos para este laboratório: o Service Bus transporta a decisão externa, o Cosmos DB armazena estado resumível e o deadline, `resume` aplica um evento exatamente uma vez, e `escalate` realiza a varredura equivalente ao timer para o deadline.
18. Registre uma troca (tradeoff). A arquitetura atual expõe mecânicas de fila e estado para aprendizado e funciona sem substituir a aplicação por Durable Functions, mas a aplicação possui a responsabilidade por segurança de replay, agendamento, tratamento de duplicatas e resolução de corrida que um framework de orquestrador durável normalmente coordena.

Isto é uma comparação conceitual opcional. Não substitua a arquitetura Service Bus/Cosmos DB do laboratório.

## Desafio opcional: Adicionar uma banda de revisores

Adicione uma segunda banda de confiança que roteie para um grupo diferente de revisores sintéticos.

**Saída esperada:** Uma solicitação nessa banda registra o limiar selecionado e o grupo de revisores e entra no estado de aprovação durável correto.

**Investigação de falha:** Retome a mesma decisão após um timeout simulado e prove que a ação protegida e o evento de auditoria não são duplicados.
## Tarefa 7: Revisar o design

1. Responda essas perguntas:

- Qual sinal deve sobrepor alta confiança do modelo?
- Por que o worker de retomada (resume worker) é responsável pela execução em vez do endpoint do revisor?
- Como você provaria que a supervisão humana é substancial e não mera formalidade (rubber-stamping)?

## Tarefa 8: Limpeza

**Remover recursos do Azure**

1. Execute `azd down --purge`.
2. Confirme que Cosmos DB e Service Bus foram deletados.
3. Remova `.env`.
4. Mantenha apenas o relatório sintético solicitado pelo instrutor.

**Desativar o ambiente virtual**

5. Execute este comando separadamente em cada terminal onde `(.venv)` apareça no prompt:

```powershell
deactivate
```

6. Confirme que `(.venv)` não aparece mais em nenhum terminal antes de mudar para outro diretório de laboratório.

## Resumo

Você implementou um workflow de aprovação humana durável com escalonamento baseado em risco, eventos assíncronos, retomada segura a reinícios, feedback de rejeição, escalonamento por timeout e evidência de auditoria imutável.
