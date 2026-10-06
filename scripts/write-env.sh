#!/usr/bin/env bash
set -euo pipefail
DEP="${1:-foundation}"
PACK="${2:-uae-labour-law}"
q() { az deployment sub show --name "$DEP" --query "properties.outputs.$1.value" -o tsv; }
AI_NAME=$(q aiName)
SEARCH=$(q searchEndpoint)
STORAGE=$(q storageName)
cat > .env <<EOF
AZURE_OPENAI_ENDPOINT=https://${AI_NAME}.openai.azure.com
AZURE_SEARCH_ENDPOINT=${SEARCH}
AZURE_STORAGE_ACCOUNT=${STORAGE}
CHAT_DEPLOYMENT=chat-mini
EMBED_DEPLOYMENT=embed-small
EMBED_DIMENSIONS=1536
SEARCH_INDEX=kb-${PACK}
DOCS_CONTAINER=docs
PACK=${PACK}
EOF
echo ".env written from deployment '$DEP'"
cat .env
