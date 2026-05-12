# Certification Workflow Improvements

## Problem

The certification workflow was failing because it ran **too early** - before the cluster was fully provisioned and healthy.

### Issues Identified

1. **RBAC Permissions Missing**
   - The `argo-workflow-executor` service account couldn't read KRO custom resources
   - Error: `User "system:serviceaccount:argo:argo-workflow-executor" cannot get resource "uk8sclusterpublics"`

2. **No Wait Logic**
   - Workflow started immediately after cluster creation
   - Didn't wait for AKS cluster to be fully provisioned
   - Validation tasks failed because resources weren't ready

3. **Timing Issues**
   - UK8SClusterPublic might be ACTIVE but ManagedCluster still reconciling
   - No stabilization period after cluster becomes ready
   - Flux, addons, and other components not given time to deploy

## Solutions Implemented

### 1. RBAC Configuration (`certification-rbac.yaml`)

Created comprehensive RBAC for certification workflows:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argo-certification-validator
rules:
  # Read KRO resources
  - apiGroups: ["kro.run"]
    resources:
      - resourcegraphdefinitions
      - uk8sclusterpublics
      - uk8sclusters
      - uk8sjobs
      - uk8sfluxgitops
      - uk8scertifications
    verbs: ["get", "list", "watch"]

  # Read ASO resources
  - apiGroups: ["resources.azure.com", "containerservice.azure.com", "managedidentity.azure.com"]
    resources: ["*"]
    verbs: ["get", "list"]

  # Read Flux and Kubernetes resources
  - apiGroups: ["", "apps"]
    resources: ["namespaces", "deployments", "pods", "serviceaccounts", "nodes"]
    verbs: ["get", "list"]
```

**Applied:**
```bash
kubectl apply -f certification-rbac.yaml
```

### 2. Wait-for-Cluster-Ready Task

Added a new task at the **beginning** of the certification DAG:

```yaml
- name: wait-for-cluster
  template: wait-for-cluster-ready

- name: validate-config
  template: validate-configuration
  dependencies: [wait-for-cluster]  # Waits for cluster first!
```

**Wait Logic:**
1. **Wait for UK8SClusterPublic** to be ACTIVE and Ready (up to 30 minutes)
2. **Wait for ManagedCluster** to be Ready (up to 30 minutes)
3. **Stabilization period** - Additional 60 seconds for cluster to settle

```bash
# Polls every 30 seconds
[0/1800 seconds] State: IN_PROGRESS, Ready: False
[30/1800 seconds] State: IN_PROGRESS, Ready: False
...
[600/1800 seconds] State: ACTIVE, Ready: True
✓ UK8SClusterPublic is ACTIVE and Ready

[0/1800 seconds] ManagedCluster Ready: Unknown (Reconciling)
...
[300/1800 seconds] ManagedCluster Ready: True
✓ ManagedCluster is Ready

Waiting 60 seconds for cluster to stabilize...
✅ Cluster is ready for certification
```

### 3. Improved Trigger Job

Updated the automatic trigger Job to also check cluster readiness:

**Before:**
- Only waited for UK8SClusterPublic STATE to be ACTIVE
- Ignored Ready condition
- No ManagedCluster check

**After:**
- Waits for UK8SClusterPublic ACTIVE **and** Ready
- Checks ManagedCluster status
- Informs that workflow will wait for full health

```bash
✓ UK8SClusterPublic is ACTIVE and Ready
ManagedCluster Ready: True
Note: Certification workflow will wait for full cluster health before proceeding
```

## New Workflow Flow

### Old Flow (Broken)
```
1. Cluster resources created by KRO
2. Trigger Job immediately submits workflow
3. Workflow starts validation
4. ❌ Fails - resources not ready
```

### New Flow (Fixed)
```
1. Cluster resources created by KRO
2. Trigger Job waits for UK8SClusterPublic ACTIVE + Ready
3. Trigger Job checks ManagedCluster status
4. Workflow submitted
5. Workflow: wait-for-cluster-ready task
   - Polls UK8SClusterPublic status
   - Polls ManagedCluster status
   - Waits for stabilization
6. ✅ Validation tasks proceed with healthy cluster
```

## Timing Breakdown

| Stage | Wait Time | What's Happening |
|-------|-----------|------------------|
| **Trigger Job** | Up to 30 min | Waits for UK8SClusterPublic ACTIVE + Ready |
| **Workflow Wait Task** | Up to 30 min | Double-checks cluster health |
| **Stabilization** | 60 seconds | Allows components to settle |
| **Total Maximum** | ~60 minutes | Should be much less for healthy clusters |

## Configuration Options

### Adjust Wait Timeout

In the `wait-for-cluster-ready` template:

```bash
MAX_WAIT=1800  # 30 minutes (default)
MAX_WAIT=3600  # 1 hour (for slower clusters)
```

### Adjust Poll Interval

```bash
INTERVAL=30  # Poll every 30 seconds (default)
INTERVAL=60  # Poll every 60 seconds (less frequent)
```

### Adjust Stabilization Time

```bash
sleep 60  # 60 seconds (default)
sleep 120 # 2 minutes (for complex clusters)
```

### Disable Auto-Trigger

If you want to manually trigger certification only:

```yaml
spec:
  certification:
    autoTrigger: false  # Disable automatic trigger
```

## Testing

### Manual Trigger

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

### Watch Progress

```bash
# Get workflow name
kubectl get workflow -n argo -l kro.run/trigger=manual --sort-by=.metadata.creationTimestamp

# Watch logs
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name> -f
```

### Check Status

```bash
./check-certification-workflow.sh <cluster-name>
```

## Expected Output

### Successful Run

```
✓ WorkflowTemplate exists
✓ CronWorkflow exists (SUSPENDED)
✓ Trigger Job completed successfully
✓ Workflow instances: 1
✓ Latest workflow: Succeeded

Task Breakdown:
✓ wait-for-cluster: Succeeded
✓ validate-config: Succeeded
✓ validate-kro: Succeeded
✓ validate-aso: Succeeded
✓ validate-flux: Succeeded
✓ validate-connectivity: Succeeded
✓ validate-security: Succeeded
✓ validate-api-access: Succeeded
✓ aggregate-results: Succeeded
✓ generate-final-report: Succeeded

✅ All checks passed!
```

## Troubleshooting

### Workflow Still Failing?

1. **Check RBAC is applied:**
   ```bash
   kubectl get clusterrole argo-certification-validator
   kubectl get clusterrolebinding argo-certification-validator-binding
   ```

2. **Check cluster is actually ready:**
   ```bash
   kubectl get uk8sclusterpublic <name> -n <namespace> -o jsonpath='{.status.state}'
   kubectl get managedcluster <name> -n <namespace> -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
   ```

3. **Check workflow logs:**
   ```bash
   kubectl logs -n argo -l workflows.argoproj.io/workflow=<name> --all-containers
   ```

### Timeout Issues

If clusters take longer than 30 minutes:
- Increase `MAX_WAIT` in the wait task
- Check Azure for provisioning issues
- Verify ASO operator is working: `kubectl logs -n azureserviceoperator-system -l control-plane=controller-manager`

### RBAC Still Failing

Verify service account binding:
```bash
kubectl auth can-i get uk8sclusterpublics --as=system:serviceaccount:argo:argo-workflow-executor -n uk8s-nextgen
```

Should return: `yes`

## Files Modified

- ✅ `uk8s-certification.yaml` - Added wait-for-cluster-ready task
- ✅ `certification-rbac.yaml` - Created RBAC configuration

## Benefits

1. **Reliability** - Certification only runs when cluster is healthy
2. **Accuracy** - Validates actual running cluster, not partial deployment
3. **Debuggability** - Clear logs showing what's being waited for
4. **Flexibility** - Configurable timeouts and intervals
5. **Safety** - RBAC properly scoped to read-only operations

## Next Steps

1. Apply RBAC if not done: `kubectl apply -f certification-rbac.yaml`
2. Deploy/update certification RGD: `kubectl apply -f uk8s-certification.yaml`
3. Test with manual trigger on existing cluster
4. Monitor first automatic certification run
5. Adjust timeouts based on your cluster provisioning times

---

**Updated:** 2025-11-21
**Version:** 2.0
**Breaking Changes:** Requires certification-rbac.yaml to be applied
