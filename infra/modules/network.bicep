@description('Workload / domain pack name')
param workload string

@description('Environment')
param env string

@description('Azure region')
param location string

@description('Short region code for names')
param regionCode string

@description('VNet address space. Must be a /22, e.g. 10.20.0.0/22')
param addressPrefix string

@description('Tags applied to every resource')
param tags object

var vnetName = 'vnet-${workload}-${env}-${regionCode}'

var snetPe      = cidrSubnet(addressPrefix, 26, 0)
var snetApp     = cidrSubnet(addressPrefix, 26, 1)
var snetFunc    = cidrSubnet(addressPrefix, 26, 2)
var snetJump    = cidrSubnet(addressPrefix, 27, 6)
var snetBastion = cidrSubnet(addressPrefix, 26, 4)
var snetAks     = cidrSubnet(addressPrefix, 24, 2)

resource nsgPe 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${workload}-pe-${env}-${regionCode}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'Allow-Services-From-VNet'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRanges: [ '443', '1433', '10000' ]
        }
      }
      {
        name: 'Deny-All-Other-Inbound'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

resource nsgJump 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${workload}-jump-${env}-${regionCode}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'Allow-SSH-From-Bastion'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: snetBastion
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '22'
        }
      }
      {
        name: 'Deny-All-Other-Inbound'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [ addressPrefix ]
    }
        privateEndpointVNetPolicies: 'Disabled'
    subnets: [
      {
        name: 'snet-pe'
        properties: {
          addressPrefix: snetPe
          networkSecurityGroup: { id: nsgPe.id }
          privateEndpointNetworkPolicies: 'Enabled'
          defaultOutboundAccess: false
        }
      }
      {
        name: 'snet-app'
        properties: {
          addressPrefix: snetApp
          delegations: [
            {
              name: 'appservice'
              properties: { serviceName: 'Microsoft.Web/serverFarms' }
            }
          ]
          defaultOutboundAccess: false
        }
      }
      {
        name: 'snet-func'
        properties: {
          addressPrefix: snetFunc
          delegations: [
            {
              name: 'flexfunctions'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
          defaultOutboundAccess: false
        }
      }
      {
        name: 'snet-jump'
        properties: {
          addressPrefix: snetJump
          networkSecurityGroup: { id: nsgJump.id }
          defaultOutboundAccess: true
        }
      }
      {
        name: 'AzureBastionSubnet'
        properties: {
          addressPrefix: snetBastion
        }
      }
      {
        name: 'snet-aks'
        properties: {
          addressPrefix: snetAks
          defaultOutboundAccess: false
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output subnetIds object = {
  pe: '${vnet.id}/subnets/snet-pe'
  app: '${vnet.id}/subnets/snet-app'
  func: '${vnet.id}/subnets/snet-func'
  jump: '${vnet.id}/subnets/snet-jump'
  bastion: '${vnet.id}/subnets/AzureBastionSubnet'
  aks: '${vnet.id}/subnets/snet-aks'
}
