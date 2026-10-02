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

@description('Object ID of the learner who runs the local data-plane validation.')
param principalId string


var suffix = uniqueString(subscription().id, resourceGroup().id, environmentName)
var foundryName = 'fdry${take(suffix, 18)}'
var projectName = 'lab10-${take(environmentName, 12)}'
var cosmosName = 'cosmos${take(suffix, 18)}'
var workspaceName = 'log-lab10-${take(suffix, 18)}'
var insightsName = 'appi-lab10-${take(suffix, 18)}'
var cosmosDataContributorRoleId = '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
var dataContainerNames = [
  'tenant-policies'
  'security-audit'
]

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
    displayName: 'Fabrikam zero-trust multi-agent review'
    description: 'Synthetic multi-agent project for tenant isolation and zero-trust policy validation.'
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

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [
      { locationName: location, failoverPriority: 0, isZoneRedundant: false }
    ]
    capabilities: [
      { name: 'EnableServerless' }
    ]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: cosmos
  name: 'fabrikam-review'
  properties: {
    resource: { id: 'fabrikam-review' }
    options: {}
  }
}

resource policyContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: database
  name: 'tenant-policies'
  properties: {
    resource: {
      id: 'tenant-policies'
      partitionKey: { paths: ['/tenantId'], kind: 'Hash' }
    }
    options: {}
  }
}

resource auditContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: database
  name: 'security-audit'
  properties: {
    resource: {
      id: 'security-audit'
      partitionKey: { paths: ['/tenantId'], kind: 'Hash' }
      defaultTtl: 2592000
    }
    options: {}
  }
}

resource learnerDataRoles 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = [for containerName in dataContainerNames: {
  parent: cosmos
  name: guid(cosmos.id, principalId, containerName)
  properties: {
    roleDefinitionId: cosmosDataContributorRoleId
    principalId: principalId
    scope: '${cosmos.id}/dbs/${database.name}/colls/${containerName}'
  }
  dependsOn: [
    policyContainer
    auditContainer
  ]
}]

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

output FOUNDRY_PROJECT_ENDPOINT string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${project.name}'
output FOUNDRY_PROJECT_ID string = project.id
output FOUNDRY_PROJECT_MANAGED_IDENTITY_PRINCIPAL_ID string = project.identity.principalId
output FOUNDRY_ACCOUNT_NAME string = foundry.name
output FOUNDRY_MODEL_NAME string = modelDeployment.name
output COSMOS_ACCOUNT_ID string = cosmos.id
output COSMOS_ENDPOINT string = cosmos.properties.documentEndpoint
output COSMOS_DATABASE_NAME string = database.name
output COSMOS_POLICY_CONTAINER_NAME string = policyContainer.name
output COSMOS_AUDIT_CONTAINER_NAME string = auditContainer.name
output APPLICATIONINSIGHTS_RESOURCE_ID string = insights.id
output LOG_ANALYTICS_WORKSPACE_ID string = workspace.properties.customerId
