# Migration Guide: Old Architecture → Layered Architecture

## Overview

This guide helps you migrate from the monolithic `uk8scluster.yaml` to the new three-layer architecture.

## What Changed?

### Before (Monolithic Architecture)

**Single RGD:** `uk8scluster.yaml`
```yaml
spec:
  resources:
    - ResourceGroup
    - ManagedCluster
    - UserAssignedIdentity (externalsecrets)      ❌ Created per cluster
    - UserAssignedIdentity (externaldns)          ❌ Created per cluster
    - UserAssignedIdentity (certmanager)          ❌ Created per cluster
    - FederatedIdentityCredential (per cluster)   ✅ Correct
    # ❌ No Service Accounts
```

**Problems:**
- 5 UAMIs × 10 clusters = 50 identities to manage
- RBAC assigned 50 times
- Service Accounts created manually
- No separation of platform vs. cluster resources

### After (Layered Architecture)

**Three RGDs:**

1. **Layer 1:** `uk8s-platform-foundation.yaml`
   ```yaml
   resources:
     - ResourceGroup (shared)
     - UserAssignedIdentity (externalsecrets)     ✅ Created once
     - UserAssignedIdentity (externaldns)         ✅ Created once
     - UserAssignedIdentity (certmanager)         ✅ Created once
     - UserAssignedIdentity (grafana)             ✅ Created once
     - UserAssignedIdentity (flux)                ✅ Created once
   ```

2. **Layer 2:** `uk8s-management-cluster.yaml`
   ```yaml
   resources:
     - ManagedCluster (management)
     - FederatedIdentityCredential (mgmt cluster) ✅ Per cluster
     - ServiceAccount (external-secrets, etc.)    ✅ Kubernetes resources
   ```

3. **Layer 3:** `uk8s-worker-cluster.yaml`
   ```yaml
   resources:
     - ManagedCluster (worker)
     - FederatedIdentityCredential (worker)       ✅ Per cluster
     - ServiceAccount (external-secrets, etc.)    ✅ Kubernetes resources
   ```

## Migration Steps

### Step 1: Audit Existing Environment

```bash
# List all existing clusters
kubectl get uk8scluster -A

# List all UAMIs created
az identity list --query "[?contains(name, 'externalsecrets')].{Name:name, RG:resourceGroup}" -o table
az identity list --query "[?contains(name, 'externaldns')].{Name:name, RG:resourceGroup}" -o table
az identity list --query "[?contains(name, 'certmanager')].{Name:name, RG:resourceGroup}" -o table
```

### Step 2: Choose Migration Strategy

#### Option A: Greenfield (Recommended for new deployments)
Start fresh with the new architecture.

**Pros:**
- Clean slate
- No migration complexity

**Cons:**
- Must recreate clusters

#### Option B: Brownfield (Migrate existing clusters)
Reuse existing resources where possible.

**Pros:**
- Keep existing clusters
- Migrate incrementally

**Cons:**
- More complex
- Requires careful RBAC reassignment

### Step 3: Brownfield Migration (Detailed)

#### 3.1 Create Platform Foundation (Reuse Existing UAMIs)

If you already have UAMIs you want to reuse:

```yaml
# Option 1: Import existing UAMIs into KRO
apiVersion: managedidentity.azure.com/v1api20230131
kind: UserAssignedIdentity
metadata:
  name: uami-platform-externaldns
  namespace: uk8s-platform
  annotations:
    serviceoperator.azure.com/reconcile-policy: skip  # Don't create, just reference
spec:
  azureName: uami-existing-externaldns  # Existing UAMI name
  owner:
    armId: /subscriptions/SUB_ID/resourceGroups/RG  # Existing RG
```

Or create new platform UAMIs and reassign RBAC:

```bash
# Deploy new platform foundation
kubectl apply -f kro-stack/definitions/uk8s-platform-foundation.yaml
kubectl apply -f kro-stack/instances/01-platform-foundation-example.yaml

# Wait for UAMIs to be created
kubectl wait --for=condition=Ready uk8splatformfoundation/myplatform-foundation -n uk8s-platform

# Get new UAMI client IDs
ESO_CLIENT_ID=$(kubectl get uk8splatformfoundation myplatform-foundation \
  -n uk8s-platform -o jsonpath='{.status.externalSecretsClientId}')

# Reassign Azure RBAC to new UAMIs
az role assignment create \
  --assignee $ESO_CLIENT_ID \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.KeyVault/vaults/VAULT_NAME

# Repeat for all UAMIs and required roles
```

#### 3.2 Migrate Existing Clusters

For each existing cluster:

1. **Extract current configuration:**
   ```bash
   kubectl get uk8scluster my-existing-cluster -n uk8s-nextgen -o yaml > existing-cluster-backup.yaml
   ```

2. **Create worker cluster instance with new architecture:**
   ```bash
   # Copy template
   cp kro-stack/instances/03-worker-cluster-dev-example.yaml \
      kro-stack/instances/migrated-cluster.yaml

   # Update with your cluster's current config
   # - clusterName (keep same)
   # - resourceGroup (keep same)
   # - network settings (keep same)
   # - Add platformFoundation references (new UAMIs)
   ```

3. **Update federated credentials:**

   The tricky part: you need to update federated credentials to point to new UAMIs.

   ```bash
   # Delete old federated credentials (per-cluster UAMIs)
   kubectl delete federatedidentitycredential externalsecrets-fic-my-existing-cluster \
     -n uk8s-nextgen

   # New federated credentials will be created by worker cluster RGD
   # pointing to shared platform UAMIs
   ```

4. **Apply worker cluster instance:**
   ```bash
   kubectl apply -f kro-stack/instances/migrated-cluster.yaml
   ```

5. **Update service accounts in the running cluster:**
   ```bash
   # Get new platform UAMI client IDs
   ESO_CLIENT_ID=$(kubectl get uk8splatformfoundation myplatform-foundation \
     -n uk8s-platform -o jsonpath='{.status.externalSecretsClientId}')

   # Update service account annotation (in the worker cluster context)
   kubectl annotate serviceaccount external-secrets \
     -n external-secrets \
     azure.workload.identity/client-id=$ESO_CLIENT_ID \
     --overwrite

   # Restart pods to pick up new identity
   kubectl rollout restart deployment external-secrets -n external-secrets
   ```

6. **Verify:**
   ```bash
   # Check pods can authenticate
   kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets

   # Should see successful Azure authentication
   ```

#### 3.3 Cleanup Old Resources

After successful migration:

```bash
# Delete old per-cluster UAMIs
az identity delete \
  --name uami-old-cluster-externalsecrets \
  --resource-group rg-old-cluster

# Remove old RBAC assignments
az role assignment delete \
  --assignee <old-uami-client-id> \
  --role "Key Vault Secrets User"
```

### Step 4: Greenfield Deployment

For new deployments, simply:

```bash
cd kro-stack/scripts
./deploy-layered-architecture.sh
```

## Comparison Table

| Aspect | Old Architecture | New Architecture |
|--------|------------------|------------------|
| UAMIs per cluster | 5 | 0 (references shared) |
| Total UAMIs (10 clusters) | 50 | 5 |
| RBAC assignments | 50+ | 5 |
| Service Accounts | Manual | Automated |
| Federated Credentials | Per cluster ✅ | Per cluster ✅ |
| Cost | High (50 UAMIs) | Low (5 UAMIs) |
| Complexity | High | Low |
| New cluster deployment | Complex | Simple |

## Testing Migration

### Pre-Migration Checklist

- [ ] Backup all existing cluster configurations
- [ ] Document current RBAC assignments
- [ ] Test deployment in dev environment first
- [ ] Verify workload identity works in test cluster
- [ ] Document rollback procedure

### Post-Migration Verification

```bash
# 1. Verify platform foundation
kubectl get uk8splatformfoundation -A
kubectl describe uk8splatformfoundation myplatform-foundation -n uk8s-platform

# 2. Verify worker clusters
kubectl get uk8sworkercluster -A

# 3. Verify federated credentials
kubectl get federatedidentitycredential -A

# 4. Verify service accounts have correct annotations
kubectl get sa -A -o json | jq -r '.items[] | select(.metadata.annotations["azure.workload.identity/client-id"]) | .metadata.namespace + "/" + .metadata.name + " -> " + .metadata.annotations["azure.workload.identity/client-id"]'

# 5. Test workload identity
# Deploy a test pod and verify it can authenticate to Azure
kubectl run test-identity --image=mcr.microsoft.com/azure-cli \
  --serviceaccount=external-secrets \
  -n external-secrets \
  -- az login --identity
```

## Rollback Procedure

If migration fails:

1. **Revert to old RGDs:**
   ```bash
   kubectl apply -f kro-stack/definitions/uk8scluster.yaml  # Old definition
   kubectl apply -f existing-cluster-backup.yaml
   ```

2. **Restore RBAC assignments to old UAMIs**

3. **Delete new platform foundation:**
   ```bash
   kubectl delete uk8splatformfoundation myplatform-foundation -n uk8s-platform
   ```

## Common Migration Issues

### Issue: Pods can't authenticate after migration

**Cause:** Service account annotation not updated

**Fix:**
```bash
# Update SA annotation with new UAMI client ID
kubectl annotate sa <sa-name> \
  -n <namespace> \
  azure.workload.identity/client-id=<new-client-id> \
  --overwrite

# Restart pods
kubectl rollout restart deployment <deployment> -n <namespace>
```

### Issue: Federated credential already exists

**Cause:** Azure has a limit of 20 federated credentials per UAMI

**Fix:**
```bash
# List existing federated credentials
az identity federated-credential list \
  --identity-name uami-platform-externaldns \
  --resource-group rg-platform-shared

# Delete unused ones
az identity federated-credential delete \
  --name old-fedcred \
  --identity-name uami-platform-externaldns \
  --resource-group rg-platform-shared
```

## FAQ

### Q: Can I mix old and new architectures?

**A:** Not recommended. Choose one approach. If you have existing clusters using old architecture, migrate them incrementally or keep them separate.

### Q: Do I need to recreate clusters?

**A:** No, you can update federated credentials and service accounts in existing clusters. The AKS cluster itself doesn't need recreation.

### Q: What about GitOps/Flux configuration?

**A:** Flux configurations remain the same. Only the identity management changes.

### Q: How do I handle multiple environments?

**A:** Create separate platform foundations:
- `platform-prod-foundation`
- `platform-nonprod-foundation`

Each with its own set of shared UAMIs.

## Next Steps

1. Review the [LAYERED_ARCHITECTURE.md](./LAYERED_ARCHITECTURE.md) for detailed architecture documentation
2. Test the new architecture in a dev environment
3. Plan your migration timeline
4. Execute migration cluster by cluster
5. Monitor and verify each migrated cluster

## Support

If you encounter issues:
1. Check the [LAYERED_ARCHITECTURE.md](./LAYERED_ARCHITECTURE.md) troubleshooting section
2. Review KRO and ASO logs
3. Verify Azure RBAC assignments
4. Check federated credential configuration
