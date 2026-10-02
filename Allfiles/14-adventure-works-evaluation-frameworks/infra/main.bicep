targetScope = 'resourceGroup'

@description('Azure region for the Microsoft Foundry resources.')
param location string = resourceGroup().location

@description('Short unique suffix used in globally unique resource names.')
param resourceToken string = uniqueString(subscription().id, resourceGroup().id)

@description('Existing Entra object ID that receives the Azure AI User role.')
param principalId string

@description('Model deployment resource name.')
param modelDeploymentName string

@description('Model catalog name.')
param modelName string = modelDeploymentName

@description('Model version available in the selected region.')
param modelVersion string

var accountName = 'aweval${resourceToken}'
var projectName = 'aw-evaluation'

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
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

resource aiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, principalId, 'Azure AI User')
  scope: account
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

output FOUNDRY_PROJECT_ENDPOINT string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}'
output FOUNDRY_ACCOUNT_ENDPOINT string = 'https://${accountName}.services.ai.azure.com'
output FOUNDRY_ACCOUNT_NAME string = account.name
output FOUNDRY_MODEL_NAME string = modelDeployment.name
output FOUNDRY_MODEL_VERSION string = modelVersion
