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

@description('Model deployments for this workload, supplied by the domain pack')
param modelDeployments array

@description('Public network access. Enabled only matters if allowedIpRanges is non-empty, because defaultAction is always Deny.')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

@description('Public IPs/CIDRs allowed to reach the data plane (dev only). Empty = private endpoint only.')
param allowedIpRanges array = []

var aifName = 'aif-${workload}-${env}-${regionCode}'

resource aif 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aifName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: aifName
    disableLocalAuth: true
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      defaultAction: 'Deny'
      ipRules: [for ip in allowedIpRanges: {
        value: ip
      }]
      virtualNetworkRules: []
    }
  }
}

@batchSize(1)
resource deployments 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [for d in modelDeployments: {
  parent: aif
  name: d.name
  sku: {
    name: d.sku
    capacity: d.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: d.model
      version: d.version
    }
    versionUpgradeOption: 'NoAutoUpgrade'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}]

output aifId string = aif.id
output aifName string = aif.name
output aifEndpoint string = aif.properties.endpoint
output aifPrincipalId string = aif.identity.principalId

@description('AVM-style role assignments on this Foundry resource: [{ principalId, principalType, roleDefinitionId }]')
param roleAssignments array = []

resource aifRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for r in roleAssignments: {
  name: guid(aif.id, r.principalId, r.roleDefinitionId)
  scope: aif
  properties: {
    principalId: r.principalId
    principalType: r.principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', r.roleDefinitionId)
  }
}]
