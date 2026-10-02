targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short azd environment name used in deterministic resource names.')
param environmentName string

@description('Model deployment resource name.')
param modelDeploymentName string

@description('Model catalog name.')
param modelName string = modelDeploymentName

@description('Model version available in the selected region.')
param modelVersion string

@description('Object ID of the learner who runs the local multi-agent workflow.')
param principalId string


var suffix = uniqueString(subscription().id, resourceGroup().id, environmentName)
var foundryName = 'fdry${take(suffix, 18)}'
var projectName = 'lab11-${take(environmentName, 12)}'
var workspaceName = 'log-lab11-${take(suffix, 18)}'
var insightsName = 'appi-lab11-${take(suffix, 18)}'
var foundryUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
var monitoringMetricsPublisherRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
var logAnalyticsReaderRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '73c42c96-874c-492b-b04d-ab87d138a893')

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: foundryName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Allow' }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundry
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Fabrikam responsible AI multi-agent review'
    description: 'Synthetic multi-agent project for content safety, fairness, transparency, and accountability validation.'
  }
  dependsOn: [modelDeployment]
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundry
  name: modelDeploymentName
  sku: { name: 'GlobalStandard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: modelName, version: modelVersion }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: {
    retentionInDays: 30
    sku: { name: 'PerGB2018' }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: insightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
  }
}

resource tracingConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  parent: project
  name: insights.name
  properties: {
    category: 'AppInsights'
    target: insights.id
    authType: 'ApiKey'
    credentials: { key: insights.properties.ConnectionString }
    metadata: {
      ApiType: 'Azure'
      ResourceId: insights.id
      location: location
    }
  }
}

resource learnerFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, principalId, 'Foundry User')
  scope: foundry
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: foundryUserRoleId
  }
}

resource learnerTelemetryPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, principalId, 'Monitoring Metrics Publisher')
  scope: insights
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: monitoringMetricsPublisherRoleId
  }
}

resource learnerTraceReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, principalId, 'Log Analytics Reader')
  scope: insights
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: logAnalyticsReaderRoleId
  }
}

output FOUNDRY_PROJECT_ENDPOINT string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${project.name}'
output FOUNDRY_PROJECT_ID string = project.id
output FOUNDRY_ACCOUNT_NAME string = foundry.name
output FOUNDRY_MODEL_NAME string = modelDeployment.name
output APPLICATIONINSIGHTS_RESOURCE_ID string = insights.id
output APPLICATIONINSIGHTS_CONNECTION_STRING string = insights.properties.ConnectionString
output LOG_ANALYTICS_WORKSPACE_ID string = workspace.properties.customerId
