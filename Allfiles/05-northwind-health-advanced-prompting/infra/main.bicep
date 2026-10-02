targetScope = 'resourceGroup'
param location string = resourceGroup().location
param environmentName string
param modelDeploymentName string
param modelName string = modelDeploymentName
param modelVersion string
var suffix = uniqueString(subscription().id, resourceGroup().id, environmentName)
var accountName = 'fdry${take(suffix, 18)}'
var workspaceName = 'log-lab05-${take(suffix, 18)}'
var insightsName = 'appi-lab05-${take(suffix, 18)}'
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
	name: accountName
	location: location
	kind: 'AIServices'
	sku: { name: 'S0' }
	identity: { type: 'SystemAssigned' }
	properties: { allowProjectManagement: true, customSubDomainName: accountName, publicNetworkAccess: 'Enabled', networkAcls: { defaultAction: 'Allow' } }
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
	parent: account
	name: 'lab05-${take(environmentName, 12)}'
	location: location
	identity: { type: 'SystemAssigned' }
	properties: { displayName: 'Lab 05 prompting' }
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
	parent: account
	name: modelDeploymentName
	sku: { name: 'GlobalStandard', capacity: 10 }
	properties: { model: { format: 'OpenAI', name: modelName, version: modelVersion }, versionUpgradeOption: 'OnceNewDefaultVersionAvailable' }
}
output FOUNDRY_PROJECT_ENDPOINT string = 'https://${account.name}.services.ai.azure.com/api/projects/${project.name}'
output FOUNDRY_PROJECT_ID string = project.id
output FOUNDRY_MODEL_NAME string = deployment.name
output APPLICATIONINSIGHTS_RESOURCE_ID string = insights.id
output LOG_ANALYTICS_WORKSPACE_ID string = workspace.properties.customerId
