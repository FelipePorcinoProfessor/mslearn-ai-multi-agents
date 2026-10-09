---
lab:
  title: 'Construir memória compartilhada persistente para agentes Foundry'
  description: 'Construa um Hosted Agent do Microsoft Foundry que recupera memória vetorial com escopo de paciente do Azure Cosmos DB com retenção, orçamento de contexto, auditoria e controles de consistência.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Construir memória compartilhada persistente para agentes Foundry

## Cenário do cliente

O agendamento, a navegação de cuidados e os agentes de suporte a medicação da Northwind Health precisam de preferências de paciente compartilhadas e revisadas. Um Coordenador de Memória deve fornecer evidência limitada com escopo por paciente, com isolamento consistente, comportamento de leitura-após-gravação, retenção e exclusão auditável.

## Cenário do laboratório

Você é o desenvolvedor da plataforma de memória. Você implementará a camada de memória personalizada no Azure Cosmos DB para NoSQL e então a conectará a um agente do Microsoft Agent Framework hospedado pelo Microsoft Foundry. O agente usa uma ferramenta local somente leitura para recordar memória de um paciente sintético configurado, constrói um contexto limitado e solicita uma resposta fundamentada a um modelo do Foundry. Gravações de memória, consolidação revisada e poda destrutiva permanecem operações administrativas explícitas via CLI.

<!-- ESPAÇADOR DE DIAGRAMA DO LABORATÓRIO: Mostre o Hosted Agent, a ferramenta de recall com escopo por paciente, a memória do Cosmos DB e os contêineres de auditoria, e os caminhos administrativos de gravação. -->

Você constrói um especialista reutilizável com uma interface controlada para outros agentes, não um modelo que se passa por vários agentes.

Ao final deste exercício, você será capaz de:

- Mapear memória de trabalho, episódica e semântica para padrões de persistência apropriados.
- Implementar memória vetorial com escopo de paciente usando Azure Cosmos DB e `VectorDistance`.
- Aplicar orçamento de contexto, políticas de retenção, poda e auditoria.
- Comparar consistência de sessão e eventual para comportamento de leitura-após-gravação.
- Hospedar um agente do Microsoft Agent Framework no Foundry e fundamentar suas respostas na memória personalizada do Cosmos DB.

> **Importante**: Validação ao vivo no Azure é necessária porque indexação vetorial, consumo de RU, comportamento de partição, TTL e consistência são comportamentos do serviço. A conta serverless é cobrável. Use apenas dados sintéticos e execute `azd down --purge` após a validação.

## Tarefa 1: Preparar o laboratório

Instale [Python 3.13](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI 1.27.1 or later](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Git](https://git-scm.com/downloads), [Visual Studio Code](https://code.visualstudio.com/download), e as extensões [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python), [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep) e [Foundry Toolkit](https://marketplace.visualstudio.com/items?itemName=ms-windows-ai-studio.windows-ai-studio). Você precisa de permissão para criar uma conta Cosmos DB, conta e projeto Foundry, implantações de modelo, Hosted Agent e atribuições de função. A pesquisa vetorial e a disponibilidade de modelos variam por região.

**Clonar e abrir o repositório**

1. Se você ainda não fez isso, clone o [repositório de origem do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.

**Verificar ferramentas e autenticação**

3. Valide as ferramentas necessárias, credenciais e assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\08-northwind-health-multi-agent-memory
az version
azd version
python --version
az account show --output table
```

4. Use `DefaultAzureCredential`.
5. Não use chaves de conta, strings de conexão, dados reais de pacientes ou partições de memória compartilhadas globalmente.

**Ponto de verificação da arquitetura**

Revise esses limites antes de editar:

| Limite | Componente |
|---|---|
| Conversa hospedada e ferramenta de recall somente leitura | `agent.py` |
| Memória durável com escopo por paciente | `src/memory_store.py` e o contêiner de memória |
| Contexto de modelo limitado | `src/context_budget.py` |
| Transferência de consistência de sessão | `src/consistency.py` |
| Retenção e exclusão | `src/retention.py` |
| Evidência de auditoria durável | Contêiner de auditoria |
| Recursos do Azure e entrada sintética | `infra/main.bicep` e `assets/memories.json` |

Antes de continuar, confirme que o Cosmos DB — não o histórico da conversa — é a autoridade durável de memória e que os registros de memória e auditoria usam contêineres separados.

> Não substitua operações do Cosmos por uma lista em memória ou cálculo vetorial local.

## Tarefa 2: Construir o ambiente virtual

1. Crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

2. Inspecione `assets/memories.json`; os IDs de paciente e as observações são sintéticos. O starter gera embeddings no momento da ingestão em vez de armazenar vetores fixos.

## Tarefa 3: Implantar os recursos do Azure

**Definir os valores de implantação**

1. Revise custo, cota de modelo e acesso antes do provisionamento.

Operações vetoriais do Cosmos DB, ambas as implantações de modelo do Foundry e o compute do Hosted Agent são cobráveis.

2. Use um ambiente único.
3. Use apenas dados sintéticos.
4. Remova os recursos após a validação.

`azd` provisiona os recursos Bicep. A ingestão e o recall de memória são executados separadamente.

5. Especifique uma região aprovada onde a pesquisa vetorial do Cosmos DB, Microsoft Foundry e ambas as implantações de modelo estejam disponíveis.
6. O exemplo a seguir usa `eastus2`; altere-o se sua assinatura tiver disponibilidade ou cota de modelo diferente.
> **Grupo de recursos:** Se seu ambiente de laboratório fornecer um grupo de recursos pré-criado, defina `$resourceGroupName` para seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um grupo de recursos exclusivo na sua assinatura.

**Validar e provisionar a infraestrutura**

7. Execute os seguintes comandos:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
az login
azd auth login
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab08-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
azd env new lab08-memory-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd provision
azd env get-values | Out-File .env -Encoding utf8
```

8. Se o provisionamento falhar, inspecione o primeiro erro de implantação do Azure. Disponibilidade regional do Cosmos DB ou do modelo, cota `GlobalStandard` e permissões de atribuição de função são causas comuns.
9. Corrija a configuração ou permissão relevante e, em seguida, execute `azd provision` novamente.

**Verificar o ambiente gerado**

10. Confirme que `.env` inclui `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL_NAME`, `AZURE_COSMOS_ENDPOINT`, o banco de dados e os nomes dos contêineres de memória/auditoria, `AZURE_OPENAI_ENDPOINT` e o nome da implantação de embedding. `AZURE_OPENAI_ENDPOINT` aponta para a conta `AIServices` do Foundry, não para uma conta `kind: OpenAI` separada.
11. Aguarde a propagação do Azure RBAC de plano de dados.
12. Não adicione chaves de conta, strings de conexão ou tokens.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada trecho fornecido para sua localização placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco incompleto indicado e preserve a indentação circundante.

O construtor já cria um `CosmosClient` async reutilizável com `DefaultAzureCredential` e consistência de sessão. Mantenha esse cliente enquanto o store estiver em uso.

> **Dica:** Depois de copiar e colar cada trecho Python, valide sua indentação em relação à função ou classe circundante antes de executar o código.

**Persistir uma memória com embedding**

1. Em `src/memory_store.py`, encontre o marcador exato `# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.`.

2. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
    patient_id = str(memory["patientId"])
    self._authorize(patient_id)
    item = {
      **memory,
      "embedding": self._embeddings.embed(str(memory["content"])),
    }
    response = await self._memories.upsert_item(item)
    headers = response.get_response_headers()
    return {
      "id": response["id"],
      "patientId": response["patientId"],
      "request_charge": float(headers.get("x-ms-request-charge", 0)),
      "session_token": headers.get("x-ms-session-token"),
    }
```

A autorização ocorre antes do embedding ou I/O. Os diagnósticos retornados expõem o custo de RU e o token de sessão sem retornar o conteúdo da memória.

O contêiner define `defaultTtl` para 2.592.000 segundos. Um item sem `ttl` herda esse padrão do contêiner, um item positivo `ttl` o substitui, e `ttl: -1` no item desativa a expiração para esse item enquanto o TTL permanece habilitado no contêiner.

**Executar recall vetorial com escopo de partição**

3. Em `src/memory_store.py`, encontre o marcador exato `# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.`.

4. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
    self._authorize(patient_id)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 20:
      raise ValueError("top_k must be an integer from 1 through 20")
    embedding = self._embeddings.embed(query_text)
    query = f"""
      SELECT TOP {top_k}
        c.id, c.patientId, c.content, c.importance, c.memoryType,
        c.critical, c.timestamp, c.ttl,
        VectorDistance(c.embedding, @embedding) AS vector_distance
      FROM c
      WHERE c.patientId = @patientId
      ORDER BY VectorDistance(c.embedding, @embedding)
    """
    response_headers: dict[str, str] = {}
    iterator = self._memories.query_items(
      query=query,
      parameters=[
        {"name": "@patientId", "value": patient_id},
        {"name": "@embedding", "value": embedding},
      ],
      partition_key=patient_id,
      response_hook=lambda headers, _: response_headers.update(headers),
    )
    results = [item async for item in iterator]
    request_charge = float(response_headers.get("x-ms-request-charge", 0))
    for item in results:
      item["request_charge"] = request_charge
    return results
```

Apenas o inteiro validado é interpolado em `TOP`; o ID do paciente e o embedding continuam sendo parâmetros. A chave de partição impõe uma única partição física por paciente.

O laboratório usa um índice vetorial `quantizedFlat`, mas testes significativos de desempenho de índice exigem uma população vetorial realmente grande. Use pelo menos 1.000 vetores antes de tirar conclusões sobre desempenho de índice ou latência; os seis registros sintéticos iniciais validam o comportamento de consulta, não a escala ou latência do índice vetorial.

**Gravar evidência de auditoria sem conteúdo**

5. Em `src/memory_store.py`, encontre o marcador exato `# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.`.

6. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
    self._authorize(patient_id)
    await self._audit.upsert_item(
      {
        "id": event_id or str(uuid4()),
        "patientId": patient_id,
        "operation": operation,
        "memoryIds": sorted(set(memory_ids)),
        "reason": reason,
        "timestamp": event_timestamp or datetime.now(UTC).isoformat(),
      }
    )
```

O evento de auditoria identifica a operação e os registros afetados, mas deliberadamente exclui conteúdo de memória e embeddings.

**Provar consistência de leitura-após-gravação**

7. Em `src/consistency.py`, encontre o marcador exato `# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.`.

8. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  diagnostics = await store.upsert_memory(memory)
  session_token = diagnostics.get("session_token")
  if not session_token:
    raise RuntimeError("The write response did not include a session token")
  item = await store._memories.read_item(
    item=memory["id"],
    partition_key=memory["patientId"],
    session_token=session_token,
  )
  return {
    "write_id": diagnostics["id"],
    "read_id": item["id"],
    "patientId": item["patientId"],
    "session_token_transferred": True,
    "request_charge": diagnostics["request_charge"],
  }
```

A leitura imediata por ponto usa tanto a mesma chave de partição quanto o token de escrita. Um cliente com consistência eventual não pode fornecer essa fronteira explícita de leitura-após-gravação.

**Construir contexto de memória delimitado**

9. Em `src/context_budget.py`, encontre o marcador exato `# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.`.

10. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  if token_budget < 1:
    raise ValueError("token_budget must be positive")
  recent_count = max(1, (len(memories) * 3 + 9) // 10) if memories else 0
  recent = sorted(memories, key=lambda item: str(item["timestamp"]), reverse=True)[:recent_count]
  ranked = sorted(
    memories,
    key=lambda item: (
      float(item.get("importance", 0)) * 0.5
      + (1.0 / (1.0 + float(item.get("vector_distance", 1)))) * 0.5
    ),
    reverse=True,
  )
  ordered = recent + [item for item in ranked if item not in recent]
  selected: list[dict[str, Any]] = []
  blocks: list[str] = []
  used = estimate_tokens("<patient_memory>\n</patient_memory>")
  for item in ordered:
    block = f"<memory id=\"{item['id']}\">{item['content']}</memory>"
    cost = estimate_tokens(block)
    if used + cost <= token_budget:
      selected.append(item)
      blocks.append(block)
      used += cost
  return {
    "selected_ids": [item["id"] for item in selected],
    "token_count": used,
    "context": "<patient_memory>\n" + "\n".join(blocks) + "\n</patient_memory>",
  }
```

Registros recentes recebem uma reserva de 30% antes que os candidatos restantes sejam ranqueados por importância e distância vetorial. Delimitadores explícitos separam memória armazenada das instruções.

**Aplicar retenção e exclusão auditada**

11. Em `src/retention.py`, encontre o marcador exato `# LAB PLACEHOLDER 6: Replace this line with the Task 6 sample.`.

12. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  store._authorize(patient_id)
  eligible_ids = sorted(
    str(memory["id"])
    for memory in memories
    if memory.get("patientId") == patient_id
    and not bool(memory.get("critical"))
    and int(memory.get("ttl", -1)) > 0
    and datetime.fromisoformat(
      str(memory["timestamp"]).replace("Z", "+00:00")
    ) + timedelta(seconds=int(memory["ttl"])) <= datetime.now(UTC)
    and float(memory.get("importance", 0)) <= 4.0
  )
  if dry_run:
    return {"status": "dry_run", "eligible_ids": eligible_ids, "deleted_count": 0}
  for memory_id in eligible_ids:
    await store._memories.delete_item(item=memory_id, partition_key=patient_id)
  if eligible_ids:
    await store.write_audit(
      patient_id,
      "retention_prune",
      eligible_ids,
      "expired noncritical memory with finite TTL and importance at or below 4.0",
    )
  return {
    "status": "applied",
    "eligible_ids": eligible_ids,
    "deleted_count": len(eligible_ids),
  }
```

Execução simulada (dry run) e apply usam a mesma regra determinística de elegibilidade. O carimbo de data/hora armazenado mais o TTL do Cosmos DB devem estar no passado antes de um registro ser elegível. Toda exclusão permanece no escopo da partição, e registros críticos, não expirados ou com TTL indefinido são preservados.

**Rever consolidação protegida**

Nenhuma substituição de código é necessária.

13. Revise os registros episódicos `mem-100-3`, `mem-100-4` e `mem-100-5`.
14. Execute a consolidação primeiro com `--dry-run`.
15. Verifique que as três fontes suportam uma preferência de lembrete repetida.
16. Em seguida, aplique-a.

O método concluído realiza leitura pontual de cada fonte da partição do paciente, deriva o TTL a partir das fontes e então envia a criação de memória semântica e cada patch condicional por ETag de fonte em um único lote transacional do Cosmos DB. Como todos os registros usam a mesma chave de partição `patientId`, o lote ou confirma todas as alterações de linhagem ou nenhuma. O ID semântico determinístico e o ID do evento de auditoria tornam as tentativas idempotentes; a auditoria permanece em seu contêiner separado e pode ser reenviada seguramente após o lote de memória do commit.

**Verificar o código concluído**

17. Execute o seguinte comando:

```powershell
python scripts/preflight.py
```

O preflight deve terminar com `Preflight passed`.

18. Execute-o somente após completar todos os seis placeholders de código para que valide a implementação do aprendiz em vez do starter não modificado.

## Tarefa 5: Executar a solução

**Executar as operações de memória**

1. Carregue as memórias sintéticas e capture diagnósticos de escrita:

```powershell
python -m src.main ingest --file assets/memories.json
```

2. Relembre a memória para um paciente e construa o contexto:

```powershell
python -m src.main recall --patient-id synthetic-patient-100 --query "medication tolerance and appointment preferences" --top 5 --budget 500
```

3. Valide a consistência de leitura-após-gravação:

```powershell
python -m src.main consistency --patient-id synthetic-patient-100
```

4. Execute uma poda em execução simulada (dry-run) antes de permitir a exclusão:

```powershell
python -m src.main prune --patient-id synthetic-patient-100 --dry-run
```

5. Consolide evidências episódicas repetidas em um padrão semântico revisado.
6. Nunca deduza um padrão clínico a partir desses exemplos de lembrete.

```powershell
python -m src.main consolidate --patient-id synthetic-patient-100 --source-id mem-100-3 --source-id mem-100-4 --source-id mem-100-5 --summary "Repeatedly requests written reminders before synthetic follow-ups." --reviewer-id reviewer-07 --dry-run
python -m src.main consolidate --patient-id synthetic-patient-100 --source-id mem-100-3 --source-id mem-100-4 --source-id mem-100-5 --summary "Repeatedly requests written reminders before synthetic follow-ups." --reviewer-id reviewer-07
```

**Entender a saída**

A ingestão reporta cada ID de memória, partição do paciente, consumo de RU e se o Cosmos retornou um token de sessão; ela não ecoa o conteúdo. O recall retorna um array `retrieved_memories` contendo os registros autorizados do paciente em ordem ascendente de `vector_distance` e seu consumo de RU de consulta. Seu objeto `bounded_context` lista IDs selecionados, estimativa de contagem de tokens e um bloco delimitado `<patient_memory>`. A saída da poda separa IDs elegíveis de `deleted_count`, enquanto a consolidação distingue `dry_run` de `consolidated` e registra a linhagem de fontes retidas.

**Executar o Coordenador de Memória localmente**

7. Abra um segundo terminal na pasta do laboratório.
8. Ative o mesmo ambiente virtual e inicie o servidor Responses.
9. Mantenha este terminal em execução:

```powershell
. ./.venv/Scripts/Activate.ps1
azd ai agent run memory-coordinator --no-client
```

10. No primeiro terminal, invoque o agente local com uma pergunta específica do paciente:

```powershell
azd ai agent invoke memory-coordinator --local --new-session "What reminder and appointment preferences should the care team consider? Cite the supporting memory IDs."
```

`AGENT_PATIENT_ID` vincula a ferramenta de recall a `synthetic-patient-100` para autorização e escopo de partição; o modelo não pode escolher um ID de paciente.

11. Confirme que a resposta cita IDs de memória recuperados e não inventa detalhes fora do contexto limitado.
12. Pressione **Ctrl+C** no terminal do servidor quando a validação local estiver completa.

**Implantar e invocar o Hosted Agent**

13. Faça o deploy do mesmo código testado no Foundry e então invoque o agente remoto:

```powershell
azd deploy memory-coordinator
azd ai agent invoke memory-coordinator --new-session "What reminder and appointment preferences should the care team consider? Cite the supporting memory IDs."
```

O Foundry hospeda o endpoint Responses e a chamada ao modelo. A ferramenta consulta o Cosmos DB usando a identidade gerenciada do projeto; a memória do paciente permanece no Cosmos DB.

## Tarefa 6: Validar a implementação

Inspecione a saída ao vivo de **Executar a solução**, então complete o portal e as verificações adicionais abaixo. O preflight local sozinho não valida esses comportamentos de serviço.

**Revisar evidências dos comandos já executados**

1. Use a saída do terminal de **Executar a solução** para confirmar:

- `ingest` reporta cada ID escrito, `patientId`, consumo de RU e um token de sessão sem ecoar o conteúdo da memória.
- `recall` retorna somente registros para `synthetic-patient-100`. Confirme que os valores `vector_distance` em `retrieved_memories` estão em ordem ascendente, cada registro reporta o mesmo consumo de consulta `request_charge`, e `bounded_context.token_count` não é maior que 500.
- `consistency` reporta `write_id` e `read_id` correspondentes, `session_token_transferred: true` e o consumo de RU de escrita.
- `prune --dry-run` reporta `status: dry_run`, `deleted_count: 0` e os IDs elegíveis enquanto preserva o registro crítico.
- A execução simulada (dry-run) da consolidação reporta três registros fonte e não realiza gravações. A execução aplicada reporta `status: consolidated`, um ID de memória semântica, os três IDs de fonte retidos e diagnósticos do lote transacional.
- Tanto as invocações local quanto a implantada do agente chamam `recall_patient_memory`, citam IDs de memória de suporte e limitam suas afirmações ao contexto delimitado.

**Inspecionar os registros persistidos no portal do Azure**

2. No [portal Microsoft Foundry](https://ai.azure.com), abra o projeto provisionado para este laboratório. Confirme que as implantações `gpt-5.4-mini` e `text-embedding-3-small` existem e que `northwind-health-memory-coordinator` tem uma versão implantada.
3. No [portal do Azure](https://portal.azure.com), abra a conta Cosmos DB provisionada para este laboratório.
4. Selecione **Explorador de dados (Data Explorer)** > **clinical-memory-db** > **patient-memories** > **Itens (Items)**.
5. Abra uma memória ingerida e confirme que ela contém `patientId`, `schemaVersion`, `memoryType`, `importance`, `timestamp`, `ttl` e um array `embedding`. A política de embedding vetorial no contêiner requer 1.536 dimensões.
6. Abra `mem-100-3`, `mem-100-4` e `mem-100-5`. Após a consolidação aplicada, confirme que os três documentos fonte permanecem e contêm o mesmo ID de memória semântica `consolidatedInto`.
7. Abra o documento correspondente `semantic_pattern` e confirme que `sourceMemoryIds` contém os três IDs fonte e `reviewerId` é `reviewer-07`.

Essas verificações no portal validam persistência e linhagem. Elas não substituem as verificações do terminal para ordenação vetorial, consumo de RU, orçamento de contexto ou transferência de token de sessão.

**Completar as verificações ao vivo restantes**

8. Primeiro, execute novamente o comando de consolidação aplicada **antes da poda**:

```powershell
python -m src.main consolidate --patient-id synthetic-patient-100 --source-id mem-100-3 --source-id mem-100-4 --source-id mem-100-5 --summary "Repeatedly requests written reminders before synthetic follow-ups." --reviewer-id reviewer-07
```

9. Espere `status: already_consolidated` com os mesmos IDs semânticos e de fonte, confirmando que a reconciliação por retry não cria uma memória semântica duplicada e restaura seguramente o evento de auditoria determinístico se necessário.

10. Em seguida, aplique a política de retenção. Este comando exclui os registros não críticos, de TTL finito, então execute-o somente após completar as verificações de consolidação e linhagem acima:

```powershell
python -m src.main prune --patient-id synthetic-patient-100
```

11. Confirme que a saída reporta `status: applied` e um `deleted_count` diferente de zero.
12. Então, no Explorador de dados (Data Explorer), selecione **clinical-memory-db** > **memory-audit** > **Itens (Items)**.
13. Confirme que o evento de auditoria `retention_prune` contém o ID do paciente, operação, IDs de memória afetados, motivo e timestamp, mas nenhum conteúdo de memória ou embedding.

A fronteira de autorização entre pacientes é uma salvaguarda no nível do código em vez de um cenário CLI separado.

14. Revise `_authorize` em `src/memory_store.py` e confirme que ele lança `PermissionError` antes do embedding ou I/O do Cosmos DB quando o paciente solicitado difere do paciente vinculado ao store.

## Desafio opcional: Controlar a consolidação de memória

Adicione um campo de confiança sintético e consolide apenas evidências com confiança igual ou superior a um limite documentado.

**Saída esperada:** Evidência de baixa confiança permanece no histórico de fonte, mas não aparece no lembrete consolidado; evidências aceitas registram o limite e o revisor.

**Investigação de falha:** Repita a mesma solicitação de consolidação e determine se idempotência ou deduplicação evita uma memória semântica duplicada.

## Tarefa 7: Revisar o design

1. Responda a estas perguntas:

- Quais campos de memória devem ser imutáveis após a criação?
- Como uma contradição deve suplantar uma memória mais antiga sem destruir o histórico de auditoria?
- Quando é necessário transferir explicitamente o token de sessão em vez do gerenciamento de token local ao cliente?
- O que uma consulta de verificação de direito à exclusão precisaria provar?

## Tarefa 8: Limpar

**Remover recursos do Azure**

1. Execute o seguinte comando:

```powershell
azd down --purge --force
```

2. Confirme que a conta Cosmos DB, a conta e o projeto Foundry, as implantações de modelo e o Hosted Agent foram excluídos.
3. Remova `.env`.

**Desativar o ambiente virtual**

4. Execute este comando em todo terminal onde `(.venv)` aparece no prompt:

```powershell
deactivate
```

5. Confirme que `(.venv)` não aparece mais antes de mudar para outro diretório de laboratório.

## Resumo

Você implementou persistência de memória vetorial ao vivo, isolamento por paciente, consistência de leitura-após-gravação, orçamento de contexto, retenção e padrões de auditoria com Azure Cosmos DB para NoSQL.
