# Comparison: Simple vs Full Stack Approaches

This document compares the two KRO stack approaches available in this repository.

## Overview

| Approach | RGD File | Use Case | Complexity |
|----------|----------|----------|------------|
| **Simple** | `akscluster-simple.yaml` | Cluster creation only | Low |
| **Full Stack** | `uk8scluster.yaml` | Complete infrastructure | High |

## Detailed Comparison

### 1. Simple Approach (`akscluster-simple.yaml`)

Based on the tested working version from `kro-aks-cluster`.

#### What it Creates
- ✅ AKS Managed Cluster only
- ❌ No Resource Group (must pre-exist)
- ❌ No Managed Identities (must pre-create)
- ❌ No Federated Credentials
- ❌ No Flux Configuration
- ❌ No Post-deployment Jobs

#### Advantages
- ✅ **Simpler**: Easier to understand and debug
- ✅ **Faster**: Fewer resources to create
- ✅ **Tested**: Based on working production configuration
- ✅ **Status Outputs**: Exposes cluster status in CRD status section
- ✅ **Flexible**: You manage identities and Flux separately

#### Disadvantages
- ❌ **Manual Setup**: Requires pre-creating Resource Group, Identities
- ❌ **No GitOps**: Flux must be configured separately
- ❌ **No Automation**: Post-deployment tasks done manually

#### When to Use
- Quick cluster creation for testing
- When you have existing resource groups and identities
- When you want to manage Flux separately
- When you're learning KRO
- Development and testing environments

---

### 2. Full Stack Approach (`uk8scluster.yaml`)

Comprehensive infrastructure-as-code approach.

#### What it Creates
- ✅ Resource Group
- ✅ AKS Managed Cluster
- ✅ User-Assigned Managed Identities (3)
  - External Secrets
  - External DNS
  - Cert Manager
- ✅ Federated Identity Credentials (6)
- ✅ Flux GitOps Configuration (via child resource)
- ✅ Post-deployment Jobs (via child resource)
- ✅ Optional CronJobs for maintenance

#### Advantages
- ✅ **Complete**: Everything created automatically
- ✅ **GitOps Ready**: Flux configured automatically
- ✅ **Workload Identity**: All federated credentials set up
- ✅ **Production Ready**: Includes monitoring integration
- ✅ **Repeatable**: Fully declarative infrastructure

#### Disadvantages
- ❌ **Complex**: More resources = more to understand
- ❌ **Slower**: Takes longer to create all resources
- ❌ **Harder to Debug**: More moving parts
- ❌ **Less Flexible**: Opinionated about identity setup

#### When to Use
- Production deployments
- When you want full GitOps automation
- When starting from scratch (no existing resources)
- Multi-cluster deployments with consistency
- Enterprise environments requiring standardization

---

## Key Technical Differences

### Schema Differences

| Feature | Simple | Full Stack |
|---------|--------|------------|
| Resource Group | `ownerResourceGroup` (existing) | `resourceGroup` (created) |
| VPA Config | `vpaAddonAutoscaling` field | Nested in `verticalPodAutoscaler` |
| Status Section | ✅ Has cluster status | ❌ Missing (should be added) |
| Child Resources | None | FluxGitOps, Jobs, CronJobs |
| Identities | Pre-created | Automatically created |

### Network Configuration

| Setting | Simple | Full Stack | Notes |
|---------|--------|------------|-------|
| `outboundType` | `loadBalancer` | `userDefinedRouting` | Full uses custom routing |
| `enablePrivateCluster` | `false` | `true` | Full is private by default |
| `enableEncryptionAtHost` | `false` | `true` | Full is more secure |

### Workload Auto Scaler

**Simple** (flat structure):
```yaml
workloadAutoScaler:
  kedaEnabled: true
  vpaEnabled: true
  vpaAddonAutoscaling: Enabled
```

**Full** (nested structure):
```yaml
workloadAutoScaler:
  keda:
    enabled: true
  verticalPodAutoscaler:
    enabled: true
```

⚠️ **Note**: The simple structure is more aligned with the actual ASO API.

---

## Migration Paths

### From Simple to Full

1. **Export existing cluster config**:
   ```bash
   kubectl get akscluster my-cluster -n azure-system -o yaml > backup.yaml
   ```

2. **Create equivalent UK8SCluster instance** with:
   - Add `environment` field
   - Change `ownerResourceGroup` to `resourceGroup`
   - Add Flux configuration
   - Add identity creation specs

3. **Consider**: Whether to recreate or just add Flux/Jobs as separate resources

### From Full to Simple

1. **Extract cluster-only configuration** from UK8SCluster
2. **Pre-create**:
   - Resource Group
   - Managed Identities
   - Federated Credentials (if needed)
3. **Create AKSCluster instance** with reference to existing resources

---

## Recommended Approach by Environment

### Development
**Recommendation**: **Simple**

**Rationale**:
- Faster iteration
- Easier to debug
- Can reuse identities across clusters
- Less overhead

**Setup**:
```bash
# One-time setup
az group create --name rg-dev-shared --location uksouth
az identity create --name uami-dev-controlplane --resource-group rg-dev-shared
az identity create --name uami-dev-kubelet --resource-group rg-dev-shared

# Then create clusters quickly
kubectl apply -f instances/dev/simple-cluster-example.yaml
```

### Staging
**Recommendation**: **Full Stack** or **Simple** (depending on similarity to production)

**Rationale**:
- If staging mirrors production: use Full Stack
- If staging is for feature testing: use Simple

### Production
**Recommendation**: **Full Stack**

**Rationale**:
- Complete automation
- Consistent deployments
- GitOps integration
- Audit trail
- Disaster recovery ready

---

## Example Scenarios

### Scenario 1: Quick Dev Cluster

**Need**: "I need an AKS cluster to test my app quickly"

**Use**: **Simple Approach**

```bash
# 1. Create resource group (one time)
az group create --name rg-my-test --location uksouth

# 2. Create identities (one time)
az identity create --name uami-test-cp --resource-group rg-my-test
az identity create --name uami-test-kubelet --resource-group rg-my-test

# 3. Apply cluster
kubectl apply -f instances/dev/simple-cluster-example.yaml

# 4. Get cluster status
kubectl get akscluster my-test-cluster -n azure-system -o yaml
```

**Time to cluster**: ~10-15 minutes

---

### Scenario 2: Production Multi-Region Deployment

**Need**: "I need to deploy production clusters across UK South and West Europe with full GitOps"

**Use**: **Full Stack Approach**

```bash
# 1. Apply RGDs (one time)
kubectl apply -f definitions/uk8scluster.yaml
kubectl apply -f definitions/uk8sfluxgitops.yaml
kubectl apply -f definitions/uk8sjobs.yaml

# 2. Create clusters
kubectl apply -f instances/production/cluster-uksouth.yaml
kubectl apply -f instances/production/cluster-westeurope.yaml

# Everything created automatically:
# - Resource Groups
# - Clusters
# - Identities
# - Federated Credentials
# - Flux Configuration
# - Grafana Integration
```

**Time to cluster**: ~30-45 minutes (but fully automated)

---

### Scenario 3: Migration from Manual to GitOps

**Need**: "I have existing AKS clusters, want to add GitOps gradually"

**Use**: **Simple Approach** + Manual Flux

```bash
# 1. Import existing cluster as AKSCluster resource
# (This doesn't recreate, just imports for management)

# 2. Add Flux separately using UK8SFluxGitOps
apiVersion: kro.run/v1alpha1
kind: UK8SFluxGitOps
metadata:
  name: flux-my-existing-cluster
spec:
  clusterName: my-existing-cluster
  # ...
```

---

## Feature Matrix

| Feature | Simple | Full | Notes |
|---------|--------|------|-------|
| Cluster Creation | ✅ | ✅ | Both create cluster |
| Resource Group Creation | ❌ | ✅ | Simple requires pre-existing |
| Identity Creation | ❌ | ✅ | Simple requires pre-existing |
| Federated Credentials | ❌ | ✅ | For External Secrets, DNS, Cert Manager |
| Flux Extension | ❌ | ✅ | GitOps automation |
| Flux Core Config | ❌ | ✅ | NAP, system components |
| Flux App Config | ❌ | ✅ | Application deployments |
| Grafana Integration Job | ❌ | ✅ | Azure Monitor setup |
| Health Check CronJobs | ❌ | ⚠️ | Optional in Full |
| Status Outputs | ✅ | ❌ | **Simple wins here** |
| Deployment Time | ~10 min | ~30 min | Approximate |
| Debugging Complexity | Low | High | Fewer resources = easier |

---

## Recommendations for This Repository

### Improve Full Stack
Add the status section to `uk8scluster.yaml`:

```yaml
status:
  provisioningState: ${managedCluster.status.provisioningState}
  powerState: ${managedCluster.status.powerState.code}
  fqdn: ${managedCluster.status.fqdn}
  currentKubernetesVersion: ${managedCluster.status.currentKubernetesVersion}
  oidcIssuerUrl: ${managedCluster.status.oidcIssuerProfile.issuerURL}
```

### Simplify Workload Auto Scaler
Consider using flat structure like Simple approach:
```yaml
workloadAutoScaler:
  kedaEnabled: boolean
  vpaEnabled: boolean
  vpaAddonAutoscaling: string
```

### Network Options
Make outboundType and enablePrivateCluster configurable:

```yaml
network:
  outboundType: string | default="userDefinedRouting" enum="loadBalancer,userDefinedRouting,userAssignedNATGateway"
  enablePrivateCluster: boolean | default=false
```

---

## Summary

**Choose Simple** if:
- You need quick cluster creation
- You're testing or developing
- You have existing resource groups and identities
- You want maximum flexibility
- You prefer to manage Flux separately

**Choose Full Stack** if:
- You want complete automation
- You're deploying to production
- You want GitOps from day one
- You need consistent multi-cluster deployments
- You want workload identity pre-configured

**Best Practice**:
- **Development**: Use Simple
- **Production**: Use Full Stack
- **Hybrid**: Use Simple for clusters, add UK8SFluxGitOps separately for GitOps

Both approaches are valid and tested. The choice depends on your specific requirements and operational maturity.
