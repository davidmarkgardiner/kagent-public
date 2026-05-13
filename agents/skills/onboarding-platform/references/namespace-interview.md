# Namespace Onboarding Interview

Use this flow for team namespace requests.

## Fields

Collect:

| Field | Rule | Default |
| --- | --- | --- |
| `NamespaceName` | lowercase DNS label | none |
| `Swc` | service, system, or cost-center code | none |
| `Environment` | `dev`, `test`, `stage`, `prod` | `dev` |
| `ResourceQuotaCPU` | integer CPU count | `2` |
| `ResourceQuotaMemoryGB` | integer GiB | `4` |
| `ResourceQuotaStorageGB` | integer GiB | `10` |
| `AllowAccessFromNS` | comma-separated namespace list | empty string |
| `BillingReference` | required for prod | none |
| `ManagedAksClusterName` | target cluster | `minikube` |

## Interview

Ask:

1. Namespace name, environment, SWC, and target cluster.
2. CPU, memory, and storage quota.
3. Which namespaces may connect to it, if any.
4. Billing reference, especially for production.

Do not invent billing references.

## Payload

The existing `namespace-onboarding-template` parses this exact JSON shape:

```json
{
  "NamespaceName": "payments-dev",
  "Swc": "payments",
  "Environment": "dev",
  "ResourceQuotaCPU": 2,
  "ResourceQuotaMemoryGB": 4,
  "ResourceQuotaStorageGB": 10,
  "AllowAccessFromNS": "ingress-nginx,monitoring",
  "BillingReference": "COST-1234",
  "ManagedAksClusterName": "minikube"
}
```

## Confirmation

Before submitting the Workflow, show the compact JSON payload and require:

```text
yes, create namespace
```

## Workflow

Submit a Workflow in namespace `argo` with:

```yaml
spec:
  workflowTemplateRef:
    name: namespace-onboarding-template
  arguments:
    parameters:
      - name: payload
      - name: targetCluster
```

The workflow creates or updates Namespace, ResourceQuota, and NetworkPolicy resources.
