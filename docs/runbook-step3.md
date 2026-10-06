# Mizan Runbook

## Step 3: VM lab
| Goal | Command |
|---|---|
| Check a size is allowed | `az vm list-skus --location uaenorth --size <size> --all -o table` |
| Check vCPU quota | `az vm list-usage --location uaenorth -o table \| grep -i "Total Regional vCPUs"` |
| Get my public IP | `MYIP=$(curl -s https://api.ipify.org)` |
| Create VM (5 questions: where, what, size, who, network) | `az vm create -g <rg> -n <name> --image Ubuntu2404 --size <size> --admin-username azureuser --generate-ssh-keys --storage-sku Premium_LRS --os-disk-size-gb 64 --nsg-rule SSH --tags ...` |
| Lock SSH to my IP | `az network nsg rule update -g <rg> --nsg-name <vm>NSG -n default-allow-ssh --source-address-prefixes $MYIP/32` |
| Auto-shutdown (UTC!) | `az vm auto-shutdown -g <rg> -n <vm> --time 1900` |
| SSH in | `ssh azureuser@<ip>` |
| Install via extension | `az vm extension set -g <rg> --vm-name <vm> --publisher Microsoft.Azure.Extensions -n CustomScript --settings '{"commandToExecute":"..."}'` |
| Stop billing (not just stop!) | `az vm deallocate -g <rg> -n <vm>` |
| Delete all lab resources | `az group delete -n rg-mizan-temp-uaen --yes` |
| Rebuild RGs from code | `az deployment sub create --name mizan-foundation --location uaenorth --parameters infra/params/mizan.dev.bicepparam` |