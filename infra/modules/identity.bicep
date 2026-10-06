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

resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${workload}-app-${env}-${regionCode}'
  location: location
  tags: tags
}

output id string = uami.id
output name string = uami.name
output principalId string = uami.properties.principalId
output clientId string = uami.properties.clientId
