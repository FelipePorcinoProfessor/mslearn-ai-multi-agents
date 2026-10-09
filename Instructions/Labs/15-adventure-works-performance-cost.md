---
lab:
  title: 'Otimizar desempenho e custo multiagente com evidência mensurada'
  description: 'Meça o uso de modelos em execução, depois implemente roteamento de modelos, cache, orçamentos de tokens e escalonamento por piso de qualidade para Adventure Works.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Otimizar desempenho e custo multiagente com evidência mensurada

## Cenário do cliente

Adventure Works direciona todas as solicitações da sua Customer Intelligence Platform para seu modelo premium e repetidamente envia contexto excessivo. A equipe da plataforma precisa de evidência de que um design mais barato atende ao envelope de qualidade, latência e orçamento de cada segmento de cliente.

## Cenário do laboratório

Você executará solicitações sintéticas contra implantações ativas do Microsoft Foundry, capturará latência real e uso de tokens, e implementará roteamento, cache de resultados, orçamentos de contexto e escalonamento por piso de qualidade. Você comparará uma execução de controle premium com a política otimizada e recomendará uma configuração com base nas evidências.

Ao final deste exercício, você será capaz de:

- Rotealar solicitações simples, moderadas e de alto risco para as camadas (tiers) de modelo apropriadas.
- Aplicar prefixos de prompt estáveis, cache distribuído de resultados e metadados explícitos de invalidação.
- Aplicar orçamentos de tokens antes da invocação do modelo.
- Comparar qualidade, custo, latência, tentativas e comportamento do cache com evidência mensurada.

> **Importante**: Chamadas de modelos ao vivo e Azure Managed Redis geram cobrança. Confirme o preço dos modelos para sua região, limite a carga de trabalho sintética fornecida e faça a limpeza imediatamente.

## Tarefa 1: Preparar o laboratório

1. Instale [Python 3.10 or later](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), e [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install).

Você precisa de uma assinatura do Azure, permissão para criar recursos do Foundry e Redis, duas ou três implantações de chat aprovadas pelo instrutor e preços atuais de tokens de entrada/saída. Use sua identidade autenticada e nunca armazene chaves de acesso.

**Clonar e abrir o repositório**

2. Se ainda não fez, clone o [repositório de origem do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

3. Abra o repositório clonado no Visual Studio Code.

**Verificar ferramentas e autenticação**

4. Valide as ferramentas necessárias, credenciais e a assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\15-adventure-works-performance-cost
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação da arquitetura**

Revise `assets/requests.jsonl`, `assets/optimization-config.json`, `src/main.py`, `src/cache.py`, `.env.example`, e `infra/main.bicep`. Antes de continuar, confirme que uma solicitação passa por seleção determinística de nível, orçamento de contexto, busca no cache, invocação do modelo ou retorno do cache, avaliação do piso de qualidade e registro de evidência.

## Tarefa 2: Criar o ambiente virtual

1. No Windows, crie e ative o ambiente virtual e inicialize `.env`:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
Copy-Item .env.example .env
```

> No macOS/Linux, execute `bash scripts/setup.sh`, `source .venv/bin/activate`, e `cp .env.example .env` em vez disso.

## Tarefa 3: Implantar recursos do Azure

1. Revise o uso de modelo do Foundry e os custos do Azure Managed Redis, cota de modelo e acesso por função antes do provisionamento.
2. Limite a carga de trabalho sintética fornecida e use um ambiente único.

`azd` provisiona a infraestrutura; o benchmark é executado separadamente e gera cobranças de modelo.

**Definir os valores de implantação**

3. Defina `$azureRegion` para uma região aprovada que ofereça os modelos e serviços requeridos.
4. Substitua o valor de exemplo `eastus2` se necessário.
> **Grupo de recursos (Resource group):** Se seu ambiente de laboratório fornece um grupo de recursos pré-criado, defina `$resourceGroupName` para seu nome. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um grupo de recursos único na sua assinatura.

> **Nota:** `AZURE_DEV_USER_AGENT` marca o provisionamento para atribuição e não é exportado para `.env`. Remova-o depois para evitar marcar comandos não relacionados.

**Validar e provisionar a infraestrutura**

5. Execute os seguintes comandos:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab15-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-optimize-dev
azd env set AZURE_LOCATION $azureRegion
azd env set AZURE_RESOURCE_GROUP $resourceGroupName
$principalId = az ad signed-in-user show --query id --output tsv
azd env set AZURE_PRINCIPAL_ID $principalId
azd env set FOUNDRY_MODEL_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_CATALOG_NAME gpt-5.4-mini
azd env set FOUNDRY_MODEL_VERSION 2026-03-17
az bicep build --file infra/main.bicep
azd provision
azd env get-values | Out-File .env -Encoding utf8
Remove-Item Env:AZURE_DEV_USER_AGENT
```

> **Nota:** Se o provisionamento falhar, inspecione o primeiro erro de implantação. Verifique disponibilidade de modelo e região, cota, disponibilidade do Redis, principal ID e permissões de atribuição de função. Corrija a causa e execute novamente `azd provision`.

**Validar o ambiente gerado**

6. Após o provisionamento ser bem-sucedido, valide que `.env` inclua o endpoint do projeto Foundry, os três nomes de implantação, o host do Redis e o principal ID exigido pela aplicação.
7. Não adicione chaves, tokens ou strings de conexão; a autenticação do Redis usa um token do Microsoft Entra ID obtido em tempo de execução.

## Tarefa 4: Implementar a solução

Cada espaço reservado marca código incompleto. Copie cada trecho fornecido para seu local de placeholder, remova o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco incompleto indicado e preserve a indentação ao redor.

Os preços da Global Standard `gpt-5.4-mini` são evidência versionada para esta execução do laboratório. Verifique e atualize-os se o modelo, tipo de implantação, moeda ou data de precificação mudar.

> **Dica:** Depois de colar cada trecho Python, valide sua indentação com a função ou classe circundante antes de executar o código.

**Classificar a complexidade da solicitação**

1. Em `src/main.py`, encontre `# LAB PLACEHOLDER 1`.
2. Substitua somente a função incompleta `classify_tier()` associada por:

```python
def classify_tier(request: dict[str, Any]) -> int:
  """Classify request complexity without spending model tokens."""
  message = request["message"].lower()
  if (
    request.get("policy_exception")
    or float(request.get("transaction_amount", 0)) > 200
    or any(term in message for term in ("legal", "regulatory", "chargeback"))
  ):
    return 3
  if "compare" in message or len(request.get("dependencies", [])) > 1:
    return 2
  return 1
```

O roteador não consome tokens do modelo e envia exceções, trabalho de alto valor e jurídico diretamente para a camada (tier) mais alta.

**Construir contexto por prioridade**

3. Encontre `# LAB PLACEHOLDER 2`.
4. Substitua somente a função incompleta `apply_context_budget()` associada por:

```python
def apply_context_budget(request: dict[str, Any], budget: int) -> str:
  """Build context that preserves required facts within a character proxy budget."""
  context = request["context"]
  required = set(request.get("required_context_fields", context.keys())) - {"unused_fields"}
  selected = {key: context[key] for key in context if key in required}
  rendered = json.dumps(selected, sort_keys=True, separators=(",", ":"))
  character_limit = budget * 4
  if len(rendered) > character_limit:
    raise ValueError(
      f"Required context needs {len(rendered)} characters; tier budget allows {character_limit}."
    )
  return rendered
```

Fatos necessários são preservados ou a solicitação falha antes da invocação; a truncagem silenciosa não pode remover uma autorização ou detalhe de pedido.

**Chaves de cache de resultado exato com versionamento**

5. Em `src/cache.py`, encontre `# LAB PLACEHOLDER 3`.
6. Substitua somente o método incompleto `result_key()` associado por:

```python
  def result_key(cls, request: dict[str, Any], agent_version: str, policy_version: str) -> str:
    signature = {
      "request": request["message"].strip().lower(),
      "segment": request["segment"],
      "context": request["context"],
      "dependencies": sorted(request["dependencies"]),
      "agent_version": agent_version,
      "policy_version": policy_version,
    }
    return f"aw:result:{cls._digest(signature)}"
```

Contexto, versão e entradas de dependência impedem reutilização depois que fatos, comportamento ou fontes mudam, enquanto o namespace `aw:result` mantém respostas exatas distintas.

**Chaves de cache de contexto de prompt com versionamento**

7. Encontre `# LAB PLACEHOLDER 4`.
8. Substitua somente o método incompleto `prompt_key()` associado por:

```python
  def prompt_key(
    cls,
    request: dict[str, Any],
    tier: int,
    input_budget: int,
    agent_version: str,
    policy_version: str,
  ) -> str:
    signature = {
      "context": request["context"],
      "dependencies": sorted(request["dependencies"]),
      "tier": tier,
      "input_budget": input_budget,
      "agent_version": agent_version,
      "policy_version": policy_version,
    }
    return f"aw:prompt:{cls._digest(signature)}"
```

Nível (tier) e orçamento afetam a construção do prompt, portanto eles devem participar da identidade do prompt-cache.

**Verificar o código concluído**

9. Verifique o código concluído localmente:

```console
python -m py_compile src/main.py src/cache.py scripts/compare_runs.py
python scripts/preflight.py --require-complete
```

10. Confirme que a compilação não retorna saída.
11. Confirme que o preflight reporta os arquivos locais e as verificações de implementação como `ready`; ele deve permanecer diferente de zero até que os preços atuais, três nomes de implantação, o endpoint do projeto, o host do Redis e o principal ID sejam configurados.

## Tarefa 5: Executar a solução

1. Execute os comandos do benchmark nessa ordem.

O controle estabelece a linha de base premium. A primeira execução otimizada usa um cache frio, a segunda demonstra acertos de resultado exato, a invalidação remove somente o resultado exato de `SYN-LOOKUP-001`, e a execução final demonstra reuso do contexto de prompt para essa solicitação.

```console
python -m src.main --policy control --output reports/control-summary.json
python -m src.main --policy optimized --output reports/optimized-summary.json
python -m src.main --policy optimized --output reports/optimized-cached-summary.json
python -m src.main --invalidate-exact SYN-LOOKUP-001
python -m src.main --policy optimized --output reports/optimized-prompt-cached-summary.json
python scripts/compare_runs.py reports/control-summary.json reports/optimized-summary.json reports/optimized-cached-summary.json
```

**Entender a saída**

Cada linha de evidência registra `initial_tier`, `final_tier`, implantação, tokens medidos, latência, preço versionado, qualidade, tentativas e `cache_level`. `miss` significa que uma chamada de modelo construiu o contexto do zero, `prompt` significa que o contexto em cache foi reutilizado mas o modelo foi chamado, e `exact_result` significa que nenhuma chamada de modelo ocorreu. O custo resumido inclui cada tentativa de retry. `needs_human_review` é definido somente quando o nível 3 permanece abaixo de seu piso de qualidade.

## Tarefa 6: Validar a implementação

**Inspecionar a evidência mensurada**

1. Confirme que cada linha de evidência, incluindo um acerto de cache de resultado exato, contém implantação, versão de preço, níveis inicial e final, `cache_level`, status do cache de prompt, contagem de retries, custo e pontuação de qualidade.
2. Confirme que linhas não em cache também contêm milissegundos decorridos medidos e tokens reais de entrada e saída da resposta do serviço.
3. Inspecione a segunda execução otimizada para `cache_level: exact_result`.
4. Execute `python -m src.main --invalidate-exact SYN-LOOKUP-001` e registre o `exact_result_key` e a contagem `deleted` relatados.
5. Reexecute a política otimizada e confirme que a solicitação `SYN-LOOKUP-001` reporta `cache_level: prompt`.
6. Confirme que o resumo `cache_hit_rate` contabiliza tanto acertos de resultado exato quanto acertos de prompt; use `exact_result_cache_hit_rate` e `prompt_cache_hit_rate` para a divisão por nível.
7. Verifique que o Redis contenha somente o contexto sintético e as respostas fornecidas, e não contenha credenciais ou dados reais de clientes.

Baseie a recomendação nas evidências medidas, excluindo economias de solicitações com falha ou acertos de cache não observados.

**Validar os recursos do Azure**

8. No portal do Microsoft Foundry, valide a conta provisionada, o projeto e a implantação nomeados por `TIER1_DEPLOYMENT`, `TIER2_DEPLOYMENT` e `TIER3_DEPLOYMENT`.
9. No Azure Managed Redis, valide o banco de dados `default` provisionado e a atribuição de política de acesso do Microsoft Entra ID `default`.

O laboratório autônomo mapeia as três camadas de roteamento para uma implantação atual única de modo que as diferenças medidas provenham de orçamentos, retries e caching. Em um experimento de produção, use implantações precificadas e benchmarkeadas separadamente quando a comparação de roteamento exigir trade-offs de qualidade do modelo.

**Revisar cobertura dos objetivos**

| Objetivo | Evidência requerida | Resultado esperado |
|---|---|---|
| Encaminhar solicitações por complexidade | Campos de nível na evidência | Casos de exceção/alto risco começam no nível 3; casos mais simples usam níveis inferiores. |
| Aplicar separação de cache e invalidação | Níveis de cache e saída de invalidação | As chaves de resultado exato e de prompt são diferentes; a invalidação remove somente o resultado exato selecionado. |
| Aplicar orçamentos de contexto | Função concluída e execuções bem-sucedidas | Os campos obrigatórios cabem no orçamento do nível ou falham antes da chamada ao modelo. |
| Comparar desempenho e custo medidos | Três resumos e relatório de comparação | A recomendação usa tokens reais, latência, tentativas, qualidade e acertos de cache. |

## Desafio opcional: Isolar entradas de cache por locatário

Adicione um identificador de locatário sintético à solicitação e às duas assinaturas de cache.

**Saída esperada:** Solicitações idênticas de dois locatários criam entradas de cache distintas, e a invalidação direcionada remove somente o resultado do locatário selecionado.

**Investigação de falha:** Use metadados de invalidação obsoletos e determine se o defeito está na construção da chave ou no escopo da invalidação.

## Tarefa 7: Revisar o design

1. Responda a estas perguntas:

- Quando uma rota inicial mais barata custou mais porque foi re-tentada?
- Quais campos de contexto consumiram tokens sem alterar a qualidade?
- Que evidência justificaria adicionar cache semântico em vez de cache de resultado exato?

## Tarefa 8: Limpeza

**Remover recursos do Azure**

1. Execute `azd down --purge` com `AZURE_DEV_USER_AGENT=microsoft_foundry_skill`.
2. Remova o `.env` local.
3. Confirme que o grupo de recursos e a instância do Redis foram excluídos.

**Desativar o ambiente virtual**

4. Execute este comando em cada terminal onde `(.venv)` aparece no prompt:

```powershell
deactivate
```

5. Confirme que `(.venv)` não aparece mais antes de trocar para outro diretório de laboratório.

## Resumo

Você otimizou uma carga de trabalho multiagente ativa com roteamento, caching, orçamentos de tokens e pisos de qualidade, e então selecionou uma política com base em evidências reais de tokens, latência, qualidade e custo.
