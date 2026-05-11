# AKS Cluster Certification Architecture

## Overview

The certification workflow validates AKS clusters across **two layers**:

1. **Management Layer** (Local Kind Cluster)
   - KRO ResourceGraphDefinitions
   - ASO Custom Resources
   - Orchestration health

2. **Target Layer** (AKS Cluster in Azure)
   - System components (Flux, Cert-Manager, etc.)
   - Pod health
   - Cluster connectivity

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    LOCAL KIND CLUSTER                                 │
│                   (Management Cluster)                                │
│                                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────────┐ │
│  │    KRO      │  │    ASO      │  │    Argo Workflows            │ │
│  │             │  │             │  │                              │ │
│  │ Orchestrates│──│ Provisions  │  │  Certification Workflow:     │ │
│  │ Resources   │  │ Azure       │  │  1. Validate KRO/ASO         │ │
│  │             │  │ Resources   │  │  2. Get AKS Credentials      │ │
│  └─────────────┘  └─────────────┘  │  3. Connect to AKS           │ │
│                                     │  4. Validate AKS Health      │ │
│                                     └──────────┬───────────────────┘ │
└────────────────────────────────────────────────┼─────────────────────┘
                                                  │
                                                  │ az aks get-credentials
                                                  │ kubectl --context aks
                                                  ▼
                        ┌───────────────────────────────────────────┐
                        │         AKS CLUSTER (Azure)               │
                        │                                           │
                        │  ┌──────────┐  ┌─────────────┐           │
                        │  │   Flux   │  │Cert-Manager │           │
                        │  └──────────┘  └─────────────┘           │
                        │                                           │
                        │  ┌──────────────┐  ┌─────────────┐       │
                        │  │External DNS  │  │   Kyverno   │       │
                        │  └──────────────┘  └─────────────┘       │
                        │                                           │
                        │  ┌──────────────────────────────┐        │
                        │  │    kube-system pods          │        │
                        │  └──────────────────────────────┘        │
                        └───────────────────────────────────────────┘
```

## Workflow Execution Flow

### Phase 1: Management Layer Validation (Local Kind)

```bash
1. wait-for-cluster-ready
   ├─ Wait for UK8SClusterPublic: ACTIVE + Ready
   ├─ Wait for ManagedCluster: Ready
   └─ 60s stabilization period

2. validate-configuration
   └─ Verify UK8SClusterPublic spec

3. validate-kro
   ├─ Check RGDs are Active
   ├─ uk8sclusterpublic.kro.run
   ├─ uk8sjobs.kro.run
   ├─ uk8sfluxgitops.kro.run
   └─ uk8scertification.kro.run

4. validate-aso
   ├─ Check ResourceGroup: Ready
   └─ Check ManagedCluster: Ready

5. validate-flux (on management cluster)
   └─ Check Flux controllers on kind
```

### Phase 2: Target Layer Validation (AKS Cluster)

```bash
6. get-aks-credentials
   ├─ Login to Azure (workload identity or managed identity)
   ├─ az aks get-credentials --admin
   ├─ Save kubeconfig for AKS cluster
   └─ Test connection: kubectl cluster-info

7. validate-aks-system-components
   ├─ Switch context: kubectl config use-context <cluster>-admin
   ├─ Check namespace: flux-system
   │  └─ Validate Flux pods are running
   ├─ Check namespace: cert-manager
   │  └─ Validate Cert-Manager pods
   ├─ Check namespace: external-dns
   │  └─ Validate External DNS pods
   ├─ Check namespace: external-secrets
   │  └─ Validate External Secrets pods
   ├─ Check namespace: kyverno
   │  └─ Validate Kyverno pods
   ├─ Check namespace: reloader
   │  └─ Validate Reloader pods
   └─ Check namespace: kube-system
      └─ Validate core system pods
```

### Phase 3: Final Validation

```bash
8. validate-connectivity
   ├─ API server accessibility
   └─ Node readiness

9. validate-security
   ├─ Workload Identity service accounts
   └─ Azure Policy addon

10. validate-api-access
    └─ Verify PUBLIC vs PRIVATE cluster type

11. aggregate-results
    └─ Generate certification report

12. generate-final-report (onExit)
    └─ Print final summary
```

## Authentication for AKS Access

The `get-aks-credentials` task supports two authentication methods:

### Option 1: Workload Identity (Recommended)

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argo-workflow-executor
  namespace: argo
  annotations:
    azure.workload.identity/client-id: "<client-id>"
    azure.workload.identity/tenant-id: "<tenant-id>"
```

The workflow automatically detects workload identity:
```bash
if [ -n "$AZURE_CLIENT_ID" ]; then
  az login --service-principal \
    -u $AZURE_CLIENT_ID \
    -t $AZURE_TENANT_ID \
    --federated-token $(cat $AZURE_FEDERATED_TOKEN_FILE)
fi
```

### Option 2: Managed Identity

If workload identity is not configured, falls back to managed identity:
```bash
az login --identity
```

## Prerequisites

### Management Cluster (Kind)

1. **KRO Installed**
   ```bash
   kubectl get resourcegraphdefinition
   ```

2. **ASO Installed**
   ```bash
   kubectl get pods -n azureserviceoperator-system
   ```

3. **Argo Workflows Installed**
   ```bash
   kubectl get pods -n argo
   ```

4. **RBAC Configured**
   ```bash
   kubectl apply -f certification-rbac.yaml
   ```

5. **Azure Credentials**
   - Workload Identity or Managed Identity configured
   - Permissions to get AKS credentials

### Target Cluster (AKS)

1. **Cluster Provisioned**
   ```bash
   kubectl get managedcluster <name> -n <namespace>
   # Should show: READY: True
   ```

2. **System Components Deployed** (Optional but validated)
   - Flux
   - Cert-Manager
   - External DNS
   - External Secrets
   - Kyverno
   - Reloader

## Configuration Parameters

The certification workflow requires these parameters:

```yaml
parameters:
  - name: clusterName              # AKS cluster name
  - name: resourceGroup            # Azure resource group
  - name: targetNamespace          # K8s namespace with cluster resources
  - name: instanceName             # UK8SClusterPublic instance name
  - name: subscriptionId           # Azure subscription ID
  - name: environment              # dev, staging, production
  - name: clusterType              # PUBLIC or PRIVATE
```

These are automatically configured by the UK8SCertification RGD.

## Running a Manual Certification

### Trigger from UK8SClusterPublic Instance

The certification is automatically triggered when a UK8SClusterPublic instance becomes ACTIVE. To trigger manually:

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

### Monitor Progress

```bash
# Watch workflow
kubectl get workflow -n argo -l kro.run/cluster=<cluster-name> -w

# Check logs
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name> -f

# Run check script
./kro-stack/scripts/check-certification-workflow.sh <cluster-name>
```

## Validation Details

### Management Layer Checks

| Component | Check | Success Criteria |
|-----------|-------|------------------|
| UK8SClusterPublic | State & Ready | STATE=ACTIVE, Ready=True |
| ResourceGraphDefinitions | Active State | All RGDs show Active |
| ResourceGroup | ASO Status | Ready=True |
| ManagedCluster | ASO Status | Ready=True |
| Flux (Management) | Pods Running | All Flux controllers running on kind |

### Target Layer Checks (AKS)

| Component | Namespace | Check | Success Criteria |
|-----------|-----------|-------|------------------|
| Flux | flux-system | Pods | All Flux pods Running |
| Cert-Manager | cert-manager | Pods | Controller, webhook, cainjector Running |
| External DNS | external-dns | Pods | External DNS pod Running |
| External Secrets | external-secrets | Pods | Controller, webhook Running |
| Kyverno | kyverno | Pods | All Kyverno controllers Running |
| Reloader | reloader | Pods | Reloader pod Running |
| Kube-System | kube-system | Pods | Core system pods Running |

## Expected Output

### Successful Certification

```
=== Waiting for Cluster to be Ready ===
✓ UK8SClusterPublic is ACTIVE and Ready
✓ ManagedCluster is Ready
✅ Cluster is ready for certification

=== Configuration Validation ===
✓ Instance YAML retrieved
✓ Kubernetes version: 1.33
✅ Configuration validation complete

=== KRO Resource Validation ===
✓ uk8sclusterpublic.kro.run is Active
✓ uk8sjobs.kro.run is Active
✓ uk8sfluxgitops.kro.run is Active
✓ uk8scertification.kro.run is Active
✓ UK8SClusterPublic instance exists
✓ Instance state is ACTIVE
✓ Instance Ready condition is True
Summary: 7 passed, 0 failed
✅ KRO validation complete

=== Getting AKS Credentials ===
Cluster: uk8s-tsshared-weu-gt025-int-dev-public2
Resource Group: at39473-weu-dev-public2
Subscription: {{AZURE_SUBSCRIPTION_ID}}
Using workload identity
Getting AKS credentials...
✓ Kubeconfig saved
Testing connection to AKS cluster...
✅ AKS credentials acquired successfully

=== AKS System Components Validation ===
Validating components IN the AKS cluster: uk8s-tsshared-weu-gt025-int-dev-public2

Checking Flux...
✓ Namespace flux-system exists
  Pods: 4/4 running
  ✓ All Flux pods are running

Checking Cert-Manager...
✓ Namespace cert-manager exists
  Pods: 3/3 running
  ✓ All Cert-Manager pods are running

[... more components ...]

Summary: 15 passed, 0 failed, 2 warnings
✅ AKS system components validation complete

=== UK8S CLUSTER CERTIFICATION REPORT ===
{
  "cluster": "uk8s-tsshared-weu-gt025-int-dev-public2",
  "namespace": "uk8s-nextgen",
  "environment": "dev",
  "cluster_type": "PUBLIC",
  "timestamp": "2025-11-21T14:15:00Z",
  "workflow": "certify-...-auto-abc123",
  "certification": {
    "status": "CERTIFIED",
    "workflow_name": "certify-uk8s-tsshared-weu-gt025-int-dev-public2"
  }
}
✅ CLUSTER CERTIFICATION COMPLETE
```

## Troubleshooting

### Cannot Get AKS Credentials

**Error**: `az login failed`

**Solutions**:
1. Check Azure authentication is configured
2. Verify workload identity annotations
3. Check service account has correct permissions
4. Verify subscription ID is correct

### Cannot Connect to AKS Cluster

**Error**: `kubectl cluster-info failed`

**Solutions**:
1. Verify cluster is fully provisioned
2. Check firewall rules (for private clusters)
3. Verify admin credentials work: `az aks get-credentials --admin`
4. Check network connectivity from kind to AKS

### Components Not Found in AKS

**Warning**: `Namespace not found (component may not be installed)`

**Explanation**: This is expected if components haven't been deployed yet. The workflow reports warnings (not failures) for missing optional components.

**To Deploy Components**:
Use Flux GitOps or Helm to deploy system components to the AKS cluster.

## Security Considerations

1. **Admin Credentials**: Uses `--admin` flag for cluster access
   - Consider using regular credentials with appropriate RBAC

2. **Kubeconfig Storage**: Kubeconfig is stored in workflow pod
   - Automatically cleaned up when pod terminates
   - Not persisted to artifacts (Minio disabled)

3. **Azure Permissions**: Service account needs:
   - `Azure Kubernetes Service Cluster User Role` (minimum)
   - `Azure Kubernetes Service Cluster Admin Role` (for --admin)

4. **Network Access**: Workflow pods need network access to:
   - Azure API (management.azure.com)
   - AKS API server (may require VPN for private clusters)

## Next Steps

1. **Deploy System Components** to AKS via Flux
2. **Enable CronWorkflow** for weekly certifications
3. **Integrate with Backstage IDP** for visualization
4. **Add Custom Validations** specific to your workloads

---

**Version**: 3.0
**Updated**: 2025-11-21
**Status**: Production Ready with AKS Validation
