# Layered Architecture Quickstart

## TL;DR

New three-layer KRO architecture that creates UAMIs **once** and shares them across all clusters.

```bash
# Deploy everything
cd kro-stack/scripts
./deploy-layered-architecture.sh
```

## Architecture in 30 Seconds

```
Layer 1: Platform Foundation → Creates 5 UAMIs (ONCE)
                 ↓
Layer 2: Management Cluster → References UAMIs + Creates Federated Creds
                 ↓
Layer 3: Worker Clusters   → References SAME UAMIs + Creates Federated Creds
```

## What Was Created

### New ResourceGraphDefinitions (RGDs)

```
kro-stack/definitions/
├── uk8s-platform-foundation.yaml      # Layer 1: Shared UAMIs
├── uk8s-management-cluster.yaml       # Layer 2: Mgmt cluster
└── uk8s-worker-cluster.yaml           # Layer 3: Worker clusters
```

### Example Instances

```
kro-stack/instances/
├── 01-platform-foundation-example.yaml     # Deploy once
├── 02-management-cluster-example.yaml      # Deploy once
└── 03-worker-cluster-dev-example.yaml      # Deploy per cluster
```

### Scripts & Documentation

```
kro-stack/
├── scripts/
│   └── deploy-layered-architecture.sh      # Automated deployment
├── LAYERED_ARCHITECTURE.md                 # Full documentation
├── MIGRATION_GUIDE.md                      # Migration from old arch
└── QUICKSTART.md                           # This file
```

## Key Differences vs. Old Architecture

| Feature | Old (uk8scluster.yaml) | New (Layered) |
|---------|------------------------|---------------|
| UAMIs | 5 per cluster | 5 total (shared) |
| 10 clusters = | 50 UAMIs | 5 UAMIs |
| RBAC assignments | 50+ | 5 |
| Service Accounts | Manual | Automated |
| New cluster | Complex | Simple |

## Quick Deploy

### Prerequisites

```bash
# Ensure you have:
- kubectl configured for your management cluster
- Azure Service Operator (ASO) installed
- KRO installed
```

### Deploy All Layers

```bash
cd kro-stack/scripts
./deploy-layered-architecture.sh
```

### Deploy Specific Layers

```bash
# Only foundation
./deploy-layered-architecture.sh yes no no

# Only clusters (foundation exists)
./deploy-layered-architecture.sh no yes yes

# Only worker (foundation + mgmt exist)
./deploy-layered-architecture.sh no no yes
```

## Manual Deployment

### Step 1: Platform Foundation

```bash
kubectl apply -f definitions/uk8s-platform-foundation.yaml
kubectl apply -f instances/01-platform-foundation-example.yaml

# Wait for ready
kubectl wait --for=condition=Ready \
  uk8splatformfoundation/myplatform-foundation \
  -n uk8s-platform --timeout=900s
```

### Step 2: Management Cluster

```bash
# Extract identity values from foundation
./scripts/deploy-layered-architecture.sh no yes no
```

### Step 3: Worker Cluster

```bash
# Deploy first worker
./scripts/deploy-layered-architecture.sh no no yes
```

## Add Another Worker Cluster

```bash
# 1. Copy template
cp instances/03-worker-cluster-dev-example.yaml \
   instances/04-worker-cluster-prod.yaml

# 2. Update configuration
# - Change clusterName
# - Update resourceGroup
# - Modify network CIDRs
# - Keep platformFoundation references (same UAMIs!)

# 3. Deploy
kubectl apply -f instances/04-worker-cluster-prod.yaml
```

## Verify Deployment

```bash
# Check platform foundation
kubectl get uk8splatformfoundation -A

# Check clusters
kubectl get uk8sworkercluster -A

# Check UAMIs (should see 5 total)
kubectl get userassignedidentity -A | grep -E "externalsecrets|externaldns|certmanager|grafana|flux"

# Check federated credentials (should see multiple, one set per cluster)
kubectl get federatedidentitycredential -A

# Check service accounts
kubectl get sa -A -o json | \
  jq -r '.items[] | select(.metadata.annotations["azure.workload.identity/client-id"]) |
  .metadata.namespace + "/" + .metadata.name'
```

## Architecture Benefits

### Before (Old Architecture)
```
Cluster 1:
  ├── uami-cluster1-externalsecrets
  ├── uami-cluster1-externaldns
  ├── uami-cluster1-certmanager
  └── ... (5 UAMIs)

Cluster 2:
  ├── uami-cluster2-externalsecrets  ← DUPLICATE
  ├── uami-cluster2-externaldns      ← DUPLICATE
  ├── uami-cluster2-certmanager      ← DUPLICATE
  └── ... (5 UAMIs)

Total: 50 UAMIs for 10 clusters ❌
```

### After (Layered Architecture)
```
Platform Foundation:
  ├── uami-platform-externalsecrets  ← SHARED
  ├── uami-platform-externaldns      ← SHARED
  ├── uami-platform-certmanager      ← SHARED
  ├── uami-platform-grafana          ← SHARED
  └── uami-platform-flux             ← SHARED

Cluster 1:
  ├── FederatedCredential → points to shared UAMI
  └── ServiceAccount → uses shared UAMI client ID

Cluster 2:
  ├── FederatedCredential → points to SAME shared UAMI
  └── ServiceAccount → uses SAME shared UAMI client ID

Total: 5 UAMIs for unlimited clusters ✅
```

## Identity Flow

```
Azure AD UAMI (Layer 1)
    ↓
Federated Credential (Layer 2/3)
    ↓ (binds UAMI to cluster OIDC + SA)
Service Account (Layer 2/3)
    ↓
Pod (workload)
```

### Example: External DNS

```yaml
# Layer 1: Create UAMI (once)
kind: UserAssignedIdentity
metadata:
  name: uami-platform-externaldns
# Azure assigns Client ID: aaaa-aaaa-aaaa-aaaa

# Layer 3: Create Federated Credential (per cluster)
kind: FederatedIdentityCredential
spec:
  owner:
    armId: /subscriptions/.../uami-platform-externaldns  ← References Layer 1
  issuer: https://oidc.cluster1.example.com              ← Cluster 1 OIDC
  subject: system:serviceaccount:external-dns:extdns-workload-identity-sa

# Layer 3: Create Service Account (per cluster)
kind: ServiceAccount
metadata:
  name: extdns-workload-identity-sa
  annotations:
    azure.workload.identity/client-id: aaaa-aaaa-aaaa-aaaa  ← Same client ID
```

Result: External DNS pods in Cluster 1 use the shared UAMI via workload identity.

## RBAC Assignment

With shared UAMIs, assign Azure RBAC **once**:

```bash
# Get UAMI client ID
ESO_CLIENT_ID=$(kubectl get uk8splatformfoundation myplatform-foundation \
  -n uk8s-platform -o jsonpath='{.status.externalSecretsClientId}')

# Assign role ONCE
az role assignment create \
  --assignee $ESO_CLIENT_ID \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.KeyVault/vaults/my-keyvault

# This permission applies to external-secrets in ALL clusters
```

## Troubleshooting

### Issue: "UAMI not found in status"

```bash
# Check foundation is ready
kubectl get uk8splatformfoundation -A

# Check ASO logs
kubectl logs -n azureserviceoperator-system \
  -l control-plane=controller-manager --tail=100
```

### Issue: "Pods can't authenticate to Azure"

```bash
# 1. Check service account annotation
kubectl get sa external-secrets -n external-secrets -o yaml | \
  grep azure.workload.identity/client-id

# 2. Check federated credential exists
kubectl get federatedidentitycredential -A | grep externalsecrets

# 3. Verify OIDC issuer matches
kubectl get managedcluster <cluster-name> -n <namespace> \
  -o jsonpath='{.status.oidcIssuerProfile.issuerURL}'
```

## Next Steps

1. **Read full docs:** [LAYERED_ARCHITECTURE.md](./LAYERED_ARCHITECTURE.md)
2. **Customize instances:** Update example YAMLs with your values
3. **Deploy foundation:** Start with Layer 1
4. **Add clusters:** Deploy as many worker clusters as needed
5. **Configure RBAC:** Assign Azure roles to platform UAMIs
6. **Install controllers:** Deploy cert-manager, external-dns, etc.

## Migration from Old Architecture

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed migration steps.

## File Reference

| File | Purpose | Deploy Frequency |
|------|---------|------------------|
| `uk8s-platform-foundation.yaml` | RGD for shared resources | Once (apply RGD) |
| `01-platform-foundation-example.yaml` | Platform instance | Once |
| `uk8s-management-cluster.yaml` | RGD for mgmt cluster | Once (apply RGD) |
| `02-management-cluster-example.yaml` | Mgmt cluster instance | Once |
| `uk8s-worker-cluster.yaml` | RGD for workers | Once (apply RGD) |
| `03-worker-cluster-dev-example.yaml` | Worker instance template | Per cluster |
| `deploy-layered-architecture.sh` | Automated deployment | As needed |

## Support

- Full documentation: [LAYERED_ARCHITECTURE.md](./LAYERED_ARCHITECTURE.md)
- Migration guide: [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
- KRO docs: https://kro.run/docs
- ASO docs: https://azure.github.io/azure-service-operator/
