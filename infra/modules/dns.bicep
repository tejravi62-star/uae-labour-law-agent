@description('Private DNS zone names to create, e.g. privatelink.openai.azure.com')
param zoneNames array

@description('Resource ID of the VNet to link the zones to')
param vnetId string

@description('Tags applied to every resource')
param tags object

resource zones 'Microsoft.Network/privateDnsZones@2024-06-01' = [for z in zoneNames: {
  name: z
  location: 'global'
  tags: tags
}]

resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (z, i) in zoneNames: {
  parent: zones[i]
  name: 'link-${last(split(vnetId, '/'))}'
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnetId
    }
  }
}]

output zoneIds array = [for (z, i) in zoneNames: zones[i].id]
