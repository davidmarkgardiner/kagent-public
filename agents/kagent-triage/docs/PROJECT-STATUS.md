# K8s Event Triage — Project Status

**Companion Document to:** `CDA-DESIGN-AUTHORITY.md`
**Document Owner:** Platform Engineering — David Gardiner
**Version:** 1.0 (Draft)
**Date:** 2026-04-28
**Status:** Snapshot of current implementation + designs in flight

---

## Purpose

Where the project is *today* — what is built, what is designed, and what is pending. The CDA covers the formal design authority position; this document complements it with concrete component status, the agent roster, and the architecture decisions driving them.

Sections that follow:

1. Executive snapshot
2. System design — agent interaction, namespace routing, output paths, ticketing integrations
3. Component status — HITL, A2A, LGTM, agentgateway, Skills, Memory
4. Agent architecture pattern — key design decisions
5. Agent cards (grouped by tier/persona)
6. Open work + risks

---

# 1. Executive Snapshot

| Theme | State | Detail |
|-------|-------|--------|
| Event ingestion (Alloy → Event Hub → Argo Events) | **Production** | Three-tier pipeline (critical / warnings / infra) tested end-to-end on `{{CLUSTER_NAME}}` |
| Argo Workflows triage DAG | **Production** | parse-otlp → fan-out → KAgent A2A → GitLab + Teams |
| KAgent A2A protocol | **Production** | JSON-RPC 2.0, `message/send`, agent-as-tool proven (Kimi 6/6 calls, Mar 2026) |
| Specialist agent roster | **Phase 2** | 11 namespace-scoped agents deployed on worker cluster bundle; ~20 planned |
| agentgateway (replacing LiteLLM) | **Phase 1 — Parallel** | Deployed alongside LiteLLM; UAMI/workload identity working; per-agent migration in flight |
| Managed LGTM integration | **Designed** | Full design in `aks-mgmt-stack/k8s-event-triage/managed-lgtm-integration/` — pending platform-team Q&A |
| Skills (kagent 0.8.0+ git/OCI bundles) | **Implemented, sparse** | Mechanism deployed; library currently shallow — grows via the "learning loop" |
| Memory (pgvector backend) | **Designed, blocked** | kagent reverted memory in v0.8.3; pgvector ready on red cluster; awaiting kagent re-enable |
| HITL (Teams approval gate) | **Designed + smoke-tested** | Istio VirtualService + AuthorizationPolicy live; mock bot + 5-min smoke test in repo |
| GitLab ticketing | **Production** | Personal project today; engineering-rollout plan to dedicated project + round-robin assignment |
| ServiceNow / ADO integrations | **Designed** | MCP servers; not yet implemented |

---

# 2. System Design

## 2.1 Management cluster orchestrating worker clusters

The management cluster is the **brain**. Worker clusters are the **eyes and hands**. Cross-cluster reads happen via AKS-MCP using Azure workload identity; events flow back via Azure Event Hub.

```
┌─────────────────────────────── MANAGEMENT CLUSTER ────────────────────────────────┐
│                                                                                    │
│  ┌──────────────────┐    ┌────────────────────────┐    ┌─────────────────────────┐│
│  │ Argo Events       │    │ Argo Workflows         │    │ kagent (system agents)   ││
│  │ EventBus (NATS)   │    │ WorkflowTemplate:      │    │  ─ infra-agent           ││
│  │ EventSource ────  │───▶│   k8s-triage-critical  │───▶│  ─ network-agent         ││
│  │   (Kafka/Event    │    │   k8s-triage-warnings  │    │  ─ change-agent          ││
│  │    Hub consumer)  │    │   k8s-triage-infra     │    │  ─ cost-agent            ││
│  │ Sensors per tier  │    │ DAG:                   │    │  ─ observability-agent   ││
│  └──────────────────┘    │  parse-otlp → fan-out  │    │  ─ incident-agent        ││
│         ▲                 │  → call agent (A2A)    │    │  ─ compliance-agent      ││
│         │                 │  → HITL gate (opt)     │    │  ─ gitops-remediation    ││
│         │                 │  → ticket + notify     │    └────────────┬─────────────┘│
│         │                 └────────────────────────┘                 │              │
│         │                                                            │ A2A          │
│  ┌──────┴────────┐    ┌────────────────────────┐    ┌────────────────▼────────────┐│
│  │ Azure Event   │    │ AKS-MCP (UAMI cross-   │    │ agentgateway                ││
│  │ Hub topics:   │    │ cluster kubectl)        │    │  • LLM proxy (Azure OpenAI ││
│  │  k8s-events   │    │ Federated Identity to:  │    │    via UAMI)                ││
│  │  alerts       │    │  worker-cluster-A       │    │  • MCP gateway              ││
│  └──────────────┘    │  worker-cluster-B       │    │  • A2A gateway              ││
│         ▲             │  worker-cluster-C       │    │  • OTel observability       ││
│         │             └────────────────────────┘    └─────────────────────────────┘│
│         │                                                                            │
└─────────┼────────────────────────────────────────────────────────────────────────────┘
          │ Kafka/TLS (SAS Send-only)
          │
┌─────────┼─────────────────── WORKER CLUSTERS (1..N) ─────────────────────────────────┐
│         │                                                                            │
│  ┌──────┴────────┐    ┌────────────────────────┐    ┌─────────────────────────────┐ │
│  │ Alloy          │    │ Worker-local kagent    │    │ Application + system        │ │
│  │  • k8s events  │◀───│ (only for namespaces   │    │ namespaces:                  │ │
│  │  • pod logs    │    │  where worker-local    │    │  cert-manager / kyverno /   │ │
│  │  • metrics     │    │  triage runs)          │    │  external-secrets / kro /   │ │
│  │  ↓             │    │ Specialist agents:     │    │  reloader / istio-system /  │ │
│  │  Event Hub     │    │  cert-manager-agent    │    │  flux-system / monitoring   │ │
│  │  Mimir/Loki/   │    │  kyverno-agent         │    │  + workload namespaces      │ │
│  │  Tempo         │    │  kro-agent ...         │    │                              │ │
│  └────────────────┘    └────────────────────────┘    └─────────────────────────────┘ │
│                                                                                       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Why split mgmt vs worker

| Concern | Management cluster | Worker cluster |
|---------|--------------------|-----------------|
| Cross-cluster orchestration | Yes — AKS-MCP, multi-cluster routing | No — only sees self |
| System namespaces it cares about | `argo`, `argo-events`, `kagent`, `agentgateway-system`, `aks-mcp` | `cert-manager`, `kyverno`, `kro`, `external-secrets`, `monitoring`, `istio-system`, `flux-system` etc. |
| Triage location | Aggregates events from N workers | Local triage when EventHub round-trip is unnecessary |
| LLM access | Yes (via agentgateway) | Yes (via agentgateway pointed at mgmt or local) |

The decision to do **worker-local triage** for namespaces that don't need cross-cluster context (cert-manager, kyverno, kro etc.) shortens the triage loop from seconds to milliseconds and removes the EventHub dependency for the most common failure modes.

## 2.2 Namespace → Agent routing

Routing happens inside the workflow's `parse-otlp` step. Two ConfigMaps drive it:

| ConfigMap | Key | Purpose |
|-----------|-----|---------|
| `agent-routing` | `namespace-routes` (JSON) | Map of namespace → agent name |
| `agent-routing` | `reason-routes` (JSON) | Map of event reason → agent name (overrides namespace-route for cross-cutting reasons like `Evicted`, `NodeNotReady`) |

```
Event arrives ─▶ parse-otlp extracts: namespace, reason
                       │
                       ▼
                 Reason match? (Evicted, NodeNotReady, FailedMount, ...)
                   │YES → reason-route agent
                   │NO  → namespace-route agent
                   │      │
                   │      └── No match → sre-triage-agent (default)
                       ▼
                 Workflow calls A2A: POST /api/a2a/kagent/<agent>/
                       │
                       ▼
                 Agent loads:
                   • System prompt (in CRD)
                   • Skills (mounted at /skills via skills-init)
                   • Memory (load_memory tool, pgvector — when re-enabled)
                   • Tools (kagent-tool-server via MCP)
                       │
                       ▼
                 Agent diagnoses → returns analysis JSON
```

Routing config lives at `eventhub-otlp-pipeline/tier-critical/agent-routing.yaml`.

## 2.3 How agents pick up Skills, Context, and Memory

| Layer | Source | Loaded When | Mechanism |
|-------|--------|-------------|-----------|
| **System prompt** | `Agent.spec.declarative.systemMessage` | Pod start | Inline in CRD |
| **A2A skill metadata** | `Agent.spec.declarative.a2aConfig.skills` | Pod start | Discovery / catalog only — not executed |
| **Executable skills** | `Agent.spec.skills.gitRefs` or `refs` (OCI) | Pod start | `skills-init` initContainer clones into `emptyDir` at `/skills`; main container mounts read-only |
| **Tools** | `Agent.spec.declarative.tools` (MCP server refs) | Per-request | RemoteMCPServer or in-cluster Service; agentgateway can act as central MCP gateway |
| **Memory** | `Agent.spec.declarative.memory` (when re-enabled) | Per-request | `load_memory(query)` returns prior summaries; `save_memory(text)` writes back; pgvector backend |
| **Prompt template data** | `Agent.spec.declarative.promptTemplate.dataSources` (ConfigMap-backed) | Per-request | Cluster-wide builtins (e.g. `kagent-builtin-prompts`) plus per-namespace overrides |

```
                    Per-Request Triage Flow
       ┌──────────────────────────────────────────────────┐
       │ Workflow sends A2A message → agent pod            │
       └─────────────────────┬────────────────────────────┘
                             │
                ┌────────────┼─────────────┐
                ▼            ▼             ▼
        ┌──────────┐  ┌─────────┐  ┌─────────────┐
        │ Static    │  │ Memory   │  │ Tools (MCP) │
        │ context:  │  │ lookup    │  │  k8s_*      │
        │ system    │  │ (pgvector│  │  AKS-MCP    │
        │ prompt +  │  │  if      │  │  GitLab MCP │
        │ skills    │  │  enabled)│  │  Git MCP    │
        │ at /skills│  │          │  │             │
        └─────┬─────┘  └────┬────┘  └──────┬──────┘
              │             │              │
              └─────────────┴──────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │ LLM via agentgateway         │
              │  (Azure OpenAI via UAMI,     │
              │   OTel metrics, guardrails)  │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │ Diagnosis JSON               │
              │  + save_memory(...)          │
              │  + (optional) A2A call to    │
              │    gitops-remediation-agent  │
              └─────────────────────────────┘
```

## 2.4 Output: Microsoft Teams via HITL function (MCP tools)

Triage finishes with a structured analysis. The workflow then walks an output DAG:

```
Triage complete
     │
     ▼
Severity router
     │
     ├──[critical / remediation needed]──▶ HITL approval gate
     │                                          │
     │                          ┌───────────────▼────────────────┐
     │                          │ Teams Adaptive Card via         │
     │                          │ Logic App webhook (or Bot Fwk)  │
     │                          │  • Approve → resume workflow    │
     │                          │  • Reject  → ticket only        │
     │                          │  • Edit    → re-prompt agent    │
     │                          └───────────────┬────────────────┘
     │                                          │ callback URL
     │                                          ▼
     │                          ┌─────────────────────────────────┐
     │                          │ Istio VirtualService +           │
     │                          │ AuthorizationPolicy gates the    │
     │                          │ inbound callback (token-checked) │
     │                          └───────────────┬────────────────┘
     │                                          ▼
     │                          ┌─────────────────────────────────┐
     │                          │ Argo Events webhook EventSource  │
     │                          │  → Sensor resumes workflow       │
     │                          └───────────────┬────────────────┘
     │                                          │
     ├──[warnings — best effort]                │
     │                                          │
     └────────▶ Ticket creation step ◀──────────┘
                     │
                     ├─ GitLab MCP → create issue
                     ├─ ServiceNow MCP → incident (planned)
                     ├─ Azure DevOps MCP → work item (planned)
                     │
                     ▼
              Notification step
                     │
                     ├─ Teams (Adaptive Card with link to ticket)
```

The HITL gate is the safety boundary for **remediation** actions. Read-only triage doesn't go through it. The Teams Adaptive Card embeds:
- Diagnosis summary
- Suggested kubectl / GitOps action
- Risk level
- "Approve / Reject / Edit" buttons

The Logic App posts the user's choice back to the cluster via a callback URL secured by Istio's AuthorizationPolicy (only requests carrying the workflow's HMAC token reach the Argo Events webhook).

Files: `feat: Istio VirtualService + AuthorizationPolicy for HITL callback webhook` (commit `f5fbdb1`), `test-approval-workflow.yaml`, `smoke-test.sh`.

## 2.5 Ticketing integrations

| Integration | Status | MCP server | Use case |
|-------------|--------|------------|----------|
| **GitLab** | Production | gitlab-mcp-server | Default ticket destination; round-robin assignment via `team-roster` ConfigMap |
| **Microsoft Teams** | Production | Logic App webhook (not strictly MCP) | Adaptive Card notifications; HITL approval surface |
| **ServiceNow** | Designed | servicenow-mcp-server (planned) | Enterprise incident creation, severity mapping, escalation chains |
| **Azure DevOps** | Designed | ado-mcp-server (planned) | Work item creation in Boards; useful where GitLab isn't the system of record |
| **PagerDuty** | Designed (incident-agent) | pagerduty-mcp-server (planned) | Page on-call for P1 / P2 |

The ticketing target is selected by the `incident-agent` based on severity + namespace ownership. The same triage payload can generate one or more downstream artefacts (e.g. `critical` → ServiceNow incident *and* GitLab issue *and* Teams card).

---

# 3. Component Status Detail

## 3.1 Human-in-the-Loop (HITL)

| Element | Status | Location |
|---------|--------|----------|
| Teams Adaptive Card payload format | Production | Logic App |
| Argo Events webhook EventSource (callback) | Designed + smoke-tested | `test-approval-workflow.yaml` |
| Istio VirtualService routing the callback | Production | Commit `f5fbdb1` |
| Istio AuthorizationPolicy (HMAC token check) | Production | Commit `f5fbdb1` |
| Mock bot for end-to-end test | Production | `smoke-test.sh` (5-min validation) |
| Workflow `Suspend` template tied to callback | Designed | Pattern doc only |
| Real Teams bot (replacing Logic App webhook) | Future | Bot Framework path documented |

**Approval semantics:** `Approve` resumes a `Suspend` step in the workflow with `approved=true`; `Reject` resumes with `approved=false` and the workflow only creates the ticket without remediation; `Edit` writes the human's modified prompt back into the workflow params and re-invokes the agent.

**Why Logic App today, not Bot Framework:** Logic App = no app registration overhead, no bot framework deployment. We pay for it in features (no rich state, no per-user authorisation beyond Azure AD on the channel). The pattern can swap to Bot Framework later without changing the cluster-side contract — only the Adaptive Card POST destination changes.

## 3.2 Agent-to-Agent (A2A) Communication

**Protocol:** JSON-RPC 2.0 over HTTP. Method `message/send`. URL pattern `POST /api/a2a/kagent/<agent>/` (trailing slash mandatory; omitting it returns 404 silently). Message body:

```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"kind": "text", "text": "..."}]
    }
  }
}
```

**Common gotchas (captured from kagent v0.8.0-beta4 testing):**

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Missing trailing slash on URL | 404 | Always end URL with `/` |
| Method `tasks/send` (older docs) | "method not supported" | Use `message/send` |
| `parts` missing `"kind": "text"` | Parse error | Always include `kind` |
| Session API used for sending | 403 even with correct user | Don't — use A2A; session API auth is broken in v0.8.0-beta4 |

**Agent-as-tool pattern:** kagent supports `tools: [{type: Agent, agent: {name: X, namespace: Y}}]` natively. Proven in March 2026 with the dev pipeline (Kimi coordinator, 6/6 consecutive tool calls including a revision loop). This is how `cert-manager-agent` will call `gitops-remediation-agent` once the latter is built.

**Routing through agentgateway:** agentgateway can act as an A2A gateway in front of kagent. Today A2A is direct (workflow → kagent controller). Future: agentgateway provides auth/authz on A2A calls and centralised routing across multiple kagent installations.

## 3.3 LGTM Integrations (managed Loki/Grafana/Tempo/Mimir)

Full design in `aks-mgmt-stack/k8s-event-triage/managed-lgtm-integration/`. Headline:

| Concern | Approach |
|---------|----------|
| Push metrics | `prometheus.operator.podmonitors` + `prometheus.operator.servicemonitors` → `prometheus.remote_write` |
| Push logs | `loki.source.kubernetes` + `loki.source.kubernetes_events` → `loki.write` |
| Push traces | `otelcol.receiver.otlp` → `otelcol.exporter.otlp` (Tempo) |
| Provision alert rules | `mimir.rules.kubernetes` + `loki.rules.kubernetes` syncing CRDs from cluster to managed Ruler |
| Loop alerts back to triage | Managed AlertManager webhook → Alloy `loki.source.api` → `otelcol.exporter.kafka` → Event Hub `alerts` topic → existing Argo Events pipeline |
| Agent anomaly detection | `agents/03-agent-anomaly-rules.yaml` — recording-rule baselines + z-score / cohort / loop / silent-failure alerts |
| Triage prompt enrichment | `agents/04-triage-prompt-enrichment.md` — workflow queries Mimir/Loki at triage-time, splices context into KAgent prompt |

Status: **designed, not yet deployed.** Pending answers from the platform team on Q1–Q14 (push endpoints, auth, ruler API access, AM webhook reach-back). See `OPEN-QUESTIONS.md`.

## 3.4 agentgateway

Replacing LiteLLM. Key reasons:

- **UAMI / workload identity native** — no API key rotation
- **MCP gateway** — central point for MCP server federation + auth
- **A2A gateway** — auth + routing for inter-agent calls
- **OTel native** — `agentgateway_gen_ai_client_token_usage_*` metrics out of the box
- **Guardrails** — regex / OpenAI moderation / custom webhooks

**Migration phase:** parallel deployment alongside LiteLLM; per-agent ModelConfig switch. See `AGENTGATEWAY-TRANSITION.md`. Token-budget alerts already mirrored from `ai-platform/agentgateway/monitoring.yaml` into the LGTM design.

## 3.5 Skills

**Mechanism:** `Agent.spec.skills.gitRefs[]` (or `refs[]` for OCI) → kagent injects a `skills-init` initContainer that clones into `emptyDir` mounted at `/skills` read-only on the main container. Each skill directory contains `SKILL.md` (frontmatter + instructions) + optional `scripts/` for executable code. Agent runs scripts via the built-in `BashTool`.

**Status:** Mechanism deployed and proven; the **library is shallow**. The "learning loop" in `ENGINEERING-ROLLOUT.md` is what fills it — every triaged-and-resolved issue closes only when an agent skill is updated to handle the same class next time.

**Naming rule (critical):** `spec.skills` (executable bundles) ≠ `a2aConfig.skills` (metadata only). The latter is just a discovery catalog used by the agent registry; it doesn't load code.

## 3.6 Memory

**Status:** Designed; **blocked on kagent**.

kagent shipped `MemorySpec` in v0.8.0 then reverted in v0.8.3. We expect re-enable in a future release. Backend ready: PostgreSQL + pgvector deployed on the red cluster (currently used by LiteLLM). Optional upgrade path: pgvectorscale (`timescale/timescaledb-ha`) for StreamingDiskANN indexing.

When re-enabled, agents will use `load_memory` / `save_memory` / `prefetch_memory` tools. Memory pattern documented in `worker-cluster-bundle/MEMORY-AND-A2A-REMEDIATION-DESIGN.md`. TTL: 90 days. Embedding ModelConfig: separate from inference (e.g. `text-embedding-3-small`).

**Workaround until re-enabled:** GitLab issues *are* the long-term memory. The triage workflow does a fuzzy search of past GitLab issues with the same `event_reason` + `namespace` labels and includes the top 3 in the agent prompt as "prior incidents".

---

# 4. Agent Architecture Pattern — Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Specialist agents per namespace, not one generalist** | Smaller models (Qwen 14B) hallucinate when asked to be domain-omniscient. Focused prompts + relevant tools = better diagnoses. |
| 2 | **Read-only by default, write only with explicit promotion** | Blast radius is the hard control. RBAC-enforced, not prompt-enforced. |
| 3 | **Namespace anchoring in every prompt** (`CRITICAL: use exact namespace "X"`) | Empirical fix for Qwen 14B namespace typos. Belt-and-braces alongside Kyverno ClusterPolicy. |
| 4 | **A2A as the inter-agent contract**, not bespoke HTTP | Standardised JSON-RPC, kagent native, agentgateway-routable. Proven 6/6 with Kimi coordinator pattern. |
| 5 | **No `kubectl edit` from agents — always `patch` / `apply`** | Interactive editors via MCP break. `patch` is deterministic and audit-friendly. |
| 6 | **GitOps remediation via MR, not direct cluster writes** | Agent never `kubectl apply`s. It opens an MR; Flux applies it. Auditable, reversible. |
| 7 | **Triage agent ≠ remediation agent** | Two CRDs, two SAs, two RBAC levels. A triage agent that gains write access becomes a remediation agent — never an upgrade in place. |
| 8 | **HITL gate before any write action** | Teams Adaptive Card with Approve/Reject/Edit. No agent writes without a human nod for the first N occurrences of a class of fix; then the skill graduates to auto. |
| 9 | **Worker-local triage where possible** | Eliminates EventHub round-trip for namespaces the management cluster doesn't need to coordinate (cert-manager, kyverno, kro etc.). |
| 10 | **Round-robin assignment, no namespace ownership** | Every team member sees every namespace. Builds breadth; visible at standups via the Kanban board. |
| 11 | **Skills are git-versioned, not in-line in CRDs** | `gitRefs` keeps the skills library reviewable in PRs and shareable across agents. The CRD stays small. |
| 12 | **Agent prompts are committed to Git** | The `systemMessage` is a code artefact. Changes go through PR review like any other config. |
| 13 | **3-layer dedup** (Alloy / Sensor rate / script TTL) | Single layer is brittle under event storms. Three layers means one can fail and the system still throttles. |
| 14 | **agentgateway as the single LLM exit point** | One place for token tracking, guardrails, UAMI auth, OTel. Agents don't know about Azure OpenAI directly. |

---

# 5. Agent Cards

We have ~20 agents across two clusters. Most of the cards below are **grouped by tier** because the User Persona / Process / Skills / Communication patterns repeat. Differences are flagged inline.

## Common card fields (shared across all agents unless noted)

| Field | Common value |
|-------|--------------|
| **Process** | Receive A2A `message/send` → load skills + memory → call MCP tools → summarise → return JSON-RPC result. Optional A2A call to `gitops-remediation-agent` for fixes. |
| **Communication** | Inbound: A2A from Argo Workflow. Outbound: A2A to other agents (agent-as-tool); MCP to `kagent-tool-server`, `aks-mcp`, `gitlab-mcp-server`, `git-mcp-server`. |
| **Tools (read)** | `k8s_get_resources`, `k8s_describe_resource`, `k8s_get_pod_logs`, `k8s_get_events`, `k8s_get_resource_yaml`, `k8s_check_service_connectivity` |
| **Tools (write — remediation tier only)** | `k8s_patch_resource`, `k8s_apply_manifest`, `k8s_delete_resource`, `k8s_label_resource`, `k8s_annotate_resource`, `k8s_execute_command` |
| **Knowledge** | System prompt + `/skills` git bundle + (when enabled) pgvector memory + `kagent-builtin-prompts` ConfigMap |
| **Evaluation** | Output schema enforced (Issue / Affected Resource / Root Cause / Remediation / Risk Level / Verification). Workflow grades structured fields and rejects malformed responses. |
| **Security** | Read-only RBAC by default; write RBAC only via explicit RoleBinding to specific namespaces. UAMI scope per cluster. Prompt constraints: never output secret values; never delete CRDs; never operate outside assigned namespace. |
| **Model routing** | All agents → agentgateway → Azure OpenAI (UAMI) or local vLLM. Same `default-model-config` ModelConfig CRD; tenant-specific overrides per agent. |

What differs per card: **Role / Problem / User Persona / Specialist Skills**.

---

## Card A — Triage Specialist (the dominant pattern)

**Applies to:** `cert-manager-agent`, `kyverno-agent`, `kro-agent`, `external-secrets-agent`, `reloader-agent`, `flux-system-agent`, `gatekeeper-system-agent`, `istio-ingress-agent`, `istio-system-agent`, `kube-system-agent`, `dns-agent`, `database-agent`, `observability-agent`, `cost-agent`, `change-agent`, `network-agent`, `storage-agent`, `infra-agent`, `security-agent`, `compliance-agent`

**Process:** Reactive — invoked by a workflow on a K8s Warning event in its target namespace. Optionally proactive via CronWorkflow for daily/hourly scans (compliance, cost, security, observability).

**User persona:** SRE / Platform Engineer responding to a triage notification. Wants: structured diagnosis with evidence, ranked remediation options, the exact kubectl commands needed, link to source events.

**Problem:** Domain-specific K8s failures hit the namespace; the on-call engineer either lacks deep specialist knowledge (e.g. cert-manager ACME internals) or doesn't have the time to dig. The agent collapses 30–60 minutes of investigation into seconds.

**Role:** Read-only investigator + remediation suggester. Writes nothing. Returns analysis JSON to the workflow, which then drives ticket / Teams / HITL.

**Specialist skills (git-mounted at `/skills/<agent>/`):**
- `cert-manager-agent` → `cert-diagnostics` (ACME challenge inspection, issuer status checks, expiry scans)
- `kyverno-agent` → `policy-report-explainer`, `admission-failure-decoder`
- `kro-agent` → `resourcegroup-status-graph`, `instance-readiness-trace`
- `network-agent` → `cni-health-probe`, `ingress-backend-walker`, `istio-config-analyse`
- `storage-agent` → `pvc-binding-trace`, `longhorn-volume-health`, `csi-driver-probe`
- `infra-agent` → `node-condition-decoder`, `kubelet-log-grep`, `inotify-pressure-check`
- `security-agent` → `pss-violation-decoder`, `falco-event-correlator`, `rbac-audit`
- `cost-agent` → `right-size-recommender`, `idle-resource-finder`, `node-utilisation-report`
- `compliance-agent` → `label-compliance-scan`, `quota-coverage-scan`, `network-policy-coverage`
- `observability-agent` → `prometheus-target-health`, `loki-stream-audit`, `cardinality-explorer`

(Full per-agent definitions in `aks-mgmt-stack/k8s-event-triage/AGENT-ROSTER.md`.)

**Communication & collaboration:**
- **Inbound:** A2A `message/send` from `WorkflowTemplate.k8s-triage-*`
- **Outbound (for fixes):** A2A `message/send` to `gitops-remediation-agent` (Card C below) — never writes to the cluster directly
- **Outbound (for tools):** MCP to `kagent-tool-server` (k8s reads); some agents add `aks-mcp` for cross-cluster reads
- **Cross-cluster:** Management-cluster agents use AKS-MCP via UAMI; worker-cluster agents stay local

**Evaluation & security:**
- Output schema validation in the workflow (rejects malformed responses, retries once)
- LLM responses truncated to 4000 chars before any external posting
- LiteLLM/agentgateway logs every prompt/completion for post-hoc audit
- Per-namespace RBAC (Role, not ClusterRole) — even if prompt-injected, can't read other namespaces
- No secret values ever in output — enforced by prompt + output post-filter regex

---

## Card B — Remediation Agent

**Applies to:** `sre-remediation-agent`

**Process:** Invoked only after HITL approval. Receives the triage agent's diagnosis + the human's approval token. Executes the recommended kubectl actions in a controlled subset.

**User persona:** Platform engineer who reviewed the triage and clicked "Approve" in Teams. Wants: the fix applied, evidence the cluster recovered, and an audit trail of what was changed.

**Problem:** Many fixes are routine (restart a pod, scale a deployment, patch a label). Doing them by hand at 3am is the slow part of the loop. Automating the **execution** while keeping the **decision** with a human is the sweet spot.

**Role:** Limited write. Allowed: `patch`, `scale`, `restart`, `label/annotate`. Forbidden: delete CRDs, delete PVCs with data, restart all replicas at once, anything outside the namespace named in the approval token.

**Skills:** Inherits diagnosis context from the triage agent; uses verification scripts to confirm recovery (`verify-deployment-rollout`, `verify-cert-issued`, etc.).

**Communication:**
- **Inbound:** Argo Workflow after HITL gate; carries `approved=true`, `approval_token=<HMAC>`, `intended_action=<kubectl-cmd>`
- **Outbound:** MCP write tools to target cluster; A2A back to triage agent for re-verification
- **Audit:** Every action logged to Loki + GitLab issue comment

**Evaluation & security:**
- Approval token verified against the workflow's HMAC signature — replay protection
- Action whitelist enforced server-side (kagent-tool-server checks the verb against an allowed list)
- Failure mode: if action fails, agent does **not** retry — escalates back to human via Teams
- All writes through GitOps where possible — direct cluster writes only for break-glass scenarios

---

## Card C — GitOps Remediation Agent

**Applies to:** `gitops-remediation-agent`

**Process:** Receives A2A call from a triage agent describing a needed config change. Clones the GitOps repo, makes the change on a branch, opens an MR. Never pushes to main.

**User persona:** SRE reviewing the MR. Wants: a clean, single-purpose diff with the agent's diagnosis as MR description and the GitLab triage issue linked.

**Problem:** Agent identifies a fix that's a code change (Helm value, manifest patch) — but the agent shouldn't `kubectl apply` directly. Need an automated path from "agent identifies fix" to "MR ready for review" without humans in the loop until the merge step.

**Role:** Branch + commit + MR. Read/write on the GitOps repo (scoped to a designated bot account). No K8s access at all.

**Skills:** Tools — `git-mcp-server` (clone/checkout/commit/push/diff/file_read/file_write), `gitlab-mcp-server` (create_merge_request with HITL `requireApproval` gate).

**Communication:**
- **Inbound:** A2A from any triage agent
- **Outbound:** Returns MR URL to caller; the triage agent then includes it in the GitLab triage issue + Teams notification
- **HITL gate:** `gitlab-mcp-server.create_merge_request` is gated — human sees the diff before MR is created

**Evaluation & security:**
- Bot account has `Developer` on a single GitOps project, not org-wide
- MR title must start with `[Auto-Fix]`
- One change per MR (rule enforced by prompt)
- No secret values committed (detect-secrets pre-commit)
- All commits signed by the bot's GPG key

---

## Card D — System Agents (management cluster)

**Applies to:** `incident-agent`, `change-agent`, `compliance-agent`, `cost-agent`, `observability-agent`

These are mostly variants of Card A but live on the management cluster and have **cluster-wide read** rather than namespace-scoped read. They run on schedules (CronWorkflow) more often than on events.

**User persona:** Engineering leadership / FinOps / SRE management. Wants: weekly reports, cross-cluster trends, budget anomalies, compliance scorecards.

**Problem:** Cross-cutting concerns that don't map to a single namespace — incident process management, deployment health across all teams, cluster-wide compliance, cost trends, monitoring stack health.

**Role:** Mostly read; some have integrations to ServiceNow/PagerDuty (incident-agent) or GitLab (compliance/cost weekly reports).

**Specialist skills:**
- `incident-agent` → `incident-correlator`, `pagerduty-escalator`, `mttr-calculator`
- `change-agent` → `rollout-watcher`, `canary-comparator`, `argocd-sync-checker`
- `compliance-agent` → `weekly-compliance-report`, `audit-evidence-exporter`
- `cost-agent` → `weekly-cost-report`, `right-sizing-recommender`
- `observability-agent` → `monitoring-stack-health`, `cardinality-explosion-detector`

**Communication:** Heavier outbound — these agents create reports as GitLab issues, post weekly summaries to Teams, page via PagerDuty.

**Evaluation & security:** Read-only across all namespaces (cluster-scoped Role); incident-agent has write access to ticketing systems (ServiceNow/PagerDuty/GitLab) only.

---

## Card E — Coordinator / Orchestrator (future)

**Applies to:** `orchestrator-agent` (planned)

**Process:** Receives a complex multi-step request and decomposes it into A2A calls to specialist agents. Proven pattern (Kimi 6/6 dev pipeline test) but not yet wired into the triage system.

**User persona:** Engineer asking "diagnose this incident across cert-manager AND DNS AND ingress" — needs joint analysis from three specialists.

**Problem:** Incidents that span multiple domains (cert-manager + DNS + ingress = a TLS outage) currently produce three separate triage outputs. A coordinator joins them into one narrative.

**Role:** Pure orchestration. Holds no domain knowledge itself; calls the specialists and synthesises.

**Skills:** None of its own. Only tool: the list of available agents (auto-discovered via kagent registry / A2A skill metadata).

**Communication:** Inbound A2A from workflow. Outbound A2A to N specialist agents in parallel (or sequential with revision loop, as proven with Kimi).

**Evaluation & security:** No direct cluster access. The risk is "wasted tokens via fan-out storm" — controlled by `max_parallel_agents` config + per-coordinator token budget in agentgateway.

---

# 6. Open Work & Risks

| Item | Status | Owner | Blocker |
|------|--------|-------|---------|
| LGTM integration deployment | Designed | Platform team Q&A | OPEN-QUESTIONS Q1–Q14 |
| kagent memory re-enable | Pending | kagent project upstream | v0.8.3 reverted; awaiting next release |
| `gitops-remediation-agent` build | Not started | David | needs git-mcp-server + gitlab-mcp-server |
| ServiceNow MCP server | Not started | TBD | Vendor evaluation |
| Azure DevOps MCP server | Not started | TBD | Vendor evaluation |
| Real Teams Bot (replace Logic App) | Designed | TBD | App registration + bot framework deployment |
| LiteLLM → agentgateway full migration | Phase 1 of 3 | David | Per-agent ModelConfig migration in flight |
| Skills library expansion | Continuous | All engineers | Driven by learning loop |
| Specialist agents on worker clusters | 11 of ~20 | David then SRE handoff | Phase 3 of `ENGINEERING-ROLLOUT.md` |
| Round-robin GitLab assignment | Designed | David | Needs dedicated GitLab project + team_roster ConfigMap |

## Top risks

1. **Memory pending kagent re-enable** — without it, agents re-investigate from scratch on every fire. GitLab-issue-as-memory is the workaround but is lower fidelity than embeddings.
2. **agentgateway migration not finished** — running both proxies in parallel doubles operational surface; cutover discipline matters.
3. **HITL via Logic App** — no per-user authorisation, no per-action audit trail beyond Logic App Run History. Bot Framework migration would tighten this.
4. **Skills library shallow** — the learning loop is the primary mechanism; if engineers don't update skills when closing tickets, the agents never get smarter.
5. **Cardinality budget on managed LGTM** — `gen_ai_request_model × agent × cluster × tenant` is a lot of label combinations once we hit 20 agents.

---

# Appendix A — Document map

| Document | Purpose |
|----------|---------|
| `kagent-triage/docs/CDA-DESIGN-AUTHORITY.md` | Formal design authority position |
| `kagent-triage/docs/PROJECT-STATUS.md` | This document — implementation snapshot |
| `kagent-triage/docs/SAD-THREAT-MODEL.md` | STRIDE threat model |
| `kagent-triage/docs/SAD-LOGGING-MONITORING-AUTH.md` | Logging/monitoring/auth design |
| `kagent-triage/docs/SAD-LOGGING-MONITORING-LLM.md` | LLM governance |
| `kagent-triage/docs/SAD-COMPLIANCE-CHECKLIST.md` | Compliance posture |
| `kagent-triage/docs/SECRET-ROTATION-RUNBOOK.md` | Secret rotation procedures |
| `kagent-triage/docs/SHARED-CLUSTER-RBAC.md` | RBAC reference |
| `kagent-triage/worker-cluster-bundle/README.md` | Worker bundle deployment |
| `kagent-triage/worker-cluster-bundle/SKILLS-AND-REMEDIATION.md` | Skills loading mechanism |
| `kagent-triage/worker-cluster-bundle/MEMORY-AND-A2A-REMEDIATION-DESIGN.md` | Memory + A2A remediation design |
| `kagent-triage/worker-cluster-bundle/AGENTGATEWAY-TRANSITION.md` | LiteLLM → agentgateway migration |
| `aks-mgmt-stack/k8s-event-triage/managed-lgtm-integration/README.md` | Managed LGTM integration design |
| `aks-mgmt-stack/k8s-event-triage/managed-lgtm-integration/agents/` | Agent-specific anomaly detection |
| `aks-mgmt-stack/k8s-event-triage/AGENT-ROSTER.md` | Full per-agent specifications |
| `aks-mgmt-stack/k8s-event-triage/ENGINEERING-ROLLOUT.md` | Three-phase team rollout plan |
| `aks-mgmt-stack/k8s-event-triage/eventhub-otlp-pipeline/` | Production event pipeline |

# Appendix B — Producing a PDF

This document is intentionally Markdown-first for git review. To turn it into a PDF for handovers / approvals:

```bash
# Option A — pandoc (preferred for clean tables + page breaks)
pandoc kagent-triage/docs/PROJECT-STATUS.md \
  -o kagent-triage/docs/PROJECT-STATUS.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=2cm \
  -V mainfont="Helvetica" \
  --toc

# Option B — Marp (matches house dark deck style — see feedback memory)
# Convert to slides first: re-author as a deck with --- separators, then:
marp kagent-triage/docs/PROJECT-STATUS.md --pdf

# Option C — Quick: print from any Markdown viewer with "save as PDF"
```
