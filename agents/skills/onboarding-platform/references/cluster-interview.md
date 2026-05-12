# Cluster Onboarding — Interview Reference

## Agent: `cluster-onboarding-agent`
## WorkflowTemplate: `provision-aks-cluster` (namespace: `argo`)

---

## Question → Parameter Mapping

| # | Question | Parameter | Validation | Default |
|---|----------|-----------|------------|---------|
| 1 | Cluster name | `clusterName` | `^[a-z][a-z0-9-]{2,30}$` | — |
| 2 | Region | `region` | enum: uksouth / westeurope / northeurope / ukwest | — |
| 3 | Size | `size` | enum: small / medium / large | — |
| 4 | Dry run? | `dryRun` | boolean | **true** |
| 5 | "yes, provision" | `confirmedBy` | exact string match | — |

---

## Platform-Enforced Values (not asked — hardcoded in workflow)

| Field | Value |
|-------|-------|
| environment | dev |
| team | AKSEngineering |
| Kubernetes version | 1.32 |
| Defender | enabled |
| Azure RBAC | enabled |
| Local accounts | disabled |

---

## Size → Infrastructure Mapping

| Size | VM SKU | Node Count |
|------|--------|------------|
| small | Standard_B8ms | 1 |
| medium | Standard_B8ms | 2 |
| large | Standard_B8ms | 3 |

---

## Existing Assets (do not rebuild)

| Asset | Location |
|-------|----------|
| WorkflowTemplate | `provision-aks-cluster` in `argo` ns |
| KRO RGD | `infra-stack/kro-stack/definitions/uk8scluster-public.yaml` |
| Predecessor agent | `agents/aso-cluster-agent/agent/aso-provisioner-agent.yaml` |

The cluster-onboarding-agent is a thin wrapper over the existing `provision-aks-cluster`
WorkflowTemplate, adding a structured five-question interview. The predecessor
`aso-cluster-provisioner` was smoke-tested on home cluster (2026-05-09).

---

## Workflow Submission Template

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: cluster-onboarding-<clusterName>-
  namespace: argo
  labels:
    platform.com/onboarding: "true"
    platform.com/cluster: <clusterName>
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
        value: "<true|false>"
      - name: confirmedBy
        value: "yes, provision"
```
