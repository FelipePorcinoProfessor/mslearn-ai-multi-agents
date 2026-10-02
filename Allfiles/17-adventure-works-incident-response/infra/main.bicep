targetScope = 'resourceGroup'

param location string = resourceGroup().location
param resourceToken string = uniqueString(subscription().id, resourceGroup().id)
param principalId string

var workspaceName = 'aw-incident-${resourceToken}'
var insightsName = 'aw-incident-${resourceToken}'
var storageName = 'awincident${resourceToken}'
var eventHubNamespaceName = 'aw-incident-alerts-${resourceToken}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: {
    retentionInDays: 30
    features: { enableLogAccessUsingOnlyResourcePermissions: true }
    sku: { name: 'PerGB2018' }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: insightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    DisableLocalAuth: true
    RetentionInDays: 30
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: { deleteRetentionPolicy: { enabled: true, days: 7 } }
}

resource snapshots 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'trace-snapshots'
  properties: { publicAccess: 'None' }
}

resource reports 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'incident-reports'
  properties: { publicAccess: 'None' }
}

resource alertEventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: eventHubNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource alertEventHubNetworkRules 'Microsoft.EventHub/namespaces/networkRuleSets@2024-01-01' = {
  parent: alertEventHubNamespace
  name: 'default'
  properties: {
    publicNetworkAccess: 'Enabled'
    defaultAction: 'Allow'
  }
}

resource alertEventHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  parent: alertEventHubNamespace
  name: 'incident-alerts'
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
  }
}

resource eventHubReceiver 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(alertEventHub.id, principalId, 'Azure Event Hubs Data Receiver')
  scope: alertEventHub
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a638d3c7-ab3a-418d-83e6-5f17a39d4fde')
  }
}

resource incidentActionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'aw-incident-response'
  location: 'global'
  properties: {
    groupShortName: 'awincident'
    enabled: true
    eventHubReceivers: [
      {
        name: 'remediation-handler'
        subscriptionId: subscription().subscriptionId
        tenantId: tenant().tenantId
        eventHubNameSpace: alertEventHubNamespace.name
        eventHubName: alertEventHub.name
        useCommonAlertSchema: true
      }
    ]
  }
}

resource syntheticFailureAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'aw-synthetic-pricing-failure'
  location: location
  kind: 'LogAlert'
  properties: {
    displayName: 'Adventure Works synthetic pricing failure'
    description: 'Detects failed synthetic pricing spans and routes common-schema evidence for remediation.'
    enabled: true
    severity: 2
    evaluationFrequency: 'PT1M'
    windowSize: 'PT15M'
    scopes: [workspace.id]
    targetResourceTypes: ['Microsoft.OperationalInsights/workspaces']
    skipQueryValidation: true
    autoMitigate: true
    criteria: {
      allOf: [
        {
          query: '''
let EmptyDependencies = datatable(TimeGenerated:datetime, Name:string, Properties:dynamic, Success:bool)
  [datetime(1900-01-01), "", dynamic({}), true]
  | where false;
union isfuzzy=true AppDependencies, EmptyDependencies
| where TimeGenerated > ago(15m)
| where Name == "pricing_agent.calculate_total"
| where tostring(Properties["tool.mock_id"]) == "catalog-response-syn-01"
| where Success == false
'''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [incidentActionGroup.id]
    }
  }
}

resource blobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, principalId, 'Storage Blob Data Contributor')
  scope: storage
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

resource logReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(workspace.id, principalId, 'Log Analytics Reader')
  scope: workspace
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '73c42c96-874c-492b-b04d-ab87d138a893')
  }
}

resource telemetryPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, principalId, 'Monitoring Metrics Publisher')
  scope: insights
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
  }
}

output APPLICATIONINSIGHTS_CONNECTION_STRING string = insights.properties.ConnectionString
output LOG_ANALYTICS_WORKSPACE_ID string = workspace.properties.customerId
output BLOB_ACCOUNT_URL string = storage.properties.primaryEndpoints.blob
output SNAPSHOT_CONTAINER string = snapshots.name
output REPORT_CONTAINER string = reports.name
output ALERT_EVENTHUB_NAMESPACE string = '${alertEventHubNamespace.name}.servicebus.windows.net'
output ALERT_EVENTHUB_NAME string = alertEventHub.name
output ALERT_RULE_ID string = syntheticFailureAlert.id
output ACTION_GROUP_ID string = incidentActionGroup.id
