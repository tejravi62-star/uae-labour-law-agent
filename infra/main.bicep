targetScope = 'subscription'

@description('Short name of the workload / domain pack, e.g. mizan, hrbot')
@minLength(2)
@maxLength(10)
param workload string

@description('Environment')
@allowed([ 'dev', 'test', 'prod' ])
param env string = 'dev'

@description('Azure region')
param location string = 'uaenorth'

@description('Short region code used in names')
param regionCode string = 'uaen'

@description('Owner tag value')
param owner string

@description('VNet address space for this workload. Must be a /22 and must not overlap other networks.')
param vnetAddressPrefix string

@description('Model deployments for this workload (from the domain pack)')
param modelDeployments array

@description('Foundry public network access. With no allowed IPs this is effectively private-only.')
@allowed([ 'Enabled', 'Disabled' ])
param aiPublicNetworkAccess string = 'Disabled'

@description('Developer public IP allowed to reach Foundry (dev only, read from environment). Empty = none.')
param devAllowedIp string = ''

@description('Deploy the admin jumpbox into the temp RG')
param deployJumpbox bool = false

@description('SSH public key for the jumpbox (read from environment, never committed)')
param jumpboxSshPublicKey string = ''

var baseTags = {
  project: workload
  env: env
  owner: owner
}
var coreTags = union(baseTags, { costmode: 'core' })
var tempTags = union(baseTags, { costmode: 'temp' })

var aiDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
]

var aiAllowedIps = empty(devAllowedIp) ? [] : [ devAllowedIp ]

resource rgCore 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${workload}-${env}-${regionCode}'
  location: location
  tags: coreTags
}

resource rgTemp 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${workload}-temp-${regionCode}'
  location: location
  tags: tempTags
}

module network 'modules/network.bicep' = {
  name: 'network-${workload}-${env}'
  scope: rgCore
  params: {
    workload: workload
    env: env
    location: location
    regionCode: regionCode
    addressPrefix: vnetAddressPrefix
    tags: coreTags
  }
}

module ai 'modules/ai.bicep' = {
  name: 'ai-${workload}-${env}'
  scope: rgCore
  params: {
    workload: workload
    env: env
    location: location
    regionCode: regionCode
    tags: coreTags
    modelDeployments: modelDeployments
    publicNetworkAccess: aiPublicNetworkAccess
    allowedIpRanges: aiAllowedIps
    roleAssignments: aiRoleAssignments
  }
}

module dnsAi 'modules/dns.bicep' = {
  name: 'dns-ai-${workload}-${env}'
  scope: rgCore
  params: {
    zoneNames: aiDnsZones
    vnetId: network.outputs.vnetId
    tags: coreTags
  }
}

module peAi 'modules/private-endpoint.bicep' = {
  name: 'pe-ai-${workload}-${env}'
  scope: rgCore
  params: {
    name: 'pe-${workload}-aif-${env}-${regionCode}'
    location: location
    subnetId: network.outputs.subnetIds.pe
    targetResourceId: ai.outputs.aifId
    groupId: 'account'
    dnsZoneIds: dnsAi.outputs.zoneIds
    tags: coreTags
  }
}

module jumpbox 'modules/jumpbox.bicep' = if (deployJumpbox) {
  name: 'jumpbox-${workload}-${env}'
  scope: rgTemp
  params: {
    workload: workload
    env: env
    location: location
    regionCode: regionCode
    tags: tempTags
    subnetId: network.outputs.subnetIds.jump
    sshPublicKey: jumpboxSshPublicKey
  }
}

output coreResourceGroup string = rgCore.name
output tempResourceGroup string = rgTemp.name
output vnetName string = network.outputs.vnetName
output subnetIds object = network.outputs.subnetIds
output aiName string = ai.outputs.aifName
output aiEndpoint string = ai.outputs.aifEndpoint
output aiPrivateEndpoint string = peAi.outputs.peName

module coreLock 'modules/lock.bicep' = {
  name: 'lock-${workload}-${env}'
  scope: rgCore
  params: {
    name: 'lock-${workload}-core'
  }
}

@description('Principals who can call Foundry models: [{ principalId, principalType }]. Users today, groups when the identity team provides them.')
param aiUsers array = []

var roleIdOpenAiUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

var aiRoleAssignments = map(aiAllPrincipals, p => {
  principalId: p.principalId
  principalType: p.principalType
  roleDefinitionId: roleIdOpenAiUser
})

module appIdentity 'modules/identity.bicep' = {
  name: 'identity-${workload}-${env}'
  scope: rgCore
  params: {
    workload: workload
    env: env
    location: location
    regionCode: regionCode
    tags: coreTags
  }
}

var aiAllPrincipals = concat(aiUsers, [
  {
    principalId: appIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
])

output appIdentityClientId string = appIdentity.outputs.clientId

var roleIdBlobContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var roleIdBlobReader = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'

var storageUserAssignments = map(aiUsers, p => {
  principalId: p.principalId
  principalType: p.principalType
  roleDefinitionId: roleIdBlobContributor
})

var storageAppAssignment = [
  {
    principalId: appIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: roleIdBlobReader
  }
]

module storage 'modules/storage.bicep' = {
  name: 'storage-${workload}-${env}'
  scope: rgCore
  params: {
    workload: workload
    env: env
    location: location
    tags: coreTags
    containerNames: [ 'docs' ]
    publicNetworkAccess: aiPublicNetworkAccess
    allowedIpRanges: aiAllowedIps
    roleAssignments: concat(storageUserAssignments, storageAppAssignment)
  }
}

module dnsBlob 'modules/dns.bicep' = {
  name: 'dns-blob-${workload}-${env}'
  scope: rgCore
  params: {
    zoneNames: [ 'privatelink.blob.${environment().suffixes.storage}' ]
    vnetId: network.outputs.vnetId
    tags: coreTags
  }
}

module peBlob 'modules/private-endpoint.bicep' = {
  name: 'pe-blob-${workload}-${env}'
  scope: rgCore
  params: {
    name: 'pe-${workload}-st-blob-${env}-${regionCode}'
    location: location
    subnetId: network.outputs.subnetIds.pe
    targetResourceId: storage.outputs.id
    groupId: 'blob'
    dnsZoneIds: dnsBlob.outputs.zoneIds
    tags: coreTags
  }
}

output storageName string = storage.outputs.name
output blobEndpoint string = storage.outputs.blobEndpoint

var roleIdSearchServiceContributor = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var roleIdSearchIndexDataContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var roleIdSearchIndexDataReader = '1407120a-92aa-4202-b7e9-c0e197c71c8f'

var searchUserServiceAssignments = map(aiUsers, p => {
  principalId: p.principalId
  principalType: p.principalType
  roleDefinitionId: roleIdSearchServiceContributor
})

var searchUserDataAssignments = map(aiUsers, p => {
  principalId: p.principalId
  principalType: p.principalType
  roleDefinitionId: roleIdSearchIndexDataContributor
})

var searchAppAssignment = [
  {
    principalId: appIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: roleIdSearchIndexDataReader
  }
]

module search 'modules/search.bicep' = {
  name: 'search-${workload}-${env}'
  scope: rgCore
  params: {
    workload: workload
    env: env
    location: location
    regionCode: regionCode
    tags: coreTags
    publicNetworkAccess: aiPublicNetworkAccess
    allowedIpRanges: aiAllowedIps
    roleAssignments: concat(searchUserServiceAssignments, searchUserDataAssignments, searchAppAssignment)
  }
}

module dnsSearch 'modules/dns.bicep' = {
  name: 'dns-search-${workload}-${env}'
  scope: rgCore
  params: {
    zoneNames: [ 'privatelink.search.windows.net' ]
    vnetId: network.outputs.vnetId
    tags: coreTags
  }
}

module peSearch 'modules/private-endpoint.bicep' = {
  name: 'pe-search-${workload}-${env}'
  scope: rgCore
  params: {
    name: 'pe-${workload}-srch-${env}-${regionCode}'
    location: location
    subnetId: network.outputs.subnetIds.pe
    targetResourceId: search.outputs.id
    groupId: 'searchService'
    dnsZoneIds: dnsSearch.outputs.zoneIds
    tags: coreTags
  }
}

output searchName string = search.outputs.name
output searchEndpoint string = search.outputs.endpoint
