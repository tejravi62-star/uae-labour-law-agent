@description('Workload / domain pack name')
param workload string

@description('Environment')
param env string

@description('Azure region')
param location string

@description('Short region code for names')
param regionCode string

@description('Tags applied to every resource')
param tags object

@description('Search tier')
@allowed([ 'basic', 'standard' ])
param sku string = 'basic'

@description('Public network access. Effective only for allowedIpRanges.')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

@description('Public IPs allowed to reach the data plane (dev only)')
param allowedIpRanges array = []

@description('AVM-style role assignments: [{ principalId, principalType, roleDefinitionId }]')
param roleAssignments array = []

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: 'srch-${workload}-${env}-${regionCode}'
  location: location
  tags: tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    disableLocalAuth: true
    publicNetworkAccess: publicNetworkAccess == 'Enabled' ? 'enabled' : 'disabled'
    networkRuleSet: {
      ipRules: [for ip in allowedIpRanges: {
        value: ip
      }]
    }
    semanticSearch: 'free'
  }
}

resource searchRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for r in roleAssignments: {
  name: guid(search.id, r.principalId, r.roleDefinitionId)
  scope: search
  properties: {
    principalId: r.principalId
    principalType: r.principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', r.roleDefinitionId)
  }
}]

output id string = search.id
output name string = search.name
output endpoint string = 'https://${search.name}.search.windows.net'
output principalId string = search.identity.principalId
