---
lab:
  title: 'Implementar RAG avançado com Azure AI Search'
  description: 'Construir e validar um pipeline de recuperação roteada híbrida, vetorial e semântica contra um Azure AI Search em execução.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Implementar RAG avançado com Azure AI Search

## Cenário do cliente

Northwind Health precisa de recuperação fundamentada em um formulário sintético, diretriz clínica e referência laboratorial. Identificadores exatos devem permanecer pesquisáveis, consultas conceituais devem se beneficiar da similaridade vetorial e o ranqueamento semântico deve melhorar a ordem e as legendas do conjunto de candidatos. A equipe de recuperação também precisa de evidência de que a escolha de chunking (fragmentação) melhora a qualidade o bastante para justificar o tamanho do índice e a latência.

## Cenário do laboratório

Compare chunking, perfis de embedding, modos de consulta e roteamento sobre seis documentos-pai sintéticos: dois monografias de formulário, duas diretrizes e duas referências laboratoriais. Tópicos sobrepostos tornam a recuperação de fonte única e cross-domain observável. Este lab recupera apenas evidência; não constrói um chatbot nem gera aconselhamento ao paciente.

Gere duas variantes por pai: **fixed overlap** usa janelas de 180 caracteres com sobreposição de 40 caracteres; **structural parent-child** cria um chunk por seção com seu título de pai e cabeçalho. A primeira pode dividir seções ou omitir títulos; a segunda repete texto contextual. Meça a troca em vez de assumir que uma é melhor.

### Entenda os ativos JSON fornecidos

| Ativo | Papel |
|---|---|
| `assets/source-documents.json` | Corpus de origem: IDs estáveis, títulos, categorias, rótulos de origem e duas seções escritas por pai. Referências sintéticas, não registros de pacientes nem política autoritativa. |
| `assets/chunk-strategies.json` | Parâmetros de chunking reproduzíveis, não chunks pré-construídos. |
| `assets/queries.json` | Três queries rotuladas por relevância: busca exata de medicação, questão laboratorial conceitual e coordenação cross-domain. IDs de pai esperados devem pontuar na recuperação; eles não são injetados nas queries. |
| `assets/documents.json` | Apenas um marcador de descontinuação. Não ingerir isto nem passá-lo para `compare`. |

Gere `artifacts-generated-chunks.json` a partir dos dois primeiros ativos. Use este mesmo artefato para ingestão e comparação; ele preserva configurações, chunks, linhagem de pai, metadados de seção e limites de caracteres.

### Siga o experimento de recuperação

Carregue ambas as estratégias de chunk em três índices por categoria. Cada chunk tem um vetor baseline apenas de conteúdo e um vetor content-aware incorporando categoria, título, ID do pai e posição. Roteie queries para índices relevantes e compare modos vector, hybrid e semantic, filtrando cada conjunto de resultados para uma estratégia.

Agregue mean reciprocal rank (MRR) e latência por estratégia, modo e perfil de embedding. MRR mede a posição do primeiro pai esperado, não correção clínica, completude ou segurança. Três queries sintéticas demonstram a mecânica; a seleção de produção requer um conjunto de avaliação representativo maior.

Ao final deste exercício, você será capaz de:

- Projetar campos pesquisáveis, filtráveis, vetoriais e semânticos para índices especializados.
- Gerar conjuntos de chunks executáveis de fixed-overlap e structural parent-child com limites registrados.
- Fazer upload de ambos os conjuntos gerados com autenticação por identidade gerenciada.
- Executar busca híbrida com `SearchClient`, `VectorizedQuery` e ranqueamento semântico.
- Roteiar queries através de fontes de conhecimento e comparar MRR, ranqueamento e latência por estratégia de chunk e perfil de embedding.

> **Importante**: Validação ao vivo no Azure é necessária porque RRF híbrido e ranqueamento semântico são comportamentos do serviço. Azure AI Search Standard e Azure OpenAI são serviços cobrados; use quota aprovada pelo instrutor e execute `azd down --purge` após a validação.

## Tarefa 1: Preparar o laboratório

Instale [Python 3.11 ou posterior](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Git](https://git-scm.com/downloads), [Visual Studio Code](https://code.visualstudio.com/download), e as extensões [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) e [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep). Você precisa de permissão para criar recursos Azure AI Search e Azure OpenAI e atribuições de função. Sua região deve suportar o deployment de embedding selecionado.

**Clone e abra o repositório**

1. Se ainda não o fez, clone o [repositório fonte do lab](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.

**Verifique ferramentas e autenticação**

3. Valide as ferramentas necessárias, credenciais e assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\07-northwind-health-advanced-rag
az version
azd version
python --version
az account show --output table
```

Todos os documentos são sintéticos.

4. Autentique-se com `DefaultAzureCredential`.
5. Nunca adicione chaves de administrador do Search ou chaves de modelo em `.env`.

**Ponto de verificação de arquitetura**

Revise estes componentes antes de editar:

| Componente | O que localizar |
|---|---|
| `assets/source-documents.json` | Dois documentos-fonte em cada categoria |
| `assets/chunk-strategies.json` | Parâmetros fixed-overlap e structural parent-child |
| `assets/queries.json` | Três queries rotuladas por relevância |
| `assets/documents.json` | Marcador de descontinuação; não ingerir |
| `src/` e `infra/main.bicep` | Geração local de chunks e as operações dependentes do Azure: embedding, indexação, ingestão, roteamento e busca |

Antes de continuar, confirme quais operações rodam localmente e quais requerem Azure AI Search ou Azure OpenAI.

> Não substitua chamadas de serviço por matemática de similaridade local ou scores pré-computados.

## Tarefa 2: Criar o ambiente virtual

1. Crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

**Gere os conjuntos de chunks**

2. Antes do provisionamento, inspeccione `assets/source-documents.json` e `assets/chunk-strategies.json`.
3. Confirme que todo registro é sintético e explique como `size_chars`, `overlap_chars`, limites de seção e contexto de título do pai podem afetar a recuperação.

4. Gere ambos os conjuntos de chunks a partir dos mesmos documentos-fonte:

```powershell
python -m src.main generate-chunks --source assets/source-documents.json --strategies assets/chunk-strategies.json --output artifacts-generated-chunks.json
$chunks = Get-Content artifacts-generated-chunks.json -Raw | ConvertFrom-Json
$chunks.strategy_summaries | Format-Table strategy,chunk_count
$chunks.strategy_summaries.boundaries | Select-Object -First 8 | Format-Table id,parent_id,start,end,section_heading
```

5. Não edite manualmente o artefato gerado.
6. Altere os documentos-fonte ou a configuração da estratégia e regenere-o para que os limites registrados permaneçam reproduzíveis.

## Tarefa 3: Provisionar os recursos do Azure

**Defina os valores de deployment**

1. Revise custo, quota de modelos e acesso antes do provisionamento.

Azure AI Search capacity e chamadas de embedding do Azure OpenAI são cobradas.

2. Use um ambiente único e delete-o após a validação.

`azd` provisiona a infraestrutura. Geração de chunks é local; ingestão e busca rodam separadamente contra o Azure.

3. Defina `$azureRegion` para uma região aprovada que suporte Azure AI Search Standard e Global Standard `text-embedding-3-small`. O exemplo usa `eastus2`; capacidade regional varia.

4. Mude-o se necessário para sua assinatura e disponibilidade atual de serviço.
> **Grupo de recursos (Resource group):** Se seu ambiente de lab fornecer um grupo de recursos pré-criado, defina `$resourceGroupName` para seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um grupo de recursos único na sua assinatura.

**Valide e faça o provisionamento da infraestrutura**

5. Execute os comandos a seguir:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
az login
azd auth login
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab07-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
az bicep build --file infra/main.bicep
azd env new lab07-rag-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
azd provision
azd env get-values | Out-File .env -Encoding utf8
```

6. Se o provisionamento falhar, inspecione o primeiro erro de deployment do Azure. Disponibilidade regional de modelo ou de pesquisa, quota de modelo e permissões de atribuição de função são causas comuns.
7. Corrija a configuração de ambiente relevante ou permissão, então execute `azd provision` novamente.

**Verifique o ambiente gerado**

8. Depois que o provisionamento for bem-sucedido, valide que `.env` inclua `AZURE_SEARCH_ENDPOINT`, `AZURE_OPENAI_ENDPOINT` e `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`. Atribuições de função concedem ao seu principal Search Service Contributor, Search Index Data Contributor e Cognitive Services OpenAI User.
9. Aguarde vários minutos para a propagação de RBAC.
10. Não adicione chaves admin ou chaves de modelo em `.env`.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada snippet fornecido para seu local placeholder, mantenha o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco indicado como incompleto e preserve a indentação ao redor.

1. Use a saída `generate-chunks` da Tarefa 2; regenere apenas se a fonte ou configuração mudou.
2. Inspecione `artifacts-generated-chunks.json`.
3. Confirme que ambos os summaries de estratégia registram sua configuração, contagem de chunks, IDs de pai e limites de caracteres.

> Dica: Depois de copiar e colar cada snippet Python, valide sua indentação em relação à função ou classe circundante antes de executar o código.

**Crie índices vetoriais especializados**

4. Em `src/index_manager.py`, localize o marcador exato `# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.`

5. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  client = SearchIndexClient(endpoint=endpoint, credential=credential)
  fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SearchableField(name="title", type=SearchFieldDataType.String),
    SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="chunk_order", type=SearchFieldDataType.Int32, sortable=True),
    SimpleField(name="chunk_strategy", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="boundary_start", type=SearchFieldDataType.Int32),
    SimpleField(name="boundary_end", type=SearchFieldDataType.Int32),
    SearchableField(name="section_heading", type=SearchFieldDataType.String),
    SearchField(
      name="content_vector",
      type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
      searchable=True,
      vector_search_dimensions=vector_dimensions,
      vector_search_profile_name="clinical-vector-profile",
    ),
    SearchField(
      name="optimized_vector",
      type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
      searchable=True,
      vector_search_dimensions=vector_dimensions,
      vector_search_profile_name="clinical-vector-profile",
    ),
  ]
  vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="clinical-hnsw")],
    profiles=[
      VectorSearchProfile(
        name="clinical-vector-profile",
        algorithm_configuration_name="clinical-hnsw",
      )
    ],
  )
  semantic_search = SemanticSearch(
    configurations=[
      SemanticConfiguration(
        name=semantic_configuration,
        prioritized_fields=SemanticPrioritizedFields(
          title_field=SemanticField(field_name="title"),
          content_fields=[SemanticField(field_name="content")],
          keywords_fields=[SemanticField(field_name="section_heading")],
        ),
      )
    ]
  )
  created = []
  for index_name in INDEX_NAMES.values():
    index = SearchIndex(
      name=index_name,
      fields=fields,
      vector_search=vector_search,
      semantic_search=semantic_search,
    )
    created.append(client.create_or_update_index(index).name)
  return created
```

O mesmo schema governado suporta três índices roteados independentemente. As dimensões vetoriais vêm da configuração, então mudar o modelo de embedding não requer editar o código-fonte.

**Gere embeddings ordenados**

6. Em `src/embeddings.py`, localize o marcador exato `# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.`

7. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  if not texts:
    raise ValueError("At least one embedding input is required")
  response = client.embeddings.create(model=deployment, input=list(texts))
  return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
```

O nome do deployment é parametrizado através da output azd. Ordenar pelo índice de resposta preserva o mapeamento documento-para-vetor do chamador.

**Embed e faça upload de ambas as estratégias**

8. Em `src/ingest.py`, localize o marcador exato `# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.`

9. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  baseline_vectors = embed_texts(
    embedding_client,
    embedding_deployment,
    [embedding_text(document, "baseline") for document in documents],
  )
  optimized_vectors = embed_texts(
    embedding_client,
    embedding_deployment,
    [embedding_text(document, "content-aware") for document in documents],
  )
  groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
  for document, baseline, optimized in zip(
    documents, baseline_vectors, optimized_vectors, strict=True
  ):
    upload_document = {
      **document,
      "content_vector": baseline,
      "optimized_vector": optimized,
    }
    key = (str(document["category"]), str(document["chunk_strategy"]))
    groups.setdefault(key, []).append(upload_document)

  counts: dict[str, int] = {}
  for (category, strategy), group in groups.items():
    client = SearchClient(endpoint, INDEX_NAMES[category], credential)
    results = client.upload_documents(group)
    failed = [result.key for result in results if not result.succeeded]
    if failed:
      raise RuntimeError(f"Index upload failed for document keys: {failed}")
    counts[f"{strategy}:{category}"] = len(results)
  return counts
```

Ambos os perfis são gerados a partir da mesma lista ordenada de documentos, enquanto batches separados por categoria/estratégia mantêm evidência de ingestão atribuível.

**Roteie por intenção explícita**

10. Em `src/router.py`, localize o marcador exato `# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.`

11. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  normalized = query.casefold()
  intent_terms = {
    "formulary": {"medication", "drug", "atorvastatin", "contraindication", "therapy"},
    "guidelines": {"guideline", "protocol", "recommendation", "coordinate", "how should"},
    "labs": {"lab", "a1c", "range", "test", "monitoring"},
  }
  matched = [
    category
    for category, terms in intent_terms.items()
    if any(term in normalized for term in terms)
  ]
  if len(matched) != 1:
    return list(INDEX_NAMES.values())
  return [INDEX_NAMES[matched[0]]]
```

Uma intenção clara roteia de forma estreita. Queries multifator ou não classificadas espalham para os três índices em vez de descartar silenciosamente uma fonte relevante.

**Execute busca vetorial, híbrida e semântica**

12. Em `src/search_pipeline.py`, localize o marcador exato `# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.`

13. Substitua somente a linha `raise NotImplementedError` abaixo dele por:

```python
  if mode not in {"vector", "hybrid", "semantic"}:
    raise ValueError(f"Unsupported search mode: {mode}")
  if vector_field not in {"content_vector", "optimized_vector"}:
    raise ValueError(f"Unsupported vector field: {vector_field}")

  search_client = SearchClient(endpoint, index_name, credential)
  options: dict[str, Any] = {
    "search_text": None if mode == "vector" else query,
    "filter": filter_expression,
    "top": top,
    "select": [
      "id", "title", "source", "parent_id", "chunk_strategy",
      "boundary_start", "boundary_end", "section_heading", "content",
    ],
  }
  if mode in {"vector", "hybrid"}:
    query_vector = embed_texts(
      embedding_client, embedding_deployment, [query]
    )[0]
    options["vector_queries"] = [
      VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top,
        fields=vector_field,
        weight=vector_weight,
      )
    ]
  if mode in {"hybrid", "semantic"}:
    options.update(
      query_type="semantic",
      semantic_configuration_name=semantic_configuration,
      query_caption="extractive",
    )

  output = []
  for result in search_client.search(**options):
    row = dict(result)
    row["citation"] = f"{result['title']} ({result['source']}#{result['id']})"
    row["captions"] = [
      getattr(caption, "text", str(caption))
      for caption in (result.get("@search.captions") or [])
    ]
    output.append(row)
  return output
```

Cada modo usa Azure AI Search. O filtro de estratégia impede conjuntos de candidatos mistos, e os IDs retornados, limites, scores do serviço, scores do reranker, legendas e citações determinísticas permanecem disponíveis para avaliação.

O branch híbrido é o padrão atual do Azure AI Search: `search_text` e `vector_queries` são enviados juntos em uma única requisição `SearchClient.search`, então Reciprocal Rank Fusion combina os conjuntos léxicos e vetoriais. Não divida isto em buscas separadas do lado do cliente nem substitua o Azure AI Search.

Para uma query híbrida de produção que use reranking semântico, profundidade de candidatos e contagem de resultados retornados são controles separados. A Microsoft recomenda alimentar o ranker semântico com um conjunto de candidatos suficientemente profundo, comumente 50 candidatos (`k=50` para o lado vetorial, ou `k` mais `maxTextRecallSize` totalizando pelo menos 50 em APIs mais novas), enquanto `top` pode permanecer a contagem final menor mostrada ao chamador. Este pequeno corpus de laboratório usa `k_nearest_neighbors=top` para que os aprendizes possam comparar cada chunk retornado sem fabricar 50 candidatos. Se o corpus crescer, ajuste a profundidade de candidatos independentemente e meça relevância, latência e custo. Veja [Create a hybrid query in Azure AI Search](https://learn.microsoft.com/azure/search/hybrid-search-how-to-query#configure-a-query-response).

## Tarefa 5: Executar a solução

**Crie e popula os índices**

1. Crie índices e ingira os chunks sintéticos:

```powershell
python -m src.main create-indexes
python -m src.main ingest --documents artifacts-generated-chunks.json
```

**Verifique os índices no portal do Azure**

2. No [portal do Azure (Azure portal)](https://portal.azure.com), abra o serviço Azure AI Search provisionado para este lab.
3. Use o valor `AZURE_SEARCH_ENDPOINT` em `.env` para identificar o serviço se sua assinatura contiver mais de um.
4. No menu do serviço, em **Gerenciamento de pesquisa (Search management)**, selecione **Índices (Indexes)**.
5. Confirme que os seguintes índices e contagens de documentos aparecem:

  | Índice | Contagem de documentos esperada |
  |---|---:|
  | `northwind-formulary-v1` | 10 |
  | `northwind-guidelines-v1` | 9 |
  | `northwind-labs-v1` | 9 |

6. Se as contagens não tiverem sido atualizadas, aguarde brevemente e selecione **Atualizar (Refresh)**.
7. Se um índice permanecer ausente ou com contagem menor, volte à saída do terminal e verifique se `create-indexes` ou um lote de ingestão `<strategy>:<category>` reportou um erro.

Para o corpus não modificado, as contagens incluem ambas as estratégias: formulary tem seis chunks fixed e quatro structural; guidelines e labs cada um tem cinco fixed e quatro structural. As contagens verificam ingestão, não qualidade de recuperação.

**Execute as queries de recuperação**

8. Execute os comandos a seguir **um de cada vez**, não em lote colado.
9. Inspecione cada resultado JSON antes de continuar.
10. Associe seus índices roteados, ranqueamento, scores e legendas com as opções do comando.

```powershell
python -m src.main search --query "atorvastatin contraindications" --chunk-strategy fixed-overlap
python -m src.main search --query "atorvastatin contraindications" --chunk-strategy structural-parent-child
python -m src.main search --query "What A1C range requires follow-up?"
python -m src.main search --query "How should diabetes therapy and monitoring be coordinated?"
python -m src.main search --query "atorvastatin contraindications" --mode vector --embedding-profile baseline --chunk-strategy fixed-overlap
python -m src.main search --query "atorvastatin contraindications" --mode hybrid --embedding-profile content-aware --chunk-strategy structural-parent-child
python -m src.main search --query "atorvastatin contraindications" --mode semantic --chunk-strategy structural-parent-child
```

> **Nota:** Queries retornam apenas chunks de grounding; nenhum modelo de chat os recebe neste lab.

11. Para cada resultado, primeiro confirme quais índices foram selecionados.
12. Compare `parent_id`, `chunk_strategy`, `@search.score`, opcional `@search.reranker_score`, legendas e citações. As primeiras quatro queries exercitam roteamento e chunking; as três finais comparam modos de recuperação e perfis para atorvastatina.

13. Execute a comparação completa uma vez para registrar cada query, estratégia, modo, perfil de embedding e tentativa de índice roteado configurados:

```powershell
python -m src.main compare --queries assets/queries.json --documents artifacts-generated-chunks.json --output artifacts-retrieval-comparison.json
```

**Entenda a saída**

`create-indexes` retorna os três nomes de índice implantados. `ingest` retorna contagens indexadas com chave `<strategy>:<category>`, o que prova que nenhum lote de estratégia/categoria desapareceu. A saída de busca é agrupada por índice roteado e inclui identidade do chunk, identidade do pai, limites, citação determinística, `@search.score`, opcional `@search.reranker_score`, e legendas semânticas. No artefato de comparação, `trials` contém evidência de ranqueamento e latência a nível de chamada, enquanto `aggregates` reporta MRR e latência média para cada estratégia, modo e perfil de embedding.

## Tarefa 6: Validar a implementação

**Valide as evidências de recuperação**

1. Capture evidência ao vivo para cada objetivo:

- `create-indexes` reporta três nomes de índice e sua configuração semântica.
- `artifacts-generated-chunks.json` registra ambas as configurações, contagens de chunks por estratégia e cada limite de chunk. Ambas as estratégias cobrem os mesmos seis IDs de pai.
- `ingest` reporta que cada chunk sintético foi ingerido com sucesso, separado por estratégia e categoria.
- A query de atorvastatina roteia para o índice de formulary e retorna correspondências por nome exato além de candidatos vetoriais.
- A query A1C roteia para o índice laboratorial e inclui `@search.reranker_score` ou uma legenda semântica.
- A query multifator pesquisa os três índices e emite citações específicas da fonte.
- Compare ranqueamentos somente vetoriais e híbridos usando a mesma query, estratégia e perfil de embedding no artefato de trial. Os ranqueamentos podem coincidir; evidência de chamada ao serviço, não uma alteração de ordenação obrigatória, estabelece a recuperação ao vivo.
- Cada trial em `artifacts-retrieval-comparison.json` identifica uma estratégia de chunk, query, índice, modo e perfil de embedding. Seu ranqueamento contém IDs filho e pai, e seus scores e latência vêm da mesma chamada de serviço.
- `aggregates` reporta MRR e latência média por estratégia de chunk, modo e perfil de embedding. Compare esses valores com contagem de chunks e comprimento de entrada de embedding antes de selecionar uma estratégia.

**Execute as checagens finais**

2. Execute novamente a validação local e de infraestrutura:

```powershell
python scripts/preflight.py
Get-ChildItem src/*.py | ForEach-Object { python -m py_compile $_.FullName }
az bicep build --file infra/main.bicep
$evidence = Get-Content artifacts-retrieval-comparison.json | ConvertFrom-Json
$evidence.chunk_strategies | Format-Table strategy,chunk_count
$evidence.aggregates | Sort-Object mode,embedding_profile,chunk_strategy | Format-Table chunk_strategy,mode,embedding_profile,trial_count,mrr,average_latency_ms
$evidence.trials | Sort-Object query,index,mode,embedding_profile,chunk_strategy | Format-Table query,index,chunk_strategy,mode,embedding_profile,reciprocal_rank,latency_ms
```

Espere `Preflight passed`, ambas as estratégias de chunk com seis IDs de pai cada, e compilação Python e Bicep sem erros. Use a checklist de evidência ao vivo acima para avaliar recuperação, não apenas checagens locais.

## Desafio opcional: Criar um desacordo de ranqueamento

Adicione uma query sintética para a qual a recuperação léxica e a vetorial selecionem documentos-top diferentes.

**Saída esperada:** O artefato de comparação identifica a rota selecionada, documento vencedor, modo de recuperação, scores de ranqueamento e a métrica usada para justificar a escolha.

**Investigação de falha:** Remova um campo requerido de uma definição de índice descartável e determine se a falha resultante pertence à ingestão, schema, roteamento ou grounding.

## Tarefa 7: Revisar o design

1. Responda a estas perguntas:

- Quais tipos de query devem desativar semantic query rewrite para preservar identificadores exatos?
- Qual evidência justificaria adicionar um cross-encoder após o ranqueamento semântico?
- Como a saúde da fonte deveria alterar o roteamento sem mudar a classificação de intenção?
- Quais campos de recuperação são seguros para incluir no contexto de um agente?

## Tarefa 8: Limpar

**Remova recursos do Azure**

1. Execute o seguinte comando:

```powershell
azd down --purge
```

2. Confirme que os recursos de search e Azure OpenAI foram deletados.
3. Remova `.env` quando não for mais necessário.

**Desative o ambiente virtual**

4. Execute este comando em todo terminal onde `(.venv)` apareça no prompt:

```powershell
deactivate
```

5. Confirme que `(.venv)` não aparece mais antes de mudar para outro diretório de lab.

## Resumo

Você comparou estratégias de chunk reproduzíveis e perfis de embedding usando recuperação roteada ao vivo, preservando linhagem, ranqueamento, MRR e evidência de latência para a decisão de design.
