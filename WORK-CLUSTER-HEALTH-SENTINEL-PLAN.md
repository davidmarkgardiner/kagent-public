agentharnes# WORK — Cluster Health Sentinel: Snapshot, Baseline Detection, and Generic Orchestrator

Status: PROVEN ON RED 2026-07-15, THEN STOOD DOWN — manifests in
`agents/cluster-health-sentinel/`. Codex review gate passed (§10). Phases 1–3
deployed and verified end-to-end: collector → breach → sensor → workflow →
orchestrator agent → GitLab issue #444. **Six defects (§11), none caught by the
review or by 44 offline tests** — including an RCE and a bug that made every
advertised time window a no-op.

Now stood down to stop token use: CronJob **suspended**, Sensor and EventSource
**deleted**, orchestrator Agent left deployed but idle. `REPORT_MODE=log-only`.
Baselines are untuned guesses.

Work handover bundle: `work-agent-bundles/cluster-health-baseline-sentinel/`
(includes `REVERSE-PROMPT.md` for an independent team).
Owner lane: TBD (`lane:symphony` vs `lane:local`)
Related: `agents/kagent-triage/`, `a2a/smart-triage-fanout-demo/`, `platform/argo-events/`, `platform/mcp-memory-server/`, `platform/aks-mcp/`

---

## 1. Problem

Today's routing is **namespace-keyed**: Argo Events sensors filter on
`body.involvedObject.namespace` (see `agents/kagent-triage/03-sensor-kagent-triage.yaml`)
and hand off to a namespace-specific agent via the `kagent-triage` WorkflowTemplate.
That works when the failing namespace *is* the problem.

It fails for **cluster-scoped or cross-cutting issues**:

- Node pressure / NotReady nodes / node-level resource exhaustion
- Pod scheduling failures (FailedScheduling, unschedulable backlog)
- IP exhaustion (Azure CNI subnet depletion, pods-per-node limits)
- Core addon degradation (CoreDNS, CNI, kube-proxy, metrics-server, cert-manager)
- Control-plane / API server latency
- Slow-brewing trends (restart-rate creep, eviction waves, PVC fill-up)

These present as *application symptoms* in many namespaces at once, so the
namespace-routed agents each investigate their own slice and miss the shared
root cause. There is no component whose job is "look at the whole cluster."

## 2. Design overview

Four pieces, layered on the existing stack (no rewrite of current sensors):

```
                    ┌──────────────────────────────────────────────┐
                    │  A. Snapshot collector (CronJob, every 10m)  │
                    │  writes cluster-health-snapshot ConfigMap    │
                    │  + history to mcp-memory-server              │
                    └──────────────┬───────────────────────────────┘
                                   │ snapshot JSON + baseline verdict
                    ┌──────────────▼───────────────────────────────┐
                    │  B. Baseline detector (same job, last step)  │
                    │  compares vs rolling baseline; on breach     │
                    │  POSTs to webhook EventSource                │
                    └──────────────┬───────────────────────────────┘
   Alertmanager                    │
   catch-all route ────────────────┤   storm detector (existing per-ns
   (cluster-scope alerts)          │   sensors firing > N/window) ──┐
                    ┌──────────────▼───────────────────────────────▼┐
                    │  C. cluster-health sensor → Workflow          │
                    │  step 1: fetch latest snapshot ConfigMap      │
                    │  step 2: A2A → cluster-health-orchestrator    │
                    │          with snapshot INLINE in the prompt   │
                    │  step 3: report → GitLab issue + notify       │
                    └──────────────┬────────────────────────────────┘
                    ┌──────────────▼────────────────────────────────┐
                    │  D. cluster-health-orchestrator (kagent Agent)│
                    │  read-only k8s + prometheus tools             │
                    │  Agent-type tool refs → existing specialists  │
                    │  (k8s, network, grafana, deployment, policy)  │
                    │  output: structured verdict + delegations     │
                    └───────────────────────────────────────────────┘
```

## 3. Component A — snapshot collector

**What:** Kubernetes CronJob (namespace `kagent`, every 10 minutes, read-only
ServiceAccount) running a small container that assembles one JSON document:

| Section | Source | Signals |
|---|---|---|
| `nodes` | `kubectl get nodes -o json`, `kubectl top nodes` | conditions (Ready/MemoryPressure/DiskPressure/PIDPressure), allocatable vs sum-of-requests, cordoned count |
| `scheduling` | pods `status.phase=Pending` + FailedScheduling events | pending count, oldest pending age, top unschedulable reasons |
| `ip_capacity` | AKS: subnet free-IP count via aks-mcp / az CLI; generic: max-pods headroom per node | free IPs, % headroom |
| `addons` | Deployments/DaemonSets in kube-system + platform namespaces | desired vs ready for CoreDNS, CNI, kube-proxy, metrics-server, cert-manager, external-secrets, kyverno |
| `events` | warning events cluster-wide, last 15m | grouped counts by `reason` and by namespace |
| `workload_stress` | pod statuses cluster-wide | OOMKilled count, CrashLoopBackOff count, restart-rate top offenders, evictions |
| `storage` | PVCs + (if kubelet metrics reachable) volume usage | Pending PVCs, >85% full volumes |
| `control_plane` | `/readyz` verbose, APF metrics if scrapeable | apiserver health |

**Why a custom script over popeye/k8sgpt:** popeye scores config hygiene, not
live pressure; k8sgpt-operator brings its own LLM loop that would compete with
kagent. A ~300-line script with a read-only SA is auditable and public-safe.
(Optional later: attach popeye JSON as an extra snapshot section.)

**Storage (revised per review — immutable snapshots):**
- Each run writes an **immutable** ConfigMap `cluster-health-snapshot-<seq>`
  (`immutable: true`, labeled `snapshot-seq`), and updates a tiny pointer
  ConfigMap `cluster-health-snapshot-latest` containing only `{seq, capturedAt,
  ref}`. Breach events carry the exact `snapshot_ref`; workflows read that
  ref, never "latest", so a newer CronJob run can't swap evidence mid-triage.
- Retention: collector garbage-collects snapshots older than 24 entries.
- History/trends: rolling window over the retained snapshot ConfigMaps for
  phases 1–3; `platform/mcp-memory-server` integration deferred (see §10).
- **Size budget:** snapshot hard-capped at 200KB (ConfigMap limit is 1MB;
  LLM prompt budget is the real constraint). Per-section item caps (e.g. top
  20 unschedulable pods, top 20 restart offenders) with explicit
  `truncated: true` markers, plus a `schema_version` field.

**CronJob hygiene:** `concurrencyPolicy: Forbid`, `startingDeadlineSeconds`,
and explicit **missing-data semantics**: every section reports
`status: ok|unavailable`; detectors treat `unavailable` as "skip check and
surface a collector-health warning", never as zero/healthy/breached.

Snapshot doubles as an on-demand tool: anyone (or any agent) can read the
ConfigMap for a "state of the cluster" answer without re-querying everything.

## 4. Component B — baseline detection

Last step of the same CronJob. Two detector classes:

1. **Absolute thresholds** (config in a `cluster-health-baselines` ConfigMap):
   - any node NotReady > 5m; pending pods > 10 or oldest pending > 10m
   - subnet free IPs < 10% ; addon ready < desired ; PVC > 90%
2. **Relative drift vs rolling baseline** (median of last 24 snapshots):
   - warning-event rate > 3× baseline; restart count delta spike; OOMKilled spike

**Fire-on-transition:** detector keeps last verdict in the ConfigMap; only a
healthy→breached transition (or severity escalation) POSTs to the webhook
EventSource — no re-firing every 10 minutes while degraded. A breached→healthy
transition posts a resolution event.

Payload: `{severity, breached_checks[], snapshot_ref, summary}`.

**Complementary, not replacement, for Prometheus:** where kube-prometheus-stack
alerts already exist (KubeNodeNotReady etc.), keep them — the Alertmanager
catch-all route (Component C) feeds those into the same funnel. The snapshot
job covers what Prometheus doesn't express well (IP headroom via Azure API,
event grouping, "one JSON doc an LLM can consume").

## 5. Component C — routing into the orchestrator

Three inputs converge on **one** new sensor + WorkflowTemplate:

1. **Baseline webhook** — new `EventSource` (reuse pattern from
   `platform/argo-events/sources/webhook/`) receiving Component B posts.
2. **Alertmanager catch-all** — new last-resort route in the Alertmanager
   config (and/or a sensor filter on cluster-scope alert names:
   KubeNodeNotReady, KubeCPUOvercommit, NodeFilesystemSpaceFillingUp, …)
   reusing `sources/alertmanager-redpanda/` wiring. Anything not matched by a
   namespace-specific route lands here instead of being dropped.
3. **Storm detector (phase 4)** — if the existing per-namespace sensors create
   > N triage workflows in M minutes, that is itself a cluster signal: fire
   cluster-health once and let per-namespace rateLimits absorb the rest.

**New WorkflowTemplate `cluster-health-triage`** (mirrors `kagent-triage`):

1. `fetch-snapshot` — read the immutable snapshot named by the trigger's
   `snapshot_ref` (Alertmanager/storm triggers use the pointer ConfigMap to
   resolve the newest ref). If the snapshot is stale (> 20m), do NOT
   re-collect inline (avoids a permissions/credentials race with the CronJob
   — see §10); instead tag the prompt `SNAPSHOT_STALE: true` so the
   orchestrator verifies pressure signals with its own read-only tools.
2. `invoke-orchestrator` — A2A `message/send` to
   `kagent/cluster-health-orchestrator`, prompt = trigger payload + **full
   snapshot inline** + trend summary. This is what saves the agent from
   re-looking-everything-up: it starts with the evidence in-context.
3. `create-gitlab-issue` / `send-logic-app` — reuse the existing steps from
   `02-workflow-kagent-triage.yaml` verbatim.

**Safeguards (revised per review):**
- **Routing partition, not overlap:** the cluster-health sensor does NOT
  subscribe to raw k8s warning events at all — that stream stays exclusively
  with the namespace sensors. Its only inputs are (a) the baseline webhook,
  (b) cluster-scope Alertmanager alert names, (c) the storm signal. This
  removes the double-handling failure mode by construction. The Alertmanager
  catch-all filters on an explicit allowlist of cluster-scope alert names
  first; a true "unmatched route" fallback comes only after the allowlist is
  proven quiet.
- **Durable incident key + correlation window:** the workflow's first step
  computes `incident_key = hash(root-signal class + top affected object)` and
  checks (via a small state ConfigMap) whether an open incident with the same
  key exists within a 60m window — if so, it annotates the existing GitLab
  issue instead of opening a new investigation. This correlates
  baseline-webhook, Alertmanager, and storm triggers into one incident.
- **Backpressure:** Argo Workflows `synchronization.mutex` on the
  cluster-health WorkflowTemplate (max 1 concurrent triage), plus sensor
  `rateLimit` (2/hour) as a secondary throttle, `activeDeadlineSeconds`,
  `ttlStrategy`.
- **Mandatory exclusions carried over from `SENSOR-SAFEGUARDS.md`:** exclude
  `PolicyViolation` reasons and the `argo` / `argo-events` namespaces from
  every input path to avoid the documented workflow-event cascade.

## 6. Component D — cluster-health-orchestrator agent

New `kagent.dev/v1alpha2` Agent, namespace `kagent`, labels
`platform.com/team` / `platform.com/type` per repo convention.

**Tools:**
- `McpServer → kagent-tool-server`, read-only set only: `k8s_get_resources`,
  `k8s_describe_resource`, `k8s_get_events`, `k8s_get_pod_logs`,
  `k8s_top_nodes`/`k8s_top_pods` (confirm exact names against
  kagent-tool-server), Prometheus query tool if exposed. **No
  `k8s_apply_manifest`** — this agent diagnoses, never mutates.
- **Agent-type tool refs** to existing specialists (kagent supports `type: Agent`
  tool entries): kubernetes, network/Hubble, grafana, deployment/GitOps,
  policy specialists from `a2a/smart-triage-fanout-demo/agents.yaml`
  (production variants, not the [DEMO MOCK] prompts). This gives dynamic
  delegation — orchestrator picks which sub-agents to consult based on the
  snapshot, exactly because we don't know the issue class up front.

**System message contract (sketch):**

```
You are the cluster-health orchestrator. You receive:
(1) the trigger (baseline breach, catch-all alert, or event storm),
(2) the latest cluster snapshot JSON, (3) a short trend summary.
Trust the snapshot as current state — do not re-collect what it already
contains; use your tools only to drill into specifics it lacks.

Steps:
1. Classify the dominant failure layer: node-pressure | scheduling |
   ip-exhaustion | addon-degradation | control-plane | storage |
   app-local | unknown.
2. Estimate blast radius: which namespaces/workloads are affected,
   and whether their symptoms are downstream of the shared cause.
3. Delegate at most 3 targeted questions to specialist agents when a
   layer needs deeper evidence. Include the relevant snapshot slice in
   each delegation so specialists do not re-query either.
4. Synthesize.

Required output:
BASELINE_CROSSED: <check names or alert names>
SEVERITY: info|warning|critical
ROOT_LAYER: <classification>
BLAST_RADIUS: <namespaces / workloads>
EVIDENCE: <bullet facts, each tagged snapshot|tool|delegate:<agent>>
DELEGATIONS: <who was asked what, or none>
BREWING_RISKS: <not-yet-breached trends worth watching>
RECOMMENDATION: <ranked next actions>
REMEDIATION_MODE: gitops_or_workflow_only
HITL_REQUIRED: yes
```

Read-only + HITL-gated remediation keeps this aligned with the existing
smart-triage posture (no direct mutation, GitOps/workflow path only).

**Delegation mechanics decision:** agent-driven (Agent-type tools) rather than
workflow-driven fanout. The smart-triage-fanout workflow fans out to a *fixed*
specialist set — right when the alert shape is known. Here the whole point is
the issue class is unknown, so the orchestrator must choose targets at
runtime. Cap delegation depth (specialists get no Agent-type tools) to
prevent loops.

## 7. Phasing

| Phase | Deliverable | Value gate |
|---|---|---|
| 1 | Snapshot CronJob + immutable snapshot ConfigMaps + **concrete ClusterRole** (read-only verbs on nodes/pods/events/workloads/PVCs/metrics; NO secrets, NO pod logs in phase 1) | snapshot ConfigMap gives usable cluster picture; humans can already use it |
| 2 | Baseline detector + webhook EventSource + sensor + minimal workflow, **observe-mode default** (`REPORT_MODE=log-only`: workflow logs verdict, no GitLab issue, no notification) | 1–2 weeks of observe-mode data validates thresholds and fire-on-transition; flipping `REPORT_MODE=ticket` is the explicit go-live switch, flipping back is the rollback |
| 3 | Orchestrator agent + workflow A2A step + specialist Agent-type tool refs (after CRD dry-run validation, see §10) | breach → classified, blast-radius-scoped report with delegated evidence |
| 4 | Alertmanager catch-all route + event-storm detector + suppression interplay + optional mcp-memory-server history | cross-cutting incidents produce ONE cluster report instead of N namespace reports |

Azure IP-capacity collection (workload identity + Azure RBAC prerequisite) is
an optional phase-1 add-on gated on `infra/workload-identity/` setup; the
snapshot's `ip_capacity` section reports `unavailable` until then.

Each phase ships independently; fault-injection tests per phase follow the
existing `*-fault-injection.yaml` pattern (e.g. cordon a node + scale a
deployment beyond capacity to force FailedScheduling; kill CoreDNS replicas
for addon breach).

## 8. Open questions

**Closed during the build (implemented in `agents/cluster-health-sentinel/`):**

1. ~~Exact read-only tool names exposed by `kagent-tool-server`.~~ **CLOSED.**
   Verified against `toolNames` blocks in use across `agents/` and `a2a/`.
   Read-only set: `k8s_get_resources`, `k8s_describe_resource`,
   `k8s_get_events`, `k8s_get_resource_yaml`, `k8s_get_cluster_configuration`,
   `k8s_get_available_api_resources`, `k8s_check_service_connectivity`.
   **`k8s_top_nodes` / `k8s_top_pods` DO NOT EXIST** — they appeared nowhere
   but this plan's own draft. Node pressure is derived from the snapshot's
   allocatable-vs-sum-of-requests maths instead.
3. ~~Snapshot history: mcp-memory-server vs rolling ConfigMap.~~ **CLOSED.**
   Rolling immutable ConfigMaps (24 retained, collector-GC'd). Memory server
   deferred to phase 4.
5. ~~Storm-detector implementation.~~ **CLOSED.** Implemented as a
   `triage_storm` snapshot section counting recent `kagent-triage-*`
   workflows, plus a threshold — no sensor-side counting needed.

**Still open (need a live cluster):**

2. IP-exhaustion source on AKS: aks-mcp vs direct `az network vnet subnet
   show` — depends on workload-identity permissions in
   `infra/workload-identity/`. Until wired, the snapshot's `ip_capacity`
   section reports `unavailable` rather than a misleading zero.
4. Whether Prometheus/Grafana MCP tools are reachable by kagent agents in this
   cluster (grafana-evidence-agent suggests yes — reuse its config). Not
   required for phases 1–3; the snapshot covers the signals without them.
6. Server-side dry-run of the orchestrator Agent CRD, and confirmation that
   Agent-type tool refs resolve at runtime (phase-3 entry criterion).

## 8b. DIRECTION CHANGE — merge into `aks-certification` (2026-07-15)

**We nearly built a parallel system to one we already owned.** `aks-certification`
has been deployed on RED for 169 days and already runs api-server / dns /
networking / storage / critical-pods / node-health / rbac / secrets, each
emitting structured JSON that `generate-report` assembles into one document.
That is ~70% of this design's collector, including four checks it never had.

**What certification cannot do is drift.** Every check is pass/fail on current
state, so a Ready node passes at 93.6% CPU commit with no headroom. It would
certify RED healthy today — the exact condition this whole plan exists to catch.
It also does not look at events at all.

**Revised design: one more check, not a parallel system.**

- `collect.py` gains `MODE=check`, emitting the certification contract
  (`/tmp/result.json` → `outputs.parameters.result`) instead of dispatching its
  own webhook — otherwise the same incident arrives twice.
- Three edits to `aks-certification`: add `check-baseline` to the DAG, add
  `baseline-result` to `generate-report`, add an `escalate-to-agent` step.
- Escalate when **any check failed OR the baseline moved**.
- A CronWorkflow provides the schedule that does not currently exist.

Manifests: `work-agent-bundles/cluster-health-baseline-sentinel/examples/`.

**Property worth naming:** same workflow, the schedule decides the question —
run on provision it is a certification gate, run every 15 minutes it is a health
monitor.

**Two findings about the existing estate:**

1. `aks-certification` **cannot run today** — every check uses
   `bitnami/kubectl:latest`, which no longer pulls. That sweep is the real first
   job (23 YAML manifests repo-wide).
2. `uk8s-cluster-certification`'s aggregator is a **stub**: `total_checks = 0`
   hardcoded, comment reads *"would be passed as parameters in real
   implementation"*, so `certified = pass_percentage >= 90 and total_failed == 0`
   evaluates False on every run. It reports NOT CERTIFIED 0.0% regardless of
   cluster state. `CERTIFICATION-IMPROVEMENTS.md` records "✓ aggregate-results:
   Succeeded" — the workflow *phase*, not the check working.

**Also corrected: §6's cross-cluster claim was over-general.** "kagent-tools is
in-cluster only" is true of that tool server, not a law. AKS-MCP authenticates
via Azure identity and targets clusters by name; a collector needs only an
endpoint and a credential; `aks-certification` is already cluster-parameterised.
And "management cannot reach workers" was over-reading the Istio policy in
`A2A-FLEET-DEMO.md`, which governs the A2A path, not API-server reachability.
Central is now the leaning design — the real trade is credential blast radius,
not capability.

## 9. Explicit non-goals

- No auto-remediation. Output is diagnosis + HITL packet; remediation stays
  GitOps/workflow-gated like everything else in this repo.
- No replacement of per-namespace sensors — they stay for the known-shape
  fast path; this layer catches what they can't.
- No new observability stack — reuse Prometheus/Alertmanager/Grafana already
  in `k8s/observability` and `observability/`.

## 10. Codex review gate — findings and resolutions (2026-07-15)

Second-opinion review ran via `codex:codex-rescue`. 1 critical, 8 high,
7 medium findings. Resolutions folded into §§3–7 above; summary:

| # | Sev | Finding | Resolution |
|---|---|---|---|
| 1 | Critical | Catch-all sensor on raw warning events double-handles what namespace sensors already consume | **Design change (§5):** cluster-health sensor never subscribes to raw k8s events; inputs limited to baseline webhook, allowlisted cluster-scope Alertmanager alerts, storm signal |
| 2 | High | Three trigger sources can open separate workflows for one incident; `breached_checks` hash insufficient | Durable `incident_key` + 60m correlation window + annotate-existing-issue behavior (§5) |
| 3 | High | rateLimit is throttling, not dedup/backpressure | Added Workflow `synchronization.mutex` (max 1 concurrent cluster triage) (§5) |
| 4 | High | PolicyViolation / argo-namespace exclusions from SENSOR-SAFEGUARDS.md not made mandatory | Made explicit for all input paths (§5) |
| 5 | High | Mutable `-latest` ConfigMap can be overwritten mid-triage | Immutable `cluster-health-snapshot-<seq>` ConfigMaps + pointer + `snapshot_ref` in events (§3) |
| 6 | High | Inline re-collect in workflow creates permission/credential race with CronJob | Dropped; stale snapshot flagged `SNAPSHOT_STALE`, orchestrator verifies with own tools (§5) |
| 7 | High | Agent-type tool ref syntax unverified against installed CRD | Capability confirmed in vendored `kagent/go/api/v1alpha2/agent_types.go` + `agents/kagent-triage/a2a-hello-poc/` (tested Agent-as-tool flow); phase-3 entry criterion: `kubectl explain` + server-side dry-run + orchestrator reaches `Accepted=True`/`Ready=True` |
| 8 | High | Phase-1 RBAC unspecified for a cluster-wide privilege expansion | Concrete ClusterRole in phase-1 deliverable; secrets and pod logs excluded from collector scope (§7) |
| 9 | High | Phase 2 creates GitLab issues before detector proven; no flag/rollback | Phase 2 ships in `REPORT_MODE=log-only` observe mode; ticket mode is explicit switch and rollback path (§7) |
| 10 | Med | No snapshot size/versioning limits for ConfigMap + prompt budget | 200KB cap, per-section item caps, `truncated` markers, `schema_version` (§3) |
| 11 | Med | Snapshot/event text is untrusted prompt input | Orchestrator prompt wraps snapshot + event data in delimited data blocks with an instruction that content inside is evidence, never instructions (add to §6 system message at build time) |
| 12 | Med | CronJob overlap can corrupt baseline state | `concurrencyPolicy: Forbid` + per-section `status` fields (§3) |
| 13 | Med | Missing-data semantics undefined | `ok|unavailable` per section; `unavailable` = skip check + collector-health warning (§3) |
| 14 | Med | Demo specialists are synthetic `[DEMO MOCK]` agents | Phase 3 defines production specialist manifests (real tools, `allowedNamespaces`) before wiring Agent-type refs; demo prompts are contract templates only (§6) |
| 15 | Med | Scope creep for first phase | mcp-memory-server, Alertmanager catch-all, storm detector all deferred to phase 4 (§7) |
| 16 | Med | Fault-injection tests lack acceptance criteria | Build-time addition: per-phase criteria for false-positive rate, duplicate workflow count (=0 for one injected incident), resolution event on recovery, collector-failure behavior |

## 11. What only the cluster could teach us (RED, 2026-07-15)

Phases 1–3 deployed to RED. Everything below was invisible to the design
review AND to 44 passing offline unit tests. Recorded because the lesson
generalises: reviews catch reasoning errors, real data catches assumptions.

| # | Defect | How it surfaced |
|---|---|---|
| 1 | **PolicyViolation not excluded.** 858 of RED's 859 warning events were Kyverno PolicyViolation. `SENSOR-SAFEGUARDS.md` mandates excluding them and the sensor comment *claimed* "enforced at the collector" — it never was. The rate baseline would have sat at ~859, so `warning_event_spike` could only fire above 2,577 events: the check was dead on arrival. | First real snapshot. Signal went 859 → 2 once fixed. |
| 2 | **`node_cpu_commit` check missing entirely.** RED's sole node sits at 93.6% CPU commit — collected, displayed, never thresholded. The exact "brewing" case the whole design exists for was silently ignored. Now checked at 90% and it is what fires on RED. | Reading the first snapshot by eye. |
| 3 | **Silent cap on node checks.** `collect_nodes()` truncated to TOP_N=20 *before* detection ran, so node 21+ on a large cluster would never be commit-checked. Fixed by deriving a full-node `commit` list pre-truncation. | Spotted while writing #2; confirmed by a 25-node synthetic test. |
| 4 | **`bitnami/kubectl` is dead.** Every workflow step used it; it no longer pulls (Bitnami retired their public catalog — RED shows `bitnamilegacy/*` leftovers). Replaced with `python:3.11-slim` + urllib against the API, matching collect.py. **23 other YAML manifests in this repo carry the same latent breakage.** | ImagePullBackOff on the first real workflow run. |
| 5 | **RCE in the workflow.** `payload_raw = r"""{{inputs.parameters.trigger-payload}}"""` — Argo does literal text substitution, so a payload containing a triple-quote closes the string and the remainder executes as Python in a pod holding `argo-events-sa`. The EventSource webhook is unauthenticated, so anything that can reach that Service in-cluster could drive it. Payload now travels via env var; it is never interpolated into source. **The open webhook itself remains a gap — NetworkPolicy at minimum.** | Suspicion while diagramming the flow; proved by compiling a hostile payload. Codex review, 44 offline tests, and a successful end-to-end run all sailed past it — every payload so far was our own. |
| 6 | **Every advertised time window was a no-op.** `_parse_ts` accepted only `%Y-%m-%dT%H:%M:%SZ`, but RED's events carry `eventTime` as a **MicroTime** (`2026-07-15T10:27:13.173860Z`) with `lastTimestamp` **null on 1192/1192 events**. So `_parse_ts` returned `None` for every event, and the guard `if ts and ts < cutoff` let `None` sail through — counting all retained history while the snapshot claimed `window_minutes: 15`. The `warning_rate_multiplier` baseline was therefore comparing an API-retention artefact, not a rate. Fixed with `fromisoformat`, an `_event_ts` helper that prefers the populated field, a **strict** window (undated ⇒ excluded, never counted), and an `undated` counter so it cannot lie silently again. Proof: `excluded_total` 1078 → 134 against a ground truth of 140. | Verifying a subagent's claim that the flood was bursty. Its number disagreed with mine — because my instrument was mislabeling its own output. **It was right; I was wrong.** |

Also corrected: the deployed GitLab secret is `gitlab-credentials`, not the
`gitlab-token` that `agents/kagent-triage/02-workflow-kagent-triage.yaml`
assumes; and Argo Events auto-creates the eventsource Service, so declaring
one collides with the controller.

**Verdict quality.** The orchestrator's output was better than expected on the
one axis that mattered: the snapshot reports *cumulative* restart counts
(kindnet 75, metallb 62), which look alarming but are meaningless without a
delta. Unprompted, the agent used its read-only tools to check, found the
restarts were ~47 days old, and discounted them as chronic rather than acute —
then correctly reported `ip_capacity: unavailable` as "no data, not evidence
of health or exhaustion". That is the layer doing its actual job.
