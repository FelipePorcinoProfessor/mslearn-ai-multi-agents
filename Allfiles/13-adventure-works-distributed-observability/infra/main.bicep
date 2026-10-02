targetScope = 'resourceGroup'

@description('Azure region for the monitoring resources.')
param location string = resourceGroup().location

@description('Short suffix used to make globally unique names.')
param resourceSuffix string = uniqueString(subscription().id, resourceGroup().id)

@description('Email receiver for lab anomaly notifications.')
param alertEmail string

var workspaceName = 'log-aw-otel-${resourceSuffix}'
var insightsName = 'appi-aw-otel-${resourceSuffix}'
var identityName = 'id-aw-telemetry-${resourceSuffix}'
var monitoringMetricsPublisherRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
var alertQuery = loadTextContent('../kql/anomaly-alert.kql')

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: insightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    DisableLocalAuth: true
    WorkspaceResourceId: workspace.id
  }
}

resource telemetryIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource telemetryPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, telemetryIdentity.id, monitoringMetricsPublisherRoleId)
  scope: insights
  properties: {
    principalId: telemetryIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: monitoringMetricsPublisherRoleId
  }
}

resource anomalyActionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-aw-agent-anomaly-${resourceSuffix}'
  location: 'global'
  properties: {
    groupShortName: 'aw-agent'
    enabled: true
    emailReceivers: [
      {
        name: 'lab-operator'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

resource anomalyAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'alert-aw-agent-policy-anomaly-${resourceSuffix}'
  location: location
  properties: {
    displayName: 'Adventure Works agent policy anomaly'
    description: 'Latency, error-rate, or token anomaly emitted by the lab agent chain.'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [
      workspace.id
    ]
    targetResourceTypes: [
      'Microsoft.OperationalInsights/workspaces'
    ]
    skipQueryValidation: true
    criteria: {
      allOf: [
        {
          query: alertQuery
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
    resolveConfiguration: {
      autoResolved: true
      timeToResolve: 'PT5M'
    }
    actions: {
      actionGroups: [
        anomalyActionGroup.id
      ]
    }
  }
}

output APPLICATIONINSIGHTS_CONNECTION_STRING string = insights.properties.ConnectionString
output APPLICATIONINSIGHTS_RESOURCE_ID string = insights.id
output LOG_ANALYTICS_WORKSPACE_ID string = workspace.properties.customerId
output TELEMETRY_IDENTITY_CLIENT_ID string = telemetryIdentity.properties.clientId
output TELEMETRY_IDENTITY_PRINCIPAL_ID string = telemetryIdentity.properties.principalId
output ANOMALY_ALERT_RULE_ID string = anomalyAlert.id
output ANOMALY_ACTION_GROUP_ID string = anomalyActionGroup.id
