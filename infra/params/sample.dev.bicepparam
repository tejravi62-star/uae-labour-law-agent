using '../main.bicep'

// --- Workload identity (change these) ---
param workload = 'mizan'                // short name, 2-10 chars, used in all resource names
param env = 'dev'                       // dev | test | prod
param location = 'uaenorth'             // Azure region with your model quota
param regionCode = 'uaen'               // short region code for names
param owner = 'your-name'               // owner tag
param vnetAddressPrefix = '10.20.0.0/22'  // must not overlap your other networks

// --- Models (must be available in your region) ---
param modelDeployments = [
  {
    name: 'chat-mini'
    model: 'gpt-5.4-mini'
    version: '2026-03-17'
    sku: 'GlobalStandard'
    capacity: 50
  }
  {
    name: 'embed-small'
    model: 'text-embedding-3-small'
    version: '1'
    sku: 'GlobalStandard'
    capacity: 30
  }
]

// --- Access (values come from environment variables, never committed) ---
param aiPublicNetworkAccess = 'Enabled'   // 'Enabled' = your IP only (dev); 'Disabled' = private only (prod)
param devAllowedIp = readEnvironmentVariable('MIZAN_DEV_IP', '')
param deployJumpbox = false
param jumpboxSshPublicKey = readEnvironmentVariable('MIZAN_SSH_PUBKEY', '')

param aiUsers = [
  {
    principalId: readEnvironmentVariable('MIZAN_USER_OBJECT_ID', '')
    principalType: 'User'
  }
]
