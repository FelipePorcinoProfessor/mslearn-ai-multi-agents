targetScope = 'resourceGroup'

param environmentName string
param location string
param principalId string
param embeddingDeploymentName string = 'text-embedding-3-small'

var suffix = take(uniqueString(subscription().id, resourceGroup().id, environmentName), 8)

module searchResources 'search-resources.bicep' = {
  name: 'search-resources-${suffix}'
  params: {
    environmentName: environmentName
    location: location
    principalId: principalId
    suffix: suffix
    embeddingDeploymentName: embeddingDeploymentName
  }
}

output AZURE_RESOURCE_GROUP_NAME string = resourceGroup().name
output AZURE_SEARCH_ENDPOINT string = searchResources.outputs.searchEndpoint
output AZURE_OPENAI_ENDPOINT string = searchResources.outputs.openAIEndpoint
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = embeddingDeploymentName
