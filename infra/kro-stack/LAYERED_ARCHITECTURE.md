# UK8S Layered KRO Architecture

## Overview

This document describes the three-layer KRO (Kubernetes Resource Orchestrator) architecture for deploying and managing Azure Kubernetes Service (AKS) clusters with shared platform resources.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Platform Foundation (Deploy ONCE)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ uk8s-platform-foundation                                  │  │
│  │  - Shared UAMIs (cert-manager, external-dns, ESO, etc.)  │  │
│  │  - Resource Group for platform resources                 │  │
│  │  - Azure resources (Key Vault, DNS zones, etc.)          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ Outputs (UAMI Client IDs, Resource IDs)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: Management Cluster (Deploy ONCE)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ uk8s-management-cluster                                   │  │
│  │  - AKS management cluster                                 │  │
│  │  - Service Accounts (external-dns, cert-manager, etc.)   │  │
│  │  - Federated Credentials (UAMI → Mgmt Cluster OIDC)      │  │
│  │  - Platform controllers (Flux, KRO, ASO, etc.)           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ (Shared UAMI IDs reused)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Worker Cluster (Deploy PER CLUSTER)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ uk8s-worker-cluster                                       │  │
│  │  - AKS worker cluster                                     │  │
│  │  - Service Accounts (same names as mgmt)                 │  │
│  │  - Federated Credentials (SAME UAMIs → Worker OIDC)      │  │
│  │  - Application workloads                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. UAMIs Created Once (Layer 1)
User-Assigned Managed Identities are created once at the platform level and shared across all clusters.

**Benefits:**
- Single source of truth for identity management
- Centralized RBAC assignment
- Cost efficiency (no duplicate identities)
- Easier lifecycle management

**UAMIs Created:**
- `uami-{platform}-externalsecrets` - For External Secrets Operator
- `uami-{platform}-externaldns` - For External DNS
- `uami-{platform}-certmanager` - For cert-manager
- `uami-{platform}-grafana` - For Grafana/monitoring
- `uami-{platform}-flux` - For Flux GitOps controllers

### 2. Service Accounts Per Cluster (Layers 2 & 3)
Service Accounts are Kubernetes resources that live within each cluster.

**Why:**
- Service Accounts are cluster-scoped resources
- Each cluster needs its own SAs in its namespaces
- SAs are lightweight and don't incur Azure costs

**Service Accounts Created:**
- `external-secrets` (namespace: external-secrets)
- `extdns-workload-identity-sa` (namespace: external-dns)
- `cert-manager` (namespace: ubs-issuer-system)
- `grafana` (namespace: monitoring)
- `source-controller` and `image-automation-controller` (namespace: flux-system)

### 3. Federated Credentials Per Cluster (Layers 2 & 3)
Federated Identity Credentials link UAMIs to Service Accounts via OIDC.

**Why:**
- Each cluster has its own OIDC issuer URL
- Federated credentials bind UAMI + OIDC Issuer + Service Account
- Must be created for each cluster to enable workload identity

**Formula:**
```
Federated Credential = UAMI (Layer 1) + Cluster OIDC Issuer + Service Account Subject
```

## File Structure

```
kro-stack/
├── definitions/
│   ├── uk8s-platform-foundation.yaml     # Layer 1 RGD
│   ├── uk8s-management-cluster.yaml      # Layer 2 RGD
│   └── uk8s-worker-cluster.yaml          # Layer 3 RGD
├── instances/
│   ├── 01-platform-foundation-example.yaml
│   ├── 02-management-cluster-example.yaml
│   └── 03-worker-cluster-dev-example.yaml
├── scripts/
│   └── deploy-layered-architecture.sh    # Automated deployment
└── LAYERED_ARCHITECTURE.md               # This file
```

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

```bash
# Deploy all three layers
cd kro-stack/scripts
chmod +x deploy-layered-architecture.sh
./deploy-layered-architecture.sh

# Deploy only foundation
./deploy-layered-architecture.sh yes no no

# Skip foundation, deploy clusters (if foundation already exists)
./deploy-layered-architecture.sh no yes yes
```

### Option 2: Manual Deployment

#### Step 1: Deploy Platform Foundation

```bash
# Apply RGD
kubectl apply -f definitions/uk8s-platform-foundation.yaml

# Create and apply instance (update with your values)
kubectl apply -f instances/01-platform-foundation-example.yaml

# Wait for foundation to be ready
kubectl wait --for=condition=Ready \
  uk8splatformfoundation/myplatform-foundation \
  -n uk8s-platform \
  --timeout=900s

# Extract identity information
kubectl get uk8splatformfoundation myplatform-foundation \
  -n uk8s-platform -o yaml | grep -A 20 "^status:"
```

#### Step 2: Deploy Management Cluster

```bash
# Extract identity values from foundation
ESO_CLIENT_ID=$(kubectl get uk8splatformfoundation myplatform-foundation \
  -n uk8s-platform -o jsonpath='{.status.externalSecretsClientId}')

ESO_RESOURCE_ID=$(kubectl get uk8splatformfoundation myplatform-foundation \
  -n uk8s-platform -o jsonpath='{.status.externalSecretsResourceId}')

# ... extract other identities ...

# Update 02-management-cluster-example.yaml with extracted values
# Replace REPLACE_FROM_FOUNDATION with actual client IDs
# Replace /subscriptions/SUB_ID/... with actual resource IDs

# Apply RGD
kubectl apply -f definitions/uk8s-management-cluster.yaml

# Apply instance
kubectl apply -f instances/02-management-cluster-example.yaml
```

#### Step 3: Deploy Worker Cluster

```bash
# Use the SAME identity values from Step 2

# Update 03-worker-cluster-dev-example.yaml with identity values

# Apply RGD
kubectl apply -f definitions/uk8s-worker-cluster.yaml

# Apply instance
kubectl apply -f instances/03-worker-cluster-dev-example.yaml
```

## Adding Additional Worker Clusters

To add a new worker cluster:

1. **Copy the worker cluster template:**
   ```bash
   cp instances/03-worker-cluster-dev-example.yaml \
      instances/04-worker-cluster-staging.yaml
   ```

2. **Update configuration:**
   - Change `clusterName`
   - Update `resourceGroup`
   - Modify `network` settings (different subnet/CIDRs)
   - Update `tags` and `environment`
   - **Keep the same `platformFoundation` identity values**

3. **Deploy:**
   ```bash
   kubectl apply -f instances/04-worker-cluster-staging.yaml
   ```

## Identity Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  Azure AD                                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  User-Assigned Managed Identity (UAMI)                 │ │
│  │  - Created in Layer 1                                  │ │
│  │  - Has Azure RBAC permissions                          │ │
│  │  - Client ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx    │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                         │
                         │ Federated Identity Credential
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│  Mgmt Cluster    │            │  Worker Cluster  │
│  ┌────────────┐  │            │  ┌────────────┐  │
│  │  OIDC      │  │            │  │  OIDC      │  │
│  │  Issuer    │  │            │  │  Issuer    │  │
│  │  URL       │  │            │  │  URL       │  │
│  └─────┬──────┘  │            │  └─────┬──────┘  │
│        │         │            │        │         │
│        ▼         │            │        ▼         │
│  ┌────────────┐  │            │  ┌────────────┐  │
│  │  Service   │  │            │  │  Service   │  │
│  │  Account   │  │            │  │  Account   │  │
│  │  (ext-dns) │  │            │  │  (ext-dns) │  │
│  └────────────┘  │            │  └────────────┘  │
└──────────────────┘            └──────────────────┘

Both clusters use the SAME UAMI but different OIDC issuers
```

## Comparison: Old vs New Architecture

### Old Architecture (uk8scluster.yaml)
```yaml
❌ Creates UAMIs per cluster
   - uami-cluster1-externaldns
   - uami-cluster2-externaldns
   - uami-cluster3-externaldns

❌ Creates federated credentials per cluster
   (Correct, but with duplicate UAMIs)

❌ No service accounts created
   (Must be created separately)
```

**Problems:**
- 5 UAMIs × 10 clusters = 50 duplicate identities
- Complex RBAC management (50 identities to manage)
- High operational overhead
- Difficult to audit and maintain

### New Architecture (Layered)
```yaml
✅ Creates UAMIs once (Layer 1)
   - uami-platform-externaldns (shared)

✅ Creates federated credentials per cluster
   (Layer 2 for mgmt, Layer 3 per worker)

✅ Creates service accounts per cluster
   (Layer 2 for mgmt, Layer 3 per worker)
```

**Benefits:**
- 5 UAMIs total (regardless of cluster count)
- Centralized RBAC management
- Clear separation of concerns
- Easy to add new clusters
- Simplified disaster recovery

## RBAC Assignment Strategy

With shared UAMIs, you assign Azure RBAC once:

```bash
# Assign DNS Zone Contributor to external-dns UAMI (ONCE)
az role assignment create \
  --assignee <uami-platform-externaldns-client-id> \
  --role "DNS Zone Contributor" \
  --scope /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.Network/dnszones/example.com

# This permission applies to external-dns in ALL clusters
```

## Disaster Recovery

### Backup Required Configuration

1. **Platform Foundation:**
   ```bash
   kubectl get uk8splatformfoundation myplatform-foundation \
     -n uk8s-platform -o yaml > backup/platform-foundation.yaml
   ```

2. **Identity Mappings:**
   Create a ConfigMap with identity information for easy reference:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: platform-identity-mapping
     namespace: uk8s-platform
   data:
     externalsecrets-client-id: "xxx"
     externalsecrets-resource-id: "/subscriptions/..."
     # ... other identities ...
   ```

### Cluster Rebuild Process

1. **Foundation intact:** Just redeploy worker cluster with same instance YAML
2. **Foundation destroyed:** Redeploy all three layers in order

## Troubleshooting

### Issue: Worker cluster pods can't authenticate to Azure

**Symptoms:**
```
Error: failed to acquire token: error getting token from Azure workload identity
```

**Check:**
1. Service Account has correct annotation:
   ```bash
   kubectl get sa external-secrets -n external-secrets -o yaml | grep azure.workload.identity
   ```

2. Federated Credential exists:
   ```bash
   kubectl get federatedidentitycredential -A
   ```

3. OIDC issuer URL matches:
   ```bash
   # Get cluster OIDC issuer
   kubectl get managedcluster <cluster-name> -n <namespace> \
     -o jsonpath='{.status.oidcIssuerProfile.issuerURL}'

   # Get federated credential issuer
   kubectl get federatedidentitycredential <name> -n <namespace> \
     -o jsonpath='{.spec.issuer}'
   ```

### Issue: UAMIs not appearing in foundation status

**Check:**
1. Foundation instance is ACTIVE:
   ```bash
   kubectl get uk8splatformfoundation -A
   ```

2. ASO is running:
   ```bash
   kubectl get pods -n azureserviceoperator-system
   ```

3. Check ASO logs:
   ```bash
   kubectl logs -n azureserviceoperator-system -l control-plane=controller-manager
   ```

## Advanced Configuration

### Multiple Platforms

You can deploy multiple platform foundations for different environments:

```yaml
# Platform A (Production)
kind: UK8SPlatformFoundation
metadata:
  name: platform-prod
spec:
  platformName: prod
  resourceGroupName: rg-platform-prod-shared

# Platform B (Non-Production)
kind: UK8SPlatformFoundation
metadata:
  name: platform-nonprod
spec:
  platformName: nonprod
  resourceGroupName: rg-platform-nonprod-shared
```

### Cross-Subscription Deployments

Worker clusters can be in different subscriptions than the platform foundation:

```yaml
# Foundation in Subscription A
kind: UK8SPlatformFoundation
spec:
  subscriptionId: "aaaa-aaaa-aaaa-aaaa"

# Worker in Subscription B
kind: UK8SWorkerCluster
spec:
  subscriptionId: "bbbb-bbbb-bbbb-bbbb"
  platformFoundation:
    # Reference UAMIs from Subscription A
    externalSecretsResourceId: "/subscriptions/aaaa-aaaa-aaaa-aaaa/..."
```

## Next Steps

1. **Customize instances:** Update example YAML files with your actual values
2. **Deploy foundation:** Start with Layer 1
3. **Deploy management cluster:** Layer 2
4. **Deploy worker clusters:** Layer 3 (as many as needed)
5. **Configure RBAC:** Assign Azure roles to platform UAMIs
6. **Install controllers:** Deploy cert-manager, external-dns, ESO, etc.

## References

- [KRO Documentation](https://kro.run/docs)
- [Azure Service Operator](https://azure.github.io/azure-service-operator/)
- [Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Federated Identity Credentials](https://learn.microsoft.com/en-us/graph/api/resources/federatedidentitycredentials-overview)
