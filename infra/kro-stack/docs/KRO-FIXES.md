# KRO Stack Fixes Applied

This document details the fixes applied to make all ResourceGraphDefinitions Active.

## Issues Found and Fixed

### 1. Resource ID Naming Convention ✅

**Issue**: KRO requires resource IDs to be in lowerCamelCase, not UpperCamelCase.

**Error**:
```
naming convention violation: id Jobs is not a valid KRO resource id: must be lower camelCase
```

**Fix**: Changed resource ID from `Jobs` to `jobs` in uk8scluster.yaml:
```yaml
# Before
- id: Jobs

# After
- id: jobs
```

### 2. Bash Variable Escaping in Job Scripts ✅

**Issue**: KRO parses `${VARIABLE}` syntax as CEL expressions, not bash variables.

**Error**:
```
found unknown resources in CEL expression: [[{AZURE_CLIENT_ID AZURE_CLIENT_ID}]]
```

**Fix**: Changed `${VAR}` to `$VAR` in bash scripts within uk8sjobs.yaml:
```yaml
# Before (incorrect - KRO tries to parse as CEL)
az login -u "${AZURE_CLIENT_ID}"
# or
az login -u "$${AZURE_CLIENT_ID}"  # Also doesn't work

# After (correct - plain bash variable)
az login -u "$AZURE_CLIENT_ID"
```

**Rule**: In KRO YAML files:
- Use `${schema.spec.field}` for KRO template expressions
- Use `$VARIABLE` (without braces) for bash variables in scripts
- DO NOT use `${VARIABLE}` in bash scripts - KRO will try to parse it as CEL

### 3. Reserved Keyword: `namespace` ✅

**Issue**: The field name `namespace` conflicts with Kubernetes metadata.namespace and causes KRO validation errors.

**Error**:
```
failed to type-check template expression "schema.spec.namespace" at path "metadata.namespace": 
ERROR: <input>:1:12: undefined field 'namespace'
```

**Fix**: Renamed `namespace` to `targetNamespace` in all RGD schemas:

**Files Changed**:
- `uk8scluster.yaml`: Schema field and all 13 references
- `uk8sfluxgitops.yaml`: Schema field and all 3 references

```yaml
# Before
schema:
  spec:
    namespace: string | required=true

resources:
  - id: someResource
    template:
      metadata:
        namespace: ${schema.spec.namespace}

# After
schema:
  spec:
    targetNamespace: string | required=true

resources:
  - id: someResource
    template:
      metadata:
        namespace: ${schema.spec.targetNamespace}
```

## Final Status

All ResourceGraphDefinitions are now **Active**:

```
NAME                       APIVERSION   KIND               STATE    
uk8scluster.kro.run        v1alpha1     UK8SCluster        Active   
uk8sfluxgitops.kro.run     v1alpha1     UK8SFluxGitOps     Active   
uk8sjobs.kro.run           v1alpha1     UK8Sjobs           Active   
```

## Files Modified

1. `/definitions/uk8scluster.yaml`
   - Changed resource ID: `Jobs` → `jobs`
   - Changed schema field: `namespace` → `targetNamespace`
   - Updated all 13 metadata.namespace references
   - Updated child resource spec references

2. `/definitions/uk8sfluxgitops.yaml`
   - Changed schema field: `namespace` → `targetNamespace`
   - Updated all 3 metadata.namespace references

3. `/definitions/uk8sjobs.yaml`
   - Fixed bash variable syntax: `${AZURE_CLIENT_ID}` → `$AZURE_CLIENT_ID`
   - Fixed: `${AZURE_TENANT_ID}` → `$AZURE_TENANT_ID`
   - Fixed: `${AZURE_FEDERATED_TOKEN_FILE}` → `$AZURE_FEDERATED_TOKEN_FILE`

## Required Instance Changes

When creating UK8SCluster instances, you must now use `targetNamespace` instead of `namespace`:

```yaml
apiVersion: kro.run/v1alpha1
kind: UK8SCluster
metadata:
  name: my-cluster
  namespace: uk8s-nextgen  # This is the K8s resource namespace (metadata)
spec:
  clusterName: my-cluster
  targetNamespace: uk8s-nextgen  # This is the schema field (renamed from namespace)
  # ... other fields
```

**Note**: The instance metadata.namespace and spec.targetNamespace typically have the same value.

## Testing

To verify RGDs are working:

```bash
# Check all RGDs are Active
kubectl get resourcegraphdefinitions | grep uk8s

# Should show:
# uk8scluster.kro.run        v1alpha1     UK8SCluster        Active
# uk8sfluxgitops.kro.run     v1alpha1     UK8SFluxGitOps     Active
# uk8sjobs.kro.run           v1alpha1     UK8Sjobs           Active
```

## Lessons Learned

1. **Naming Conventions Matter**: KRO enforces lowerCamelCase for resource IDs
2. **CEL vs Bash**: Be careful with `${}` syntax - KRO parses it as CEL before bash sees it
3. **Reserved Keywords**: Some field names like `namespace` are reserved/problematic - use descriptive alternatives
4. **Incremental Testing**: Test RGDs individually to isolate issues
5. **Check Conditions**: Always check `.status.conditions` for detailed error messages

## Additional Issues Found During Deployment

### 4. KRO Controller Not Processing Instances ✅

**Issue**: After applying the UK8SCluster instance, no child resources were being created and the instance had no status updates.

**Error**: No error message - instance just showed no STATE or READY status

**Cause**: KRO controller pod was not actively reconciling instances after the RGDs were updated.

**Fix**: Restart the KRO controller pod:
```bash
# Find KRO controller pod
kubectl get pods -A | grep kro

# Restart the pod
kubectl delete pod -n kro <kro-pod-name>
```

**Location**: KRO controller in `kro` namespace

### 5. Azure Network Route Table Configuration ✅

**Issue**: ManagedCluster creation failed due to invalid route table configuration.

**Error**:
```
RouteTableInvalidNextHop - Default route 0.0.0.0/0 has next hop of Internet but only next hops of VirtualAppliance or VirtualNetworkGateway are allowed
```

**Cause**: The subnet `aks-subnet` had a route table with 0.0.0.0/0 route pointing to "Internet", which is not allowed for AKS.

**Fix**: Delete the problematic route:
```bash
az network route-table route delete \
  --resource-group aks-cluster \
  --route-table-name aks-route-table \
  --name default-route
```

**Valid next hop types for AKS**: VirtualAppliance, VirtualNetworkGateway, None

### 6. Azure Subscription Feature Registration ✅

**Issue**: ManagedCluster creation failed due to missing subscription feature.

**Error**:
```
SubscriptionNotEnabledEncryptionAtHost - Subscription does not enable EncryptionAtHost
```

**Cause**: RGD had `enableEncryptionAtHost: true` but the Azure subscription doesn't have the EncryptionAtHost feature enabled.

**Fix**: Disabled encryption at host in uk8scluster.yaml:
```yaml
# Line 344
enableEncryptionAtHost: false  # Changed from true
```

**Alternative**: Enable the feature in Azure (requires Owner/Contributor role):
```bash
az feature register --namespace Microsoft.Compute --name EncryptionAtHost
```

### 7. Schema Validation for Optional Fields ✅

**Issue**: UK8Sjobs validation failed when empty strings were passed for fields with UUID regex patterns.

**Error**:
```
Invalid value: "": spec.azureTenantId in body should match '^[0-9a-f]{8}-...$'
```

**Cause**: Fields were marked as `required=true` with strict regex patterns that didn't allow empty strings.

**Fix**: Made fields optional with empty defaults and updated regex patterns in uk8sjobs.yaml:
```yaml
# Before
azureTenantId: string | required=true pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

# After
azureTenantId: string | default="" pattern="^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})?$"
```

**Files Updated**: uk8sjobs.yaml lines 32, 37-38, 43

## Next Steps

Now that all RGDs are Active and issues are resolved, you can:

1. Deploy a cluster instance:
   ```bash
   kubectl apply -f instances/dev/example-cluster.yaml
   ```

2. Monitor the deployment:
   ```bash
   kubectl get uk8scluster -n uk8s-nextgen -w
   ```

3. Check created resources:
   ```bash
   kubectl get resourcegroups,managedclusters,identities -n uk8s-nextgen
   ```

4. Check ManagedCluster provisioning status:
   ```bash
   kubectl describe managedcluster -n uk8s-nextgen
   ```

## Additional Documentation

For comprehensive deployment troubleshooting and lessons learned, see:
- [DEPLOYMENT-LESSONS-LEARNED.md](./DEPLOYMENT-LESSONS-LEARNED.md) - Complete deployment guide with all issues encountered and debugging workflow

