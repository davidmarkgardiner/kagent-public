# Namespace Onboarding — Interview Reference

## Agent: `namespace-onboarding-agent`
## WorkflowTemplate: `namespace-onboarding-template` (namespace: `argo`)

---

## Question → Parameter Mapping

| # | Question | Parameter | Default |
|---|----------|-----------|---------|
| 1 | Namespace name | `NamespaceName` | — |
| 2 | Target cluster | `ManagedAksClusterName` + `targetCluster` | — |
| 3 | Environment | `Environment` | — (dev / staging / prod) |
| 4 | SWC / cost centre | `Swc` | — |
| 5 | Billing reference | `BillingReference` | — |
| 6 | CPU quota | `ResourceQuotaCPU` | 2 |
| 7 | Memory quota (GiB) | `ResourceQuotaMemoryGB` | 2 |
| 8 | Storage quota (GiB) | `ResourceQuotaStorageGB` | 0 |
| 9 | Allow ingress from NS | `AllowAccessFromNS` | "" (blank = no rule) |

---

## Workflow Output

The `namespace-onboarding-template` creates:
- Namespace with labels: environment, swc, billing-reference, team
- ResourceQuota
- NetworkPolicy (only if `AllowAccessFromNS` is non-empty)

---

## NetworkPolicy Label Warning ⚠️

The template selects the source namespace using its `name` label. **Not all namespaces
carry this label.** Always surface this warning when `AllowAccessFromNS` is set:

> "Note — the NetworkPolicy allow-from rule selects the source namespace by its `name` label.
> If the rule doesn't work after creation, run:
> `kubectl label ns <source-namespace> name=<source-namespace>`"

---

## Optional: Triage Agent Chain

After successful workflow submission, offer to invoke `byoa-builder-guided` via A2A
to create a triage agent for the new namespace.

- A2A endpoint: `POST /api/a2a/kagent/byoa-builder-guided/`
- Pass the namespace name as context in the opening message

---

## Confirmation Phrase

User must type exactly: `yes, create namespace`

---

## Workflow Submission Template

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: ns-onboarding-<NamespaceName>-
  namespace: argo
  labels:
    platform.com/onboarding: "true"
    platform.com/namespace: <NamespaceName>
spec:
  workflowTemplateRef:
    name: namespace-onboarding-template
  arguments:
    parameters:
      - name: NamespaceName
        value: "<NamespaceName>"
      - name: ManagedAksClusterName
        value: "<cluster>"
      - name: targetCluster
        value: "<cluster>"
      - name: Environment
        value: "<dev|staging|prod>"
      - name: Swc
        value: "<Swc>"
      - name: BillingReference
        value: "<BillingReference>"
      - name: ResourceQuotaCPU
        value: "<cpu>"
      - name: ResourceQuotaMemoryGB
        value: "<memory>"
      - name: ResourceQuotaStorageGB
        value: "<storage>"
      - name: AllowAccessFromNS
        value: "<source-namespace or empty>"
```
