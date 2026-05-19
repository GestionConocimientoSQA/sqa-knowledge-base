// VNet + subnets para Container Apps y PostgreSQL Flexible Server.
param environmentName string
param location string
param tags object

var vnetName = 'vnet-sqa-kb-${environmentName}'

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.20.0.0/16'] }
    subnets: [
      {
        name: 'snet-aca'
        properties: {
          addressPrefix: '10.20.0.0/23'
          delegations: [
            {
              name: 'aca-delegation'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'snet-db'
        properties: {
          addressPrefix: '10.20.2.0/24'
          delegations: [
            {
              name: 'pg-delegation'
              properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' }
            }
          ]
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output acaSubnetId string = vnet.properties.subnets[0].id
output dbSubnetId string = vnet.properties.subnets[1].id
