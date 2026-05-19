// ============================================================
// SQA Knowledge Base — Bicep main (subscription scope)
// ============================================================
// Esqueleto Fase 0. Los módulos se completan en Fase 11.
// Despliega un resource group y delega a módulos por capa.
// ============================================================

targetScope = 'subscription'

@description('Entorno: dev | staging | prod')
@allowed(['dev', 'staging', 'prod'])
param environmentName string

@description('Región principal del despliegue.')
param location string = 'eastus2'

@description('Tags aplicados a todos los recursos.')
param tags object = {
  project: 'sqa-kb'
  environment: environmentName
  managedBy: 'bicep'
  owner: 'sqa-ti'
}

var rgName = 'rg-sqa-kb-${environmentName}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

// --- Networking (capa base) ---
module networking 'modules/networking.bicep' = {
  scope: rg
  name: 'networking'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

// --- Monitoring (transversal) ---
module monitoring 'modules/monitoring.bicep' = {
  scope: rg
  name: 'monitoring'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

// --- Key Vault (secrets) ---
module keyVault 'modules/key-vault.bicep' = {
  scope: rg
  name: 'keyVault'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

// --- Storage (Blob para documentos) ---
module storage 'modules/storage.bicep' = {
  scope: rg
  name: 'storage'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

// --- PostgreSQL Flexible Server (DB + vectorial) ---
module postgres 'modules/postgres.bicep' = {
  scope: rg
  name: 'postgres'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    subnetId: networking.outputs.dbSubnetId
  }
}

// --- Container Apps (frontend + backend) ---
module containerApps 'modules/container-apps.bicep' = {
  scope: rg
  name: 'containerApps'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    keyVaultName: keyVault.outputs.keyVaultName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
  }
}

output resourceGroupName string = rg.name
output frontendUrl string = containerApps.outputs.frontendFqdn
output backendUrl string = containerApps.outputs.backendFqdn
