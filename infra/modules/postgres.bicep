// PostgreSQL Flexible Server con pgvector.
param environmentName string
param location string
param tags object
param subnetId string

@secure()
@description('Password del usuario administrador. Inyectar desde Key Vault o pipeline.')
param adminPassword string = newGuid() // override en parámetros

var serverName = 'pg-sqa-kb-${environmentName}'

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: environmentName == 'prod' ? 'Standard_D2ds_v5' : 'Standard_B2s'
    tier: environmentName == 'prod' ? 'GeneralPurpose' : 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: 'sqaadmin'
    administratorLoginPassword: adminPassword
    storage: { storageSizeGB: 32, autoGrow: 'Enabled' }
    backup: {
      backupRetentionDays: environmentName == 'prod' ? 14 : 7
      geoRedundantBackup: environmentName == 'prod' ? 'Enabled' : 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: subnetId
    }
    highAvailability: {
      mode: environmentName == 'prod' ? 'ZoneRedundant' : 'Disabled'
    }
  }
}

// Habilita pgvector (debe ser allowed en server params)
resource extensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgres
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR,UUID-OSSP,PG_TRGM,BTREE_GIN'
    source: 'user-override'
  }
}

output postgresFqdn string = postgres.properties.fullyQualifiedDomainName
output postgresName string = postgres.name
