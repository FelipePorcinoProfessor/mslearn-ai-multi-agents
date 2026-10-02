param environmentName string
param location string
param principalId string
param suffix string
param embeddingDeploymentName string

var searchName = 'srch${replace(take(environmentName, 12), '-', '')}${suffix}'
var openAIName = 'aoai${replace(take(environmentName, 12), '-', '')}${suffix}'
var searchServiceContributorRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
var searchIndexDataContributorRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
var openAIUserRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: searchName
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    disableLocalAuth: true
    hostingMode: 'default'
    publicNetworkAccess: 'Enabled'
    replicaCount: 1
    partitionCount: 1
    semanticSearch: 'free'
  }
}

resource openAI 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAIName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAIName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource embedding 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAI
  name: embeddingDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 20
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

resource searchServiceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, principalId, searchServiceContributorRole)
  scope: search
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: searchServiceContributorRole
  }
}

resource searchDataRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, principalId, searchIndexDataContributorRole)
  scope: search
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: searchIndexDataContributorRole
  }
}

resource openAIRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAI.id, principalId, openAIUserRole)
  scope: openAI
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: openAIUserRole
  }
}

output searchEndpoint string = 'https://${search.name}.search.windows.net'
output openAIEndpoint string = openAI.properties.endpoint
