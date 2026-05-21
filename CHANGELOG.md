# Changelog

## [2026-05-21] - K-Agent memory, BYO agents, chaos drills, observability roadmap

High-level handoff entry for the latest public-safe K-Agent platform materials.

### Added
- `infra/byo-kagent/SHOWCASE-DEMO.md` - presenter path for Bring Your Own Agent onboarding, including demo agents, model configuration, skills, tools, memory, and Agent Gateway control points.
- `observability/managed-lgtm-integration/GITLAB-ISSUE-KAGENT-AGENTIC-OBSERVABILITY-ROADMAP.md` - GitLab-ready issue body for kagent, Agent Gateway, agentic workflow, LGTM dashboard, rule, alert, and evidence gaps.

### Changed
- `docs/kagent-memory/README.md` and `docs/memory-integration.md` now compare native kagent memory with the custom MCP memory option and call out when to use each pattern.
- `chaos/litmus/WORK-INSTALL.md` now includes a fire-drill operating model for LitmusChaos events, agent triage, GitLab issue creation, SRE response tracking, and agent-platform fault drills.
- `DEMOS.md` now points the memory demo at live evidence plus the native-vs-custom-MCP guide, and links the BYO Agent showcase as the starting point for presenter walkthroughs.
- `README.md` now links this changelog from Quick Navigation so recent committed scope is easy to find after a pause.

## [Unreleased] — refresh/platform-monorepo

Complete repo refresh: narrow Alertmanager→Redpanda PoC → full platform monorepo.

### Added
- `infra/kro-stack/` — KRO + ASO declarative AKS cluster lifecycle
- `infra/workload-identity/` — OIDC discovery + federated identity credentials
- `infra/byo-kagent/` — Bring Your Own Agent platform (CRDs, Kyverno policies)
- `platform/argo-workflows/` — WorkflowTemplates: namespace onboarding, app/MCP/BYO-kagent onboarding, ASO provisioning, certification, canary
- `platform/argo-events/` — EventBus, EventSources, Sensors, RBAC, sensor safeguards
- `platform/agentgateway/` — AI gateway: Azure OpenAI, KubeAI, vLLM backends
- `platform/aks-mcp/` — AKS-MCP deployment manifests
- `platform/teams-hitl/` — Human-in-the-loop approval gate
- `observability/alloy-eventhub-pipeline/` — Grafana Alloy → Azure Event Hub OTLP
- `observability/managed-lgtm-integration/` — LGTM alert wiring into Argo Events
- `observability/prometheus-alertmanager/` — AlertManager → Argo Events
- `agents/kagent-triage/` — Worker-cluster AI triage: Agent CRs, sensors, workflow, BYOA builders
- `agents/aso-cluster-agent/` — Chat-to-cluster-provisioning PoC
- 
- `agents/networking-triage/` — Container Network Insights Agent
- `agents/skills/` — kagent skill manifests
- `a2a/` — A2A protocol memory reference and call examples

### Changed
- Alertmanager→Redpanda/webhook PoC moved to `platform/argo-events/sources/`
- `README.md` rewritten as platform monorepo navigation hub

### Important version pins
- Argo Events chart pinned to **2.4.14 / app v1.9.5** — v1.9.6+ crashes on EventHub messages without `messageId` (upstream Issue #3595)

## [0.1.0] — Initial PoC

Alertmanager → Redpanda/Kafka → Argo Events Kafka EventSource → consumer pod.
