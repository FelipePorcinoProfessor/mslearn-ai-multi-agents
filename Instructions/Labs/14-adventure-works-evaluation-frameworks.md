---
lab:
  title: 'Construa um portão de qualidade de avaliação multiagente'
  description: 'Avalie as jornadas multiagente da Adventure Works com evaluators do Microsoft Foundry, dados sintéticos, evidências de calibração e limites de regressão.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Construa um portão de qualidade de avaliação multiagente

## Cenário do cliente

A Adventure Works precisa detectar regressões em sua Customer Intelligence Platform antes que uma nova configuração de agente alcance os clientes. Agentes individuais podem retornar respostas plausíveis enquanto a jornada completa falha por causa de resolução de intenção deficiente, transferências incompletas ou respostas contraditórias.

## Cenário do laboratório

Você é o engenheiro de plataforma responsável por uma execução de avaliação Microsoft Foundry repetível. Você completará uma fábrica de avaliadores, avaliará um dataset JSONL que preserva privacidade, calibrará a saída do juiz contra rótulos humanos e aplicará limites determinísticos de regressão aos resultados medidos.

Ao final deste exercício, você será capaz de:

- Definir métricas de sucesso em nível de componente, jornada e sistema.
- Executar avaliadores baseados em Responses através do framework batch do Azure AI Evaluation SDK.
- Usar dados sintéticos de canário, regressão e falhas históricas.
- Converter a saída de avaliação em uma recomendação de implantação auditável.

> **Importante**: A execução ao vivo usa um modelo implantado e gera cobranças por tokens. Use apenas os dados sintéticos fornecidos. Confirme cota e limpe a execução ao terminar.

## Tarefa 1: Preparar o laboratório

Você precisa de [Python 3.10 ou posterior](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd), uma assinatura do Azure e permissão para criar uma conta Microsoft Foundry, projeto e implantação de modelo. Use uma região com cota para o modelo de chat aprovado pelo instrutor. Autentique-se localmente com `DefaultAzureCredential`; não coloque chaves em arquivos.

**Clone e abra o repositório**

1. Se ainda não fez, clone o [repositório de origem do laboratório](https://github.com/MicrosoftLearning/mslearn-ai-multi-agents/tree/main), ou faça um fork do repositório e clone seu fork:

```console
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
```

2. Abra o repositório clonado no Visual Studio Code.

**Valide ferramentas e autenticação**

3. Valide as ferramentas necessárias, credenciais e assinatura ativa a partir do terminal do VS Code:

```powershell
cd Allfiles\14-adventure-works-evaluation-frameworks
az version
azd version
python --version
az account show --output table
```

**Ponto de verificação de arquitetura**

Revise `assets/evaluation-data.jsonl`, `assets/evaluation-config.json`, `src/evaluators.py`, `src/main.py` e `infra/main.bicep`. Antes de continuar, confirme que uma linha do dataset produz métricas determinísticas e baseadas no modelo, evidência no nível da linha, calibração do juiz e uma decisão de liberação determinística.

Complete o conjunto de avaliadores, calibração, execução em lote e o portão determinístico. O juiz do modelo fornece sinais de qualidade; o código da aplicação é responsável pela decisão de liberação.

## Tarefa 2: Crie o ambiente virtual

1. No Windows, crie e ative o ambiente virtual:

```powershell
./scripts/setup.ps1
. ./.venv/Scripts/Activate.ps1
```

> No macOS/Linux, execute `bash scripts/setup.sh` e `source .venv/bin/activate` em vez disso.

## Tarefa 3: Provisionar recursos do Azure

1. Use um ambiente isolado e o user-agent inline requerido para workflows do Foundry.

2. Revise custo, cota e acesso por função do modelo-juiz do Foundry antes de provisionar.

`azd` provisiona a conta Foundry, o projeto e a implantação de modelo; as execuções de avaliação são separadas e geram cobranças pelo modelo.

**Defina os valores de implantação**

3. Defina `$azureRegion` para uma região aprovada que suporte o modelo selecionado.
4. Substitua o valor de exemplo `eastus2` se necessário.
> **Grupo de recursos:** Se seu ambiente de laboratório fornecer um grupo de recursos pré-criado, defina `$resourceGroupName` para o nome dele. Caso contrário, deixe `$resourceGroupName` vazio para que o script crie um grupo de recursos único em sua assinatura.

> **Nota:** `AZURE_DEV_USER_AGENT` marca o provisionamento para atribuição e não é exportado para `.env`. Remova-o posteriormente para evitar marcar comandos não relacionados.

**Valide e provisione a infraestrutura**

5. Execute os seguintes comandos:

```powershell
$azureRegion = 'eastus2'
$resourceGroupName = ''
if ([string]::IsNullOrWhiteSpace($resourceGroupName)) {
  $resourceGroupName = "rg-lab14-$((New-Guid).Guid.Substring(0, 8))"
  az group create --name $resourceGroupName --location $azureRegion | Out-Null
}
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd env new aw-eval-dev
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

> **Nota:** Se o provisionamento falhar, inspecione o primeiro erro de implantação. Verifique disponibilidade do modelo e da região, cota, principal ID e permissões de atribuição de função. Corrija a causa e execute novamente `azd provision`.

**Verifique o ambiente gerado**

6. Após o provisionamento ser bem-sucedido, valide que `.env` inclui `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL_NAME` e os valores do projeto e do principal exigidos pelo avaliador.
7. Não adicione chaves, tokens ou connection strings; a aplicação usa sua identidade autenticada.

## Tarefa 4: Implementar a solução

Cada placeholder marca código incompleto. Copie cada snippet fornecido para seu local placeholder, remova o comentário `LAB PLACEHOLDER`, substitua somente a linha ou bloco incompleto indicado e preserve a indentação ao redor.

> **Dica:** Após colar cada snippet Python, valide sua indentação em relação à função ou classe circundante antes de executar o código.

**Crie o conjunto de avaliadores**

1. Em `src/evaluators.py`, encontre `# LAB PLACEHOLDER 1`.
2. Substitua a função incompleta `create_evaluators()` associada por:

```python
def create_evaluators(
  model_config: dict[str, str], credential: TokenCredential
) -> dict[str, Any]:
  """Create Responses-based evaluators for the batch run."""
  judge_options = {
    "project_endpoint": model_config["project_endpoint"],
    "deployment_name": model_config["azure_deployment"],
    "credential": credential,
  }
  return {
    "intent_resolution": IntentResolutionEvaluator(**judge_options),
    "task_adherence": TaskAdherenceEvaluator(**judge_options),
    "response_completeness": ResponseCompletenessEvaluator(**judge_options),
    "journey_coherence": JourneyCoherenceEvaluator(**judge_options),
  }
```

Isto combina métricas de componente com o juiz de nível de jornada enquanto reutiliza a implantação parametrizada e a credential sem senha.

> **Observação (prévia):** Os avaliadores de agentes do Foundry e os avaliadores compostos **Output Quality** e **Tool Use Quality** são recursos em prévia. APIs, definições de pontuação, modelos de juiz suportados e nomes de pacotes podem mudar. Este laboratório mantém avaliadores individuais porque seus sinais no nível da linha suportam o exercício de calibração. Verifique [Avaliadores de agentes](https://learn.microsoft.com/azure/foundry-classic/concepts/evaluation-evaluators/agent-evaluators) antes de usá-los em um portão de produção.

**Calcule o acordo de calibração**

3. Em `src/main.py`, encontre `# LAB PLACEHOLDER 2`.
4. Substitua a função incompleta `calibration_agreement()` associada por:

```python
def calibration_agreement(rows: list[dict[str, Any]]) -> float:
  """Return exact agreement between rounded judge scores and human labels."""
  labeled = []
  for row in rows:
    human_label = (
      row.get("human_label")
      or row.get("data.human_label")
      or row.get("inputs.human_label")
    )
    judge_score = row.get("outputs.journey_coherence.journey_coherence")
    if human_label is not None and judge_score is not None:
      labeled.append(int(human_label) == round(float(judge_score)))
  return sum(labeled) / len(labeled) if labeled else 0.0
```

A calibração mantém a discordância do juiz visível em vez de tratar uma pontuação do modelo como verdade absoluta.

**Aplique portões determinísticos de regressão**

5. Encontre `# LAB PLACEHOLDER 3`.
6. Substitua a função incompleta `apply_regression_gate()` associada por:

```python
def apply_regression_gate(
  metrics: dict[str, float], agreement: float, config: dict[str, Any]
) -> dict[str, Any]:
  """Compare measured metrics with absolute, delta, and calibration gates."""
  comparisons = []
  failed_gates = []
  for name, policy in config["metrics"].items():
    measured = metrics.get(name)
    if measured is None:
      failed_gates.append(f"{name}: missing measured metric")
      comparisons.append({"metric": name, "status": "missing"})
      continue
    delta = measured - float(policy["baseline"])
    passed = measured >= float(policy["minimum"]) and delta >= -float(policy["maximum_drop"])
    comparisons.append({
      "metric": name,
      "measured": measured,
      "baseline": policy["baseline"],
      "delta": round(delta, 4),
      "minimum": policy["minimum"],
      "maximum_drop": policy["maximum_drop"],
      "passed": passed,
    })
    if not passed:
      failed_gates.append(name)
  if agreement < float(config["minimum_calibration_agreement"]):
    failed_gates.append("judge_calibration")
  return {
    "passed": not failed_gates,
    "failed_gates": failed_gates,
    "comparisons": comparisons,
    "calibration_agreement": agreement,
    "minimum_calibration_agreement": config["minimum_calibration_agreement"],
  }
```

O modelo produz medições semânticas; o código determinístico é o responsável pela decisão de liberação e falha-se fechado quando uma métrica está ausente.

**Execute a avaliação em lote**

7. Encontre `# LAB PLACEHOLDER 4`.
8. Substitua a atribuição `evaluation = None` e o bloco `if` que a segue por:

```python
  evaluation = evaluate(
    data=str(data_path),
    evaluators=evaluators,
    evaluator_config={
      "intent_resolution": {
        "column_mapping": {
          "query": "${data.query}",
          "response": "${data.response}",
        }
      },
      "task_adherence": {
        "column_mapping": {
          "query": "${data.query}",
          "response": "${data.response}",
        }
      },
      "response_completeness": {
        "column_mapping": {
          "response": "${data.response}",
          "ground_truth": "${data.expected_behavior}",
        }
      },
      "journey_coherence": {
        "column_mapping": {
          "query": "${data.query}",
          "response": "${data.response}",
          "context": "${data.context}",
          "expected_behavior": "${data.expected_behavior}",
        }
      }
    },
    output_path=str(output_path.with_suffix(".rows.jsonl")),
  )
```

Cada avaliador recebe seu contrato de dataset documentado. A completude de resposta compara o candidato com `expected_behavior` como verdade de referência, enquanto o juiz de jornada também recebe contexto. A evidência no nível da linha permanece separada do resumo.

**Proteja a geração de relatório**

9. Encontre `# LAB PLACEHOLDER 5`.
10. Insira esta guarda no local placeholder:

```python
  if not rows:
    raise RuntimeError("Evaluation returned no rows; no release decision can be made.")
```

Uma avaliação vazia não deve produzir uma recomendação de implantação com aparência plausível.

**Verifique o código completado**

11. Verifique o código completado localmente:

```console
python -m py_compile src/evaluators.py src/main.py
python scripts/preflight.py --require-complete
```

12. Confirme que a compilação não retorna saída.
13. Confirme que o preflight reporta a versão do Python, o dataset, a configuração e o Evaluation SDK como `ready`; endpoint e implantação podem permanecer `not ready` até o provisionamento ser concluído.

## Tarefa 5: Execute a solução

1. Execute a avaliação em lote:

```console
python -m src.main --data assets/evaluation-data.jsonl --output reports/evaluation-result.json
```

2. Confirme que o comando invoca o modelo avaliador ao vivo, preserva evidência no nível da linha e produz uma recomendação de liberação derivada de métricas medidas.

**Entenda a saída**

`reports/evaluation-result.rows.jsonl` contém um registro de evidência por caso sintético, incluindo pontuações de avaliadores e razões. `reports/evaluation-result.json` é o resumo da liberação: `metrics` contém agregados, `gate.comparisons` mostra valores medidos contra limites absolutos e delta, `gate.calibration_agreement` compara o juiz de jornada com rótulos humanos, e `gate.passed` é verdadeiro somente quando `failed_gates` está vazio. `deployment` é o nome de implantação configurado, não um modelo codificado estaticamente.

## Tarefa 6: Validar a implementação

**Inspecione a evidência de avaliação**

1. Confirme que `reports/evaluation-result.json` contém metadados do dataset, nomes dos avaliadores, pontuações agregadas, acordo de calibração, comparações de limites, portões falhos e o nome da implantação do modelo.
2. Inspecione linhas com pontuação baixa e explique se a falha é em nível de componente, nível de handoff ou nível de sistema.

**Teste o portão de regressão**

3. Altere uma resposta candidata sintética para contradizer um handoff anterior.
4. Execute novamente a avaliação.
5. Confirme que a pontuação da avaliação muda e que o portão de regressão usa o resultado medido em vez de um rótulo de cenário codificado.

**Valide os recursos do Azure**

6. No portal Microsoft Foundry, valide a conta Foundry provisionada, o projeto e a implantação de modelo usados por este laboratório.

**Revise a cobertura dos objetivos**

| Objetivo | Evidência exigida | Critério de aprovação |
|---|---|---|
| Definir métricas de componente, jornada e sistema | Nomes dos avaliadores e comparações de portões | Todas as métricas configuradas aparecem; métricas ausentes causam falha em modo fechado. |
| Executar avaliadores baseados em Responses através do framework batch do SDK | JSONL por linha e resumo agregado | Cada linha sintética possui saída do avaliador e razões. |
| Usar casos de cobertura sintética | Metadados do dataset e linhas revisadas | Apenas casos sintéticos fornecidos ou criados pelo aprendiz estão presentes. |
| Produzir uma recomendação auditável | Resultado do portão, calibração e implantação | A recomendação segue os limites medidos e nomeia a implantação configurada. |

## Desafio opcional: Adicione uma falha de grounding

Adicione um caso sintético que complete a tarefa solicitada mas contradiga ou omita a evidência de grounding fornecida.

**Saída esperada:** O avaliador relevante falha na linha, o relatório agregado mostra a métrica afetada e o portão determinístico de qualidade bloqueia a liberação.

**Investigação de falha:** Crie desacordo entre juiz e rótulo humano e distinga falha de calibração de falha no resultado da tarefa.

## Tarefa 7: Revise o design

1. Responda a estas perguntas:

- Qual métrica em nível de sistema expondo uma resposta de agente bem-sucedida seguida por um handoff falho?
- Que tamanho de amostra de calibração você exigiria antes que um juiz pudesse bloquear produção?
- Quais casos pertencem às partições canary, regression e historical-failure?

## Tarefa 8: Limpeza

**Remova recursos do Azure**

1. Execute os seguintes comandos:

```powershell
$env:AZURE_DEV_USER_AGENT='microsoft_foundry_skill'
azd down --purge
Remove-Item Env:AZURE_DEV_USER_AGENT
```

2. Confirme que o grupo de recursos foi excluído.
3. Mantenha apenas relatórios locais sintéticos que seu instrutor exigir.

**Desative o ambiente virtual**

4. Execute este comando em todo terminal onde `(.venv)` apareça no prompt:

```powershell
deactivate
```

5. Confirme que `(.venv)` não aparece mais antes de mudar para outro diretório de laboratório.

## Resumo

Você implementou um workflow de avaliação Microsoft Foundry que usa datasets sintéticos, avaliadores especializados, calibração com rótulos humanos e portões determinísticos de regressão para produzir evidência de liberação.
