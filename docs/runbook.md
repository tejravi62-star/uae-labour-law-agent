
## Step 4: Network & Private Endpoints
| Goal | Command |
|---|---|
| Set env vars (every new terminal) | `export MIZAN_SSH_PUBKEY="$(cat ~/.ssh/id_rsa.pub)"` and `export MIZAN_DEV_IP=$(curl -s https://api.ipify.org)` |
| Preview all infra | `az deployment sub what-if --name mizan-foundation --location uaenorth --parameters infra/params/mizan.dev.bicepparam` |
| Deploy all infra | `az deployment sub create --name mizan-foundation --location uaenorth --parameters infra/params/mizan.dev.bicepparam` |
| Check subnets | `az network vnet subnet list -g rg-mizan-dev-uaen --vnet-name vnet-mizan-dev-uaen -o table` |
| Private endpoint IPs | `az network private-endpoint show -g rg-mizan-dev-uaen -n pe-mizan-aif-dev-uaen --query "customDnsConfigs[].{FQDN:fqdn, IP:ipAddresses[0]}" -o table` |
| Run command inside jumpbox | `az vm run-command invoke -g rg-mizan-temp-uaen -n vm-mizan-jump-dev-uaen --command-id RunShellScript --scripts "<cmd>" --query "value[0].message" -o tsv` |
| Start / stop jumpbox | `az vm start ...` / `az vm deallocate -g rg-mizan-temp-uaen -n vm-mizan-jump-dev-uaen` |
| Test Foundry with token | `TOKEN=$(az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv)` then `curl -H "Authorization: Bearer $TOKEN" https://aif-mizan-dev-uaen.openai.azure.com/openai/v1/models` |
| My IP changed | Re-export MIZAN_DEV_IP, then redeploy |
| 401 vs 403 | 401 = identity refused; 403 with a valid token = network refused |
