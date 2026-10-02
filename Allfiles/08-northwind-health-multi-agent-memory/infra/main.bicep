targetScope = 'resourceGroup'

param environmentName string
param location string
param principalId string
param chatDeploymentName string = 'gpt-5.4-mini'
param embeddingDeploymentName string = 'text-embedding-3-small'

var suffix = take(uniqueString(subscription().id, resourceGroup().id, environmentName), 8)

module memoryResources 'memory-resources.bicep' = {
  name: 'memory-resources-${suffix}'
  params: {
    environmentName: environmentName
    location: location
    principalId: principalId
    suffix: suffix
    chatDeploymentName: chatDeploymentName
    embeddingDeploymentName: embeddingDeploymentName
  }
}

output AZURE_RESOURCE_GROUP_NAME string = resourceGroup().name
output AZURE_COSMOS_ENDPOINT string = memoryResources.outputs.cosmosEndpoint
output AZURE_COSMOS_DATABASE_NAME string = 'clinical-memory-db'
output AZURE_COSMOS_MEMORY_CONTAINER string = 'patient-memories'
output AZURE_COSMOS_AUDIT_CONTAINER string = 'memory-audit'
output FOUNDRY_PROJECT_ID string = memoryResources.outputs.foundryProjectId
output FOUNDRY_ACCOUNT_NAME string = memoryResources.outputs.foundryAccountName
output FOUNDRY_PROJECT_NAME string = memoryResources.outputs.foundryProjectName
output FOUNDRY_PROJECT_ENDPOINT string = memoryResources.outputs.foundryProjectEndpoint
output AZURE_OPENAI_ENDPOINT string = memoryResources.outputs.foundryOpenAIEndpoint
output FOUNDRY_MODEL_NAME string = chatDeploymentName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = embeddingDeploymentName
output AZURE_AI_PROJECT_ID string = memoryResources.outputs.foundryProjectId
output AZURE_AI_PROJECT_ENDPOINT string = memoryResources.outputs.foundryProjectEndpoint
output AZURE_AI_MODEL_DEPLOYMENT_NAME string = chatDeploymentName
output AZURE_TENANT_ID string = tenant().tenantId
