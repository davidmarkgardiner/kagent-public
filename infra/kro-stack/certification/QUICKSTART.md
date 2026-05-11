# UK8S Cluster Certification - Quick Start Guide

Get your UK8S cluster certified in 3 simple steps!

## Prerequisites Check

Before starting, ensure you have:
- ✅ Argo Workflows installed (`kubectl get namespace argo`)
- ✅ kubectl configured and connected to your cluster
- ✅ UK8SCluster instance deployed

## Step 1: Deploy the Certification Workflow (One-time Setup)

```bash
cd kro-stack/certification
./deploy-certification.sh
```

This will:
- Create ConfigMap with validation scripts
- Set up RBAC permissions
- Deploy the certification WorkflowTemplate

**Expected output:**
```
==> UK8S Cluster Certification Workflow Deployment

[INFO] Checking prerequisites...
[INFO] kubectl found
[INFO] Connected to cluster: my-cluster
[INFO] Argo namespace exists

[INFO] ConfigMap 'uk8s-certification-scripts' created/updated
[INFO] RBAC configured for certification workflow
[INFO] WorkflowTemplate 'uk8s-cluster-certification' deployed

[INFO] Deployment complete!
```

## Step 2: Run Certification

### Option A: Using the Example Script

Certify the example cluster from `instances/dev/simple-cluster-example.yaml`:

```bash
./example-run.sh
```

### Option B: Using Argo CLI Directly

Certify your own cluster:

```bash
argo submit -n argo \
  --from workflowtemplate/uk8s-cluster-certification \
  -p clusterName=YOUR_CLUSTER_NAME \
  -p resourceGroup=YOUR_RESOURCE_GROUP \
  -p targetNamespace=azure-system \
  -p instanceName=YOUR_INSTANCE_NAME \
  --watch
```

Replace:
- `YOUR_CLUSTER_NAME` - Your AKS cluster name
- `YOUR_RESOURCE_GROUP` - Azure resource group
- `YOUR_INSTANCE_NAME` - UK8SCluster custom resource name

### Option C: Using kubectl

If you don't have argo CLI:

```bash
cat <<EOF | kubectl create -f -
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: uk8s-cert-
  namespace: argo
spec:
  workflowTemplateRef:
    name: uk8s-cluster-certification
  arguments:
    parameters:
      - name: clusterName
        value: "YOUR_CLUSTER_NAME"
      - name: resourceGroup
        value: "YOUR_RESOURCE_GROUP"
      - name: targetNamespace
        value: "azure-system"
      - name: instanceName
        value: "YOUR_INSTANCE_NAME"
EOF
```

## Step 3: View Results

### Check Workflow Status

```bash
# Using argo CLI
argo list -n argo

# Using kubectl
kubectl get workflows -n argo
```

### View Certification Report

```bash
# Using argo CLI
argo logs <workflow-name> -n argo | grep -A 50 "CERTIFICATION REPORT"

# Using kubectl
kubectl logs <workflow-pod> -n argo | grep -A 50 "CERTIFICATION REPORT"
```

### Example Success Output

```
======================================
UK8S CLUSTER CERTIFICATION REPORT
======================================
{
  "cluster": "my-test-cluster",
  "namespace": "azure-system",
  "timestamp": "2025-01-13T15:30:00Z",
  "workflow": "uk8s-cert-abc123",
  "certification": {
    "status": "CERTIFIED",
    "pass_percentage": 95.5,
    "total_passed": 42,
    "total_failed": 2,
    "total_checks": 44
  }
}
======================================
✅ CLUSTER IS CERTIFIED
======================================
```

## Understanding the Validation Sections

The certification workflow validates **13 critical sections**:

| Section | What It Checks | Critical? |
|---------|----------------|-----------|
| 1. Configuration | YAML validity, K8s version | ✅ Yes |
| 2. KRO Resources | RGDs, instances, conditions | ✅ Yes |
| 3. ASO Resources | ResourceGroup, ManagedCluster, Identities | ✅ Yes |
| 4. Flux GitOps | Controllers, GitRepositories, Kustomizations | ✅ Yes |
| 5. Post-Deploy Jobs | Job completion status | No |
| 6. Connectivity | API server, nodes, system pods | ✅ Yes |
| 7. Security | Workload identity, Azure Policy | ✅ Yes |
| 8. Istio | Service mesh components | No |
| 9. Storage | CSI drivers, storage classes | No |
| 10. Addons | Key Vault, KEDA, VPA | No |
| 11. Monitoring | metrics-server, monitoring | No |
| 12. GitOps Reconciliation | HelmReleases, Kustomizations | No |
| 13. Lifecycle | Job cleanup, auto-upgrade | No |

**Certification requires:**
- ✅ 90%+ overall pass rate
- ✅ All critical sections passing
- ✅ Zero security issues

## Troubleshooting

### "Workflow template not found"

**Solution:** Run the deployment script:
```bash
./deploy-certification.sh
```

### "Cannot connect to cluster"

**Solution:** Verify kubectl is configured:
```bash
kubectl cluster-info
kubectl config current-context
```

### "Instance not found"

**Solution:** Verify your UK8SCluster instance exists:
```bash
kubectl get uk8scluster -n azure-system
```

Update parameters to match the actual instance name.

### "Permission denied" errors

**Solution:** Re-deploy RBAC:
```bash
./deploy-certification.sh
```

### Workflow stays in "Pending" state

**Solution:** Check workflow controller logs:
```bash
kubectl logs -n argo -l app=workflow-controller
```

## Next Steps

### Schedule Regular Certifications

Create a CronWorkflow for automatic weekly certification:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: CronWorkflow
metadata:
  name: weekly-uk8s-certification
  namespace: argo
spec:
  schedule: "0 2 * * 0"  # Every Sunday at 2 AM
  timezone: "UTC"
  workflowSpec:
    workflowTemplateRef:
      name: uk8s-cluster-certification
    arguments:
      parameters:
        - name: clusterName
          value: "prod-cluster"
        - name: resourceGroup
          value: "rg-prod"
        - name: targetNamespace
          value: "azure-system"
        - name: instanceName
          value: "prod-uk8s"
```

Apply it:
```bash
kubectl apply -f weekly-certification.yaml
```

### Integrate with CI/CD

Add to your deployment pipeline:

```yaml
# Azure DevOps example
- script: |
    argo submit -n argo \
      --from workflowtemplate/uk8s-cluster-certification \
      -p clusterName=$(clusterName) \
      -p resourceGroup=$(resourceGroup) \
      -p targetNamespace=azure-system \
      -p instanceName=$(instanceName) \
      --wait
  displayName: 'Certify AKS Cluster'
```

### Enable Backstage Integration

For real-time progress tracking in your IDP:

1. Create Backstage token:
```bash
kubectl create secret generic backstage-token \
  -n argo \
  --from-literal=token='your-token'
```

2. Run with Backstage parameters:
```bash
argo submit -n argo \
  --from workflowtemplate/uk8s-cluster-certification \
  -p clusterName=my-cluster \
  -p resourceGroup=my-rg \
  -p targetNamespace=azure-system \
  -p instanceName=my-instance \
  -p backstage-url=https://backstage.company.com \
  -p component-name=my-cluster \
  --watch
```

## Complete Example: Dev to Prod Workflow

### 1. Deploy Development Cluster

```bash
kubectl apply -f instances/dev/simple-cluster-example.yaml
```

### 2. Wait for Provisioning

```bash
kubectl wait --for=condition=Ready \
  uk8scluster/my-test-cluster \
  -n azure-system \
  --timeout=30m
```

### 3. Run Certification

```bash
./example-run.sh
```

### 4. Verify Certification Passed

```bash
argo get @latest -n argo | grep "Status: Succeeded"
```

### 5. Promote to Production

If certification passed, deploy to production:

```bash
kubectl apply -f instances/production/prod-cluster.yaml
```

### 6. Certify Production

```bash
argo submit -n argo \
  --from workflowtemplate/uk8s-cluster-certification \
  -p clusterName=prod-cluster \
  -p resourceGroup=rg-prod \
  -p targetNamespace=azure-system \
  -p instanceName=prod-uk8s \
  -p certification-timeout=2400 \
  --watch
```

## Additional Resources

- **Full Documentation:** [README.md](README.md)
- **Certification Checklist:** [../CERTIFICATION_CHECKLIST.md](../CERTIFICATION_CHECKLIST.md)
- **Argo Workflows Docs:** https://argoproj.github.io/argo-workflows/
- **KRO Documentation:** https://kro.run/docs/

## Support

For issues or questions:
1. Check the [README.md](README.md) for detailed troubleshooting
2. Review workflow logs for specific errors
3. Verify all prerequisites are met
4. Consult the certification checklist for validation criteria

---

**Ready to certify?** Start with Step 1 above! 🚀
