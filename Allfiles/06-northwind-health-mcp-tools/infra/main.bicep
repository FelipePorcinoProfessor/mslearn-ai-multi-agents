targetScope = 'resourceGroup'

@minLength(1)
param environmentName string

@description('Azure region approved for the lab.')
param location string

@description('Container image used before azd deploy publishes the lab image.')
param bootstrapImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Client ID of the Microsoft Entra application registration that protects the MCP API.')
param mcpEntraClientId string

@description('Tenant ID that issues access tokens for the MCP API.')
param mcpEntraTenantId string


var suffix = uniqueString(subscription().id, resourceGroup().id, environmentName)

module resources 'resources.bicep' = {
  name: 'mcp-resources-${suffix}'
  params: {
    environmentName: environmentName
    location: location
    suffix: suffix
    bootstrapImage: bootstrapImage
    mcpEntraClientId: mcpEntraClientId
    mcpEntraTenantId: mcpEntraTenantId
  }
}

output AZURE_RESOURCE_GROUP_NAME string = resourceGroup().name
output AZURE_CONTAINER_APP_NAME string = resources.outputs.containerAppName
output MCP_SERVER_URL string = resources.outputs.mcpServerUrl
output MCP_TOKEN_SCOPE string = resources.outputs.mcpTokenScope
output MCP_ENTRA_CLIENT_ID string = mcpEntraClientId
output MANAGED_IDENTITY_PRINCIPAL_ID string = resources.outputs.managedIdentityPrincipalId
