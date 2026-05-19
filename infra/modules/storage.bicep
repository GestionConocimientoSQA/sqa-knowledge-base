// Blob Storage para documentos físicos.
param environmentName string
param location string
param tags object

var storageName = 'stsqakb${environmentName}${uniqueString(resourceGroup().id)}'

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: take(storageName, 24)
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: { enabled: true, days: 30 }
    isVersioningEnabled: true
  }
}

var containerNames = [
  'base-conocimiento'
  'inbox-pendientes'
  'borradores'
]

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = [for name in containerNames: {
  parent: blobService
  name: name
  properties: { publicAccess: 'None' }
}]

output storageAccountName string = storage.name
output blobEndpoint string = storage.properties.primaryEndpoints.blob
