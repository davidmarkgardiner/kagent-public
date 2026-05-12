---
name: onboarding-platform
description: Three-pillar platform onboarding. Routes to cluster, namespace, or app onboarding agents based on what the user needs. Use when a team wants to onboard anything new to the platform — a new AKS cluster, a new namespace, or a new application.
metadata:
  openclaw:
    emoji: "🚀"
    requires:
      anyBins: ["kubectl"]
---

# Onboarding Platform

Three-pillar guided onboarding for the shared platform. Each pillar has a dedicated
interview-driven agent. Read the relevant reference file before starting.

---

## Routing

Ask: "What do you need to onboard?"

| User says | Pillar | Agent |
|-----------|--------|-------|
| "cluster" / "I need a new AKS cluster" | 1 | `cluster-onboarding-agent` |
| "namespace" / "I need a namespace" | 2 | `namespace-onboarding-agent` |
| "app" / "I want to deploy my application" | 3 | `app-onboarding-agent` |

Route via A2A: `POST /api/a2a/kagent/{agent-name}/`

If unsure which pillar applies, ask: "Are you onboarding a new **cluster**, a new **namespace**
on an existing cluster, or a new **application**?"

---

## Reference Files

- `references/cluster-interview.md` — Q→parameter mapping, region/size enums, platform-enforced values
- `references/namespace-interview.md` — Q→parameter mapping, NetworkPolicy label warning, optional chain
- `references/app-interview.md` — Q→output mapping, generated file list, request.yaml schema

## Asset Files

- `assets/agent-template.yaml` — base `kagent.dev/v1alpha2` Agent CRD for onboarding agents
- `assets/request-template.yaml` — BYO-KAgent `request.yaml` template

---

## Design Principles

| Principle | Implementation |
|-----------|---------------|
| Interview → YAML, never LLM → live cluster | Agents generate YAML; Argo workflows do K8s work |
| dryRun: true default | Cluster agent defaults dry-run; user must opt out explicitly |
| Namespace anchoring | CRITICAL — always use exact namespace names, character-for-character |
| RBAC separation | Agent SA submits Workflows only; workflow SA does actual K8s work |
| Confirmation gate | Each agent requires an exact confirmation phrase before acting |
| No new WorkflowTemplates | All three pillars reuse existing templates |
