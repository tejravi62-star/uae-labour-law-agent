# Mizan Network Plan

VNet: vnet-mizan-dev-uaen, 10.20.0.0/22 (non-default range; avoids overlap for future hub peering)

| Subnet | CIDR | Size | Purpose | Notes |
|---|---|---|---|---|
| snet-pe | 10.20.0.0/26 | 64 | Private endpoints | NSG |
| snet-app | 10.20.0.64/26 | 64 | App Service VNet integration | Delegated Microsoft.Web/serverFarms |
| snet-func | 10.20.0.128/26 | 64 | Functions VNet integration | Delegated (service-specific) |
| snet-jump | 10.20.0.192/27 | 32 | Jumpbox VM | SSH only from Bastion |
| spare | 10.20.0.224/27 | 32 | Reserved | |
| AzureBastionSubnet | 10.20.1.0/26 | 64 | Azure Bastion | Name + min /26 required |
| spare | 10.20.1.64/26 | 64 | Future API Management / AI gateway | |
| snet-aks | 10.20.2.0/24 | 256 | AKS nodes (CNI Overlay) | Step 16 |
| spare | 10.20.3.0/24 | 256 | Growth | |

Rules: Azure reserves 5 IPs per subnet. Address space is a per-workload parameter (IPAM). Spoke-ready for hub-and-spoke peering.