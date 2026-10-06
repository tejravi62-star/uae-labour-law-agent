@description('Lock name')
param name string

@description('Why the lock exists')
param notes string = 'Core platform resources. Change or remove via IaC only.'

resource lock 'Microsoft.Authorization/locks@2020-05-01' = {
  name: name
  properties: {
    level: 'CanNotDelete'
    notes: notes
  }
}
