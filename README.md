# kagent-public

Platform engineering monorepo — GitOps-first delivery, fleet automation, and AI-driven SRE on Azure Kubernetes Service.

This is the primary working repo for a six-month platform modernisation programme targeting declarative AKS fleet management, Argo-based orchestration, and AI-driven SRE via kagent.

---

## What is this?

A complete platform stack for production Kubernetes on Azure:

- **KRO + ASO** — declarative AKS cluster lifecycle; replace ARM templates with GitOps PRs
- **Flux CD** — single reconciliation plane across management + worker clusters
- **Argo Workflows + Argo Events** — namespace onboarding, cluster provisioning, fleet updates, AI-driven triage
- **kagent** — CNCF Sandbox AI agent framework ([upstream](https://github.com/kagent-dev/kagent))
- **agentgateway** — unified LLM + MCP + A2A routing ([upstream](https://github.com/envoyproxy/ai-gateway))
- **AKS-MCP** — kubectl/az access via Model Context Protocol ([upstream](https://github.com/Azure/aks-mcp))

---

## Repository Layout

```
infra/              KRO + ASO cluster provisioning, workload identity, BYO-kagent platform
platform/           Argo Workflows templates, Argo Events sources/sensors, agentgateway, HITL
observability/      Alloy → EventHub pipeline, LGTM stack, AlertManager → Argo Events
agents/             kagent Agent CRs, sensors, skills — organised by agent purpose
a2a/                A2A protocol memory reference + call examples
docs/               Architecture diagrams, runbooks, handover notes
examples/           Quickstart and sample payloads
```

---

## Quick Navigation

| I want to… | Go to |
|---|---|
| Provision a new AKS cluster declaratively | [`infra/kro-stack/`](infra/kro-stack/README.md) |
| Onboard a namespace via PR | [`platform/argo-workflows/templates/namespace-onboarding/`](platform/argo-workflows/templates/namespace-onboarding/) |
| Set up AI triage for a namespace | [`agents/kagent-triage/`](agents/kagent-triage/README.md) |
| Wire K8s events → EventHub → AI diagnosis | [`observability/alloy-eventhub-pipeline/`](observability/alloy-eventhub-pipeline/) |
| Deploy the AI gateway (LLM + MCP + A2A) | [`platform/agentgateway/`](platform/agentgateway/README.md) |
| Add a HITL approval gate for remediation | [`platform/teams-hitl/`](platform/teams-hitl/README.md) |
| Bring Your Own Agent to the platform | [`infra/byo-kagent/`](infra/byo-kagent/README.md) |
| Understand A2A + kagent memory | [`a2a/`](a2a/README.md) |
| See the full programme scope | [`STATEMENT-OF-WORK.md`](STATEMENT-OF-WORK.md) |

---

## Prerequisites

- Kubernetes cluster (AKS or kind for local dev)
- [KRO](https://github.com/kro-run/kro) on management cluster
- [Azure Service Operator v2](https://github.com/Azure/azure-service-operator) on management cluster
- [Argo Workflows v3.x](https://argoproj.github.io/argo-workflows/) in `argo` namespace
- [Argo Events](https://argoproj.github.io/argo-events/) in `argo-events` namespace — **pin chart 2.4.14 / app v1.9.5** (see [EventHub regression note](platform/argo-events/README.md#eventhub-version-pin))
- [kagent v0.8.0+](https://github.com/kagent-dev/kagent) in `kagent` namespace

---

## Public Safety

Do not commit secrets, private hostnames, cluster IPs, connection strings, tokens, or internal URLs.
Use `{{PLACEHOLDER}}` tokens for all environment-specific values. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Related

- [kagent upstream](https://github.com/kagent-dev/kagent)
- [A2A specification](https://a2aproject.org)
- [Argo Workflows docs](https://argoproj.github.io/argo-workflows/)
- [Argo Events docs](https://argoproj.github.io/argo-events/)
- [KRO docs](https://kro.run)
- [Azure Service Operator docs](https://azure.github.io/azure-service-operator/)
