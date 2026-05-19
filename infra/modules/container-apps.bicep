// Container Apps environment + frontend + backend.
// La imagen real se inyecta en deploy (placeholder hasta tener ACR).
param environmentName string
param location string
param tags object
param keyVaultName string
param appInsightsConnectionString string
param logAnalyticsWorkspaceId string

@description('Imagen Docker del frontend (registry/repo:tag)')
param frontendImage string = 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'

@description('Imagen Docker del backend')
param backendImage string = 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: last(split(logAnalyticsWorkspaceId, '/'))
}

resource acaEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'aca-env-sqa-kb-${environmentName}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'aca-sqa-kb-backend-${environmentName}'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*'] // ajustar en parámetros prod
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'SQA_KB_APP_ENV', value: environmentName }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            // Secrets reales se inyectan vía Key Vault references en Fase 11
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health/live', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health/ready', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: environmentName == 'prod' ? 2 : 0
        maxReplicas: environmentName == 'prod' ? 10 : 3
      }
    }
  }
}

resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'aca-sqa-kb-frontend-${environmentName}'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'NEXT_PUBLIC_API_URL', value: 'https://${backend.properties.configuration.ingress.fqdn}/api/v1' }
          ]
        }
      ]
      scale: {
        minReplicas: environmentName == 'prod' ? 2 : 0
        maxReplicas: environmentName == 'prod' ? 5 : 2
      }
    }
  }
}

output backendFqdn string = 'https://${backend.properties.configuration.ingress.fqdn}'
output frontendFqdn string = 'https://${frontend.properties.configuration.ingress.fqdn}'
