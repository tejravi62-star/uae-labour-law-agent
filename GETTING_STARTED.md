# Getting Started

Deploy the full platform into **your own Azure subscription**. Everything runs inside your tenant: private endpoints, no keys, your data stays with you.

**Time:** ~45 minutes · **Cost:** a few dollars per day while running (Search Basic is the main cost). Delete the resource groups when you're done.

---

## 1. Prerequisites

| Need | Check |
|---|---|
| Azure subscription with **Owner** role | `az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) -o table` |
| Azure CLI + Bicep | `az version` · `az bicep install` |
| Python 3.12+ | `python3 --version` |
| Model quota in your region (chat + embedding) | `az cognitiveservices usage list --location <region> -o table` |

## 2. Get the code

```bash
git clone https://github.com/<owner>/uae-labour-law-agent.git
cd uae-labour-law-agent
```

## 3. Sign in and prepare the subscription

```bash
az login
az account set --subscription <your-subscription-id>
./scripts/bootstrap.sh
```

## 4. Configure

```bash
cp infra/params/sample.dev.bicepparam infra/params/my.dev.bicepparam
```
Edit `my.dev.bicepparam`: `workload`, `location`, `vnetAddressPrefix`, and model versions available in your region.

Set the values that must never be committed:
```bash
export MIZAN_DEV_IP=$(curl -s https://api.ipify.org)
export MIZAN_USER_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
export MIZAN_SSH_PUBKEY="$(cat ~/.ssh/id_rsa.pub 2>/dev/null || echo '')"
```

## 5. Deploy the platform

```bash
az deployment sub what-if --name foundation --location <region> --parameters infra/params/my.dev.bicepparam
az deployment sub create  --name foundation --location <region> --parameters infra/params/my.dev.bicepparam
```
Creates: VNet + subnets + NSGs, Foundry with chat and embedding models, AI Search, Storage, private endpoints + private DNS, managed identity, RBAC, and a delete lock. Takes ~10–15 minutes.

## 6. Python environment

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r src/requirements.lock
./scripts/write-env.sh foundation uae-labour-law
```

## 7. Load the knowledge pack

```bash
STORAGE=$(grep AZURE_STORAGE_ACCOUNT .env | cut -d= -f2)
az storage blob upload-batch --account-name $STORAGE --destination docs \
  --destination-path uae-labour-law --source packs/uae-labour-law/docs \
  --pattern "*.pdf" --auth-mode login
cd src/runtime
python create_index.py
python ingest.py --dry-run     # inspect chunks first: packs/uae-labour-law/chunks.preview.jsonl
python ingest.py               # embed + upload
```
RBAC can take up to 10 minutes to propagate. If you get 403, wait and retry.

## 8. Test and run

```bash
python -m pytest ../tests -v
python agent.py "I worked 6 years and my basic salary is 12,000 AED. How much gratuity will I get?"
streamlit run app.py
```
Open http://localhost:8501.

## 9. Go private (production)

In your parameter file set `aiPublicNetworkAccess = 'Disabled'` and redeploy. The app must then run inside the VNet (e.g. App Service with VNet integration into `snet-app`).

## 10. Add your own knowledge pack

1. Copy `packs/uae-labour-law/` to `packs/<your-pack>/`
2. Replace `docs/`, edit `pack.json` (name, strategy, glossary), `prompt.md`, and optionally `tools.py`
3. `./scripts/write-env.sh foundation <your-pack>` → upload docs → `create_index.py` → `ingest.py`

## 11. Tear down

```bash
az lock delete --name lock-<workload>-core --resource-group rg-<workload>-<env>-<regionCode>
az group delete --name rg-<workload>-<env>-<regionCode> --yes
az group delete --name rg-<workload>-temp-<regionCode> --yes
az cognitiveservices account purge --location <region> --resource-group rg-<workload>-<env>-<regionCode> --name aif-<workload>-<env>-<regionCode>
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `429` rate limit | Raise `capacity` in the parameter file; output tokens are capped in `agent.py` |
| `403` on Search/Storage/Foundry | RBAC propagation (wait 5–10 min) or your IP changed (re-export `MIZAN_DEV_IP`, redeploy) |
| `SkuNotAvailable` | Model or VM size not offered in your region/subscription: change it in the parameter file |
| Answers miss relevant content | Run `ingest.py --dry-run`, inspect chunks, extend the glossary in `pack.json` |
