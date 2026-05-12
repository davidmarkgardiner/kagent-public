# UK8S Cluster Certification System

The UK8S certification system provides automated validation and compliance checking for AKS clusters deployed through KRO (Kubernetes Resource Orchestrator).

## Overview

The certification system is externalized into its own ResourceGraphDefinition (`uk8s-certification.yaml`) and can be referenced from any cluster definition, making it reusable and maintainable.

## Architecture

```
uk8sclusterpublic.kro.run (or uk8sclusterprivate.kro.run)
    └── UK8SCertification instance
        ├── WorkflowTemplate (certify-{cluster-name})
        │   ├── validate-configuration
        │   ├── validate-kro-resources
        │   ├── validate-aso-resources
        │   ├── validate-flux-gitops
        │   ├── validate-cluster-connectivity
        │   ├── validate-security-compliance
        │   ├── validate-api-access-type
        │   └── aggregate-certification
        ├── CronWorkflow (weekly-cert-{cluster-name})
        └── Job (trigger-cert-{cluster-name})
```

## Files

- **`uk8s-certification.yaml`** - The main ResourceGraphDefinition for the certification system
- **`uk8scluster-public.yaml`** - References the certification system
- **`uk8scluster-private.yaml`** - (Future) Will also reference the certification system

## Usage

### In Cluster Definitions

Reference the certification system from your cluster RGD:

```yaml
resources:
  - id: certification
    template:
      apiVersion: kro.run/v1alpha1
      kind: UK8SCertification
      metadata:
        name: cert-${schema.spec.clusterName}
        namespace: ${schema.spec.targetNamespace}
      spec:
        clusterName: ${schema.spec.clusterName}
        resourceGroup: ${schema.spec.resourceGroup}
        targetNamespace: ${schema.spec.targetNamespace}
        instanceName: ${schema.metadata.name}
        subscriptionId: ${schema.spec.subscriptionId}
        environment: ${schema.spec.environment}
        clusterType: "PUBLIC"  # or "PRIVATE"
        certification:
          timeout: 1800
          schedule: "0 2 * * 0"  # Weekly, Sunday 2 AM UTC
          suspended: true  # Start suspended
          autoTrigger: true  # Trigger after cluster creation
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `clusterName` | string | required | Name of the AKS cluster |
| `resourceGroup` | string | required | Azure resource group |
| `targetNamespace` | string | required | K8s namespace for cluster resources |
| `instanceName` | string | required | UK8SClusterPublic instance name |
| `subscriptionId` | string | required | Azure subscription ID |
| `environment` | string | required | Environment (dev/staging/production) |
| `clusterType` | string | required | Cluster type (PUBLIC/PRIVATE) |
| `certification.timeout` | integer | 1800 | Certification timeout (seconds) |
| `certification.schedule` | string | "0 2 * * 0" | Cron schedule for weekly certification |
| `certification.suspended` | boolean | true | Start CronWorkflow suspended |
| `certification.autoTrigger` | boolean | true | Auto-trigger initial certification |

## Validation Checks

The certification workflow performs the following validations:

### 1. Configuration Validation
- Verifies UK8SClusterPublic instance exists and is readable
- Validates Kubernetes version specification

### 2. KRO Resource Validation
- Checks all ResourceGraphDefinitions are Active
- Verifies UK8SClusterPublic instance state is ACTIVE
- Confirms Ready condition is True

### 3. ASO Resource Validation
- Validates ResourceGroup is ready
- Checks ManagedCluster is ready
- Confirms ASO resources are properly provisioned

### 4. Flux GitOps Validation
- Verifies flux-system namespace exists
- Checks source-controller is available
- Validates kustomize-controller is available
- Confirms helm-controller is available

### 5. Cluster Connectivity Validation
- Tests API server accessibility
- Counts total and ready nodes
- Validates all nodes are in Ready state

### 6. Security & Compliance Validation
- Checks for workload identity service accounts
- Validates Azure Policy addon is running
- Confirms security configurations

### 7. API Access Type Validation
- For PUBLIC clusters: Verifies `enablePrivateCluster: false`
- For PRIVATE clusters: Verifies `enablePrivateCluster: true`
- Validates outbound network configuration

### 8. Certification Report
- Aggregates all validation results
- Generates JSON certification report
- Creates artifact with certification status

## Workflow Components

### WorkflowTemplate
The main certification workflow template that defines all validation tasks.

**Resource Name:** `certify-{cluster-name}`
**Namespace:** `argo`
**Entrypoint:** `certify-cluster`

### CronWorkflow
Scheduled weekly certification runs.

**Resource Name:** `weekly-cert-{cluster-name}`
**Namespace:** `argo`
**Default Schedule:** Every Sunday at 2 AM UTC
**Initial State:** Suspended (enable manually when ready)

### Trigger Job
Automatically triggers initial certification after cluster creation.

**Resource Name:** `trigger-cert-{cluster-name}`
**Namespace:** `argo`
**Behavior:**
- Waits for WorkflowTemplate to exist (up to 5 minutes)
- Waits for UK8SClusterPublic to be ACTIVE (up to 30 minutes)
- Submits certification workflow automatically
- Self-cleans up after 5 minutes (TTL)

## Checking Certification Status

Use the provided script to check certification status:

```bash
./check-certification-workflow.sh <cluster-name>
```

This script checks:
- WorkflowTemplate existence
- CronWorkflow schedule
- Trigger Job status
- Workflow execution instances
- Task-level validation results
- Workflow logs
- Certification reports

## Manual Certification Trigger

To manually trigger certification for a cluster:

```bash
# Create a workflow instance from the template
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

## Enabling Weekly Certification

To enable the weekly certification schedule:

```bash
kubectl patch cronworkflow weekly-cert-<cluster-name> -n argo \
  -p '{"spec":{"suspend":false}}' --type=merge
```

## Disabling Auto-Trigger

To disable automatic initial certification, set `autoTrigger: false`:

```yaml
spec:
  certification:
    autoTrigger: false
```

## Viewing Certification Reports

```bash
# Get the latest workflow
WORKFLOW=$(kubectl get workflow -n argo -l kro.run/cluster=<cluster-name> \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')

# View the workflow status
kubectl get workflow $WORKFLOW -n argo -o yaml

# View the certification report (if available in logs)
kubectl logs -n argo -l workflows.argoproj.io/workflow=$WORKFLOW \
  -c main --tail=-1 | grep -A 50 "CERTIFICATION REPORT"
```

## Integration with Backstage IDP

The certification workflow is designed to integrate with Backstage for:
- Real-time progress tracking
- Certification status badges
- Historical certification records
- Compliance reporting

## Troubleshooting

### Workflow Not Created
```bash
# Check KRO controller logs
kubectl logs -n kro-system -l app=kro-controller --tail=100

# Check UK8SCertification instance
kubectl get uk8scertification -A
kubectl describe uk8scertification cert-<cluster-name> -n <namespace>
```

### Certification Failing
```bash
# Check workflow status
kubectl describe workflow <workflow-name> -n argo

# View task logs
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name> --all-containers

# Check specific task
kubectl logs -n argo <pod-name> -c main
```

### Trigger Job Timing Out
```bash
# Check job logs
kubectl logs -n argo job/trigger-cert-<cluster-name>

# Check if cluster is ACTIVE
kubectl get uk8sclusterpublic <instance-name> -n <namespace> -o jsonpath='{.status.state}'
```

## Benefits of Externalization

### Maintainability
- Single source of truth for certification logic
- Easy to update validation rules
- Version controlled independently

### Reusability
- Same certification RGD works for PUBLIC and PRIVATE clusters
- Can be used across different cluster types
- Reduces code duplication

### Clarity
- Cluster definitions remain focused on infrastructure
- Certification logic is cleanly separated
- Easier to understand and review

### Flexibility
- Configure certification per cluster
- Disable/enable features independently
- Customize validation for different environments

## Best Practices

1. **Keep CronWorkflow suspended initially** - Enable after confirming manual certification works
2. **Review certification reports** - Don't just trust pass/fail, review details
3. **Update validation rules** - Keep certification checks aligned with security policies
4. **Monitor certification trends** - Track certification success rates over time
5. **Document custom validations** - If you add checks, document them clearly

## Future Enhancements

- [ ] Integration with policy enforcement systems
- [ ] Custom validation plugins
- [ ] Multi-cluster certification aggregation
- [ ] Certification compliance reporting dashboard
- [ ] Automated remediation workflows
- [ ] Integration with Azure Policy assessments
- [ ] Cost optimization validation checks
- [ ] Performance benchmark validations
