@description('Workload / domain pack name')
param workload string

@description('Environment')
param env string

@description('Azure region')
param location string

@description('Tags applied to every resource')
param tags object

@description('Blob containers to create, e.g. docs')
param containerNames array = [ 'docs' ]

@description('Public network access. Effective only for allowedIpRanges because defaultAction is Deny.')
@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Disabled'

@description('Public IPs allowed to reach the data plane (dev only)')
param allowedIpRanges array = []

@description('AVM-style role assignments: [{ principalId, principalType, roleDefinitionId }]')
param roleAssignments array = []

var storageName = take('st${workload}${env}${uniqueString(resourceGroup().id)}', 24)

resource st 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      ipRules: [for ip in allowedIpRanges: {
        value: ip
        action: 'Allow'
      }]
      virtualNetworkRules: []
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: st
  name: 'default'
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for c in containerNames: {
  parent: blobService
  name: c
  properties: {
    publicAccess: 'None'
  }
}]

resource stRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for r in roleAssignments: {
  name: guid(st.id, r.principalId, r.roleDefinitionId)
  scope: st
  properties: {
    principalId: r.principalId
    principalType: r.principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', r.roleDefinitionId)
  }
}]

output id string = st.id
output name string = st.name
output blobEndpoint string = st.properties.primaryEndpoints.blob
