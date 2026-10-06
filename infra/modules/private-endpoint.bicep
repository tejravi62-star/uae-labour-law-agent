@description('Private endpoint name')
param name string

@description('Azure region')
param location string

@description('Subnet the endpoint NIC is placed in')
param subnetId string

@description('Resource ID of the service being made private')
param targetResourceId string

@description('Sub-resource to connect, e.g. account (Foundry), blob (Storage), searchService')
param groupId string

@description('Private DNS zone IDs to register the endpoint in')
param dnsZoneIds array

@description('Tags applied to every resource')
param tags object

resource pe 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    customNetworkInterfaceName: 'nic-${name}'
    privateLinkServiceConnections: [
      {
        name: name
        properties: {
          privateLinkServiceId: targetResourceId
          groupIds: [ groupId ]
        }
      }
    ]
  }
}

resource dnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: pe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [for (id, i) in dnsZoneIds: {
      name: 'zone-${i}'
      properties: {
        privateDnsZoneId: id
      }
    }]
  }
}

output peId string = pe.id
output peName string = pe.name
