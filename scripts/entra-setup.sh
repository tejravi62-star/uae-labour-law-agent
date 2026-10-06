#!/usr/bin/env bash
set -euo pipefail

WORKLOAD="${1:-mizan}"
ENV="${2:-dev}"
ME=$(az ad signed-in-user show --query id -o tsv)

for ROLE in admins users; do
  NAME="grp-${WORKLOAD}-${ENV}-${ROLE}"
  ID=$(az ad group list --display-name "$NAME" --query "[0].id" -o tsv)
  if [ -z "$ID" ]; then
    ID=$(az ad group create --display-name "$NAME" --mail-nickname "$NAME" --description "${WORKLOAD}-${ENV} ${ROLE} (framework-managed)" --query id -o tsv)
    echo "Created: $NAME"
  else
    echo "Exists:  $NAME"
  fi
  az ad group owner add --group "$ID" --owner-object-id "$ME" 2>/dev/null || true
  az ad group member add --group "$ID" --member-id "$ME" 2>/dev/null || true
  echo "  ${ROLE} group id = ${ID}"
done
