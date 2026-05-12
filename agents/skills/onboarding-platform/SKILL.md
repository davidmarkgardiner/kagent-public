---
name: onboarding-platform
description: Three-pillar onboarding assistant for cluster, namespace, and app requests. Use when a user needs a guided interview that either triggers existing Argo WorkflowTemplates for cluster or namespace onboarding, or returns Kubernetes-only app YAML for dry-run review.
metadata:
  openclaw:
    requires:
      anyBins: ["kubectl"]
---

# Onboarding Platform

Guide users through the three onboarding pillars:

1. Cluster onboarding: collect AKS cluster requirements and submit the existing `provision-aks-cluster` WorkflowTemplate with `dryRun: true` by default.
2. Namespace onboarding: collect namespace, quota, network policy, and billing data, then submit the existing `namespace-onboarding-template` WorkflowTemplate.
3. App onboarding: collect app deployment data and return Kubernetes-only YAML. Do not apply it and do not include Azure resources.

Read the relevant reference before starting:

- `references/cluster-interview.md`
- `references/namespace-interview.md`
- `references/app-interview.md`

Use `assets/agent-template.yaml` as the Agent CRD shape and `assets/request-template.yaml` for the Workflow and app manifest request shapes.

---

## Routing

Ask the user which pillar they need unless it is obvious from their request:

- Cluster: new AKS or managed cluster request.
- Namespace: team space, quota, billing, or network policy request.
- App: Deployment, Service, or Kubernetes YAML request.

If a request spans multiple pillars, handle them in this order: cluster, namespace, app. Finish one pillar before moving to the next.

---

## Cluster Pillar

Use `references/cluster-interview.md`.

Output or submit a Workflow that references `provision-aks-cluster`. The dry-run value must default to `true`.

Never generate UK8SClusterPublic, ASO, or Azure resource YAML in this pillar.

---

## Namespace Pillar

Use `references/namespace-interview.md`.

Output or submit a Workflow that references `namespace-onboarding-template`. The payload keys must match the existing WorkflowTemplate:

- `NamespaceName`
- `Swc`
- `Environment`
- `ResourceQuotaCPU`
- `ResourceQuotaMemoryGB`
- `ResourceQuotaStorageGB`
- `AllowAccessFromNS`
- `BillingReference`
- `ManagedAksClusterName`

---

## App Pillar

Use `references/app-interview.md`.

Return YAML only. Do not submit a Workflow. Do not call `kubectl apply`. Do not include Azure or ASO resources.

The generated YAML must pass:

```bash
kubectl apply --dry-run=client -f app-onboarding.yaml
```

---

## Validation Checklist

Before finalizing:

- [ ] Correct pillar selected and completed.
- [ ] Cluster pillar defaults `dryRun` to `true`.
- [ ] Cluster and namespace pillars reference existing WorkflowTemplates only.
- [ ] Namespace payload uses exact keys consumed by `namespace-onboarding-template`.
- [ ] App pillar outputs Kubernetes-only YAML and no Azure resources.
- [ ] App YAML has no placeholders.
- [ ] App YAML includes resource requests, limits, probes, and restricted security context.
- [ ] User-facing output includes the next validation or status command.
