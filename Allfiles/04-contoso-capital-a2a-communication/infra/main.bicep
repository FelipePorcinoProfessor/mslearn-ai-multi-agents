targetScope = 'resourceGroup'
param location string = resourceGroup().location
param environmentName string
param modelDeploymentName string
param modelName string = modelDeploymentName
param modelVersion string
param principalId string
var suffix = uniqueString(subscription().id, resourceGroup().id, environmentName)
var foundryName = 'fdry${take(suffix, 18)}'
var cosmosName = 'cosmos${take(suffix, 18)}'
var workspaceName = 'log-lab04-${take(suffix, 18)}'
var insightsName = 'appi-lab04-${take(suffix, 18)}'
resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
	name: foundryName
	location: location
	kind: 'AIServices'
	sku: { name: 'S0' }
	identity: { type: 'SystemAssigned' }
	properties: { allowProjectManagement: true, customSubDomainName: foundryName, publicNetworkAccess: 'Enabled', networkAcls: { defaultAction: 'Allow' } }
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
	parent: foundry
	name: 'lab04-${take(environmentName, 12)}'
	location: location
	identity: { type: 'SystemAssigned' }
	properties: { displayName: 'Lab 04 A2A' }
	dependsOn: [deployment]
}
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
	name: workspaceName
	location: location
	properties: { retentionInDays: 30, sku: { name: 'PerGB2018' } }
}
resource insights 'Microsoft.Insights/components@2020-02-02' = {
	name: insightsName
	location: location
	kind: 'web'
	properties: { Application_Type: 'web', WorkspaceResourceId: workspace.id }
}
resource tracingConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
	parent: project
	name: insights.name
	properties: { category: 'AppInsights', target: insights.id, authType: 'ApiKey', credentials: { key: insights.properties.ConnectionString }, metadata: { ApiType: 'Azure', ResourceId: insights.id, location: location } }
}
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
	parent: foundry
	name: modelDeploymentName
	sku: { name: 'GlobalStandard', capacity: 10 }
	properties: { model: { format: 'OpenAI', name: modelName, version: modelVersion }, versionUpgradeOption: 'OnceNewDefaultVersionAvailable' }
}
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
	name: cosmosName
	location: location
	kind: 'GlobalDocumentDB'
	properties: {
		databaseAccountOfferType: 'Standard'
		disableLocalAuth: true
		consistencyPolicy: { defaultConsistencyLevel: 'Session' }
		locations: [{ locationName: location, failoverPriority: 0, isZoneRedundant: false }]
		publicNetworkAccess: 'Enabled'
	}
}
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
	parent: cosmos
	name: 'agent-ecosystem'
	properties: { resource: { id: 'agent-ecosystem' }, options: { throughput: 400 } }
}
resource containers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = [for item in [{ name: 'registry', ttl: 300 }, { name: 'tasks', ttl: -1 }, { name: 'audit', ttl: -1 }]: {
	parent: database
	name: item.name
	properties: { resource: { id: item.name, partitionKey: { paths: ['/tenantId'], kind: 'Hash' }, defaultTtl: item.ttl }, options: {} }
}]
resource dataRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = {
	parent: cosmos
	name: guid(cosmos.id, principalId, 'data-contributor')
	properties: { roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002', principalId: principalId, scope: cosmos.id }
}
output FOUNDRY_PROJECT_ENDPOINT string = 'https://${foundry.name}.services.ai.azure.com/api/projects/${project.name}'
output FOUNDRY_PROJECT_ID string = project.id
output FOUNDRY_MODEL_NAME string = deployment.name
output COSMOS_ENDPOINT string = cosmos.properties.documentEndpoint
output COSMOS_DATABASE_NAME string = database.name
output APPLICATIONINSIGHTS_RESOURCE_ID string = insights.id
output LOG_ANALYTICS_WORKSPACE_ID string = workspace.properties.customerId
