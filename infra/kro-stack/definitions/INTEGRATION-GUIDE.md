# Integrating Certification Workflow into UK8SCluster RGD

This guide shows you how to add the automated certification workflow directly into your UK8SCluster ResourceGraphDefinition so it deploys automatically with every cluster.

## Benefits of Integration

When integrated into the RGD:
✅ **Automatic deployment** - Certification workflow created with every cluster
✅ **Cluster-specific** - Each cluster gets its own pre-configured workflow
✅ **No manual setup** - Scripts and templates deployed automatically
✅ **GitOps-friendly** - Everything in one place, version-controlled
✅ **Self-service** - Users can run certification without admin intervention

## Option 1: Quick Integration (Copy-Paste)

### Step 1: Open the UK8SCluster RGD

```bash
vim kro-stack/definitions/uk8scluster.yaml
```

### Step 2: Add Certification Resources

At the **end** of the `spec.resources` section (after line 644), add the certification resources:

```yaml
    # ----------------------------------------
    # CERTIFICATION WORKFLOW RESOURCES
    # ----------------------------------------
    - id: certificationScripts
      template:
        apiVersion: v1
        kind: ConfigMap
        metadata:
          name: uk8s-cert-scripts-${schema.spec.clusterName}
          namespace: argo
          labels:
            kro.run/cluster: ${schema.spec.clusterName}
            kro.run/component: certification-scripts
        data:
          validate_kro_section.py: |
            # [Script content from uk8scluster-certification-addon.yaml]
            # Copy the entire Python script here

    - id: certificationWorkflow
      template:
        apiVersion: argoproj.io/v1alpha1
        kind: WorkflowTemplate
        metadata:
          name: certify-${schema.spec.clusterName}
          namespace: argo
          labels:
            kro.run/cluster: ${schema.spec.clusterName}
            kro.run/component: certification
        spec:
          # [Workflow spec from uk8scluster-certification-addon.yaml]
          # Copy the entire workflow spec here

    - id: certificationSchedule
      template:
        apiVersion: argoproj.io/v1alpha1
        kind: CronWorkflow
        metadata:
          name: weekly-cert-${schema.spec.clusterName}
          namespace: argo
        spec:
          schedule: "0 2 * * 0"
          suspend: true
          workflowSpec:
            workflowTemplateRef:
              name: certify-${schema.spec.clusterName}
```

### Step 3: Apply the Updated RGD

```bash
kubectl apply -f kro-stack/definitions/uk8scluster.yaml
```

### Step 4: Deploy or Update a Cluster

When you deploy a new cluster:

```bash
kubectl apply -f kro-stack/instances/dev/simple-cluster-example.yaml
```

The certification workflow will be automatically created!

## Option 2: Merge with yq (Automated)

If you have `yq` installed, you can merge automatically:

```bash
# Backup original
cp kro-stack/definitions/uk8scluster.yaml kro-stack/definitions/uk8scluster.yaml.bak

# Merge certification resources
yq eval-all 'select(fileIndex == 0) * select(fileIndex == 1)' \
  kro-stack/definitions/uk8scluster.yaml \
  kro-stack/definitions/uk8scluster-certification-addon.yaml \
  > kro-stack/definitions/uk8scluster-merged.yaml

# Review and apply
mv kro-stack/definitions/uk8scluster-merged.yaml kro-stack/definitions/uk8scluster.yaml
kubectl apply -f kro-stack/definitions/uk8scluster.yaml
```

## Verification

### 1. Check RGD Updated

```bash
kubectl get resourcegraphdefinition uk8scluster.kro.run -o yaml | grep -A 5 "id: certificationWorkflow"
```

You should see the certification workflow resource definition.

### 2. Deploy Test Cluster

```bash
kubectl apply -f kro-stack/instances/dev/simple-cluster-example.yaml
```

### 3. Verify Workflow Created

```bash
# Check WorkflowTemplate created
kubectl get workflowtemplate -n argo | grep certify-my-test-cluster

# Check ConfigMap created
kubectl get configmap -n argo | grep uk8s-cert-scripts-my-test-cluster

# Check CronWorkflow created
kubectl get cronworkflow -n argo | grep weekly-cert-my-test-cluster
```

Expected output:
```
certify-my-test-cluster        7s
uk8s-cert-scripts-my-test-cluster    1    7s
weekly-cert-my-test-cluster    False    0 2 * * 0    <none>    7s
```

## Using the Integrated Workflow

### Run Manual Certification

Once integrated, certify your cluster with a simple command:

```bash
argo submit -n argo \
  --from workflowtemplate/certify-my-test-cluster \
  --watch
```

Notice:
- ✅ No parameters needed! (Pre-configured by RGD)
- ✅ Cluster name, namespace, resource group all set automatically
- ✅ Just submit and watch

### Enable Scheduled Certification

Enable weekly automatic certification:

```bash
# Enable the CronWorkflow
kubectl patch cronworkflow weekly-cert-my-test-cluster -n argo \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/suspend", "value": false}]'

# Verify it's enabled
kubectl get cronworkflow weekly-cert-my-test-cluster -n argo
```

The cluster will now be certified every Sunday at 2 AM UTC.

### View Certification History

```bash
# List all certification runs
argo list -n argo | grep certify-my-test-cluster

# View latest certification
argo get -n argo @latest

# View logs from latest
argo logs -n argo @latest
```

## Customization

### Change Certification Schedule

Edit the CronWorkflow schedule in the RGD:

```yaml
- id: certificationSchedule
  template:
    spec:
      schedule: "0 6 * * 1"  # Every Monday at 6 AM
      timezone: "America/New_York"  # Change timezone
```

### Add More Validation Steps

Add custom validation templates to the WorkflowTemplate:

```yaml
- name: validate-custom-requirement
  script:
    image: bitnami/kubectl:latest
    command: [bash]
    source: |
      echo "=== Custom Validation ==="
      # Your validation logic here
      echo "✅ Custom validation complete"
```

Then add to the DAG:

```yaml
- name: validate-custom
  template: validate-custom-requirement
  dependencies: [validate-connectivity]
```

### Configure Notifications

Add Argo Workflows notifications to the CronWorkflow:

```yaml
spec:
  workflowSpec:
    hooks:
      failed:
        expression: workflow.status == "Failed"
        template: send-alert
```

## Multi-Cluster Deployment

When you deploy multiple clusters, each gets its own certification workflow:

```bash
# Deploy dev cluster
kubectl apply -f instances/dev/dev-cluster.yaml
# Creates: certify-dev-cluster, uk8s-cert-scripts-dev-cluster

# Deploy staging cluster
kubectl apply -f instances/staging/staging-cluster.yaml
# Creates: certify-staging-cluster, uk8s-cert-scripts-staging-cluster

# Deploy production cluster
kubectl apply -f instances/production/prod-cluster.yaml
# Creates: certify-prod-cluster, uk8s-cert-scripts-prod-cluster
```

Each cluster's workflow is pre-configured with its specific:
- Cluster name
- Resource group
- Namespace
- Subscription ID
- Environment

## Troubleshooting

### Issue: Workflow Not Created

**Check KRO instance status:**
```bash
kubectl get uk8scluster my-test-cluster -n azure-system -o yaml
```

Look for:
```yaml
status:
  state: ACTIVE
  conditions:
    - type: Ready
      status: "True"
```

### Issue: ConfigMap Not Created

**Check if argo namespace exists:**
```bash
kubectl get namespace argo
```

If not, create it:
```bash
kubectl create namespace argo
```

### Issue: Cannot Submit Workflow

**Verify RBAC:**
```bash
kubectl get serviceaccount argo-workflow-executor -n argo
kubectl get clusterrole uk8s-certification-role
kubectl get clusterrolebinding argo-workflow-executor-uk8s-cert
```

If missing, apply RBAC from the standalone deployment:
```bash
cd kro-stack/certification
./deploy-certification.sh
```

## Comparison: Integrated vs Standalone

| Feature | Integrated (RGD) | Standalone (Scripts) |
|---------|------------------|----------------------|
| **Deployment** | Automatic with cluster | Manual setup required |
| **Configuration** | Pre-configured per cluster | Manual parameters |
| **Multi-cluster** | Each cluster gets own workflow | Shared workflow template |
| **Maintenance** | Update RGD, redeploy clusters | Update scripts, redeploy |
| **Discoverability** | Listed with cluster resources | Separate in argo namespace |
| **Versioning** | Same version as RGD | Independent versioning |

**Recommendation:**
- **Use Integrated** for new clusters (easier, automated)
- **Use Standalone** for existing clusters or when you need a universal workflow

## Complete Example

### 1. Update RGD (One-time)

```bash
# Add certification resources to uk8scluster.yaml
vim kro-stack/definitions/uk8scluster.yaml
# [Add certification resources as shown above]

# Apply updated RGD
kubectl apply -f kro-stack/definitions/uk8scluster.yaml
```

### 2. Deploy Cluster

```bash
kubectl apply -f kro-stack/instances/dev/simple-cluster-example.yaml
```

### 3. Wait for Cluster Ready

```bash
kubectl wait --for=condition=Ready \
  uk8scluster/my-test-cluster \
  -n azure-system \
  --timeout=30m
```

### 4. Run Certification

```bash
argo submit -n argo \
  --from workflowtemplate/certify-my-test-cluster \
  --watch
```

### 5. View Report

```bash
argo logs -n argo @latest | grep -A 50 "CERTIFICATION REPORT"
```

Done! 🎉

## Next Steps

1. ✅ Integrate certification into RGD
2. ✅ Deploy a test cluster
3. ✅ Verify workflow created automatically
4. ✅ Run manual certification
5. ✅ Enable scheduled certification
6. ✅ Monitor certification results
7. ✅ Add custom validations as needed

## Support

- **Full Documentation:** [../certification/README.md](../certification/README.md)
- **Standalone Deployment:** [../certification/deploy-certification.sh](../certification/deploy-certification.sh)
- **Certification Checklist:** [../CERTIFICATION_CHECKLIST.md](../CERTIFICATION_CHECKLIST.md)
