---
name: onboarding-platform
description: >
  Three-pillar agentic onboarding platform. Routes to the correct onboarding journey:
  cluster (new AKS cluster via ASO/KRO), namespace (quota + NetworkPolicy on existing cluster),
  or application (GitOps YAML generation). Use when a user wants to onboard any resource
  onto the shared platform. Mirrors the BYOA builder pattern from byoa-agent-builder.
metadata:
  openclaw:
    emoji: "🚀"
    requires:
      anyBins: ["kubectl"]
---

# Agentic Onboarding Platform

Three interview-driven agents that provision platform resources. Each agent collects
requirements, confirms with the user, then either submits an Argo Workflow or generates
GitOps YAML. No resources are created without explicit user confirmation.

Read `references/cluster-interview.md`, `references/namespace-interview.md`, and
`references/app-interview.md` before starting. Use `assets/agent-template.yaml` when
generating or modifying agent CRDs.

---

## Routing

Determine which pillar the user needs:

| User says | Route to |
|-----------|----------|
| "new cluster", "AKS cluster", "provision a cluster" | **Pillar 1** — cluster-onboarding-agent |
| "new namespace", "namespace on existing cluster" | **Pillar 2** — namespace-onboarding-agent |
| "deploy my app", "onboard my service", "generate manifests" | **Pillar 3** — app-onboarding-agent |
| Unclear | Ask: "Are you looking to create a cluster, a namespace, or deploy an application?" |

---

## Pillar 1 — Cluster Onboarding

**Agent CRD:** `agents/kagent-triage/cluster-onboarding-agent.yaml`
**Calls:** `provision-aks-cluster` WorkflowTemplate in namespace `argo`
**Interview:** See `references/cluster-interview.md`

Entry point via A2A:
```bash
curl -s -X POST http://<kagent-host>/api/a2a/kagent/cluster-onboarding-agent/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"I need a new AKS cluster"}]}}}'
```

Key constraints (enforced by workflow, not agent):
- Kubernetes 1.32, Azure RBAC on, Defender on, local accounts off
- Dry-run default: `true` — change annotation `DRY_RUN_DEFAULT` on the agent to `false` for real provisioning

---

## Pillar 2 — Namespace Onboarding

**Agent CRD:** `agents/kagent-triage/namespace-onboarding-agent.yaml`
**Calls:** `namespace-onboarding-template` WorkflowTemplate → Namespace + ResourceQuota + NetworkPolicy
**Interview:** See `references/namespace-interview.md`

Optional chain: after namespace creation, agent can call `byoa-builder-guided` via A2A to
set up an AI triage agent for the new namespace.

NetworkPolicy note: allow-from rule selects source namespace by `name` label.
If missing: `kubectl label ns <source> name=<source>`

---

## Pillar 3 — Application Onboarding

**Agent CRD:** `agents/kagent-triage/app-onboarding-agent.yaml`
**Output:** GitOps YAML only — never applies to cluster directly
**Interview:** See `references/app-interview.md`

Generated artifacts:
- `deployment.yaml` + `service.yaml` (always)
- `virtualservice.yaml` (Istio ingress, optional)
- `authorizationpolicy.yaml` (Istio auth, optional)
- `hpa.yaml` (optional)
- `request.yaml` for BYO-KAgent submission (optional)

---

## Deploying the Agents

```bash
# Apply all three onboarding agents
kubectl apply -f agents/kagent-triage/cluster-onboarding-agent.yaml
kubectl apply -f agents/kagent-triage/namespace-onboarding-agent.yaml
kubectl apply -f agents/kagent-triage/app-onboarding-agent.yaml

# Verify
kubectl get agents -n kagent | grep onboarding
```

---

## Testing via A2A

```bash
# Cluster agent
curl -s -X POST http://<kagent-host>/api/a2a/kagent/cluster-onboarding-agent/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Hi, I want a cluster called test-cluster in uksouth, small size"}]}}}' \
  | jq -r '.result.artifacts[].parts[].text'

# Namespace agent
curl -s -X POST http://<kagent-host>/api/a2a/kagent/namespace-onboarding-agent/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"I need a namespace called payments-dev"}]}}}' \
  | jq -r '.result.artifacts[].parts[].text'

# App agent
curl -s -X POST http://<kagent-host>/api/a2a/kagent/app-onboarding-agent/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"I want to deploy my app called payments-api"}]}}}' \
  | jq -r '.result.artifacts[].parts[].text'
```

A2A notes:
- Trailing slash on agent name URL is REQUIRED — 404 without it
- `parts` must include `"kind": "text"` field
- Response: `.result.artifacts[].parts[].text`

---

## Related Skills

- [`byoa-agent-builder`](../byoa-agent-builder/SKILL.md) — build a triage/remediation Agent CRD via interview
- [`kagent-namespace-agent`](../kagent-namespace-agent/) — namespace-scoped triage agent pattern
