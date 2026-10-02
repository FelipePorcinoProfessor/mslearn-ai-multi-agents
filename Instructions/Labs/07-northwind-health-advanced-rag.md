---
lab:
  title: 'Implement advanced RAG with Azure AI Search'
  description: 'Build and validate a routed hybrid, vector, and semantic retrieval pipeline against live Azure AI Search.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
---

# Implement advanced RAG with Azure AI Search

## Customer scenario

Northwind Health needs grounded retrieval across synthetic formulary, clinical-guideline, and laboratory-reference knowledge. Exact identifiers must remain discoverable, conceptual queries must benefit from vector similarity, and semantic ranking must improve the order and captions of the candidate set. The retrieval team also needs evidence that its chunking choice improves quality enough to justify its index size and latency.

## Lab scenario

Compare chunking, embedding profiles, query modes, and routing over six synthetic parent documents: two formulary monographs, two guidelines, and two laboratory references. Overlapping topics make single-source and cross-domain retrieval observable. This lab retrieves evidence only; it does not build a chatbot or generate patient advice.

Generate two variants per parent: **fixed overlap** uses 180-character windows with 40-character overlap; **structural parent-child** creates one chunk per section with its parent title and heading. The former may split sections or omit titles; the latter repeats contextual text. Measure the trade-off rather than assuming either is better.

### Understand the supplied JSON assets

| Asset | Role |
|---|---|
| `assets/source-documents.json` | Source corpus: stable IDs, titles, categories, source labels, and two authored sections per parent. Synthetic references, not patient records or authoritative policy. |
| `assets/chunk-strategies.json` | Reproducible chunking parameters, not prebuilt chunks. |
| `assets/queries.json` | Three relevance-labeled queries: exact medication lookup, conceptual laboratory question, and cross-domain coordination. Expected parent IDs score retrieval; they are not injected into queries. |
| `assets/documents.json` | Deprecation marker only. Do not ingest it or pass it to `compare`. |

Generate `artifacts-generated-chunks.json` from the first two assets. Use this same artifact for ingestion and comparison; it preserves configurations, chunks, parent lineage, section metadata, and character boundaries.

### Follow the retrieval experiment

Upload both chunk strategies to three category indexes. Each chunk has a content-only baseline vector and a content-aware vector incorporating category, title, parent ID, and position. Route queries to relevant indexes and compare vector, hybrid, and semantic modes, filtering each result set to one strategy.

Aggregate mean reciprocal rank (MRR) and latency by strategy, mode, and embedding profile. MRR measures the first expected parent's rank, not clinical correctness, completeness, or safety. Three synthetic queries demonstrate the mechanics; production selection requires a larger representative evaluation set.

By the end of this exercise, you will be able to:

- Design searchable, filterable, vector, and semantic fields for specialized indexes.
- Generate executable fixed-overlap and structural parent-child chunk sets with recorded boundaries.
- Upload both generated chunk sets with managed-identity authentication.
- Execute hybrid search with `SearchClient`, `VectorizedQuery`, and semantic ranking.
- Route queries across knowledge sources and compare MRR, ranking, and latency by chunk strategy and embedding profile.

> **Important**: Live Azure validation is required because hybrid RRF and semantic ranking are service behaviors. Azure AI Search Standard and Azure OpenAI are billable; use instructor-approved quota and run `azd down --purge` after validation.

## Task 1: Prepare the lab

Install [Python 3.11 or later](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), [Git](https://git-scm.com/downloads), [Visual Studio Code](https://code.visualstudio.com/download), and the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep) extensions. You need permission to create Azure AI Search and Azure OpenAI resources and role assignments. Your region must support the selected embedding deployment.

**Clone and open the repository**

1. If you haven't already done so, clone the [lab source repository](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), or fork the repository and clone your fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Open the cloned repository in Visual Studio Code.

**Verify tools and authentication**

3. Validate the required tools, credentials, and active subscription from the VS Code terminal:

```powershell
cd Allfiles\07-northwind-health-advanced-rag
az version
azd version
python --version
az account show --output table
```

All documents are synthetic.

4. Authenticate with `DefaultAzureCredential`.
5. Never add search admin keys or model keys to `.env`.

**Architecture checkpoint**

Review these components before editing:

| Component | What to locate |
|---|---|
| `assets/source-documents.json` | Two source documents in each category |
| `assets/chunk-strategies.json` | Fixed-overlap and structural parent-child parameters |
| `assets/queries.json` | Three relevance-labeled queries |
| `assets/documents.json` | Deprecation marker; do not ingest it |
| `src/` and `infra/main.bicep` | Local chunk generation and the Azure-dependent embedding, indexing, ingestion, routing, and search operations |

Before continuing, confirm which operations run locally and which require Azure AI Search or Azure OpenAI.

> Do not replace service calls with local similarity math or precomputed scores.

## Task 2: Build the virtual environment

1. Create and activate the virtual environment:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> On macOS/Linux, run `bash scripts/setup.sh` and `source .venv/bin/activate` instead.

**Generate the chunk sets**

2. Before provisioning, inspect `assets/source-documents.json` and `assets/chunk-strategies.json`.
3. Confirm every record is synthetic and explain how `size_chars`, `overlap_chars`, section boundaries, and parent-title context can affect retrieval.

4. Generate both chunk sets from the same source documents:

```powershell
python -m src.main generate-chunks --source assets/source-documents.json --strategies assets/chunk-strategies.json --output artifacts-generated-chunks.json
$chunks = Get-Content artifacts-generated-chunks.json -Raw | ConvertFrom-Json
$chunks.strategy_summaries | Format-Table strategy,chunk_count
$chunks.strategy_summaries.boundaries | Select-Object -First 8 | Format-Table id,parent_id,start,end,section_heading
```

5. Do not manually edit the generated artifact.
6. Change the source documents or strategy configuration and regenerate it so the recorded boundaries remain reproducible.

## Task 3: Deploy the Azure resources

**Set the deployment values**

1. Review cost, model quota, and access before provisioning.

Azure AI Search capacity and Azure OpenAI embedding calls are billable.

2. Use a unique environment and delete it after validation.

`azd` provisions infrastructure. Chunk generation is local; ingestion and search run separately against Azure.

3. Set `$azureRegion` to an approved region supporting Standard Azure AI Search and Global Standard `text-embedding-3-small`. The example uses `eastus2`; regional capacity varies.

4. Change it if necessary for your subscription and current service availability.
> **Resource group:** If your lab environment provides a precreated resource group, set `$resourceGroupName` to its name. Otherwise, leave `$resourceGroupName` empty so the script creates a unique resource group in your subscription.

**Validate and provision the infrastructure**

5. Run the following commands:

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

6. If provisioning fails, inspect the first Azure deployment error. Search or model regional availability, model quota, and role-assignment permissions are common causes.
7. Correct the relevant environment setting or permission, then run `azd provision` again.

**Verify the generated environment**

8. After provisioning succeeds, validate that `.env` includes `AZURE_SEARCH_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`, and `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`. Role assignments grant your principal Search Service Contributor, Search Index Data Contributor, and Cognitive Services OpenAI User.
9. Allow several minutes for RBAC propagation.
10. Do not add admin keys or model keys to `.env`.

## Task 4: Implement the solution

Each placeholder marks incomplete code. Copy each supplied snippet into its placeholder location, keep the `LAB PLACEHOLDER` comment, replace only the indicated incomplete line or block, and preserve the surrounding indentation.

1. Use the `generate-chunks` output from Task 2; regenerate only if the source or configuration changed.
2. Inspect `artifacts-generated-chunks.json`.
3. Confirm that both strategy summaries record their configuration, chunk count, parent IDs, and character boundaries.

> **Tip:** After you copy and paste each Python snippet, validate its indentation against the surrounding function or class before running the code.

**Create specialized vector indexes**

4. In `src/index_manager.py`, find the exact marker `# LAB PLACEHOLDER 1: Replace this line with the Task 1 sample.`

5. Replace only the `raise NotImplementedError` line beneath it with:

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

The same governed schema supports three independently routed indexes. Vector dimensions come from configuration, so changing the embedding model does not require editing source.

**Generate ordered embeddings**

6. In `src/embeddings.py`, find the exact marker `# LAB PLACEHOLDER 2: Replace this line with the Task 2 sample.`

7. Replace only the `raise NotImplementedError` line beneath it with:

```python
  if not texts:
    raise ValueError("At least one embedding input is required")
  response = client.embeddings.create(model=deployment, input=list(texts))
  return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
```

The deployment name is parameterized through the azd output. Sorting by response index preserves the caller's document-to-vector mapping.

**Embed and upload both strategies**

8. In `src/ingest.py`, find the exact marker `# LAB PLACEHOLDER 3: Replace this line with the Task 3 sample.`

9. Replace only the `raise NotImplementedError` line beneath it with:

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

Both profiles are generated from the same ordered document list, while separate category/strategy batches keep ingestion evidence attributable.

**Route by explicit intent**

10. In `src/router.py`, find the exact marker `# LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.`

11. Replace only the `raise NotImplementedError` line beneath it with:

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

One clear intent routes narrowly. Multi-factor or unclassified queries fan out to all three indexes rather than silently dropping a relevant source.

**Execute vector, hybrid, and semantic search**

12. In `src/search_pipeline.py`, find the exact marker `# LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.`

13. Replace only the `raise NotImplementedError` line beneath it with:

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

Every mode uses Azure AI Search. The strategy filter prevents mixed candidate sets, and the returned IDs, boundaries, service scores, reranker scores, captions, and deterministic citations remain available for evaluation.

The hybrid branch is the current Azure AI Search pattern: `search_text` and `vector_queries` are submitted together in one `SearchClient.search` request, then Reciprocal Rank Fusion combines the lexical and vector result sets. Do not split this into separate client-side searches or replace Azure AI Search.

For a production hybrid query that uses semantic reranking, candidate depth and returned result count are separate controls. Microsoft recommends feeding semantic ranker a sufficiently deep candidate set, commonly 50 candidates (`k=50` for the vector side, or `k` plus `maxTextRecallSize` totaling at least 50 in newer APIs), while `top` can remain the smaller final count shown to the caller. This tiny lab corpus uses `k_nearest_neighbors=top` so learners can compare every returned chunk without manufacturing 50 candidates. If the corpus grows, tune candidate depth independently and measure relevance, latency, and cost. See [Create a hybrid query in Azure AI Search](https://learn.microsoft.com/azure/search/hybrid-search-how-to-query#configure-a-query-response).

## Task 5: Run the solution

**Create and populate the indexes**

1. Create indexes and ingest the synthetic chunks:

```powershell
python -m src.main create-indexes
python -m src.main ingest --documents artifacts-generated-chunks.json
```

**Verify the indexes in the Azure portal**

2. In the [Azure portal](https://portal.azure.com), open the Azure AI Search service provisioned for this lab.
3. Use the `AZURE_SEARCH_ENDPOINT` value in `.env` to identify the service if your subscription contains more than one.
4. On the service menu, under **Search management**, select **Indexes**.
5. Confirm that the following indexes and document counts appear:

  | Index | Expected document count |
  |---|---:|
  | `northwind-formulary-v1` | 10 |
  | `northwind-guidelines-v1` | 9 |
  | `northwind-labs-v1` | 9 |

6. If the counts have not updated, wait briefly and select **Refresh**.
7. If an index remains missing or has a lower count, return to the terminal output and check whether `create-indexes` or an `<strategy>:<category>` ingestion batch reported an error.

For the unmodified corpus, counts include both strategies: formulary has six fixed and four structural chunks; guidelines and labs each have five fixed and four structural chunks. Counts verify ingestion, not retrieval quality.

**Run the retrieval queries**

8. Run the following commands **one at a time**, not as a pasted batch.
9. Inspect each JSON result before continuing.
10. Associate its routed indexes, ranking, scores, and captions with the command's options.

```powershell
python -m src.main search --query "atorvastatin contraindications" --chunk-strategy fixed-overlap
python -m src.main search --query "atorvastatin contraindications" --chunk-strategy structural-parent-child
python -m src.main search --query "What A1C range requires follow-up?"
python -m src.main search --query "How should diabetes therapy and monitoring be coordinated?"
python -m src.main search --query "atorvastatin contraindications" --mode vector --embedding-profile baseline --chunk-strategy fixed-overlap
python -m src.main search --query "atorvastatin contraindications" --mode hybrid --embedding-profile content-aware --chunk-strategy structural-parent-child
python -m src.main search --query "atorvastatin contraindications" --mode semantic --chunk-strategy structural-parent-child
```

> **Note:** Queries return grounding chunks only; no chat model receives them in this lab.

11. For each result, first confirm which index or indexes were selected.
12. Compare `parent_id`, `chunk_strategy`, `@search.score`, optional `@search.reranker_score`, captions, and citations. The first four queries exercise routing and chunking; the final three compare retrieval modes and profiles for atorvastatin.

13. Run the full comparison once to record every configured query, strategy, mode, embedding-profile, and routed-index trial:

```powershell
python -m src.main compare --queries assets/queries.json --documents artifacts-generated-chunks.json --output artifacts-retrieval-comparison.json
```

**Understand the output**

`create-indexes` returns the three deployed index names. `ingest` returns counts keyed as `<strategy>:<category>`, which proves that no strategy/category batch disappeared. Search output is grouped by routed index and includes chunk identity, parent identity, boundaries, deterministic citation, `@search.score`, optional `@search.reranker_score`, and semantic captions. In the comparison artifact, `trials` contains call-level ranking and latency evidence, while `aggregates` reports MRR and average latency for each strategy, mode, and embedding profile.

## Task 6: Validate the implementation

**Validate the retrieval evidence**

1. Capture live evidence for each objective:

- `create-indexes` reports three index names and their semantic configuration.
- `artifacts-generated-chunks.json` records both configurations, per-strategy chunk counts, and every chunk boundary. Both strategies cover the same six parent IDs.
- `ingest` reports every synthetic chunk succeeded, separated by strategy and category.
- The atorvastatin query routes to the formulary index and returns exact-name matches plus vector candidates.
- The A1C query routes to the laboratory index and includes `@search.reranker_score` or a semantic caption.
- The multi-factor query searches all three indexes and emits source-specific citations.
- Compare vector-only and hybrid rankings using the same query, strategy, and embedding profile in the trial artifact. Rankings may coincide; service-call evidence, not a required ordering change, establishes live retrieval.
- Every trial in `artifacts-retrieval-comparison.json` identifies one chunk strategy, query, index, mode, and embedding profile. Its ranking contains child and parent IDs, and its scores and latency come from the same service call.
- `aggregates` reports MRR and average latency by chunk strategy, mode, and embedding profile. Compare these values with chunk count and embedding-input length before selecting a strategy.

**Run the final checks**

2. Run local and infrastructure validation again:

```powershell
python scripts/preflight.py
Get-ChildItem src/*.py | ForEach-Object { python -m py_compile $_.FullName }
az bicep build --file infra/main.bicep
$evidence = Get-Content artifacts-retrieval-comparison.json | ConvertFrom-Json
$evidence.chunk_strategies | Format-Table strategy,chunk_count
$evidence.aggregates | Sort-Object mode,embedding_profile,chunk_strategy | Format-Table chunk_strategy,mode,embedding_profile,trial_count,mrr,average_latency_ms
$evidence.trials | Sort-Object query,index,mode,embedding_profile,chunk_strategy | Format-Table query,index,chunk_strategy,mode,embedding_profile,reciprocal_rank,latency_ms
```

Expect `Preflight passed`, both chunk strategies with six parent IDs each, and error-free Python and Bicep compilation. Use the live evidence checklist above to assess retrieval, not local checks alone.

## Optional challenge: Create a ranking disagreement

Add a synthetic query for which lexical and vector retrieval select different top documents.

**Expected output:** The comparison artifact identifies the selected route, winning document, retrieval mode, ranking scores, and the metric used to justify the choice.

**Failure investigation:** Remove one required field from a disposable index definition and determine whether the resulting failure belongs to ingestion, schema, routing, or grounding.
## Task 7: Review the design

1. Answer these questions:

- Which query types should disable semantic query rewrite to preserve exact identifiers?
- What evidence would justify adding a cross-encoder after semantic ranking?
- How should source health alter routing without changing intent classification?
- Which retrieval fields are safe to include in agent context?

## Task 8: Clean up

**Remove Azure resources**

1. Run the following command:

```powershell
azd down --purge
```

2. Confirm the search and Azure OpenAI resources are deleted.
3. Remove `.env` when no longer needed.

**Deactivate the virtual environment**

4. Run this command in every terminal where `(.venv)` appears in the prompt:

```powershell
deactivate
```

5. Confirm that `(.venv)` no longer appears before changing to another lab directory.

## Summary

You compared reproducible chunk strategies and embedding profiles using live routed retrieval, preserving lineage, ranking, MRR, and latency evidence for the design decision.
