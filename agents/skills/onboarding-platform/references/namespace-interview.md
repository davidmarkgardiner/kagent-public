# Namespace Onboarding — Interview Reference

Maps the 9 interview questions to JSON payload fields for `namespace-onboarding-template`.

---

## Parameter Map

| Question | JSON field | Validation | Default |
|----------|-----------|-----------|---------|
| Namespace name? | `NamespaceName` | lowercase, hyphens, max 63 chars | — (required) |
| Which cluster? | `targetCluster` | cluster name / context | — (required) |
| Environment? | `Environment` | enum: `dev`, `staging`, `prod` | — (required) |
| SWC / cost centre? | `Swc` | string (e.g. SWC-12345) | — (required) |
| Billing reference? | `BillingReference` | string | — (required) |
| CPU quota (cores)? | `ResourceQuotaCPU` | integer string | `"2"` |
| Memory quota (GiB)? | `ResourceQuotaMemoryGB` | integer string | `"2"` |
| Storage quota (GiB)? | `ResourceQuotaStorageGB` | integer string | `"0"` (skip) |
| Allow access from namespace? | `AllowAccessFromNS` | namespace name or empty | `""` (skip) |

---

## JSON Payload Structure

```json
{
  "NamespaceName": "payments-dev",
  "Environment": "dev",
  "Swc": "SWC-12345",
  "BillingReference": "PROJECT-001",
  "ResourceQuotaCPU": "4",
  "ResourceQuotaMemoryGB": "8",
  "ResourceQuotaStorageGB": "0",
  "AllowAccessFromNS": ""
}
```

---

## Workflow Submitted

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: namespace-onboarding-<NamespaceName>-
  namespace: argo
spec:
  workflowTemplateRef:
    name: namespace-onboarding-template
  arguments:
    parameters:
      - name: payload
        value: '<JSON payload as single-quoted string>'
      - name: targetCluster
        value: "<targetCluster>"
```

---

## Resources Created by Workflow

1. **Namespace** — with labels: `environment`, `swc`, `billing-reference`, `timestamp`
2. **ResourceQuota** — CPU + memory + storage limits
3. **NetworkPolicy** — default deny-all ingress; optional allow-from rule if `AllowAccessFromNS` set

---

## NetworkPolicy allow-from warning

The allow-from NetworkPolicy selects the source namespace by its `name` label:

```yaml
namespaceSelector:
  matchLabels:
    name: <AllowAccessFromNS>
```

If the source namespace doesn't carry this label, the rule won't match. Fix:

```bash
kubectl label ns <source-ns> name=<source-ns>
```

---

## Optional Triage Agent Chain

After namespace creation, the agent can call `byoa-builder-guided` via A2A to configure
a namespace-scoped AI triage agent. The agent passes the namespace name as opening context:

```
POST /api/a2a/kagent/byoa-builder-guided/
{
  "jsonrpc": "2.0",
  "id": "ns-chain",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"kind": "text", "text": "Hi, I want a triage agent for namespace <NamespaceName>. Team: <Swc>."}]
    }
  }
}
```

---

## Source Files

| File | Location |
|------|----------|
| Agent CRD | `agents/kagent-triage/namespace-onboarding-agent.yaml` |
| WorkflowTemplate | `platform/argo-workflows/templates/namespace-onboarding/` |
| byoa-builder-guided | `agents/kagent-triage/byoa-builder-guided.yaml` |
| Sensor safeguards | `agents/kagent-triage/SENSOR-SAFEGUARDS.md` |
