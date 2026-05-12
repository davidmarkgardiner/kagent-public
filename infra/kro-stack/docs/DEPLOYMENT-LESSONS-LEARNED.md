# KRO Stack Deployment - Lessons Learned

## Session Summary
Successfully deployed a complete AKS cluster using KRO (Kubernetes Resource Orchestration) with Azure Service Operator (ASO). The deployment created:
- ResourceGroup in Azure
- AKS ManagedCluster with NAP (Node Auto-Provisioning)
- 3 User Assigned Managed Identities (External Secrets, External DNS, Cert Manager)
- 6 Federated Identity Credentials for Workload Identity
- UK8Sjobs for post-deployment configuration
- UK8SFluxGitOps for GitOps continuous delivery

## Critical Issues & Fixes

### 1. KRO Controller Not Processing Instances
**Symptom**: UK8SCluster instance created but no child resources appearing, no status updates
**Diagnosis**:
- RGDs were Active but instances weren't being reconciled
- No logs in KRO controller about the instance
**Root Cause**: KRO controller pod needed restart to pick up instances
**Solution**:
```bash
# Find KRO controller pod
kubectl get pods -A | grep kro
# KRO was in 'kro' namespace, not 'kro-system'

# Restart the pod
kubectl delete pod -n kro <kro-pod-name>
```
**Lesson**: After applying RGDs and instances, check KRO controller logs. If no activity, restart the controller pod.

### 2. Azure Network Route Table Validation
**Error**: `RouteTableInvalidNextHop - Default route 0.0.0.0/0 has next hop of Internet`
**Root Cause**: AKS does not allow route tables with 0.0.0.0/0 routes pointing to "Internet"
**Valid Next Hop Types for AKS**:
- `VirtualAppliance` (for firewall/NVA routing)
- `VirtualNetworkGateway` (for VPN/ExpressRoute)
- `None` (drop traffic)
**Solution**:
```bash
# Option 1: Delete the problematic route
az network route-table route delete \
  --resource-group <rg> \
  --route-table-name <rt-name> \
  --name default-route

# Option 2: Remove route table from subnet (if testing)
az network vnet subnet update \
  --resource-group <rg> \
  --vnet-name <vnet> \
  --name <subnet> \
  --remove routeTable
```
**Reference**: https://aka.ms/aks/outboundtype

### 3. Azure Subscription Feature Registration
**Error**: `SubscriptionNotEnabledEncryptionAtHost`
**Root Cause**: RGD had `enableEncryptionAtHost: true` but subscription doesn't have the feature enabled
**Solution Options**:
```bash
# Option 1: Enable the feature (requires Owner/Contributor, takes 15+ min)
az feature register --namespace Microsoft.Compute --name EncryptionAtHost
az feature show --namespace Microsoft.Compute --name EncryptionAtHost
az provider register --namespace Microsoft.Compute

# Option 2: Disable in RGD for dev/test (simpler)
enableEncryptionAtHost: false
```
**Lesson**: For production RGDs, document required Azure features in README

### 4. Schema Field Validation - Making Required Fields Optional
**Problem**: UK8Sjobs required fields (`azureTenantId`, `asoClientId`) with UUID patterns failed validation when empty strings were passed
**Error**: `Invalid value: "": spec.azureTenantId in body should match '^[0-9a-f]{8}-...$'`
**Solution**: Make fields optional with empty default and update regex pattern
```yaml
# Before (FAILS with empty string)
azureTenantId: string | required=true pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

# After (ALLOWS empty string)
azureTenantId: string | default="" pattern="^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})?$"
```
**Key Changes**:
- Remove `required=true`
- Add `default=""`
- Wrap regex pattern in group with `?` to make it optional: `^(pattern)?$`

### 5. OIDC ConfigMap Creation
**Issue**: FederatedIdentityCredentials showed `ConfigMapNotFound` errors
**Explanation**: The OIDC ConfigMap is automatically created by ASO when:
1. ManagedCluster is successfully provisioned in Azure
2. `oidcIssuerProfile.enabled: true` is set
3. `operatorSpec.configMaps.oidcIssuerProfile` is configured

**Example**:
```yaml
spec:
  operatorSpec:
    configMaps:
      oidcIssuerProfile:
        name: oidc-${clusterName}
        key: issuer-url
  oidcIssuerProfile:
    enabled: true
```

**Lesson**: FederatedIdentityCredentials will remain in "ConfigMapNotFound" state until cluster is fully provisioned. This is normal and expected.

## Previously Documented Fixes (from earlier session)

### 6. Resource ID Naming Convention
**Error**: `naming convention violation: id Jobs is not a valid KRO resource id`
**Fix**: Use lowerCamelCase for all resource IDs
```yaml
# Before
- id: Jobs

# After
- id: jobs
```

### 7. Bash Variable Escaping in Scripts
**Error**: `found unknown resources in CEL expression: [[{AZURE_CLIENT_ID AZURE_CLIENT_ID}]]`
**Root Cause**: KRO parses `${VARIABLE}` syntax as CEL expressions before bash sees it
**Fix**: Use `$VARIABLE` without braces in bash scripts
```yaml
# Before (INCORRECT - KRO tries to parse as CEL)
command:
  - /bin/bash
  - -c
  - |
    az login -u "${AZURE_CLIENT_ID}"

# After (CORRECT - plain bash variable)
command:
  - /bin/bash
  - -c
  - |
    az login -u "$AZURE_CLIENT_ID"
```
**Rule**: In KRO YAML:
- Use `${schema.spec.field}` for KRO template expressions
- Use `$VARIABLE` (no braces) for bash variables in scripts

### 8. Reserved Keywords - namespace Field
**Error**: `failed to type-check template expression "schema.spec.namespace" at path "metadata.namespace"`
**Root Cause**: Field name `namespace` conflicts with Kubernetes `metadata.namespace`
**Fix**: Rename schema field to `targetNamespace`
```yaml
# Before
schema:
  spec:
    namespace: string | required=true

resources:
  - template:
      metadata:
        namespace: ${schema.spec.namespace}

# After
schema:
  spec:
    targetNamespace: string | required=true

resources:
  - template:
      metadata:
        namespace: ${schema.spec.targetNamespace}
```

## Debugging Workflow

### Step 1: Check RGD Status
```bash
kubectl get resourcegraphdefinitions
# All should show STATE: Active
```

### Step 2: Check RGD Conditions
```bash
kubectl describe resourcegraphdefinition <name>
# Look for validation errors in conditions
```

### Step 3: Check Instance Status
```bash
kubectl get <CustomResource> -n <namespace>
# Should show STATE and READY columns

kubectl describe <CustomResource> -n <namespace>
# Check Status.Conditions for errors
```

### Step 4: Check KRO Controller Logs
```bash
# Find KRO controller
kubectl get pods -A | grep kro

# Check logs for errors
kubectl logs -n kro <pod-name> --tail=100 | grep -i error
```

### Step 5: Check Child Resources
```bash
# List all child resources created by the instance
kubectl get <resource-type> -n <namespace>

# Check ASO resources for Azure errors
kubectl describe <aso-resource> -n <namespace>
```

### Step 6: Check Azure Resource Status
```bash
# For ASO resources, check Azure portal or CLI
az resource show --ids <resource-id>
```

## Best Practices Learned

1. **Start Simple**: Test RGDs with minimal child resources first, then add complexity
2. **Incremental Testing**: Apply RGDs one at a time, verify Active before applying instances
3. **KRO Controller Restarts**: Restart controller after major RGD changes or if reconciliation seems stuck
4. **Check Azure Prerequisites**: Verify networking, subscription features, and RBAC before deployment
5. **Optional vs Required**: Make fields optional when they're used for integrations that may not always be needed
6. **Pattern Matching**: Always test regex patterns with empty strings if field has default=""
7. **Status Monitoring**: Watch both KRO instance status and ASO resource status - they tell different parts of the story

## Files Modified in This Session

1. **uk8scluster.yaml** (line 344)
   - Changed: `enableEncryptionAtHost: true` → `false`

2. **uk8sjobs.yaml** (lines 32, 37-38, 43)
   - Made fields optional with empty defaults
   - Updated regex patterns to allow empty strings

3. **Azure Infrastructure**
   - Deleted route: `aks-route-table/default-route`

## Deployment Timeline

- RGDs applied: 3 definitions (UK8SCluster, UK8SFluxGitOps, UK8Sjobs)
- Instance created: UK8SCluster instance
- KRO controller restart: Required to begin reconciliation
- Child resources created: 13 resources in dependency order
- Azure provisioning: 10-15 minutes for AKS cluster
- Total time: ~20 minutes from instance creation to cluster ready

## Success Metrics

✅ All RGDs Active
✅ UK8SCluster instance: ACTIVE, READY=True
✅ ResourceGroup created in Azure
✅ ManagedCluster provisioning in Azure
✅ User Assigned Identities created
✅ Federated Identity Credentials waiting for OIDC issuer (expected)
✅ UK8Sjobs child resource created
✅ UK8SFluxGitOps child resource created

## Next Steps After Cluster Provisioning

1. OIDC ConfigMap will be auto-created by ASO
2. Federated Identity Credentials will become Ready
3. Flux Extension will be installed
4. Flux configurations will sync from Git
5. Post-deployment jobs will execute

## References

- KRO Docs: https://kro.run
- ASO Docs: https://azure.github.io/azure-service-operator/
- AKS Outbound Types: https://aka.ms/aks/outboundtype
- Azure Feature Registration: https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/preview-features
