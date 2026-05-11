# Certification Workflow Troubleshooting Guide

## Issues Resolved

### 1. CRD Ownership Conflict

**Problem**: The `uk8sclusterpublic.kro.run` ResourceGraphDefinition was stuck in `Inactive` state with error:
```
conflict detected: CRD uk8sclusterpublics.kro.run has ownership by another ResourceGraphDefinition
```

**Root Cause**: The CRD label `kro.run/resource-graph-definition-id` referenced an old RGD UID that no longer matched the current RGD.

**Solution**:
```bash
# Get current RGD UID
CURRENT_UID=$(kubectl get resourcegraphdefinition uk8sclusterpublic.kro.run -o jsonpath='{.metadata.uid}')

# Update CRD label to match
kubectl label crd uk8sclusterpublics.kro.run \
  kro.run/resource-graph-definition-id=$CURRENT_UID --overwrite

# Restart KRO controller
kubectl rollout restart deployment kro -n kro
```

**Result**: RGD transitioned from `Inactive` to `Active`, allowing instances to be processed.

---

### 2. ResourceGroup Deletion Conflict

**Problem**: Second cluster instance (`uk8s-tsshared-weu-gt025-int-dev-public2`) was blocked with:
```
Owner "at39473-weu-dev-public, Group/Kind: resources.azure.com/ResourceGroup" cannot be found
```

**Root Cause**: Both cluster instances were configured to use the same ResourceGroup name (`at39473-weu-dev-public`). The first instance was being deleted, which triggered deletion of the ResourceGroup. Azure blocks resource creation in a ResourceGroup that's being deleted.

**Solution**:
```bash
# Update the second instance to use a different ResourceGroup
kubectl patch uk8sclusterpublic uk8s-tsshared-weu-gt025-int-dev-public2 \
  -n uk8s-nextgen --type=merge \
  -p '{"spec":{"resourceGroup":"at39473-weu-dev-public2"}}'
```

**Result**:
- New ResourceGroup created immediately and became Ready
- ManagedCluster found its owner and started reconciling
- Cluster instance transitioned to `ACTIVE` and `Ready`

---

### 3. Argo Workflows Minio Artifact Storage Failure

**Problem**: All certification workflows failed with:
```
Error (exit code 64): failed to put file: Get "http://minio:9000/my-bucket/?location=":
dial tcp: lookup minio: no such host
```

**Root Cause**: Argo Workflows was configured globally to use Minio for artifact storage, but Minio wasn't deployed. Even with `archiveLogs: false`, the workflow controller tried to save logs.

**Solution 1 - Remove Global Artifact Repository**:
```bash
# Remove artifact repository requirement from global config
kubectl patch configmap workflow-controller-configmap -n argo \
  --type=json -p='[{"op": "remove", "path": "/data/artifactRepository"}]'

# Restart workflow controller
kubectl rollout restart deployment argo-argo-workflows-workflow-controller -n argo
```

**Solution 2 - Disable Artifacts in Workflow Template**:
```yaml
spec:
  archiveLogs: false
  artifactGC:
    strategy: Never
  podGC:
    strategy: OnWorkflowSuccess
```

**Result**: Workflows no longer attempt to save artifacts to Minio.

---

### 4. Duplicate Workflow Controllers

**Problem**: Workflows appeared stuck after completing tasks, not transitioning to next phases.

**Root Cause**: Two workflow controller deployments running simultaneously, causing conflicts:
- `argo-argo-workflows-workflow-controller` (from Helm)
- `workflow-controller` (standalone)

**Solution**:
```bash
# List controllers
kubectl get deployment -n argo | grep workflow-controller

# Scale down duplicate
kubectl scale deployment workflow-controller -n argo --replicas=0

# Keep only: argo-argo-workflows-workflow-controller
```

**Result**: Single controller properly manages workflow state transitions.

---

## Enhancements Added

### System Components Validation

Added comprehensive validation task that checks if critical system namespaces exist and their pods are healthy:

**Components Checked**:
- **ASO** (Azure Service Operator) - `azureserviceoperator-system`
- **KRO** (Kubernetes Resource Orchestrator) - `kro`
- **Cert-Manager** - `cert-manager`
- **External DNS** - `external-dns`
- **External Secrets** - `external-secrets`
- **Kyverno** - `kyverno`
- **Reloader** - `reloader`

**Validation Logic**:
```bash
check_component() {
  local NS=$1
  local COMPONENT_NAME=$2
  local LABEL_SELECTOR=$3

  if kubectl get namespace $NS &>/dev/null; then
    echo "✓ Namespace $NS exists"

    TOTAL_PODS=$(kubectl get pods -n $NS -l "$LABEL_SELECTOR" --no-headers | wc -l)
    RUNNING_PODS=$(kubectl get pods -n $NS -l "$LABEL_SELECTOR" \
      --field-selector=status.phase=Running --no-headers | wc -l)

    if [ $RUNNING_PODS -eq $TOTAL_PODS ] && [ $TOTAL_PODS -gt 0 ]; then
      echo "✓ All $COMPONENT_NAME pods are running"
    else
      echo "✗ Some $COMPONENT_NAME pods are not running"
    fi
  else
    echo "⚠ Namespace $NS not found (component may not be installed)"
  fi
}
```

**Integration**: Added to certification DAG after ASO validation:
```yaml
- name: validate-system-components
  template: validate-system-components
  dependencies: [validate-aso]
```

---

## Warnings Explained

### "CronWorkflow is SUSPENDED"

**Status**: ⚠️ Warning (Expected)

**Explanation**: The weekly certification CronWorkflow starts in `suspended: true` state by design. This allows you to:
- Review the cluster before enabling automatic weekly certifications
- Test manual certifications first
- Control when recurring certifications begin

**To Enable Weekly Certifications**:
```bash
# Unsuspend the CronWorkflow
kubectl patch cronworkflow weekly-cert-<cluster-name> -n argo \
  --type=merge -p '{"spec":{"suspend":false}}'
```

### "Workflow Status: Running"

**Status**: ⚠️ Warning (Transient)

**Explanation**: This indicates the certification workflow is currently executing validation tasks. It's normal to see this during:
- Initial 60-second cluster stabilization wait
- Validation task execution (2-5 minutes total)

**Expected Timeline**:
1. Wait for cluster ready: ~60 seconds (if cluster already healthy)
2. Validate config: ~5 seconds
3. Validate KRO: ~10 seconds
4. Validate ASO: ~10 seconds
5. Validate Flux: ~10 seconds
6. Validate system components: ~15 seconds
7. Validate connectivity: ~5 seconds
8. Validate security: ~5 seconds
9. Validate API access: ~5 seconds
10. Aggregate results: ~5 seconds
11. Generate report: ~5 seconds

**Total**: ~2-3 minutes for a healthy cluster

---

## Verification Commands

### Check Certification Workflow Status
```bash
./kro-stack/scripts/check-certification-workflow.sh <cluster-name>
```

### Check Cluster Health
```bash
# Check UK8SClusterPublic instance
kubectl get uk8sclusterpublic <instance-name> -n <namespace>

# Check ManagedCluster
kubectl get managedcluster <cluster-name> -n <namespace>

# Check ResourceGroup
kubectl get resourcegroup <rg-name> -n <namespace>
```

### Check RGD Status
```bash
# List all RGDs
kubectl get resourcegraphdefinition

# Check specific RGD
kubectl get resourcegraphdefinition uk8sclusterpublic.kro.run -o yaml

# Check CRD ownership
kubectl get crd uk8sclusterpublics.kro.run \
  -o jsonpath='{.metadata.labels.kro\.run/resource-graph-definition-id}'
```

### Check Argo Workflows
```bash
# List recent workflows
kubectl get workflow -n argo -l kro.run/cluster=<cluster-name> \
  --sort-by=.metadata.creationTimestamp

# Check specific workflow
kubectl get workflow <workflow-name> -n argo

# View workflow logs
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name>

# Check workflow controller
kubectl get pods -n argo -l app=workflow-controller
```

### Manual Workflow Trigger
```bash
cat <<EOF | kubectl create -f -
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: certify-<cluster-name>-manual-
  namespace: argo
  labels:
    kro.run/cluster: <cluster-name>
    kro.run/trigger: manual
spec:
  workflowTemplateRef:
    name: certify-<cluster-name>
EOF
```

---

## Common Issues

### Workflow Stuck in "Running"

**Check For**:
1. Multiple workflow controllers running
2. Minio artifact storage errors
3. RBAC permission issues

**Debug**:
```bash
# Check events
kubectl describe workflow <workflow-name> -n argo | grep -A20 "Events:"

# Check controller logs
kubectl logs -n argo -l app=workflow-controller --tail=100

# Check for errors in workflow
kubectl get workflow <workflow-name> -n argo -o json | \
  jq '.status.nodes[] | select(.phase == "Error" or .phase == "Failed")'
```

### Instance Not Progressing

**Check For**:
1. RGD in Inactive state
2. CRD ownership conflicts
3. ResourceGroup conflicts

**Debug**:
```bash
# Check RGD state
kubectl get resourcegraphdefinition uk8sclusterpublic.kro.run

# Check instance status
kubectl get uk8sclusterpublic <instance-name> -n <namespace> -o yaml | grep -A20 status

# Check KRO logs
kubectl logs -n kro deployment/kro --tail=100
```

### RBAC Permission Errors

**Error Example**:
```
User "system:serviceaccount:argo:argo-workflow-executor" cannot get resource "uk8sclusterpublics"
```

**Solution**:
```bash
# Apply RBAC configuration
kubectl apply -f kro-stack/definitions/certification-rbac.yaml

# Verify permissions
kubectl auth can-i get uk8sclusterpublics \
  --as=system:serviceaccount:argo:argo-workflow-executor -n <namespace>
```

---

## Files Modified

1. **uk8s-certification.yaml**
   - Added system components validation task
   - Disabled artifact archiving
   - Added pod GC configuration

2. **certification-rbac.yaml**
   - Comprehensive RBAC for certification workflows
   - Read access to KRO, ASO, Flux resources

3. **Argo ConfigMap** (`workflow-controller-configmap`)
   - Removed Minio artifact repository requirement

---

## Best Practices

1. **Always check RGD status** before creating instances
2. **Use unique ResourceGroup names** for each cluster instance
3. **Monitor KRO logs** when troubleshooting instance creation
4. **Verify RBAC** is applied before running workflows
5. **Clean up failed workflows** to avoid clutter
6. **Use manual triggers** for testing before enabling CronWorkflow

---

**Updated**: 2025-11-21
**Version**: 2.1
**Status**: Production Ready
