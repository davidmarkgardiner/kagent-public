# Changelog

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
