targetScope = 'resourceGroup'

@description('Azure region for the Foundry account and project.')
param location string = resourceGroup().location

@description('Model deployment resource name.')
param modelDeploymentName string

@description('Model catalog name.')
param modelName string = modelDeploymentName

@description('Model version available in the selected region.')
param modelVersion string

@description('Short suffix used to make globally unique names.')
param resourceSuffix string = uniqueString(subscription().id, resourceGroup().id)


var accountName = 'aif-fab-life-${resourceSuffix}'
var projectName = 'fabrikam-lifecycle'
var cosmosName = 'cos-fab-life-${resourceSuffix}'
var usageIdentityName = 'id-fab-life-usage-${resourceSuffix}'
var cosmosDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

resource usageIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: usageIdentityName
  location: location
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource lifecycleDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'lifecycle'
  properties: {
    resource: {
      id: 'lifecycle'
    }
  }
}

resource usageContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: lifecycleDatabase
  name: 'usage-meters'
  properties: {
    resource: {
      id: 'usage-meters'
      partitionKey: {
        paths: [
          '/allocation_key'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource usageDataContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, usageIdentity.id, cosmosDataContributorRoleId)
  properties: {
    principalId: usageIdentity.properties.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    scope: cosmos.id
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
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
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundry
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Fabrikam agent lifecycle governance'
    description: 'Synthetic lab project for governed prompt-agent topology releases.'
  }
  dependsOn: [modelDeployment]
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundry
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

output FOUNDRY_PROJECT_ENDPOINT string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${project.name}'
output FOUNDRY_PROJECT_ID string = project.id
output FOUNDRY_ACCOUNT_NAME string = foundry.name
output FOUNDRY_PROJECT_NAME string = project.name
output PROJECT_PRINCIPAL_ID string = project.identity.principalId
output COSMOS_ENDPOINT string = cosmos.properties.documentEndpoint
output COSMOS_DATABASE string = lifecycleDatabase.name
output COSMOS_CONTAINER string = usageContainer.name
output USAGE_IDENTITY_CLIENT_ID string = usageIdentity.properties.clientId
output USAGE_IDENTITY_PRINCIPAL_ID string = usageIdentity.properties.principalId
output FOUNDRY_MODEL_NAME string = modelDeployment.name
output FOUNDRY_MODEL_VERSION string = modelVersion
