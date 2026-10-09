---
lab:
  title: 'Implementar CI/CD para hosted agents do Microsoft Foundry'
  description: 'Liberar versões imutáveis de hosted-agents do Microsoft Foundry com GitHub Actions e, em seguida, usar um dashboard leve em Container Apps para demonstrar progressive delivery e rollback por conjunto compatível.'
  duration: 45
  level: 400
  islab: true
  status: 'released'
layout: default
---

# Implementar CI/CD para hosted agents do Foundry

## Cenário do cliente

Fabrikam usa três agentes de IA para revisar alterações de código:

- O **scanner** identifica vulnerabilidades de segurança.
- O **reviewer** avalia a manutenibilidade e o risco de release.
- O **orchestrator** invoca ambos os especialistas e produz uma única recomendação de release.

Scanner, reviewer e orchestrator são hosted agents v2 do Microsoft Foundry. Cada `azd deploy` bem-sucedido cria uma nova versão imutável do agente Foundry. As chamadas usam o endpoint Responses do hosted-agent apenas depois de criar uma session com um `version_ref` concreto, de modo que a sessão fica vinculada à versão imutável gravada. Eles não são Container Apps.

A Fabrikam também opera um aplicativo web tradicional deliberadamente fino: um dashboard e gateway em Container Apps. Cada revisão do dashboard aponta para uma versão exata do orchestrator e exibe:

- Sua revisão do Container App e canal de release.
- O ID do release-set selecionado.
- O nome do agente orchestrator imutável, a versão Foundry e o endpoint Responses.

O dashboard é a fronteira de progressive delivery. Durante um canário, Container Apps envia 75% das requisições para a revisão estável do dashboard e 25% para a revisão candidata do dashboard. Os agentes não alegam roteamento ponderado nativo do Foundry.

## Cenário do laboratório

Prepare acesso GitHub sem senha ao Azure, ative os workflows fornecidos e faça o deploy do release inicial para um ambiente de desenvolvimento. Em seguida, altere a versão lógica do scanner, revise evidências de pull request sem credenciais e implante um release set candidato.

Use a URL ponderada do dashboard para observar roteamento 75/25. Use as URLs com rótulos stable e candidate para verificação determinística. Promova o tráfego saudável do dashboard para 0/100 e então exerça um perfil de regressão. O rollback deve usar um manifesto de release verificado e persistido, restaurar a revisão do dashboard que aponta para esse release set compatível e verificar a versão exata restaurada do orchestrator tanto através do dashboard quanto por invocação com versionamento fixo.

<!-- ESPAÇO PARA DIAGRAMA DO LAB: Mostrar deployment do scanner e reviewer antes do orchestrator, a revisão do dashboard vinculada à versão, tráfego canário, promoção e rollback para um release set verificado. -->

Ao final deste exercício, você saberá:

- Validar versões semânticas lógicas estritas, contratos de ferramenta, um DAG de dependência, política de modelo e manifests de hosted-agent v2 sem credenciais Azure.
- Implantar hosted agents do Foundry de forma serial em estado compartilhado azd e capturar nomes imutáveis, versões e endpoints Responses.
- Vincular evidência determinística de avaliação a um commit de origem e ao release set do Foundry.
- Usar GitHub environments, OIDC, Bicep e projetos Foundry separados para development, staging e production.
- Aplicar tráfego canary e blue-green em uma fronteira tradicional Container Apps sem representar incorretamente o roteamento do Foundry.
- Restaurar um release set compatível a partir de evidências persistidas e manter o fechamento de rollback por dependências reversas.

> [!IMPORTANT]
> Este laboratório cria recursos faturáveis em Azure Container Registry, Log Analytics, Container Apps e Microsoft Foundry, incluindo um deployment de modelo `gpt-5.4-mini` fixado na versão `2026-03-17`. Use uma assinatura de treinamento isolada e remova os grupos de recurso quando terminar. A disponibilidade e cota de modelos variam por região.

## Entenda as três identidades de versão

O laboratório mantém intencionalmente três sistemas de versão separados.

| Identidade | Exemplo | Propósito |
|---|---|---|
| Versão semântica lógica | `scanner 1.2.0` | Compatibilidade de origem e intervalos de dependência |
| Versão imutável do agente Foundry | `fabrikam-code-scanner`, versão `7` | Agente executável implantado, endpoint de versão e session vinculada à versão |
| Revisão do Container App do dashboard | `fabrikam-release-dev--abc123` | Canal de release do aplicativo tradicional e tráfego 75/25 ou 0/100 |

Uma versão lógica não é uma versão do Foundry. Uma versão do Foundry não é uma revisão do Container App. O manifesto do release-set registra as três e impede que o pipeline as trate como intercambiáveis.

## Entenda a arquitetura de release

O grafo de deployment é:

```text
scanner  --------+
                  +--> orchestrator --> version-bound hosted-agent session
reviewer --------+                           ^
                                              |
                                   dashboard revision
                                   (stable or candidate)
```

A origem tem quatro partes:

- `azure.yaml` e `src/*_agent.py` definem os três hosted agents; `dashboard/app.py` é o único serviço Container Apps.
- `agents/*.yml` define versões lógicas, dependências, política de modelo, identidade de avaliação, instruções e contratos de ferramenta.
- `scripts/` captura saídas de deployment imutáveis em um release set, enquanto `assets/evaluation/` e os perfis de qualidade fornecem evidência de validação.
- `infra/` e `assets/workflows/` criam a fronteira Azure e fornecem os templates de workflow inativos que você ativa durante o laboratório.

O release set capturado vincula a origem revisada e os metadados de política a cada versão imutável do agente Foundry e à revisão do dashboard que invoca o orchestrator.

## Tarefa 1: Preparar o laboratório

Você precisará de:

- Uma assinatura Azure na qual um administrador possa conceder as funções necessárias.
- Uma conta GitHub que possa criar um repositório privado, workflows, environments, variables, regras de proteção, releases e issues.
- [Python 3.13](https://www.python.org/downloads/), [Git](https://git-scm.com/downloads), [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) e [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd).
- Visual Studio Code com as extensões Python, GitHub Actions e Bicep.

1. Clone o repositório fonte do laboratório, abra-o no Visual Studio Code e mude para o diretório starter:

```powershell
git clone https://github.com/MicrosoftLearning/mslearn-ai-multi-agents.git
cd mslearn-ai-multi-agents\Allfiles\09-fabrikam-multi-agent-cicd
```

2. Faça login e confirme a assinatura:

```powershell
az login
az account show --output table
$env:AZURE_DEV_USER_AGENT = 'microsoft_foundry_skill'; azd auth login
```

3. Use apenas dados sintéticos. Não adicione um client secret do Azure nem um segredo `AZURE_CREDENTIALS` ao GitHub.

4. Abra `azure.yaml`. Confirme que scanner, reviewer e orchestrator são hosted agents e que dashboard é o único serviço Container Apps.

5. Abra `agents/orchestrator.yml`. Identifique sua versão lógica, intervalos de dependência scanner/reviewer, versão exata do modelo, identidade de avaliação e manifest Responses hospedado.

6. Abra `dashboard/app.py`. Encontre os campos release-set, release-channel, Container App revision, versão do orchestrator e endpoint Responses mostrados aos alunos.

## Tarefa 2: Validar o starter localmente

1. Crie o virtual environment e instale dependências:

```powershell
.\scripts\setup.ps1
. .\.venv\Scripts\Activate.ps1
```

2. Execute a validação completa sem credenciais:

```powershell
python scripts\preflight.py
python scripts\validate_workflows.py
python -m unittest discover -s Allfiles\09-fabrikam-multi-agent-cicd\tests -v
python scripts\export_release.py --agents agents --manifest artifacts\release-set.json --contracts artifacts\current-contracts.json --source-commit local-validation --environment pr-validation --status validated
python -m src.main validate --manifest artifacts\release-set.json --baseline assets\contracts\baseline.json --candidate artifacts\current-contracts.json --quality assets\quality-metrics-healthy.json --output artifacts\compatibility-report.json
az bicep build --file infra\main.bicep
```

Resultados esperados:

- O preflight reporta três hosted agents v2 do Foundry e um dashboard.
- A validação de workflow confirma OIDC, deployments seriais, chamadas smoke com versão fixa, evidência de rollback persistida e tráfego apenas pelo dashboard.
- Testes direcionados passam.
- O relatório de compatibilidade possui `"compatible": true`.
- Bicep compila sem erros.

3. Abra `artifacts/release-set.json`. Confirme que nomes remotos do Foundry, versões e endpoints são `null`. A validação de pull-request é isenta de credenciais e não pode inventar evidência de deployment. O workflow de deployment preenche esses campos somente após um `azd deploy` bem-sucedido.

4. Opcional: pressione **F5** e escolha uma configuração de hosted-agent para iniciar o ponto de entrada selecionado com o depurador Python do VS Code. O Foundry Toolkit Agent Inspector pode se conectar ao servidor hosted-agent local depois que você fornecer os valores de ambiente locais necessários.

## Tarefa 3: Criar o repositório de prática

1. No GitHub, crie um repositório privado nomeado `fabrikam-agent-cicd`.
2. Não o inicialize com um README, `.gitignore` ou licença.
3. Registre o valor exato `<owner>/fabrikam-agent-cicd`.
4. Copie o starter para um repositório de prática separado:

```powershell
$labRoot = (Get-Location).Path
$practiceRepo = Join-Path (Split-Path $labRoot -Parent) 'fabrikam-agent-cicd'
New-Item -ItemType Directory -Force $practiceRepo
Get-ChildItem $labRoot -Force |
  Where-Object { $_.Name -notin @('.azure', '.env', '.venv', 'artifacts', '__pycache__') } |
  Copy-Item -Destination $practiceRepo -Recurse -Force
Set-Location $practiceRepo
git init
git branch -M main
git remote add origin '<repository-url>'
```

5. Não faça push ainda. Um push para `main` implanta development.

## Tarefa 4: Configurar acesso GitHub sem senha

GitHub Actions troca um token OIDC de curta duração do GitHub por um token Entra. Não crie um client secret.

1. No Microsoft Entra admin center, crie um app registration single-tenant nomeado `fabrikam-agent-github`.
2. Registre:
   - Application (client) ID como `AZURE_CLIENT_ID`.
   - Directory (tenant) ID como `AZURE_TENANT_ID`.
3. Abra a Enterprise application vinculada e registre seu Object ID como `GITHUB_PRINCIPAL_ID`.
4. Adicione uma federated credential para cada GitHub environment:

```text
repo:<owner>/fabrikam-agent-cicd:environment:development
repo:<owner>/fabrikam-agent-cicd:environment:staging
repo:<owner>/fabrikam-agent-cicd:environment:production
```

5. Selecione ou crie um resource group por ambiente:

```powershell
$azureRegion = 'eastus2'
$suffix = (New-Guid).Guid.Substring(0, 8)
@('dev', 'stg', 'prod') | ForEach-Object {
  az group create --name "rg-lab09-$($_)-$suffix" --location $azureRegion | Out-Null
}
```

6. Um administrador Azure deve atribuir à Enterprise application estas funções em cada resource group selecionado:

- **Contributor**
- **Role Based Access Control Administrator**

Essas permissões permitem que o workflow crie Foundry projects específicos do ambiente, deployments de modelos, identities, atribuições RBAC e recursos do dashboard.

## Tarefa 5: Configurar GitHub environments

1. Em Configurações (Settings) > Ambientes (Environments) do repositório, crie:
   - `development`
   - `staging`
   - `production`
2. Adicione estas variáveis de ambiente a cada environment:

| Variável | Exemplo (Development) | Requisito |
|---|---|---|
| `AZURE_CLIENT_ID` | `<application-client-id>` | Mesma aplicação OIDC |
| `AZURE_TENANT_ID` | `<directory-tenant-id>` | Mesmo tenant |
| `AZURE_SUBSCRIPTION_ID` | `<subscription-id>` | Subscription alvo |
| `AZURE_LOCATION` | `eastus2` | Região com cota exata do modelo |
| `AZURE_ENV_NAME` | `lab09-cicd-dev` | Único por ambiente |
| `GITHUB_PRINCIPAL_ID` | `<enterprise-app-object-id>` | Enterprise application Object ID |
| `AZURE_RESOURCE_GROUP_NAME` | `rg-lab09-dev-...` | Único por ambiente |

3. Use `lab09-cicd-stg` e `lab09-cicd-prod` mais seus resource groups distintos para staging e production.
4. Adicione revisores exigidos e restrinja branches de deploy para staging e production.

Cada GitHub environment mapeia para um resource group separado e um Foundry project. O workflow promove a mesma identidade de origem revisada. A produção adicionalmente verifica que staging tem um manifesto verificado e persistido para o mesmo commit e reviewed release ID.

## Tarefa 6: Ativar os workflows

1. Crie `.github/workflows`:

```powershell
New-Item -ItemType Directory -Force .github\workflows
```

2. Copie os quatro templates fornecidos:

```powershell
Copy-Item assets\workflows\validate-agents.yml .github\workflows\validate-agents.yml
Copy-Item assets\workflows\deploy-environment.yml .github\workflows\deploy-environment.yml
Copy-Item assets\workflows\canary-quality-gate.yml .github\workflows\canary-quality-gate.yml
Copy-Item assets\workflows\rollback-agents.yml .github\workflows\rollback-agents.yml
```

3. Revise `.github/workflows/validate-agents.yml`.

Ele não tem login Azure. Ele valida:

- Contratos e versões semânticas lógicas estritas.
- DAG de dependência e fechamento de dependência reversa.
- Política exata de modelo `gpt-5.4-mini` / `2026-03-17`.
- Declarações hosted-agent v2 e entrypoints separados.
- Compilação da origem, testes direcionados, workflows e forma determinística do dataset.

4. Revise `.github/workflows/deploy-environment.yml`.

A ordem de deployment importante é:

```text
azd deploy scanner
azd ai agent show scanner
azd ai agent invoke scanner --version <captured-version>

azd deploy reviewer
azd ai agent show reviewer
azd ai agent invoke reviewer --version <captured-version>

azd deploy orchestrator
azd ai agent show orchestrator
azd ai agent invoke orchestrator --version <captured-version>

azd deploy dashboard
```

Cada comando azd define `AZURE_DEV_USER_AGENT=microsoft_foundry_skill` inline. Scanner e reviewer são seriais porque deploys concorrentes não devem mutar o mesmo estado azd selecionado. Orchestrator só faz deploy depois que seus endpoints imutáveis existirem. A evidência de deployment também registra um endpoint `/versions/<version>` concreto para verificação via CLI. Chamadas HTTP em runtime criam uma session com essa mesma versão concreta solicitada e rejeitam uma versão retornada que não coincida.

5. Encontre `capture_release_set.py` no workflow de deployment. Ele captura:

```text
AGENT_SCANNER_NAME
AGENT_SCANNER_VERSION
AGENT_SCANNER_RESPONSES_ENDPOINT
AGENT_REVIEWER_NAME
AGENT_REVIEWER_VERSION
AGENT_REVIEWER_RESPONSES_ENDPOINT
AGENT_ORCHESTRATOR_NAME
AGENT_ORCHESTRATOR_VERSION
AGENT_ORCHESTRATOR_RESPONSES_ENDPOINT
```

6. Revise `.github/workflows/canary-quality-gate.yml`.

Ele recusa promoção a menos que o artefato candidato contenha evidência de avaliação vinculada à versão e em passing. O fixture healthy/regression é evidência secundária usada apenas para exercitar os ramos de política.

7. Revise `.github/workflows/rollback-agents.yml`.

Ele faz o download de `release-set.json` do GitHub release persistido `verified-<environment>`, valida o environment, o status verificado, a identidade do release-set, todos os bindings de agente, o app/revision do dashboard e a evidência do label stable, então o restaura. Ele não infere que a segunda-revisão-mais-recente seja segura.

Os workflows de deploy, quality e rollback compartilham um grupo de concorrência keyeado por environment com `cancel-in-progress: false`, então duas operações não podem concorrer ao alterar o tráfego do dashboard ou a evidência de release persistida.

8. Valide as cópias ativadas:

```powershell
python scripts\validate_workflows.py
git status --short
```

## Tarefa 7: Implantar o release inicial de development

1. Commit e push:

```powershell
git add .
git commit -m "Initialize Foundry hosted-agent delivery"
git push -u origin main
```

2. Em GitHub Actions, abra Deploy hosted-agent release set.

Observe:

- A validação sem credenciais completa primeiro.
- O GitHub troca seu token OIDC do environment; nenhum client secret armazenado é usado.
- Bicep cria um Foundry project de development, deployment de modelo exato, ACR, Log Analytics, Container Apps environment e um Container App de dashboard.
- Scanner, reviewer e orchestrator cada um cria uma versão imutável do hosted-agent do Foundry.
- Cada agente é checado com `azd ai agent show` e uma invocação smoke com versão fixa.
- O ambiente do orchestrator aponta para os endpoints Responses capturados de scanner e reviewer mais versões exatas; cada chamada cria e verifica uma session fixada naquela versão.
- O dataset determinístico de dois registros roda contra o orchestrator fixado.
- Uma revisão do dashboard é implantada com 100% do tráfego e exibe o release set selecionado exato.
- Como não existe um release `verified-development` e o Azure reporta apenas a revisão de bootstrap da infraestrutura, o workflow trata isso como um primeiro release explícito. Após smoke, avaliação, label stable do dashboard e checagens de evidência de versão passarem, ele persiste este release como a primeira baseline verificada.

3. Baixe `deployment-evidence-development-<run-id>`.
4. Abra `release-set.json`. Compare cada versão lógica com a versão imutável do Foundry.
5. Abra `evaluation-evidence.json`. Confirme o commit de origem, release-set ID, versão exata do orchestrator, identidade do dataset/evaluator e `"status": "passed"`.

## Tarefa 8: Verificar os recursos iniciais

1. No portal do Azure, abra o resource group de development.
2. Abra o projeto Microsoft Foundry.
3. Confirme que o deployment `gpt-5.4-mini` está na versão `2026-03-17`.
4. Abra **Agentes (Agents)** e confirme que scanner, reviewer e orchestrator são hosted agents com versões imutáveis ativas.
5. Compare os nomes e versões dos agentes com `release-set.json`.
6. Confirme que não existem Container Apps scanner, reviewer ou orchestrator.
7. Abra o único Container App do dashboard Fabrikam.
8. Em **Gerenciamento de revisões (Revision management)**, confirme que uma revisão selecionada do dashboard tem 100% do tráfego.
9. Abra a URL do dashboard. Confirme que exibe:
   - Canal `STABLE`.
   - Sua revisão do Container App.
   - Release-set ID.
   - Nome exato do orchestrator, versão Foundry e endpoint Responses.
10. Envie o formulário de revisão sintético. Confirme que o dashboard invoca o orchestrator selecionado.

## Tarefa 9: Criar e revisar um candidato

1. Crie uma branch:

```powershell
git checkout -b feature/scanner-release-metadata
```

2. Em `agents/scanner.yml`, altere:

```yaml
version: 1.2.0
```

para:

```yaml
version: 1.2.1
```

3. Adicione uma sentença de instrução que não altere o contrato da ferramenta:

```text
Include a short confidence explanation for each reported finding.
```

4. Execute a validação local.
5. Commit, push e crie um pull request:

```powershell
git add agents\scanner.yml
git commit -m "Clarify scanner finding confidence"
git push -u origin feature/scanner-release-metadata
```

6. Abra o artefato do workflow de pull-request.
7. Confirme:
   - Versão lógica do scanner é `1.2.1`.
   - O digest do contrato está presente.
   - Não existe finding de quebra de contrato.
   - A dependência `>=1.0.0,<2.0.0` do orchestrator aceita scanner `1.2.1`.
   - Manifests hospedados permanecem Responses `2.0.0`, Python `3.13`.
   - Campos de deployment remoto do Foundry permanecem `null`.

8. Faça merge do pull request.

## Tarefa 10: Verificar exposição 75/25 do dashboard

Após o deployment do merge ter sucesso:

1. Baixe sua evidência de deployment.
2. Confirme que o release set candidato tem novas versões imutáveis do Foundry e um novo release-set ID.
3. Confirme que a revisão do dashboard registra o endpoint de versão exata do orchestrator candidato e usa uma session Responses fixada naquela versão.
4. Abra a URL normal do dashboard e atualize-a pelo menos 12 vezes.
5. Registre quando a página mostrar:
   - Canal stable e a identidade do último release-set verificado.
   - Canal candidate e a identidade do release-set candidato.

A amostra é pequena, então não espere exatamente nove respostas stable e três candidate. Os pesos configurados, não uma curta amostra aleatória, são autoritativos.

6. Abra o `stable_label_url` do `release-set.json` candidato. Seu hostname começa com `stable---`; o workflow obtém o FQDN do app do Azure e verifica o mapeamento label->revision antes de registrá-lo.
7. Atualize-o três vezes. Confirme que ele sempre reporta a mesma revisão de dashboard estável e a versão do orchestrator estável.
8. Abra o `candidate_label_url`.
9. Atualize-o três vezes. Confirme que ele sempre reporta a revisão do dashboard candidata e a versão do orchestrator candidata.
10. No portal do Azure, abra Gerenciamento de revisões (Revision management) do dashboard e verifique os pesos 75/25 e os labels `stable`/`candidate`.

Essas rotas diretas por label são verificação determinística. Os alunos não devem confiar apenas em atualizações aleatórias.

## Tarefa 11: Promover o candidato entre ambientes

1. Em GitHub Actions, execute Assess dashboard canary quality com:
   - Environment: `development`
   - Deployment run ID: deployment run ID candidato
   - Failed agent: `scanner`
   - Metric profile: `healthy`
2. Confirme:
   - Evidência de avaliação vinculada à versão está em passing.
   - A ação de política é `promote`.
   - O tráfego do dashboard muda de 75/25 para 0/100.
   - A revisão candidata do dashboard recebe o label `stable`.
   - `verified-development` contém o `release-set.json` verificado e persistido.
3. Abra a URL do label stable e verifique o release-set promovido e a versão exata do orchestrator.

4. Execute Deploy hosted-agent release set manualmente para `staging`.
5. Informe o mesmo commit de origem revisado implantado em development.
6. Aprove (approve) o environment protegido de staging.
7. Execute sua avaliação healthy canary para criar `verified-staging`.
8. Execute Deploy hosted-agent release set para `production` com o mesmo commit de origem.
9. Confirme que production aguarda sua aprovação de environment protegido e verifica staging:
   - Commit de origem.
   - Reviewed release ID.
   - Status verificado.

Os números de versão do agente Foundry podem diferir entre projects. A identidade da origem revisada, versões lógicas, contratos, política de modelo e identidade de avaliação permanecem as mesmas.

## Tarefa 12: Exercitar rollback por conjunto compatível

1. Execute Assess dashboard canary quality para um candidato com:
   - Metric profile: `regression`
   - Failed agent: `scanner`
2. Confirme que a ação de política é `rollback`.
3. Abra Restore verified Foundry release set.
4. Confirme que ele:
   - Faz o download do release set candidato do deployment run.
   - Faz o download do manifesto ambiente do último verificado persistido.
   - Deriva o fechamento de rollback `orchestrator, scanner` em ordem de dependência reversa.
   - Restaura 100% do tráfego do dashboard para a revisão exata registrada no manifesto verificado.
   - Aplica o label `stable` a essa revisão.
   - Verifica que o dashboard reporta o release-set ID persistido e a versão exata do orchestrator.
   - Invoca essa versão exata do orchestrator Foundry com `azd ai agent invoke --version`.
   - Cria uma issue de incidente no GitHub e faz upload da evidência de rollback.

5. Abra `rollback-evidence.json`. Confirme que registra:
   - Release-set ID restaurado.
   - Revisão do dashboard.
   - Nome exato do orchestrator, versão e endpoint Responses.
   - 100% do tráfego.
6. Abra a URL estável do dashboard e verifique os mesmos valores.

Rollback não exclui versões imutáveis do Foundry. Ele restaura o tráfego para uma revisão do dashboard que já está vinculada a um release set do Foundry conhecido como compatível.

## Tarefa 13: Revisar as evidências do release

Retenha:

- Relatório de compatibilidade do pull-request.
- Manifests do release-set candidato e verificado.
- Evidência de avaliação vinculada à versão.
- Evidência de tráfego 75/25 e 0/100.
- Respostas de rota direta stable/candidate.
- Fechamento de rollback, metadados restaurados do dashboard, saída de invocação fixada e link do incidente.

### Reflita sobre o design do release

1. Por que uma versão semântica lógica é insuficiente para identificar um agente deployed do Foundry?
2. Por que o release set deve capturar um endpoint de versão imutável e criar uma session vinculada à versão em vez de invocar apenas um nome lógico do agente?
3. Por que o orchestrator faz deploy depois do scanner e reviewer mesmo que os agentes especialistas sejam independentes?
4. Por que o dashboard, em vez dos agentes Foundry, é a fronteira de tráfego 75/25?
5. Como URLs diretas por label tornam a verificação canary determinística?
6. Por que o rollback não pode supor que a segunda-revisão-mais-recente do Container App seja segura?
7. Por que o fechamento por dependência reversa inclui o orchestrator quando o scanner falha?
8. Quais campos de release devem permanecer idênticos ao promover a origem revisada de staging para production, e quais valores Foundry específicos do ambiente podem diferir?
9. Por que os fixtures healthy/regression são secundários à evidência de avaliação smoke vinculada à versão?
10. Qual identidade gerenciada invoca o Foundry a partir do dashboard, e por que uma API key armazenada é desnecessária?

## Desafio opcional: Estender o dataset de smoke-test

Adicione um terceiro registro determinístico de smoke que exija que o orchestrator explique por que um release deve ser retido quando scanner e reviewer discordam. Incremente a versão do dataset em cada definição de agente, atualize a expectativa do teste direcionado e confirme que o reviewed release ID muda mesmo sem alteração do contrato da ferramenta. Não enfraqueça a política de modelo exata nem promova sem evidência vinculada à versão.

## Tarefa 14: Limpeza

Delete cada grupo de recurso do laboratório:

```powershell
az group delete --name '<development-resource-group>' --yes --no-wait
az group delete --name '<staging-resource-group>' --yes --no-wait
az group delete --name '<production-resource-group>' --yes --no-wait
```

Em seguida:

1. Exclua os GitHub environments `development`, `staging` e `production`.
2. Exclua os GitHub releases de propriedade da automação `verified-development`, `verified-staging` e `verified-production`.
3. Exclua o app registration do Entra e a Enterprise application se eles foram criados apenas para este laboratório.
4. Exclua o repositório de prática se você não precisar mais da evidência.

## Suposições apenas para execução ao vivo

Nenhum deployment ao vivo é necessário para validar a origem do laboratório. Durante um deployment real do aluno:

- A região selecionada deve suportar `gpt-5.4-mini` versão `2026-03-17` com cota suficiente.
- `azd` deve retornar `AGENT_<SERVICE>_NAME`, `AGENT_<SERVICE>_VERSION` e `AGENT_<SERVICE>_RESPONSES_ENDPOINT` após cada deployment de hosted-agent.
- Hosted-agent session e endpoints Responses devem aceitar tokens bearer Microsoft Entra obtidos por `DefaultAzureCredential`, e a criação de session deve retornar a versão concreta solicitada.
- A proteção de environment do GitHub deve impor aprovações para staging e production.
- Labels de revisão do Container Apps e URLs diretas por label devem ser habilitados pela versão atual do Azure CLI/Container Apps API.
