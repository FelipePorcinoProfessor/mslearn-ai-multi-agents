targetScope = 'resourceGroup'

param location string = resourceGroup().location
param resourceToken string = uniqueString(subscription().id, resourceGroup().id)
param principalId string

var cosmosName = 'awapproval${resourceToken}'
var busName = 'awapproval-${resourceToken}'

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    locations: [{ locationName: location, failoverPriority: 0 }]
    capabilities: [{ name: 'EnableServerless' }]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'approvals'
  properties: { resource: { id: 'approvals' } }
}

resource state 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'workflow-state'
  properties: {
    resource: { id: 'workflow-state', partitionKey: { paths: ['/workflow_id'], kind: 'Hash' } }
  }
}

resource audit 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'approval-audit'
  properties: {
    resource: { id: 'approval-audit', partitionKey: { paths: ['/workflow_id'], kind: 'Hash' } }
  }
}

resource cosmosDataRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, principalId)
  properties: {
    principalId: principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmos.id
  }
}

resource bus 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: busName
  location: location
  sku: { name: 'Standard', tier: 'Standard' }
  properties: { disableLocalAuth: true, minimumTlsVersion: '1.2' }
}

resource requests 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  parent: bus
  name: 'approval-requests'
  properties: { duplicateDetectionHistoryTimeWindow: 'PT10M', requiresDuplicateDetection: true }
}

resource decisions 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  parent: bus
  name: 'approval-decisions'
  properties: { duplicateDetectionHistoryTimeWindow: 'PT10M', requiresDuplicateDetection: true }
}

resource busDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(bus.id, principalId, 'Azure Service Bus Data Owner')
  scope: bus
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '090c5cfd-751d-490a-894a-3ce6f1109419')
  }
}

output COSMOS_ENDPOINT string = cosmos.properties.documentEndpoint
output COSMOS_DATABASE string = database.name
output STATE_CONTAINER string = state.name
output AUDIT_CONTAINER string = audit.name
output SERVICE_BUS_NAMESPACE string = '${bus.name}.servicebus.windows.net'
output REQUEST_QUEUE string = requests.name
output DECISION_QUEUE string = decisions.name
