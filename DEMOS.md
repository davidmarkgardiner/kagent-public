# Demos

Showcase index for everything in this repo worth presenting to colleagues.
Each demo is self-contained — read the per-area README for full setup. This
page is the map of **what to show** and **where the entry point lives**, so a
clean clone can replicate every pillar without hunting.

| # | Pillar | Entry point |
|---|---|---|
| 1 | Kagent + agentgateway observability | [`docs/observability/k-agent-alloy-grafana.md`](docs/observability/k-agent-alloy-grafana.md) |
| 2 | Agentgateway MVP control-plane demo set | [`platform/agentgateway/DEMO-SCHEMA-GATE.md`](platform/agentgateway/DEMO-SCHEMA-GATE.md) |
| 3 | Bring Your Own Agent (BYO-kagent) | [`infra/byo-kagent/README.md`](infra/byo-kagent/README.md) |
| 4 | Build Your Own Cluster Skill (ASO) | [`agents/aso-cluster-agent/README.md`](agents/aso-cluster-agent/README.md) |
| 5 | Agent-to-Agent (A2A) communication | [`a2a/kagent-hitl-skills-demo/README.md`](a2a/kagent-hitl-skills-demo/README.md) |
| 6 | Teams human-in-the-loop (HITL) | [`platform/teams-hitl/README.md`](platform/teams-hitl/README.md) |
| 7 | Kagent memory | [`docs/kagent-memory/README.md`](docs/kagent-memory/README.md) |
| 8 | Kagent knowledge base (RAG) | [`ai-platform/kagent-knowledge-base/README.md`](ai-platform/kagent-knowledge-base/README.md) |
| 9 | Cross-namespace A2A through Agentgateway | [`examples/cross-namespace-a2a/00-README.md`](examples/cross-namespace-a2a/00-README.md) |
| 10 | Smart triage fan-out | [`a2a/smart-triage-fanout-demo/README.md`](a2a/smart-triage-fanout-demo/README.md) |
| 11 | Kagent agent eval scorecard | [`observability/agent-evals/agent-eval-scorecard-demo.html`](observability/agent-evals/agent-eval-scorecard-demo.html) |

---

## 11. Kagent Agent Eval Scorecard

**Story.** Agents need a promotion gate: not "the reply sounded good", but a
repeatable score that checks diagnosis quality, evidence, tool use, namespace
safety, HITL compliance, remediation outcome, ticket hygiene, latency, and
cost. The eval path scores captured agent runs and full incident lifecycles so
prompt/tool/workflow regressions can fail before an agent is promoted.

**Replicable artefacts**

- TLDR and run commands — [`observability/agent-evals/README.md`](observability/agent-evals/README.md)
- Lifecycle scoring design — [`observability/agent-evals/LIFECYCLE-EVALUATION.md`](observability/agent-evals/LIFECYCLE-EVALUATION.md)
- Argo runtime hook — [`observability/agent-evals/ARGO-RUNTIME.md`](observability/agent-evals/ARGO-RUNTIME.md)
- Lift-and-shift handoff — [`KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md`](KAGENT-EVAL-LIFT-AND-SHIFT-HANDOFF.md)
- Local PR review request — [`KAGENT-EVAL-PR-REVIEW.md`](KAGENT-EVAL-PR-REVIEW.md)
- Visual walkthrough — [`observability/agent-evals/agent-eval-scorecard-demo.html`](observability/agent-evals/agent-eval-scorecard-demo.html)
- Golden cases — [`observability/agent-evals/cases/`](observability/agent-evals/cases/)
- Lifecycle case and sanitized Argo sample — [`observability/agent-evals/results/sample/lifecycle/`](observability/agent-evals/results/sample/lifecycle/)
- Deterministic scorer — [`observability/agent-evals/scripts/score-agent-run.py`](observability/agent-evals/scripts/score-agent-run.py)
- Lifecycle collector/scorer — [`observability/agent-evals/scripts/collect-lifecycle-evidence.py`](observability/agent-evals/scripts/collect-lifecycle-evidence.py)
- Batch runner — [`observability/agent-evals/scripts/run-agent-evals.py`](observability/agent-evals/scripts/run-agent-evals.py)
- Summary/Prometheus exporter — [`observability/agent-evals/scripts/summarize-agent-scores.py`](observability/agent-evals/scripts/summarize-agent-scores.py)
- Starter Grafana dashboard — [`observability/agent-evals/grafana/agent-eval-scorecard-dashboard.json`](observability/agent-evals/grafana/agent-eval-scorecard-dashboard.json)
- Starter alert rules — [`observability/agent-evals/alerting/agent-eval-rules.yaml`](observability/agent-evals/alerting/agent-eval-rules.yaml)

**What to show.** Open the visual walkthrough first, then run the sample score
commands from the README. Show the Argo workflow export becoming a normalized
lifecycle run, then show that missing HITL, missing verification, wrong
namespace, and forbidden `k8s_*` tools are hard failures regardless of the
numeric score.

---

## 1. Kagent + Agentgateway Observability

**Story.** Alloy DaemonSet scrapes kagent + agentgateway pods and tails their
logs, ships everything to LGTM (Mimir + Loki) via `remote_write`. Grafana
renders the kagent dashboard, runs ad-hoc PromQL / LogQL queries, and a
PrometheusRule fires alerts on token spend, gateway health, kagent restarts,
and suspicious log patterns.

**Replicable artefacts**

- Authoritative runbook (start here) — [`docs/observability/k-agent-alloy-grafana.md`](docs/observability/k-agent-alloy-grafana.md)
  Sections: Preconditions · Files · Deployment Plan · Proof Queries (PromQL + LogQL) · Work Verification Checklist · Live Lab Findings
- CAF-style handoff for the work Grafana/alerts/Argo flow — [`docs/observability/caf-style-observability-handoff.md`](docs/observability/caf-style-observability-handoff.md)
- Visual walkthrough — [`docs/observability/k-agent-observability-playbook.html`](docs/observability/k-agent-observability-playbook.html)
- POC evidence (real run output) — [`docs/observability/MIL-124-POC-EVIDENCE.md`](docs/observability/MIL-124-POC-EVIDENCE.md)
- Alloy collector (DaemonSet, RBAC, scrape + log pipeline, `remote_write`) — [`k8s/observability/k-agent-alloy.yaml`](k8s/observability/k-agent-alloy.yaml)
- Alert rules (PrometheusRule, 9 alert groups) — [`k8s/observability/k-agent-alerts.yaml`](k8s/observability/k-agent-alerts.yaml)
- Public-ready dashboard JSON (16 panels — availability, gateway rate/error/latency, token metrics and fallback, alert/workflow loop, logs) — [`observability/grafana/dashboards/k-agent-agentgateway-public-ready.json`](observability/grafana/dashboards/k-agent-agentgateway-public-ready.json)
- Legacy kagent dashboard JSON (8 panels) — [`observability/grafana/dashboards/k-agent-metrics.json`](observability/grafana/dashboards/k-agent-metrics.json)
- Grafana provisioning (drop into a vanilla Grafana to auto-load the dashboard against your LGTM):
  - Datasources, UIDs `kagent-mimir` / `kagent-loki` — [`observability/grafana/provisioning/datasources/`](observability/grafana/provisioning/datasources/)
  - Dashboard sidecar — [`observability/grafana/provisioning/dashboards/`](observability/grafana/provisioning/dashboards/)
- Agentgateway side (PodMonitor + agentgateway-specific PrometheusRule) — [`platform/agentgateway/monitoring.yaml`](platform/agentgateway/monitoring.yaml)

**Known gotchas — read [`docs/observability/MIL-124-review.md`](docs/observability/MIL-124-review.md) before applying to a fresh cluster:**

- Alloy ClusterRole is missing `pods/log` — log collection 403s silently.
- `CLUSTER_NAME` env defaults to `"unset"` — poisons every metric/log label; override per cluster.
- Dashboard + alerts depend on **kube-state-metrics** being installed.
- Loki stream labels include high-cardinality fields (`path`, `status`, `agent`, `model`); consider moving to structured metadata under load.

**What to show.** Open the public-ready dashboard over `Last 24 hours`, confirm
K-Agent pods, gateway scrape targets, gateway request rate, p95 latency, and
the Alertmanager-to-Argo log panel. Then trigger the synthetic alert route with
`scripts/observability/verify-k-agent-observability.sh --context {{KUBE_CONTEXT}} --synthetic-alert`
in an approved test window and show the `k-agent-alert-triage-*` workflow.
For the chaos/SRE operating model, open the presenter page
[`docs/ai-grafana/iteration-review-chaos-agent-demo.html`](docs/ai-grafana/iteration-review-chaos-agent-demo.html)
and walk the alert, Grafana MCP evidence, HITL approval, remediation, and
verification stages before running live commands.

---

## 2. Agentgateway MVP Control-Plane Demo Set

**Story.** agentgateway becomes the control plane between kagent, model
providers, MCP tools, and management-cluster agents. The demo set is staged
as schema-gated PRs: first verify the installed CRD shape, then show
gateway-injected SRE prompts, `/llm/v1` local-primary failover with Azure
fallback, the current Argo OpenAPI-to-MCP decision boundary, and a
cross-cluster A2A escalation path through the gateway.

**Replicable artefacts**

- Schema gate and verdict table (read first) — [`platform/agentgateway/DEMO-SCHEMA-GATE.md`](platform/agentgateway/DEMO-SCHEMA-GATE.md)
- Agentgateway reference README and deploy path — [`platform/agentgateway/README.md`](platform/agentgateway/README.md)
- PR 1 prompt enrichment policy — [`platform/agentgateway/policy-prompt-enrichment.yaml`](platform/agentgateway/policy-prompt-enrichment.yaml)
- PR 2 `/llm/v1` local-primary / Azure fallback manifest — [`platform/agentgateway/backend-llm-failover.yaml`](platform/agentgateway/backend-llm-failover.yaml)
- PR 2 failover runbook and safe failure triggers — [`platform/agentgateway/FAILOVER-DEMO.md`](platform/agentgateway/FAILOVER-DEMO.md)
- PR 3 Argo OpenAPI-to-MCP runbook and blocked/rescope guidance — [`platform/agentgateway/ARGO-OPENAPI-MCP-DEMO.md`](platform/agentgateway/ARGO-OPENAPI-MCP-DEMO.md)
- PR 3 gated manifests — [`platform/agentgateway/backend-argo-openapi-mcp.yaml`](platform/agentgateway/backend-argo-openapi-mcp.yaml), [`platform/agentgateway/policy-argo-openapi-mcp.yaml`](platform/agentgateway/policy-argo-openapi-mcp.yaml), [`platform/agentgateway/remotemcpserver-argo.yaml`](platform/agentgateway/remotemcpserver-argo.yaml)
- PR 4 A2A fleet escalation runbook — [`platform/agentgateway/A2A-FLEET-DEMO.md`](platform/agentgateway/A2A-FLEET-DEMO.md)
- PR 4 plan-B routing manifests — [`platform/agentgateway/service-a2a-fleet-agent.yaml`](platform/agentgateway/service-a2a-fleet-agent.yaml), [`platform/agentgateway/route-a2a-fleet-agent.yaml`](platform/agentgateway/route-a2a-fleet-agent.yaml), [`platform/agentgateway/policy-a2a-fleet-agent.yaml`](platform/agentgateway/policy-a2a-fleet-agent.yaml)
- Ingress allowlist carrying the demo paths — [`platform/agentgateway/istio-authorization-policy.yaml`](platform/agentgateway/istio-authorization-policy.yaml)

**Current verdicts from an approved non-production demo cluster on 2026-05-14**

- PR 1 is green after route-name inventory is aligned: `AgentgatewayPolicy.spec.backend.ai.prompt.prepend[]` exists and injects an org-wide SRE prompt at the gateway.
- PR 2 is green with auth-shape caveats: `spec.ai.groups[]` supports mixed providers, but per-provider Azure auth is API-key `secretRef`; UAMI requires the two-backend route-level pattern in the runbook.
- PR 3 is red/blocked as a direct OpenAPI target: `agentgatewaybackend.spec.mcp.targets[].openapi` is absent on this CRD release. Ship it only after a CRD upgrade or rescope it as a thin Argo MCP shim.
- PR 4 is amber/plan B: A2A-specific backend and policy fields are absent, so the demo uses plain HTTP routing to `kagent-controller` plus `ReferenceGrant`; identity is enforced at Istio ingress, not by gateway A2A auth.

**Known gotchas**

- On the captured cluster the Gateway is `agent-gw`, while repo manifests default to `ai-gateway`; align `parentRefs` before applying.
- Server-side dry-run does not prove secret key names, real ingress allowlists, or worker-to-management traffic. Test runtime paths after dry-run.
- Use `traffic.timeouts.request`, not the older `traffic.requestTimeout` shape.
- Canonical A2A path is `/a2a/fleet/` with a trailing slash; the runbook includes `/a2a/fleet`, `/a2a/fleet/`, and nested-path checks.

**What to show.** Open `DEMO-SCHEMA-GATE.md` first and walk the verdict table.
Apply PR 1 and PR 2 with server-side dry-run, then run the `/llm/v1`
happy-path and failover probes from `FAILOVER-DEMO.md`. For PR 3, show why
the direct OpenAPI target is blocked and explain the thin-shim alternative.
For PR 4, show the plan-B HTTPRoute/ReferenceGrant path and the real-ingress
identity test from `A2A-FLEET-DEMO.md`.

---

## 3. Bring Your Own Agent (BYO-kagent)

**Story.** A team wants their own kagent in the platform. They open a PR with
their `Agent` CRD; Argo Events picks it up; an orchestrator reviews; Flux
reconciles; Kyverno admission policies enforce tool/RBAC/network guards; the
agent lands live with the right ModelConfig wired through agentgateway.

**Replicable artefacts**

- Architecture + bootstrap — [`infra/byo-kagent/README.md`](infra/byo-kagent/README.md)
- Presenter showcase path — [`infra/byo-kagent/SHOWCASE-DEMO.md`](infra/byo-kagent/SHOWCASE-DEMO.md)
- Sandbox walkthrough (manual setup with NetworkPolicy + tool verification) — [`infra/byo-kagent/SANDBOX-ONBOARDING.md`](infra/byo-kagent/SANDBOX-ONBOARDING.md)
- Tool catalog (6 verified entries) — [`infra/byo-kagent/bootstrap-catalog/`](infra/byo-kagent/bootstrap-catalog/)
- Kyverno enforcement policies (6) — [`infra/byo-kagent/kyverno-policies/`](infra/byo-kagent/kyverno-policies/)
- Agentgateway ModelConfig wiring — [`platform/agentgateway/README.md`](platform/agentgateway/README.md)
- Skill scaffold for building new agents — [`agents/skills/byoa-agent-builder/SKILL.md`](agents/skills/byoa-agent-builder/SKILL.md)
  Includes `references/tool-catalog.md`, `references/system-prompt-patterns.md`, `assets/agent-template.yaml`.

**What to show.** Open the showcase path first. Then walk the BYO-kagent
architecture diagram, one Kyverno policy, the `byoa-agent-builder` skill, and
the Agent Gateway MCP authorization demo that projects `ToolGrant` into runtime
tool enforcement.

---

## 4. Build Your Own Cluster Skill — ASO Cluster Agent

**Story.** Natural-language request ("I'd like a cluster") becomes a
structured interview (name, region, size, dry-run), which is rendered into a
KRO instance backed by Azure Service Operator CRDs, applied through an Argo
Workflow, and certified by a follow-up trigger. Dry-run by default; real
provisioning is a separate opt-in script.

**Replicable artefacts**

- Architecture + cost policy + troubleshooting — [`agents/aso-cluster-agent/README.md`](agents/aso-cluster-agent/README.md)
- Turn-by-turn demo script (stakeholder walk-through) — [`agents/aso-cluster-agent/DEMO-SCRIPT.md`](agents/aso-cluster-agent/DEMO-SCRIPT.md)
- Design decisions (Plan A-lite chosen, why) — [`agents/aso-cluster-agent/DESIGN-DECISIONS.md`](agents/aso-cluster-agent/DESIGN-DECISIONS.md)
- Agent CRD — [`agents/aso-cluster-agent/agent/aso-provisioner-agent.yaml`](agents/aso-cluster-agent/agent/aso-provisioner-agent.yaml)
- Workflow template (6-step DAG: validate → render → apply → wait → cert-trigger → status) — [`agents/aso-cluster-agent/workflow/provision-aks-cluster-template.yaml`](agents/aso-cluster-agent/workflow/provision-aks-cluster-template.yaml)
- Workflow RBAC — [`agents/aso-cluster-agent/workflow/rbac.yaml`](agents/aso-cluster-agent/workflow/rbac.yaml)
- Deploy + smoke scripts (5 — RBAC, dry-run, bad-input, deploy-home, teardown) — [`agents/aso-cluster-agent/scripts/`](agents/aso-cluster-agent/scripts/)
- Sibling skill scaffolds — [`agents/skills/aks-specialist/SKILL.md`](agents/skills/aks-specialist/SKILL.md), [`agents/skills/fleet-health/SKILL.md`](agents/skills/fleet-health/SKILL.md), [`agents/skills/k8s-troubleshooter/SKILL.md`](agents/skills/k8s-troubleshooter/SKILL.md)

**What to show.** Run `bash agents/aso-cluster-agent/scripts/deploy-home-dryrun.sh`,
then open kagent UI and follow `DEMO-SCRIPT.md` turn-by-turn. Show the
generated KRO/ASO YAML and the Argo Workflow execution.

---

## 5. Agent-to-Agent (A2A) Communication

**Story.** A coordinator agent receives a request, calls a skill-loader agent
over kagent agent-as-tool A2A, then calls an approval agent that produces a
human approval packet. The Argo workflow posts the packet to a (mock) Teams
bot, suspends, resumes on the callback, and re-invokes the coordinator with
the human decision.

**Replicable artefacts**

- Demo README + manual A2A test instructions — [`a2a/kagent-hitl-skills-demo/README.md`](a2a/kagent-hitl-skills-demo/README.md)
- Three demo agents (`demo-a2a-coordinator-agent`, `demo-skill-loader-agent`, `demo-hitl-approval-agent`) — [`a2a/kagent-hitl-skills-demo/agents.yaml`](a2a/kagent-hitl-skills-demo/agents.yaml)
- Argo Workflow orchestrating the three agents — [`a2a/kagent-hitl-skills-demo/workflow.yaml`](a2a/kagent-hitl-skills-demo/workflow.yaml)
- Workflow RBAC — [`a2a/kagent-hitl-skills-demo/workflow-rbac.yaml`](a2a/kagent-hitl-skills-demo/workflow-rbac.yaml)
- Mock Teams bot runtime — [`a2a/kagent-hitl-skills-demo/mock-bot-runtime.yaml`](a2a/kagent-hitl-skills-demo/mock-bot-runtime.yaml)
- One-command runner — [`a2a/kagent-hitl-skills-demo/scripts/run-demo.sh`](a2a/kagent-hitl-skills-demo/scripts/run-demo.sh)
- A2A protocol reference (JSON-RPC 2.0, trailing-slash requirement) — [`a2a/README.md`](a2a/README.md)
- Standalone curl example — [`a2a/examples/a2a-call-example.sh`](a2a/examples/a2a-call-example.sh)
- Review notes (label drift, RBAC, image-tag polish — non-blocking) — [`docs/checkpoint/MIL-126-review.md`](docs/checkpoint/MIL-126-review.md)

**Prerequisites.** kagent in `kagent` namespace with `default-model-config`,
Argo Workflows in `argo`, Argo Events in `argo-events`, plus `kubectl`,
`argo`, `jq` locally.

**What to show.** Run `bash a2a/kagent-hitl-skills-demo/scripts/run-demo.sh`;
watch the Argo workflow suspend at the approval step; POST the approval
callback; show the workflow resume.

---

## 6. Teams Human-in-the-Loop (HITL)

**Story.** The HITL gate is the suspend/resume step from Demo 5 expressed as a
generic platform pattern: agent decides an action needs human sign-off →
workflow suspends → Teams (or Slack/Discord/curl) sends an approval card →
Argo Events sensor catches the callback → workflow resumes or terminates.

**Replicable artefacts**

- Architectural design + decision matrix (Options A/B/C) + four testing paths — [`platform/teams-hitl/README.md`](platform/teams-hitl/README.md)
- Argo Events sensors (approve, reject, expire) — [`platform/teams-hitl/sensor.yaml`](platform/teams-hitl/sensor.yaml)
- HITL in action (workflow shipped with the A2A demo) — [`a2a/kagent-hitl-skills-demo/workflow.yaml`](a2a/kagent-hitl-skills-demo/workflow.yaml)

**What to show.** Walk the architecture diagram in the README. Apply
`sensor.yaml`. Replay the A2A demo and `curl` the approve / reject / expire
callbacks to demonstrate each path.

---

## 7. Kagent Memory

**Story.** Three different "memory" scopes coexist in kagent: A2A session
memory, the native long-term memory API (vector store keyed by
`agent_name` + `user_id`), and the agent-facing memory tools
(`prefetch_memory`, `load_memory`, `save_memory`, auto-save). The first two
work on the captured non-production demo cluster today; the third is gated on an
embedding-capable ModelConfig.

**Replicable artefacts**

- Authoritative reference (Helm enablement, CRD schema, tools, gotchas) — [`a2a/memory-reference.md`](a2a/memory-reference.md)
- Live evidence from `red` plus native-vs-custom-MCP memory guide — [`docs/kagent-memory/README.md`](docs/kagent-memory/README.md)
- Smoke test (controller config, native API, A2A session continuity) — [`a2a/scripts/kagent-memory-smoke.sh`](a2a/scripts/kagent-memory-smoke.sh)

**What to show.** Run `bash a2a/scripts/kagent-memory-smoke.sh` with your
kube-context pointed at the demo cluster. Walk through the three scenario
results in `docs/kagent-memory/README.md`. Open `a2a/memory-reference.md`
§"Build Plan to Enable Full Agent Memory" to show the path to production.

---

## 8. Kagent Knowledge Base (RAG)

**Story.** A POC of the kagent RAG pattern: `doc2vec` indexes the platform
documentation into a vector store, a `querydoc` MCP server exposes
`query_documentation` to agents, and the indexer runs on a CronJob. The
agent reads platform docs at runtime instead of being trained on them.

**Replicable artefacts**

- Architecture + prerequisites + local + cluster flows — [`ai-platform/kagent-knowledge-base/README.md`](ai-platform/kagent-knowledge-base/README.md)
- HTML walkthrough — [`ai-platform/kagent-knowledge-base/platform-kb-poc-presentation.html`](ai-platform/kagent-knowledge-base/platform-kb-poc-presentation.html)
- Build/validate scripts — [`ai-platform/kagent-knowledge-base/scripts/`](ai-platform/kagent-knowledge-base/scripts/)
- Cluster manifests (Kustomize) — [`ai-platform/kagent-knowledge-base/k8s/`](ai-platform/kagent-knowledge-base/k8s/)
- Options write-up (storage / provider / retrieval choices) — [`docs/KAGENT-RAG-KNOWLEDGE-BASE-OPTIONS.md`](docs/KAGENT-RAG-KNOWLEDGE-BASE-OPTIONS.md)
- Repo-access permissions write-up — [`docs/KNOWLEDGE-BASE-AGENT-REPO-ACCESS.md`](docs/KNOWLEDGE-BASE-AGENT-REPO-ACCESS.md)
- Review (read before promoting to production) — [`docs/checkpoint/kagent-knowledge-base-review.md`](docs/checkpoint/kagent-knowledge-base-review.md)

**Known gotchas — flagged in `kagent-knowledge-base-review.md`:**

- CronJob hardcodes `EMBEDDING_PROVIDER=openai`; cluster indexer doesn't yet support Azure (local builder does). Parameterise or document explicitly.
- No `securityContext` on the workloads — will fail under restricted Pod Security Standards. Add `runAsNonRoot`, `seccompProfile`, drop capabilities.
- `RemoteMCPServer.timeout` is 10s; bump to 30s before real load.
- A seed `docs/platform-kb/` corpus needs to exist before the indexer has anything to index.

**What to show.** Set `OPENAI_API_KEY`, run
`bash ai-platform/kagent-knowledge-base/scripts/build-platform-kb-db.sh`, then
`bash ai-platform/kagent-knowledge-base/scripts/smoke-querydoc-local.sh`.
For the cluster path, run `validate.sh` then `kubectl apply -k k8s/`.

---

## Tracked review checkpoints (read before promoting any demo)

- [`docs/checkpoint/MIL-126-review.md`](docs/checkpoint/MIL-126-review.md) — A2A + HITL + skills demo review
- [`docs/checkpoint/kagent-knowledge-base-review.md`](docs/checkpoint/kagent-knowledge-base-review.md) — KB POC review
- [`docs/observability/MIL-124-review.md`](docs/observability/MIL-124-review.md) — Observability stack review
- [`platform/agentgateway/DEMO-SCHEMA-GATE.md`](platform/agentgateway/DEMO-SCHEMA-GATE.md) — Agentgateway MVP demo schema gate and CRD verdicts

These reviews list the deferred fixes that don't block a controlled demo but
should be addressed before applying any of this to a shared / production
cluster.
