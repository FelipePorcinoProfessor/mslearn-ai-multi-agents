targetScope = 'resourceGroup'

param location string = resourceGroup().location
param resourceToken string = uniqueString(subscription().id, resourceGroup().id)
param principalId string
param modelDeploymentName string
param modelName string = modelDeploymentName
param modelVersion string

var accountName = 'awopt${resourceToken}'
var cacheName = 'awopt-cache-${resourceToken}'

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: 'aw-optimization'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {}
  dependsOn: [
    modelDeployment
  ]
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: modelDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

resource cache 'Microsoft.Cache/redisEnterprise@2025-07-01' = {
  name: cacheName
  location: location
  sku: { name: 'Balanced_B0' }
  properties: {
    highAvailability: 'Disabled'
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource cacheDatabase 'Microsoft.Cache/redisEnterprise/databases@2025-07-01' = {
  parent: cache
  name: 'default'
  properties: {
    accessKeysAuthentication: 'Disabled'
    clientProtocol: 'Encrypted'
    clusteringPolicy: 'NoCluster'
    evictionPolicy: 'AllKeysLRU'
  }
}

resource cacheAccess 'Microsoft.Cache/redisEnterprise/databases/accessPolicyAssignments@2025-07-01' = {
  parent: cacheDatabase
  name: uniqueString(cacheDatabase.id, principalId)
  properties: {
    accessPolicyName: 'default'
    user: { objectId: principalId }
  }
}

resource aiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, principalId, 'Azure AI User')
  scope: account
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

output FOUNDRY_PROJECT_ENDPOINT string = 'https://${accountName}.services.ai.azure.com/api/projects/aw-optimization'
output REDIS_HOST string = cache.properties.hostName
output REDIS_PORT int = cacheDatabase.properties.port
output TIER1_DEPLOYMENT string = modelDeployment.name
output TIER2_DEPLOYMENT string = modelDeployment.name
output TIER3_DEPLOYMENT string = modelDeployment.name
