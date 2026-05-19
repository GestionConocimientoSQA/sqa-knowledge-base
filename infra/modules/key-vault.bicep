// Key Vault para secrets (Anthropic key, DB connection, etc.).
param environmentName string
param location string
param tags object

var kvName = 'kv-sqa-kb-${environmentName}-${uniqueString(resourceGroup().id)}'

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: kvName
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 30
    enablePurgeProtection: environmentName == 'prod' ? true : null
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

output keyVaultName string = kv.name
output keyVaultUri string = kv.properties.vaultUri
