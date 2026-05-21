# GitLab Issue Body — copy/paste

Title: `[Platform] K-Agent, Agent Gateway, agentic workflow observability roadmap`

Labels: `platform`, `observability`, `lgtm`, `kagent`, `agentgateway`, `alerting`, `roadmap`

---

## Background

We now have enough working patterns across K-Agent, Agent Gateway, BYO agents,
Litmus fire drills, managed LGTM, dashboards, rules, alerts, and Argo-driven
triage to turn this into a focused platform observability workstream.

The goal is not only to collect logs and metrics. The goal is to make agentic
platform operations observable end to end:

```text
User / event / alert / chaos drill
  -> Agent Gateway / ModelConfig / MCP tools / A2A
  -> kagent agent runtime
  -> Argo Events / Argo Workflows / HITL
  -> LGTM dashboards, rules, alerts, evidence, tickets
  -> SRE and platform-team learning loop
```

This issue captures the gaps and proposed roadmap so we can present the current
state, agree the target operating model, and track delivery.

## Current assets in the repo

Use these as the source material rather than rebuilding from scratch:

| Area | Artifact |
| --- | --- |
| K-Agent + Agent Gateway observability bundle | `docs/observability/k-agent-agentgateway-observability.md` |
| Alloy/Grafana observability plan | `docs/observability/k-agent-alloy-grafana.md` |
| Verification script | `scripts/observability/verify-k-agent-observability.sh` |
| Grafana dashboards | `observability/grafana/dashboards/k-agent-agentgateway-public-ready.json`, `observability/grafana/dashboards/k-agent-metrics.json` |
| Managed LGTM design | `observability/managed-lgtm-integration/README.md` |
| Managed LGTM rule sync proof and handoff | `observability/managed-lgtm-integration/rule-sync/README.md`, `docs/observability/mimir-rule-sync-evidence.md` |
| PromQL/LogQL recipes | `observability/managed-lgtm-integration/dashboards/QUERIES.md` |
| K-Agent / Agent Gateway metric alerts | `k8s/observability/k-agent-alerts.yaml` |
| K-Agent / Agent Gateway log alerts | `observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml` |
| Alertmanager -> Argo Events -> kagent triage path | `k8s/observability/k-agent-alertmanager-eventsource.yaml`, `k8s/observability/k-agent-alert-triage-sensor.yaml` |
| BYO agent showcase and policy model | `infra/byo-kagent/SHOWCASE-DEMO.md`, `infra/byo-kagent/README.md` |
| Agent Gateway MCP tool authorization | `docs/agentgateway-mcp-tool-auth/` |
| K-Agent memory and custom MCP memory | `docs/kagent-memory/README.md`, `docs/memory-integration.md` |
| Litmus chaos fire-drill loop | `chaos/litmus/WORK-INSTALL.md` |
| A2A + HITL + skills runtime proof | `a2a/kagent-hitl-skills-demo/README.md` |

## What we learned

1. **K-Agent observability needs both metrics and logs.** Some token metrics may
   not exist in every Agent Gateway build, so dashboards need LogQL fallbacks
   from structured kagent logs.
2. **Agent Gateway is the right control point for model traffic.** `ModelConfig`
   should route through Agent Gateway so we can observe auth, rate limiting,
   prompt policy, failover, model spend, and upstream failures centrally.
3. **Tool access needs runtime enforcement, not just prompt wording.** The
   platform model should be `ToolCatalogEntry` -> `ToolGrant` -> Agent Gateway
   MCP policy -> kagent `Agent.toolNames`. `toolNames` is useful narrowing, but
   Agent Gateway should enforce discovery and execution.
4. **A2A access is not fully gateway-authorized on the current CRD release.**
   Current repo evidence says A2A-specific Agent Gateway policy fields are not
   available on the checked cluster. For now, A2A identity enforcement sits at
   Istio/ingress/network/routing, with gateway providing route, timeout, rate
   limit, and telemetry.
5. **Managed LGTM rule sync is viable but endpoint-dependent.** The isolated
   proof showed Alloy can sync `PrometheusRule` objects into Mimir Ruler and
   Grafana can show the synced rule firing. Production depends on Mimir/Loki
   Ruler URLs, tenant IDs, auth, and routing labels.
6. **Rules, dashboards, contact points, and notification policies are separate
   ownership surfaces.** Alloy `mimir.rules.kubernetes` handles PromQL rules.
   Alloy `loki.rules.kubernetes` handles LogQL rules. Neither manages Grafana
   dashboards or notification policies.
7. **Agentic workflows need their own SLOs.** We should observe Argo Events,
   sensors, workflow success/failure, kagent A2A success, HITL expiry/reject
   rates, and model/backend latency as one product surface.
8. **Chaos/fire drills are learning loops.** Litmus should create evidence and
   SRE follow-up, not just prove that a pod can be killed. GitLab should hold
   the durable drill record; Teams/HITL should handle time-sensitive approvals.
9. **Memory has two distinct observability stories.** Native kagent memory is
   per-agent/per-user and depends on durable DB + embeddings. The custom
   `memory-mcp` graph is shared operational memory and needs write-queue or
   serialization before high-concurrency use.
10. **BYO agents need a presenter-ready path.** The repo now has the
    architecture, builder agents, policies, and a showcase guide, but still
    needs a one-command demo that deploys two agents and validates all layers.

## Gaps to close

### 1. Data plane: prove metrics, logs, and traces consistently land

- Confirm Alloy can push kagent and Agent Gateway logs to Loki.
- Confirm gateway and kagent metrics land in Mimir/Prometheus.
- Add a Tempo trace path for Agent Gateway -> kagent -> workflow spans where
  possible.
- Ensure every signal has stable labels: `cluster`, `environment`, `namespace`,
  `team`, `agent`, `model`, `route`, and `workflow_template` where applicable.

References:

- `docs/observability/k-agent-alloy-grafana.md`
- `docs/observability/k-agent-agentgateway-observability.md`
- `observability/managed-lgtm-integration/alloy-snippets/`

### 2. Dashboards: build the operator view

We need a small set of dashboards that answer these questions quickly:

- Are kagent and Agent Gateway healthy?
- Which agents are active, failing, slow, or expensive?
- Which model backends are returning 4xx/5xx/timeouts?
- Are Argo Events and Workflows triggering and completing?
- Are alert and chaos-drill loops reaching kagent and SRE?
- Are BYO agents using approved model configs and tools?

Start from:

- `observability/grafana/dashboards/k-agent-agentgateway-public-ready.json`
- `observability/grafana/dashboards/k-agent-metrics.json`
- `observability/managed-lgtm-integration/dashboards/QUERIES.md`

### 3. Alert rules: make agentic platform failure modes visible

Baseline alert families:

- K-Agent controller down or restarting.
- Agent pod crash loops.
- A2A parse errors or repeated request failures.
- Agent Gateway 5xx/timeout/upstream reset bursts.
- Model token burn or missing token metrics.
- Argo sensor/workflow failure rate.
- HITL callback expiry or reject spikes.
- Litmus chaos experiment failed or not triaged.
- Rule-sync failure or managed Ruler not accepting updates.

Start from:

- `k8s/observability/k-agent-alerts.yaml`
- `observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml`
- `observability/managed-lgtm-integration/rule-sync/README.md`

### 4. Alert routing: close the loop from LGTM to kagent triage

Route fired alerts into the same agentic triage path:

```text
PrometheusRule / LokiRule
  -> Mimir/Loki Ruler
  -> Alertmanager/Grafana notification policy
  -> Argo Events webhook or Event Hub bridge
  -> Argo Workflow
  -> kagent A2A triage
  -> GitLab issue / Teams / Mattermost / evidence store
```

Open decision: whether managed Alertmanager can call our webhook directly or
whether we need an Alloy/Event Hub bridge.

References:

- `observability/managed-lgtm-integration/OPEN-QUESTIONS.md`
- `observability/managed-lgtm-integration/README-METRICS-EVENTS-ALERTING.md`
- `k8s/observability/k-agent-alertmanager-eventsource.yaml`
- `k8s/observability/k-agent-alert-triage-sensor.yaml`

### 5. BYO agents: observe and enforce tenant-owned agents

For tenant agents, we need dashboards and alerts for:

- Agent readiness and restart loops.
- ModelConfig compliance: approved Agent Gateway route vs direct provider.
- ToolGrant coverage and expiry.
- Unauthorized tool discovery/call attempts.
- A2A invocation success/failure.
- Memory MCP use and write failures.

References:

- `infra/byo-kagent/SHOWCASE-DEMO.md`
- `infra/byo-kagent/kyverno-policies/`
- `docs/agentgateway-mcp-tool-auth/`
- `docs/memory-integration.md`

### 6. Fire drills: convert chaos into SRE learning

Each controlled chaos drill should produce:

- GitLab issue created before the drill.
- Litmus `ChaosResult`.
- Argo workflow run.
- kagent report.
- Deployment annotations or evidence ConfigMap.
- SRE notes: what was detected, what was missed, what should change.
- Follow-up agent/runbook/rule/dashboard task.

Reference:

- `chaos/litmus/WORK-INSTALL.md`

## Open questions

These should be answered before production rollout:

1. What are the managed Mimir remote-write and Ruler endpoints, tenant IDs, and
   auth method?
2. What are the managed Loki push and Ruler endpoints, tenant IDs, and auth
   method?
3. Do we own rules through Alloy CRD sync, or do we PR rules into a central
   platform repo?
4. How do managed Alertmanager/Grafana alerts call back into our triage system?
5. How do dashboards get provisioned: UI export, Grafana API, Operator, or
   sidecar?
6. What labels are mandatory for cross-cluster correlation?
7. What are the cardinality and log-volume limits?
8. What is the fallback when managed LGTM is unavailable?
9. Which A2A authorization controls are available in the target Agent Gateway
   release?
10. Which SRE team owns each alert family and fire-drill follow-up?

## Proposed delivery plan

### Phase 1 — Baseline proof

- [ ] Run `scripts/observability/verify-k-agent-observability.sh` static checks.
- [ ] Run live checks against the target non-prod cluster.
- [ ] Confirm kagent logs and gateway logs land in Loki.
- [ ] Confirm gateway metrics and kagent/Kubernetes health metrics land in
      Mimir/Prometheus.
- [ ] Import or provision the K-Agent / Agent Gateway dashboard.

### Phase 2 — Rules and routing

- [ ] Apply PromQL rules for kagent, Agent Gateway, Argo Events, and Workflows.
- [ ] Apply LogQL rules for A2A parse errors, gateway resets/timeouts, and chaos
      failures.
- [ ] Prove Mimir rule sync and Loki rule sync.
- [ ] Prove one synthetic alert reaches Argo Events and creates a kagent triage
      workflow.
- [ ] Document alert labels and notification route ownership.

### Phase 3 — Agentic product dashboard

- [ ] Add panels for agent readiness, A2A success/failure, workflow outcomes,
      model traffic, tool errors, HITL outcomes, and chaos-drill status.
- [ ] Add dashboard links from metric panels to matching Loki logs.
- [ ] Add a cost/token fallback panel when gateway token metrics are missing.
- [ ] Add runbook links for each alert family.

### Phase 4 — BYO and governance visibility

- [ ] Add BYO-agent dashboard panels for ToolGrants, ModelConfigs, policy
      reports, and tenant namespaces.
- [ ] Alert on expired/missing ToolGrants and non-approved direct ModelConfigs.
- [ ] Prove Agent Gateway MCP policy blocks unauthorized tool calls.
- [ ] Add a one-command BYO showcase demo that validates two agents end to end.

### Phase 5 — Fire drills and SRE learning loop

- [ ] Run one Litmus `pod-delete` drill and one `pod-cpu-hog` drill.
- [ ] Capture the GitLab issue, ChaosResult, workflow, kagent report, and SRE
      notes.
- [ ] Add one agent-platform drill, such as broken ModelConfig or failed HITL
      callback, with rollback pre-written.
- [ ] Convert learnings into rule, dashboard, prompt, runbook, or policy updates.

## Acceptance criteria

- [ ] A non-prod cluster has kagent + Agent Gateway logs visible in Loki.
- [ ] Gateway/kagent/Argo metrics are visible in Prometheus or Mimir.
- [ ] Dashboard import works without hardcoded datasource UIDs.
- [ ] At least one PromQL rule and one LogQL rule are synced or otherwise active.
- [ ] A synthetic alert routes to Argo Events and creates a successful kagent
      triage workflow.
- [ ] Alert routing labels and owning teams are documented.
- [ ] BYO-agent observability includes ModelConfig, ToolGrant, and policy report
      visibility.
- [ ] One fire drill is executed and closed with SRE follow-up actions.
- [ ] Known platform gaps are tracked with owners and target dates.

## Non-goals

- Replacing the managed LGTM platform.
- Making agents auto-remediate production without HITL and policy gates.
- Treating kagent memory as the canonical documentation/RAG store.
- Assuming Agent Gateway A2A authorization exists until target CRDs prove it.
- Bypassing GitOps or admission policies for tenant-owned agents.

## Suggested first milestone

Pilot this on a single non-prod environment with the `kagent`,
`agentgateway-system` / `kgateway-system`, `argo`, and `argo-events` namespaces
only. Do not expand to all tenant namespaces until the synthetic alert path,
dashboard, and first fire drill are working.

## How to create this in GitLab

```bash
glab issue create \
  --title "[Platform] K-Agent, Agent Gateway, agentic workflow observability roadmap" \
  --label "platform,observability,lgtm,kagent,agentgateway,alerting,roadmap" \
  --description "$(awk '/^## Background/{flag=1} flag' observability/managed-lgtm-integration/GITLAB-ISSUE-KAGENT-AGENTIC-OBSERVABILITY-ROADMAP.md)"
```

Or copy from `## Background` onward into a new GitLab issue.
