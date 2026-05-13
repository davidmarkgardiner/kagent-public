# Cluster Onboarding — Interview Reference

Maps the 5 interview questions to workflow parameters for `provision-aks-cluster`.

---

## Parameter Map

| Question | Parameter | Validation | Default |
|----------|-----------|-----------|---------|
| Cluster name? | `clusterName` | `^[a-z][a-z0-9-]{2,30}$` | — (required) |
| Region? | `region` | enum: `uksouth`, `westeurope`, `northeurope`, `ukwest` | — (required) |
| Size? | `size` | enum: `small`, `medium`, `large` | — (required) |
| Dry run? | `dryRun` | boolean string | `"true"` |
| Your name / team alias? | `confirmedBy` | any string | — (required) |

---

## Size → Infrastructure Mapping

| Size | VM SKU | Node count | Approx use case |
|------|--------|-----------|----------------|
| small | Standard_B8ms | 1 | Dev / PoC |
| medium | Standard_B8ms | 2 | Small team workloads |
| large | Standard_B8ms | 3 | Production-grade |

---

## Platform-Enforced Settings (not asked — hardcoded in workflow)

| Setting | Value | Why |
|---------|-------|-----|
| `kubernetesVersion` | `1.32` | Platform standard |
| `aadProfile.enableAzureRBAC` | `true` | Security baseline |
| `securityProfile.defender.enabled` | `true` | Security baseline |
| `disableLocalAccounts` | `true` | Security baseline |
| `tags.managed-by` | `kro` | Cost attribution |
| `tags.environment` | `dev` | Default; change in workflow if needed |

---

## Workflow Submitted

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: provision-aks-<clusterName>-
  namespace: argo
spec:
  workflowTemplateRef:
    name: provision-aks-cluster
  arguments:
    parameters:
      - name: clusterName
        value: "<clusterName>"
      - name: region
        value: "<region>"
      - name: size
        value: "<size>"
      - name: dryRun
        value: "<dryRun>"
      - name: confirmedBy
        value: "<confirmedBy>"
```

Status ConfigMap created by workflow: `provision-status-<workflow-name>` in namespace `argo`.

---

## Status Polling

After submission, the agent polls via:
- `k8s_get_resources`: ConfigMap `provision-status-<workflow-name>` in `argo`
- `k8s_get_resources`: Workflow `<workflow-name>` in `argo` → check `status.phase`

Expected phases: `Pending` → `Running` → `bootstrapping-node-pool` → `Succeeded`

---

## Source Files

| File | Location |
|------|----------|
| Agent CRD | `agents/kagent-triage/cluster-onboarding-agent.yaml` |
| WorkflowTemplate | `platform/argo-workflows/templates/aso-provisioning/` |
| KRO RGD | `infra/kro-stack/definitions/uk8scluster-public.yaml` |
| Demo script | `agents/aso-cluster-agent/DEMO-SCRIPT.md` |
