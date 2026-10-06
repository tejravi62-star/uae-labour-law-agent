#!/usr/bin/env bash
set -euo pipefail
for p in Microsoft.Web Microsoft.Storage Microsoft.Network Microsoft.KeyVault \
         Microsoft.Search Microsoft.CognitiveServices Microsoft.ManagedIdentity \
         Microsoft.Insights Microsoft.OperationalInsights Microsoft.Compute Microsoft.DevTestLab; do
  az provider register --namespace "$p" --output none
  echo "registered: $p"
done
echo "Providers registering in background (2-5 min). Check: az provider list --query \"[?registrationState=='Registered'].namespace\" -o table"
