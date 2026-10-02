param environmentName string
param location string
param suffix string
param bootstrapImage string
param mcpEntraClientId string
param mcpEntraTenantId string

var appName = 'mcp-${take(environmentName, 16)}-${take(suffix, 6)}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${take(environmentName, 18)}-${take(suffix, 6)}'
  location: location
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
  sku: {
    name: 'PerGB2018'
  }
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${take(environmentName, 18)}-${take(suffix, 6)}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'mcp'
          image: bootstrapImage
          env: [
            {
              name: 'PORT'
              value: '8000'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 2
      }
    }
  }
}

resource authConfig 'Microsoft.App/containerApps/authConfigs@2024-03-01' = {
  parent: containerApp
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      unauthenticatedClientAction: 'Return401'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: mcpEntraClientId
          openIdIssuer: '${environment().authentication.loginEndpoint}${mcpEntraTenantId}/v2.0'
        }
        validation: {
          allowedAudiences: [
            'api://${mcpEntraClientId}'
          ]
        }
      }
    }
  }
}

output containerAppName string = containerApp.name
output mcpServerUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}/mcp'
output mcpTokenScope string = 'api://${mcpEntraClientId}/.default'
output managedIdentityPrincipalId string = containerApp.identity.principalId
