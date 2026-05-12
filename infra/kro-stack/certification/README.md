# UK8S Cluster Certification Workflow

Automated certification workflow that validates UK8S cluster deployments as part of the KRO stack. The certification runs automatically when a cluster is deployed and can be scheduled for recurring validation.

## What Gets Tested

The certification workflow validates **6 critical sections** of your UK8S cluster:

### 1. Configuration Validation
**What it tests:**
- UK8SCluster custom resource exists and is accessible
- Instance YAML is valid and retrievable
- Kubernetes version is specified correctly

**Why it matters:**
Ensures the base configuration is correct before validating dependent resources.

### 2. KRO Resource Validation
**What it tests:**
- ResourceGraphDefinitions are `Active`:
  - `uk8scluster.kro.run`
  - `uk8sjobs.kro.run`
  - `uk8sfluxgitops.kro.run`
- UK8SCluster instance exists in target namespace
- Instance state is `ACTIVE`
- Instance Ready condition is `True`

**Why it matters:**
Validates that KRO is properly orchestrating all cluster resources and the cluster stack is healthy.

### 3. ASO (Azure Service Operator) Resource Validation
**What it tests:**
- ResourceGroup status is `Ready`
- ManagedCluster (AKS) status is `Ready`

**Why it matters:**
Confirms Azure infrastructure is provisioned correctly and operational.

### 4. Flux GitOps Validation
**What it tests:**
- `flux-system` namespace exists
- Flux controllers are running and `Available`:
  - `source-controller`
  - `kustomize-controller`
  - `helm-controller`

**Why it matters:**
Ensures GitOps continuous deployment is operational for managing cluster configuration.

### 5. Cluster Connectivity Validation
**What it tests:**
- Kubernetes API server is accessible
- All nodes are in `Ready` state
- Node count matches expected configuration

**Why it matters:**
Verifies the cluster is accessible and all infrastructure is healthy.

### 6. Security & Compliance Validation
**What it tests:**
- Workload Identity service accounts are configured
- Azure Policy addon is installed (if applicable)

**Why it matters:**
Confirms security best practices are enforced.

---

## How It Works

### Automatic Certification Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User Applies UK8SCluster Instance                            │
│    kubectl apply -f my-cluster.yaml                             │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. KRO Creates Resources (via ResourceGraphDefinition)          │
│    ├─ Azure Resources (ResourceGroup, ManagedCluster, etc.)     │
│    ├─ Flux GitOps Resources                                     │
│    ├─ WorkflowTemplate (certify-<cluster-name>)                 │
│    ├─ CronWorkflow (weekly-cert-<cluster-name>)                 │
│    └─ Job (trigger-cert-<cluster-name>) ◄── AUTOMATIC TRIGGER   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Trigger Job Starts                                           │
│    ├─ Waits for WorkflowTemplate to exist                       │
│    ├─ Waits for UK8SCluster state = ACTIVE                      │
│    └─ Submits certification Workflow                            │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Certification Workflow Executes (DAG)                        │
│                                                                  │
│    validate-config                                              │
│         ▼                                                        │
│    validate-kro                                                 │
│         ▼                                                        │
│    validate-aso                                                 │
│         ├──────────┬─────────────┐                              │
│         ▼          ▼             ▼                              │
│    validate-flux   validate-connectivity   validate-security   │
│         └──────────┴─────────────┘                              │
│                    ▼                                            │
│            aggregate-results                                    │
│                    ▼                                            │
│         generate-final-report                                   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Results Available                                            │
│    ├─ Workflow Status: Succeeded/Failed                         │
│    ├─ Certification Report (JSON artifact)                      │
│    └─ Logs with validation details                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Resources Created

When you deploy a UK8SCluster, the following certification resources are automatically created:

### 1. WorkflowTemplate
**Name:** `certify-<cluster-name>`
**Purpose:** Reusable workflow definition with pre-configured parameters
**Location:** `argo` namespace

**Key Features:**
- All parameters pre-filled from cluster spec (clusterName, resourceGroup, etc.)
- No manual configuration required
- Uses `bitnami/kubectl:latest` for all validations (lightweight, fast)

### 2. CronWorkflow
**Name:** `weekly-cert-<cluster-name>`
**Purpose:** Schedule automatic recurring certification
**Schedule:** Every Sunday at 2 AM UTC (configurable)
**Default State:** Suspended (enable manually when ready)

**To enable weekly certification:**
```bash
kubectl patch cronworkflow weekly-cert-<cluster-name> -n argo \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/suspend", "value": false}]'
```

### 3. Job (Trigger)
**Name:** `trigger-cert-<cluster-name>`
**Purpose:** Automatically trigger initial certification after cluster deployment
**TTL:** 300 seconds (auto-cleanup after completion)
**Image:** `bitnami/kubectl:latest`

**What it does:**
1. Polls for WorkflowTemplate creation (max 5 minutes)
2. Waits for UK8SCluster status = `ACTIVE` (max 30 minutes)
3. Submits certification workflow using kubectl
4. Self-destructs after 5 minutes

---

## Usage

### View Automatically Triggered Workflow

After deploying a cluster, check the automatic certification:

```bash
# List all workflows (automatic ones have 'auto' in the name)
argo list -n argo | grep certify-<cluster-name>-auto

# Get workflow details
argo get -n argo certify-<cluster-name>-auto-xxxxx

# View logs
argo logs -n argo certify-<cluster-name>-auto-xxxxx
```

### Manual Certification

Trigger certification manually at any time:

```bash
argo submit -n argo \
  --from workflowtemplate/certify-<cluster-name> \
  --watch
```

**Note:** Manual runs won't have the `-auto-` suffix in the name.

### View Certification Report

Extract the certification report from workflow logs:

```bash
argo logs -n argo <workflow-name> | grep -A 20 "CERTIFICATION REPORT"
```

**Example output:**
```
============================================================
UK8S CLUSTER CERTIFICATION REPORT
============================================================
{
  "cluster": "my-cluster",
  "namespace": "uk8s-nextgen",
  "environment": "dev",
  "timestamp": "2025-11-13T07:38:18.292358Z",
  "workflow": "certify-my-cluster-auto-abc123",
  "certification": {
    "status": "CERTIFIED",
    "workflow_name": "certify-my-cluster"
  }
}
============================================================
✅ CLUSTER CERTIFICATION COMPLETE
============================================================
```

---

## Architecture Details

### Workflow DAG Structure

The certification workflow uses a DAG (Directed Acyclic Graph) for efficient parallel execution:

```
validate-config (5s)
    ↓
validate-kro (4s)
    ↓
validate-aso (5s)
    ↓
    ├─→ validate-flux (5s) ────────┐
    ├─→ validate-connectivity (5s) ├─→ aggregate-results (3s)
    └─→ validate-security (3s) ────┘
                                    ↓
                         generate-final-report (3s)
```

**Total Duration:** ~1 minute 10 seconds

### Validation Scripts

All validations use **bash scripts** with `bitnami/kubectl:latest`:

**Benefits:**
- ✅ No Python dependencies or package installations
- ✅ Faster execution (3x faster than Python-based validation)
- ✅ Smaller container images (~120MB vs ~300MB)
- ✅ Consistent with Kubernetes best practices

**Example validation pattern:**
```bash
#!/bin/bash
set -e
PASSED=0
FAILED=0

if kubectl get <resource> <name> -n <namespace> &>/dev/null; then
  STATUS=$(kubectl get <resource> <name> -n <namespace> -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
  if [[ "$STATUS" == "True" ]]; then
    echo "✓ Resource is ready"
    PASSED=$((PASSED+1))
  else
    echo "✗ Resource not ready"
    FAILED=$((FAILED+1))
  fi
fi

echo "Summary: $PASSED passed, $FAILED failed"
```

---

## RBAC Requirements

The certification workflow requires these permissions:

**ServiceAccount:** `argo-workflow-executor` (in `argo` namespace)

**ClusterRole:** `uk8s-certification-role`
- Read access to:
  - UK8SCluster, UK8SJobs, UK8SFluxGitOps (kro.run)
  - ResourceGroups, ManagedClusters (ASO)
  - Flux resources (GitRepository, Kustomization, HelmRelease)
  - Istio resources (VirtualService, Gateway, etc.)
  - Core K8s resources (Namespaces, Pods, Services, etc.)

**Applied automatically:** RBAC is created via `kro-stack/certification/rbac-uk8s-certification.yaml`

---

## Troubleshooting

### Certification Failed

**Check workflow status:**
```bash
argo get -n argo <workflow-name>
```

**View detailed logs:**
```bash
argo logs -n argo <workflow-name>
```

**Common issues:**
- ASO resources not ready → Check Azure portal for provisioning status
- Flux not installed → Verify Flux GitOps is deployed
- RBAC permissions → Ensure `uk8s-certification-role` exists

### Trigger Job Failed

**Check trigger job logs:**
```bash
kubectl logs -n argo -l job-name=trigger-cert-<cluster-name>
```

**Common issues:**
- Timeout waiting for cluster → Cluster provisioning taking longer than 30 minutes
- WorkflowTemplate not found → Check if RGD applied correctly

### No Automatic Certification

**Verify resources created:**
```bash
# Check WorkflowTemplate
kubectl get workflowtemplate -n argo | grep certify-<cluster-name>

# Check trigger Job
kubectl get job -n argo | grep trigger-cert-<cluster-name>

# Check UK8SCluster status
kubectl get uk8scluster <cluster-name> -n <namespace> -o yaml
```

---

## Customization

### Change Certification Schedule

Edit the CronWorkflow schedule:

```bash
kubectl edit cronworkflow weekly-cert-<cluster-name> -n argo
```

Change `spec.schedule`:
```yaml
spec:
  schedule: "0 6 * * 1"  # Every Monday at 6 AM
  timezone: "America/New_York"
```

### Add Custom Validations

To add custom validation steps, edit the ResourceGraphDefinition:

```yaml
# In kro-stack/definitions/uk8scluster.yaml
- name: validate-custom
  template: validate-custom-requirement
  dependencies: [validate-security]
```

Then add the validation template:

```yaml
- name: validate-custom-requirement
  script:
    image: bitnami/kubectl:latest
    command: [bash]
    source: |
      set -e
      echo "=== Custom Validation ==="
      # Your validation logic here
      echo "✅ Custom validation complete"
```

### Disable Automatic Trigger

To prevent automatic certification on new cluster deployments, remove the `certificationTrigger` resource from the RGD:

```yaml
# Comment out or remove this section in uk8scluster.yaml:
# - id: certificationTrigger
#   template:
#     apiVersion: batch/v1
#     kind: Job
#     ...
```

---

## Multi-Cluster Deployment

When deploying multiple clusters, each gets its own isolated certification resources:

```
Cluster: dev-cluster
├─ WorkflowTemplate: certify-dev-cluster
├─ CronWorkflow: weekly-cert-dev-cluster
└─ Job: trigger-cert-dev-cluster (auto-cleaned up)

Cluster: staging-cluster
├─ WorkflowTemplate: certify-staging-cluster
├─ CronWorkflow: weekly-cert-staging-cluster
└─ Job: trigger-cert-staging-cluster (auto-cleaned up)

Cluster: prod-cluster
├─ WorkflowTemplate: certify-prod-cluster
├─ CronWorkflow: weekly-cert-prod-cluster
└─ Job: trigger-cert-prod-cluster (auto-cleaned up)
```

**List all certification workflows:**
```bash
argo list -n argo | grep certify
```

**List all certification schedules:**
```bash
kubectl get cronworkflow -n argo | grep weekly-cert
```

---

## Integration with CI/CD

### Azure DevOps Pipeline

```yaml
- task: Bash@3
  displayName: 'Wait for Certification'
  inputs:
    targetType: 'inline'
    script: |
      # Wait for automatic certification to complete
      WORKFLOW=$(kubectl get workflows -n argo -l kro.run/cluster=$(clusterName),kro.run/trigger=automatic --sort-by=.metadata.creationTimestamp -o name | tail -1)

      echo "Waiting for certification: $WORKFLOW"
      kubectl wait --for=condition=Completed $WORKFLOW -n argo --timeout=10m

      # Check if succeeded
      STATUS=$(kubectl get $WORKFLOW -n argo -o jsonpath='{.status.phase}')
      if [[ "$STATUS" != "Succeeded" ]]; then
        echo "Certification failed!"
        exit 1
      fi
      echo "✅ Cluster certified successfully"
```

### GitHub Actions

```yaml
- name: Wait for Cluster Certification
  run: |
    WORKFLOW=$(kubectl get workflows -n argo \
      -l kro.run/cluster=${{ env.CLUSTER_NAME }},kro.run/trigger=automatic \
      --sort-by=.metadata.creationTimestamp -o name | tail -1)

    kubectl wait --for=condition=Completed $WORKFLOW -n argo --timeout=10m

    STATUS=$(kubectl get $WORKFLOW -n argo -o jsonpath='{.status.phase}')
    if [[ "$STATUS" != "Succeeded" ]]; then
      echo "::error::Certification failed"
      exit 1
    fi
```

---

## Performance

**Typical execution times:**
- Configuration validation: 5 seconds
- KRO validation: 4 seconds
- ASO validation: 5 seconds
- Connectivity validation: 5 seconds
- Flux validation: 5 seconds
- Security validation: 3 seconds
- Result aggregation: 3 seconds

**Total:** ~1 minute 10 seconds

**Resource usage:**
- CPU: ~100m per validation step
- Memory: ~100Mi per validation step
- Total workflow: ~2 seconds CPU, ~53 seconds memory

---

## Files Reference

```
kro-stack/
├── certification/
│   ├── README.md                          # This file
│   ├── QUICKSTART.md                      # Quick start guide
│   ├── rbac-uk8s-certification.yaml       # RBAC configuration
│   └── deploy-certification.sh            # Standalone deployment script
├── definitions/
│   ├── uk8scluster.yaml                   # Main RGD (includes certification)
│   ├── uk8scluster-certification-addon.yaml  # Certification addon (reference)
│   └── INTEGRATION-GUIDE.md               # Integration documentation
└── instances/
    └── dev/
        └── simple-cluster-example.yaml    # Example cluster instance
```

---

## Support

**View workflow in Argo UI:**
```bash
kubectl port-forward -n argo svc/argo-server 2746:2746
# Visit: https://localhost:2746
```

**Debug workflow:**
```bash
# Get workflow details
argo get -n argo <workflow-name>

# View specific step logs
argo logs -n argo <workflow-name> <step-name>

# View all logs
argo logs -n argo <workflow-name>
```

**Additional documentation:**
- [Argo Workflows Docs](https://argoproj.github.io/argo-workflows/)
- [KRO Documentation](https://kro.run/docs/)
- [CERTIFICATION_CHECKLIST.md](../CERTIFICATION_CHECKLIST.md)

---

## Summary

The UK8S certification workflow provides:
- ✅ **Automatic validation** - Runs automatically when cluster is deployed
- ✅ **Comprehensive testing** - Validates 6 critical sections
- ✅ **Fast execution** - Completes in ~70 seconds using bash/kubectl
- ✅ **Zero configuration** - Parameters pre-filled from cluster spec
- ✅ **GitOps friendly** - Integrated directly into KRO stack
- ✅ **Multi-cluster support** - Each cluster gets its own workflow
- ✅ **Scheduling** - Optional weekly recurring certification
- ✅ **CI/CD ready** - Easy integration with pipelines

**Deploy a cluster, get automatic certification. It's that simple.**
