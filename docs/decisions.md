# Mizan: Architecture Decision Records

## ADR-001 Region & Models
- Region: UAE North for all resources (verified 2026-09-26 via az cognitiveservices model list).
- Models: gpt-5.4-mini (agent), gpt-5.4-nano (helper tasks), text-embedding-3-small (embeddings). Versions pinned.
- Deployment type: Global Standard in dev (cost/quota); Standard regional in prod (UAE data residency).
- Review model retirement schedule quarterly.

## ADR-002 Naming & Tags
- Pattern: <type>-mizan-<env>-<region>, e.g. rg-mizan-dev-uaen.
- Tags on every resource: project=mizan, env, owner=heart, costmode=core|temp.

## ADR-003 Cost Guardrails
- $30 monthly budget: alerts at 50% actual, 80% actual, 100% forecasted. Anomaly alerts on.
- Free Account limits: Linux B1s VM + Premium SSD ≤64 GB, Cosmos ≤400 RU/s & ≤25 GB, Blob Hot LRS ≤5 GB, SQL S0.
- Expensive services tagged costmode=temp and deleted same day.

## ADR-004 Shared Responsibility
- IaaS: jumpbox VM (I patch OS).
- PaaS: App Service, Functions, SQL, Cosmos, AI Search, Redis, AKS (Microsoft runs platform; I own code, config, data).
- SaaS: Entra ID (I own identities and access).
- AI layer: Microsoft secures model infra; I own grounding data, prompts, content filters, output validation, tool permissions.

## ADR-005 Subscription Model
- Build on Free Trial ($200 credit, spending limit on) within 11-day window.
- Gate: if Foundry model deployment is blocked on trial, upgrade to Pay-As-You-Go at that point.
- Portfolio does not depend on live URL: GitHub repo + azd up one-command deploy + demo video.

## ADR-006 Resource Groups, IaC & Governance
- Two RGs: rg-mizan-dev-uaen (core, CanNotDelete lock) and rg-mizan-temp-uaen (temp, delete whole RG to clean up).
- All infra in Bicep (infra/main.bicep), always what-if before deploy.
- Policy: resource groups must carry a project tag (deny effect, verified).
- Foundry resource keyless (disableLocalAuth=true); access via Entra RBAC only.
- Model deployments named by role (chat-mini), not model name, so models can be swapped without code changes.

## ADR-007 Compute: Jumpbox VM
- Free-tier only: Standard_B1s + Premium SSD 64 GB (P6) in zone 1, Ubuntu 24.04, SSH keys only.
- SSH restricted to my IP via NSG; auto-shutdown 19:00 UTC; deallocate when idle.
- Lab VM proved Foundry endpoint resolves to a public IP (evidence saved). Private endpoint required (Step 4).
- VMs are for admin/jumpbox only; app compute is PaaS (App Service, Functions, AKS).

## ADR-008 Reusable Agent Accelerator
- Three layers: platform (Bicep modules), agent runtime (code), domain pack (data, prompt, tools, evals, groups).
- Only the domain pack changes per team; platform and runtime are parameterised and reused.
- Default isolation: one deployment per team via azd + parameter file. Shared multi-team platform requires per-team indexes, security trimming, and an AI gateway.
- RBAC granted to Entra groups, never individual users.
## ADR-009 Parameterised Platform
- Templates never contain workload-specific values; each team/env gets infra/params/<workload>.<env>.bicepparam.
- Parameters validated with @allowed/@minLength/@maxLength to fail fast before Azure.
- Refactors verified with what-if = no change before commit.

## Well-Architected Mapping
| Pillar | How Mizan addresses it |
|---|---|
| Reliability | Stateless API, managed PaaS, Bicep redeploy in minutes |
| Security | Managed identity, no keys, private endpoints, WAF, content safety |
| Cost | Free tiers, mini/nano models, semantic cache, costmode=temp cleanup |
| Operational Excellence | IaC, CI/CD, ADRs, App Insights tracing |
| Performance | Redis cache, hybrid search, autoscale |
## ADR-010 Network Design
- Spoke VNet 10.20.0.0/22 (non-default, hub-peering ready). Subnets calculated with cidrSubnet from one parameter.
- One subnet per role: snet-pe, snet-app (delegated Web), snet-func (delegated App/environments), snet-jump, AzureBastionSubnet, snet-aks; spare ranges reserved.
- NSGs at subnet level with explicit deny; privateEndpointNetworkPolicies Enabled so NSGs apply to private endpoints.
- defaultOutboundAccess false everywhere except snet-jump (documented trade-off; NAT Gateway/Firewall is the prod fix).
- Not deployed (cost): hub, firewall, UDRs, NAT Gateway, VPN/ExpressRoute. Design is spoke-ready.

## ADR-011 Private Endpoints & Access Model
- Reusable modules: dns.bicep (zones + VNet links) and private-endpoint.bicep (any service, any groupId).
- Foundry needs 3 zones: privatelink.openai / cognitiveservices / services.ai. Missing zone = silent public resolution.
- Foundry adopted into Bicep; model version pinned (NoAutoUpgrade); content filter explicit (Microsoft.DefaultV2).
- networkAcls defaultAction is hard-coded Deny. Dev: publicNetworkAccess Enabled + my IP only (from env var). Prod: Disabled.
- Proven: internet + valid token = 403; VNet resolves to 10.20.0.5; dev IP + token = 200.
- Jumpbox: no public IP, reached via Run Command/Bastion, behind a deployJumpbox switch in the temp RG.

## ADR-012 Identity & Access
- Order of preference: managed identity > service principal > keys. Mizan has zero secrets today.
- RBAC in code (AVM-style roleAssignments), deterministic GUIDs, role fixed by template; parameter file only says who.
- App runs as user-assigned identity id-mizan-app (roles granted before the app exists; shared by App Service/Functions/AKS).
- Company tenant blocks group creation for developers: users assigned today, group IDs later with no template change. scripts/entra-setup.sh is the admin handover. Activity disclosed to manager/IT as a learning sandbox.
- CanNotDelete lock moved into Bicep; it also blocks deleting child role assignments (unlock is a deliberate change).
- Key Vault deferred: no secrets exist. Would be added (private endpoint, RBAC mode, purge protection on in prod / off in dev for teardown) for third-party keys. Secrets as params must use @secure() (deployment history stores plain params).
- Conditional Access / MFA: tenant-owned by IT; app design assumes CA applies to human sign-in, managed identities are exempt.

## ADR-013 Document Storage
- StorageV2 Standard_LRS Hot (free meter), name = take('st'+workload+env+uniqueString(rg.id), 24) for global uniqueness and stable redeploys.
- No shared keys, no public blobs, TLS1.2, defaultAction Deny + dev IP, bypass AzureServices (for AI Search later).
- Blob private endpoint via the same dns/private-endpoint modules (zone privatelink.blob.core.windows.net, groupId blob): ~15 lines, no new module.
- RBAC: people = Blob Data Contributor, app identity = Blob Data Reader (least privilege).
- One container (docs), one prefix per domain pack (uae-labour-law/). Provenance recorded in packs/<pack>/SOURCES.md. English is a translation; Arabic is authoritative.

## ADR-015 Retrieval
- Ingestion strategy is per pack (pack.json "strategy"). Labour law uses "page": side-column headings are extracted after their bodies, breaking heading-first splitting. Page chunks carry the articles found on that page as metadata; 300-char carry-over keeps cross-page articles together; TOC pages auto-skipped. Citations say "PDF page N" (spreads: printed page numbers differ).
- Measured: keyword search for "gratuity" missed the relevant page (law says "end of service benefits"); vector found it at #1; hybrid+semantic dropped it to #4 (keyword noise + diluted page chunks).
- Fix: per-pack glossary query expansion (gratuity -> end of service benefits). Result: keyword #1, hybrid #1 (rerank 1.82 -> 2.14), plus the Executive Regulation's implementing article.
- Remaining limit: page chunks mix 3-5 articles (moderate rerank ~2). Production fix: Document Intelligence layout -> per-article chunks.
