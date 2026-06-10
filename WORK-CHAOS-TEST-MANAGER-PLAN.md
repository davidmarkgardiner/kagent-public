# Work Chaos Test Manager Plan

Status: design and implementation plan for review. Nothing in this document
mutates a cluster, creates a GitLab MR, or builds a real chaos catalogue. It is
the planning artefact produced from `WORK-CHAOS-TEST-MANAGER-PLANNING-PROMPT.md`
and is intended to be handed back to Codex for review before the first build
spike.

Codex review status: reviewed and tightened for a **planning-only** next pass.
The plan should be used to implement the process skeleton first: request intake,
safe spec drafting, HITL, GitOps proposal, observability/reporting shape, and
evaluation contracts. It should not be read as approval to build a full AKS
feature chaos catalogue or run real experiments today.

This plan extends Kagent v2 (smart-triage fan-out, Grafana evidence, GitLab MCP,
knowledge base, shared memory/A2A, HITL, LitmusChaos validation, lifecycle eval)
into a natural-language chaos/test design loop and a reliability test-suite
backbone. It reuses the existing building blocks rather than inventing parallel
ones:

- 8-specialist fan-out contract and proof markers (`SMART-TRIAGE-FANOUT-WORK-HANDOFF.md`).
- LitmusChaos 3.28 → ChaosResult → Argo Events → kagent loop (`chaos/litmus/WORK-INSTALL.md`).
- Argo suspend/resume HITL with Argo Events as callback receiver (`platform/teams-hitl/README.md`).
- Lifecycle eval score model + hard gates (`observability/agent-evals/`).
- Grafana MCP read-only tool policy and `grafana-evidence-agent` (`docs/ai-grafana/README.md`).
- Shared `memory-mcp` with curator-mediated writes and Git-backed KB via doc2vec/querydoc (`WORK-MEMORY-KB-NEXT-HANDOFF-README.md`).

All environment-specific values use `{{PLACEHOLDER}}` tokens per `CONTRIBUTING.md`.

---

## 1. Executive TLDR

- This is the next evolution after Kagent v2: from *responding to incidents* to
  *deliberately provoking and scoring* them. We add a chaos/test design loop on
  top of the existing AI SRE system.
- An operator describes, in plain language, a platform/app and what can go wrong;
  the system plans, approves, injects, observes, triages, evaluates, scores,
  reports, and remembers.
- It reuses the proven smart-triage fan-out as the *observer* of every chaos run.
  The chaos run is just a controlled way to trigger the triage system we already
  built.
- Durable scheduled chaos is GitOps-first: specs land as Git artefacts, Flux/Argo
  syncs them, nothing self-mutates the cluster.
- Every mutation (inject, remediate, MR merge) stays behind HITL. Read-only
  agents never get write tools. This matches the existing safety model.
- Tests produce a score out of 10. Below the 8/10 benchmark routes to a
  review-manager agent that classifies the failure and proposes backlog items.
- Suites aggregate per-test scores into a platform/application reliability score
  with a trend over time — the stabilisation evidence for the shared platform.
- Observability is a first-class product surface: Grafana Alloy collects the
  chaos/test lifecycle telemetry; dashboards work live and for management review.
- Production chaos is out of scope for v1. It is sketched only as a future
  game-day mode with strict controls.
- The learning loop turns a missed production issue into a lower-env regression
  chaos test, a curator-gated memory lesson, a HITL-gated KB runbook MR, and an
  eval fixture.
- First execution pass should prove the workflow skeleton with one low-risk
  candidate scenario, such as pod-delete on a labelled sandbox workload. The
  scenario is a vehicle for proving the process, not the beginning of a locked
  test catalogue.
- Net effect: a repeatable, auditable, GitOps-managed reliability test factory
  whose unit of value is a scored, evidenced, remembered chaos run.

---

## 2. Proposed Architecture

### 2.1 Agents / skills

Reuse first. New agents are thin orchestrators over existing specialists.

| Agent / skill | New? | Tools (capability) | Responsibility |
|---|---|---|---|
| `chaos-designer-agent` | new | read-only KB (querydoc), read-only memory lookup, read-only k8s get | Turn plain-language request → reviewable `ChaosTestSpec`. No write, no inject. |
| `chaos-test-manager-agent` | new | Argo submit (workflow only), read-only status, no cluster mutation | Own the test lifecycle: approve → inject/schedule → watch triage → collect evidence → score → report. |
| `chaos-scheduler-agent` | new | GitOps MR (sandbox branch only) OR scoped in-cluster schedule create | Plan sporadic/randomised chaos across opt-in lower-env or fleet slices under policy. GitOps-first. |
| `fleet-selector-skill` | new skill | read-only cluster inventory / labels | Resolve requests such as "test cert-manager on four clusters" into an auditable random or policy-selected cluster set. |
| `reliability-suite-designer-agent` | new | read-only KB/memory | Platform/app + failure-mode list → `ReliabilitySuite` spec of many tests. |
| `reliability-reporting-agent` | new | read-only eval/Grafana/GitLab read | Per-test, per-suite, daily, weekly, stakeholder reports. |
| `review-manager-agent` | new | read-only evidence + GitLab issue/MR draft (sandbox) | Triggered below benchmark. Classify failure, propose backlog + GitLab issue/MR. |
| Lifecycle eval | reuse | `observability/agent-evals/` scorer | Score detection/triage/remediation/recovery. Extend rubric for chaos. |
| `memory-curator` path | reuse | write to `memory-mcp` only via curator workflow | Persist lessons with audit fields. General agents stay read-only. |
| GitLab/GitOps specialist | reuse | GitLab write (feature branch / sandbox MR only) | Create branches/MRs for specs, suites, reports, issues. Called only after HITL. |
| `grafana-evidence-agent` | reuse | Grafana MCP read-only | Dashboard links, PromQL, LogQL, recovery queries. |
| Knowledge specialist (querydoc) | reuse | doc2vec/querydoc read-only + KB-gap MR after HITL | Cite runbooks; propose KB updates. |
| 8 triage specialists | reuse | per `SMART-TRIAGE-FANOUT-WORK-HANDOFF.md` | Observe what broke when chaos is injected. |

Design rule (matches repo): the front-door/design agents submit workflows or
draft MRs; **workflow service accounts** hold the resource-changing permissions;
the chaos injection itself is performed by Litmus runner SAs scoped to allowed
namespaces, never by an LLM agent calling `kubectl`.

### 2.2 Interaction map

```text
operator (plain language)
  -> chaos-designer-agent
       -> querydoc KB lookup (runbooks, prior incidents)
       -> memory-mcp lookup (shared incident lessons)
       -> emits ChaosTestSpec (draft, sanitized)
  -> HITL (Argo suspend + Teams/Slack/mock-bot Adaptive Card)
  -> GitLab/GitOps specialist opens feature-branch MR with the spec
  -> Flux/Argo CD syncs approved spec (ChaosEngine / CronWorkflow / Git config;
     optional CRD only after later review)
  -> chaos-test-manager-agent launches or watches the experiment
       -> Litmus injects bounded fault in allowed namespace
       -> ChaosResult -> Argo Events -> smart-triage fan-out (8 specialists)
       -> grafana-evidence-agent + k8s + GitLab + KB + memory evidence captured
  -> lifecycle eval scores detection / triage / remediation / recovery -> /10
  -> if score < 8: review-manager-agent classifies + proposes backlog/MR
  -> memory-curator writes the lesson; querydoc proposes KB MR (HITL-gated)
  -> reliability-reporting-agent updates per-test / suite / daily reports
  -> Grafana Alloy collects telemetry at every step above
```

Transport: A2A for agent-to-agent, Argo Workflows/Events for orchestration and
eventing, GitLab MCP for repo actions, Grafana MCP for telemetry reads,
LitmusChaos for injection, Flux/Argo CD for sync, the eval scorer for scoring,
and Grafana Alloy as the telemetry collection backbone.

---

## 3. Natural-Language Request Contract

### 3.1 Prompt shape

```text
Build a {{chaos|regression}} test for {{platform_or_app}} in {{environment}}.
The failure I care about: {{plain-language failure description}}.
It should detect {{expected signal}} and recover by {{expected recovery}}.
Blast radius limit: {{namespace/workload/labels}}.
```

Fleet-style example:

```text
Test cert-manager on four approved non-production clusters.
Pick the clusters randomly from the opt-in pool, inject the default safe
certificate renewal failure scenario, run smart triage, and give me a report and
Grafana dashboard.
```

### 3.2 Fields the designer must infer or ask for

| Field | Required | Default if absent |
|---|---|---|
| target environment | yes | reject if not in lower-env allowlist |
| cluster / fleet scope | yes for fleet requests | ask if not provided |
| max cluster count | yes for random fleet tests | default 1; ask before selecting more |
| namespace | yes | must be in `{{CHAOS_ALLOWED_NAMESPACES}}` |
| workload / service | yes | resolved from labels/ownership |
| experiment type | yes | mapped to Litmus experiment |
| allowed blast radius | yes | single workload, single namespace |
| time window | yes | next business-hours slot in env tier |
| rollback / abort conditions | yes | hard-stop on SLO breach |
| expected detection signal | yes | ask if missing |
| expected recovery signal | yes | ask if missing |
| related runbook / incident memory | no | querydoc + memory lookup |

### 3.3 Stop-and-ask conditions

The designer must stop and request clarification when: target is production or
not in the allowlist; cluster selection policy is missing for a fleet request;
requested cluster count exceeds policy; no owner can be resolved; no
rollback/abort condition is given; experiment type is node-level or
network-level and scope is not approved; blast radius cannot be bounded to a
single namespace; or the request implies multiple simultaneous faults. Never
guess past a safety boundary.

---

## 4. Chaos Test Specification (`ChaosTestSpec`)

Reviewable, environment-agnostic, Git-storable. Proposed CRD-shaped YAML
(`kind: ChaosTest`, kept as a config object first, promoted to a CRD only if
spike 1 justifies it — see §6).

```yaml
apiVersion: reliability.platform.example/v1alpha1
kind: ChaosTest
metadata:
  name: {{TEST_NAME}}
  labels:
    reliability.platform/suite: {{SUITE_NAME}}
    reliability.platform/owner: {{TEAM}}
    reliability.platform/env-tier: {{dev|test|staging}}
spec:
  owner: {{TEAM_OR_USER}}
  description: {{plain-language intent}}
  target:
    environment: {{ENV}}
    clusters:
      selectionMode: {{explicit|random|label-selector}}
      count: {{N}}
      selector: {{CLUSTER_LABEL_SELECTOR}}
      resolved: [{{CLUSTER_PLACEHOLDER_LIST}}]
    namespace: {{NAMESPACE}}            # must be in allowlist
    selector:
      matchLabels: {{WORKLOAD_LABELS}}
    serviceOwnership: {{CATALOG_REF}}
  experiment:
    provider: litmus                    # default; justify alternatives
    type: {{pod-delete|pod-cpu-hog|...}}
    parameters: {{TUNABLES}}
  schedule:
    mode: {{manual|cron}}
    cron: {{CRON_OR_EMPTY}}
    window: {{ALLOWED_WINDOW}}
  safety:
    blastRadius: {{single-workload}}
    maxDurationSeconds: {{N}}
    abortConditions: [{{SLO_BREACH}}, {{ERROR_BUDGET}}]
    rollback: {{ROLLBACK_DESC}}
    requiresHITL: true
  observability:
    expectedSignals: [{{DETECTION_SIGNAL}}]
    recoverySignals: [{{RECOVERY_SIGNAL}}]
    grafanaDashboard: {{DASHBOARD_REF}}
  triage:
    workflowTemplate: {{SMART_TRIAGE_TEMPLATE}}
  eval:
    rubricRef: {{RUBRIC}}
    benchmark: 8                        # out of 10
  reporting:
    destination: [{{GITLAB}}, {{GRAFANA_ANNOTATION}}, {{TEAMS}}]
  learning:
    memoryUpdatePolicy: curator-only
    kbUpdatePolicy: hitl-gated-mr
```

---

## 5. Reliability Suite Specification (`ReliabilitySuite`)

A suite is many chaos/regression tests bound to a platform or application, with
declared failure modes and aggregate scoring.

```yaml
apiVersion: reliability.platform.example/v1alpha1
kind: ReliabilitySuite
metadata:
  name: {{SUITE_NAME}}
spec:
  owner: {{TEAM}}
  underTest:
    kind: {{platform|application}}
    name: {{AKS_FEATURE_OR_APP}}
  featureAreas: [{{cert-manager}}, {{external-secrets}}, {{ingress}}]
  failureModes:
    - id: {{FM_ID}}
      description: {{plain-language}}
      generatedTests: [{{ChaosTest names}}]
  environmentTiers: [{{dev}}, {{test}}, {{staging}}]
  schedulePolicy:
    cadence: {{daily|weekly|on-demand}}
    randomization: {{policy ref §8}}
  scoring:
    weights: {{per-failure-mode weights}}
    benchmark: 8
    aggregate: weighted-mean
  dashboards: [{{required panels §11}}]
  reporting:
    cadence: {{daily|weekly}}
    reviewManagerRouting:
      belowBenchmark: review-manager-agent
```

The suite spec becomes GitOps-managed: `reliability-suite-designer-agent`
proposes it as a Git artefact via MR; once merged, a generator (Argo
WorkflowTemplate or controller) renders each declared test into the durable
chaos definitions chosen in §6. Suites never auto-apply; they sync through
Flux/Argo CD like any other GitOps resource.

---

## 6. GitOps Design

Recommendation, in priority order:

1. **Default: Argo `CronWorkflow` / `WorkflowTemplate` + parameter files** for
   scheduled chaos. Reason: the repo already runs Argo Workflows/Events as the
   orchestration plane; chaos becomes one more parameterised workflow that
   submits a Litmus `ChaosEngine` and then drives the triage/eval/report steps.
   Lowest new surface.
2. **Litmus `ChaosEngine` manifests** committed alongside, referenced by the
   workflow. Keep these declarative and reviewable; do not let an agent generate
   them inline at run time.
3. **`ChaosTest` / `ReliabilitySuite` as config objects first, CRDs later.**
   Start as Git-stored YAML rendered by a workflow. Promote to CRDs only if a
   controller adds real value (status, drift detection, admission validation) —
   decided in spike 1, not assumed now.

Trade-offs: CronWorkflows reuse existing infra and audit but spread suite intent
across many files; custom CRDs give a clean API and status surface but add a
controller to build, secure, and operate. Bias to CronWorkflows for v1.

GitLab MCP flow (reusing the proven lite shim / official endpoint):

- `chaos-designer` / `suite-designer` never push direct. The **GitOps specialist**
  creates a feature branch `{{GITLAB_SOURCE_BRANCH_PREFIX}}/chaos-{{name}}`,
  commits the spec/suite/report, opens a **draft MR**, and comments evidence.
- Review reports, failed-test issues, and backlog items are separate MRs/issues
  in the sandbox project, labelled `chaos-drill, kagent-triage, environment/{{ENV}}`.
- Approvals/CODEOWNERS/MR templates/policy checks: CODEOWNERS gate the
  `reliability/` path; an MR template requires owner, blast radius, abort
  condition, and env tier; a policy check (Kyverno/CI) rejects specs targeting
  non-allowlisted namespaces or production.

---

## 7. In-Cluster Execution Design

- **Who executes chaos:** the Litmus runner ServiceAccount, scoped by RoleBinding
  to `{{CHAOS_ALLOWED_NAMESPACES}}` only (the repo uses `chaos-demo` as the single
  target today). No agent SA holds chaos-execution permissions.
- **RBAC boundaries:** read-only specialists hold no apply/delete/patch/exec
  tools. The triage workflow SA orchestrates only. The chaos-injection SA can
  create ChaosEngines only in allowed namespaces. The GitOps SA writes to GitLab,
  not to the cluster.
- **Namespace allowlists / selectors:** an explicit allowlist ConfigMap plus
  required workload labels (`reliability.platform/chaos-optin: "true"`). Anything
  unlabelled is ineligible.
- **Trigger / monitor / cancel / cleanup:** experiments are triggered by Argo
  (manual submit or CronWorkflow), monitored via `ChaosResult` + Argo node
  status, cancellable by deleting the ChaosEngine / stopping the workflow, and
  cleaned up by Litmus TTL plus a workflow finaliser that verifies steady state.
- **Prevent production mutation by default:** namespace allowlist excludes
  production; admission policy rejects production targets; node-level and
  network-level experiments stay disabled until separately approved (matches
  `kubernetes-chaos-values-work.yaml` defaults).

---

## 8. Random / Sporadic Chaos Policy

Safe randomisation model, all values policy-driven:

- **opt-in labels** — only `reliability.platform/chaos-optin: "true"` workloads.
- **max concurrent experiments** — `{{MAX_CONCURRENT}}` per cluster, default 1.
- **minimum quiet period per service** — `{{QUIET_PERIOD}}`, default 24h.
- **blackout windows** — change freezes, incident windows, release windows.
- **business-hours policy** — lower envs only, working hours, with an on-call aware.
- **environment tiers** — dev → test → staging promotion; production excluded.
- **fleet selection** — random cluster selection is from an opt-in labelled pool
  only; record candidate pool, random seed or selection reason, excluded
  clusters, and final cluster list in the evidence.
- **escalation / abort** — auto-abort on SLO breach or error-budget burn; page on
  abort.
- **audit trail** — every randomised pick writes a GitLab issue + Grafana
  annotation + memory record (who/what/when/why/scope).

**Production is out of scope for v1.** It is allowed only as a future, explicitly
designed game-day mode with named approvers, break-glass procedure, tighter
blast radius, and senior on-call presence.

---

## 9. End-to-End Workflow

### 9.1 Single plain-language chaos test

```text
1.  Operator: "test cert-manager not renewing a secret in sandbox ns X"
2.  chaos-designer-agent: querydoc + memory lookup -> draft ChaosTestSpec
3.  HITL: Argo suspend, Adaptive Card -> approve/reject
4.  GitOps specialist: feature branch + draft MR with the spec
5.  Flux/Argo CD: sync approved spec
6.  chaos-test-manager-agent: submit Litmus ChaosEngine (allowed ns only)
7.  Litmus injects -> ChaosResult -> Argo Events -> smart-triage fan-out
8.  8 specialists + grafana-evidence-agent capture k8s/Grafana/GitLab/KB/memory
9.  lifecycle eval scores detection/triage/remediation/recovery -> /10
10. memory-curator writes lesson; querydoc proposes KB MR (HITL-gated)
11. reliability-reporting-agent writes per-test report + Grafana annotation
12. if score < 8 -> review-manager-agent
```

### 9.2 Suite from app + failure-mode list

```text
1.  Operator provides app + ["cert renewal fails","ingress 5xx","bad image tag"]
2.  reliability-suite-designer-agent generates ReliabilitySuite (N tests)
3.  Suite reviewed + merged via GitLab/GitOps
4.  Tests run manually or on CronWorkflow schedule
5.  Grafana shows live progress via Alloy-collected telemetry
6.  Per-test + per-suite reports + aggregate score + trend produced
7.  Below-threshold tests route to review-manager
```

---

## 10. Evaluation Design

Extend the existing lifecycle scorer (`observability/agent-evals/`,
`agent_lifecycle_eval_*` metrics). Keep the normalised 0.0–1.0 model internally,
present as `/10` externally.

Scoring dimensions (chaos-aware extension of the current weights):

- detection latency (time fault → first specialist signal)
- correct specialist routing
- quality of evidence (Grafana/k8s/trace deeplinks present and relevant)
- remediation recommendation safety
- HITL compliance
- recovery verification (steady state restored)
- knowledge citation quality
- memory use correctness
- GitLab hygiene (branch/MR/issue well-formed, sanitized)
- suite coverage of declared failure modes
- reporting quality

Hard failures (fail the run regardless of numeric score — extends the existing
hard-gate list):

- mutation/inject before HITL approval
- production target without explicit game-day approval
- missing owner
- missing rollback/abort condition
- no Grafana or Kubernetes evidence captured
- no eval result produced
- unsafe output or secret/private-value leak

Benchmark model: individual score out of 10; default pass threshold **8/10**;
suite aggregate = weighted mean of test scores; trend stored over time; automatic
`review-manager-agent` trigger below threshold.

---

## 11. Observability and Dashboards

Telemetry backbone: **Grafana Alloy / Grafana Alloy Operator**, matching the
existing Alloy→EventHub/LGTM direction. Alloy collects logs, metrics, events,
traces, and Grafana annotations from Argo, Litmus, kagent, agentgateway, GitLab
MCP, Grafana MCP, shared memory/A2A, and eval jobs.

Lifecycle signals to emit (metric + event + annotation per stage):

- test requested / spec drafted
- HITL approved / rejected
- GitLab MR created / merged
- GitOps sync status
- chaos injection started / completed / aborted
- affected namespace / workload
- smart-triage workflow status + per-specialist completion markers
- remediation recommendation
- recovery verification
- eval score
- review-manager routing

Dashboard panels:

- live chaos timeline
- active experiments by cluster / namespace / service
- selected cluster set and randomisation evidence for fleet tests
- reliability score by platform feature / application
- failed tests below 8/10
- MTTA / MTTR / detection latency
- specialist health and A2A/MCP errors
- GitLab MR/issue status
- recurring failure modes
- daily / weekly reliability trend

Mandatory labels for drill-down: `suite`, `test`, `env_tier`, `namespace`,
`workload`, `failure_mode`, `experiment_type`, `workflow_name`, `score`,
`review_status`.

---

## 12. Reporting Design

Report outputs: per-test, per-suite, daily, weekly trend, stakeholder summary.

Report fields: suite/test name, owner, target, failure mode, injection result,
detection result, triage result, remediation recommendation, recovery
verification, score, threshold, review-manager status, linked Grafana dashboard,
linked GitLab MR/issue, linked memory/runbook update.

Where reports live: **GitLab** for the durable record and review trail (Markdown
in the reliability path), **Grafana annotations** for the live/historical
timeline, **Teams** for stakeholder TLDRs, and optional **object storage** for
raw evidence beyond the Git retention window. The daily/weekly reports become
part of the shared-platform stabilisation evidence.

---

## 13. Review Manager Design

Invoked automatically when a test scores below benchmark, or on demand.

Reviews: low scores, missing detection signals, failed remediation, flaky tests,
unsafe experiments, missing runbooks, repeated weak platform areas.

Output (sanitized, no raw model reasoning): root-cause hypothesis; whether the
*test* was valid; whether the *system response* was valid; recommended backlog
item; GitLab issue/MR proposal; memory proposal (via curator); KB/runbook update
proposal (HITL-gated MR).

---

## 14. Memory and Knowledge Loop

Findings become: shared incident memory (curator-gated `memory-mcp` write with
audit fields), KB runbook updates (HITL-gated GitLab MR via querydoc gap path),
regression chaos tests (new `ChaosTest` in the suite), eval fixtures (new
lifecycle golden case), reliability-suite updates, and review-manager findings.

Boundaries (from `WORK-MEMORY-KB-NEXT-HANDOFF-README.md`): canonical runbooks and
procedures live in **Git**, never only in memory; shared-memory writes go only
through the **curator** workflow; general agents stay read-only.

---

## 15. Initial Spike Backlog

| # | Spike | Objective | Artefacts | Prereqs | Test command | Proof markers | Done | Risks |
|---|---|---|---|---|---|---|---|---|
| 1 | Spec schema | Define `ChaosTestSpec` as Git config first (+ explicitly defer CRD decision) | schema YAML, 2 example specs | repo Litmus install | schema validate with repo-local tool; do **not** require a CRD | `CHAOS_SPEC_DRAFTED: yes` | spec validates, reviewer signs schema | over-engineering CRD too early |
| 2 | Designer agent | Plain language → draft spec with KB+memory lookup | `chaos-designer-agent` CR, prompt | querydoc + memory-mcp reachable | A2A call returns valid spec + citations | `CHAOS_REQUEST_PARSED`, `KNOWLEDGE_CONTEXT_ATTACHED`, `MEMORY_CONTEXT_ATTACHED` | one request → valid sanitized spec | hallucinated targets; mitigate with allowlist check |
| 3 | Manager + inject loop | Approved spec → Litmus inject → triage observes → eval scores | `chaos-test-manager-agent`, Argo template | spikes 1–2, smart-triage workflow | run pod-delete in `chaos-demo`, capture Argo node table | `CHAOS_INJECTION_*`, `SMART_TRIAGE_FANOUT: started`, `EVAL_SCORE` | one scored run end to end, non-prod | scope creep beyond allowed ns |
| 4 | Report + review-manager | Score → report; <8 → review-manager + GitLab issue | `reliability-reporting-agent`, `review-manager-agent` | spike 3 | force a sub-8 run, check issue draft | `TEST_REPORT_CREATED`, `REVIEW_MANAGER_TRIGGERED: yes` | low score routes correctly | noisy false-fail routing |
| 5 | Alloy + dashboards | Collect lifecycle telemetry, build live dashboard | Alloy config, dashboard JSON | spike 3 | run + observe panels populate | `ALLOY_TELEMETRY_CAPTURED: yes`, `GRAFANA_DASHBOARD_UPDATED: yes` | live timeline shows a run | label gaps break drill-down |
| 6 | Suite + scheduler | Suite spec → many tests → GitOps CronWorkflow + randomisation policy | `ReliabilitySuite` schema, suite-designer, scheduler, CronWorkflow | spikes 1–5 | merge suite, dry-run schedule | `RELIABILITY_SUITE_DRAFTED`, `CHAOS_SCHEDULE_CREATED` | suite renders + schedules safely | randomisation safety; gate hard |

---

## 16. Minimal First Demo

**Smallest single test for the next execution pass:** `pod-delete` on a labelled
demo workload in `chaos-demo` (the namespace already used by `chaos/litmus/`).
It proves the whole loop — request → spec → HITL → MR → sync → inject → triage
→ evidence → eval → report → memory/KB — without touching production. Candidate
alternates (pick one, do not build the catalogue): cert-manager secret not
renewing in a sandbox ns; external-secrets sync failure; ingress route
misconfig; rollout with bad image tag.

**Smallest fleet-selection demo concept:** "test cert-manager on four clusters"
should initially be a dry-run planning proof unless the target work environment
explicitly approves multi-cluster execution. The proof should show the opt-in
cluster pool, selection policy, final selected clusters, generated specs, HITL
approval packet, and dashboard/report shape. Actual injection can remain
disabled until the process is reviewed.

**Smallest suite demo concept:**

- one platform/app (e.g. the sample workload)
- two or three declared failure modes
- two or three planned tests
- one deliberately below-threshold score (to exercise routing)
- one review-manager report
- one Grafana dashboard view

---

## 17. Public-Safe Handoff

Environment variables / placeholders required (non-exhaustive, all `{{...}}`):
`{{KUBE_CONTEXT}}`, `{{KAGENT_NAMESPACE}}`, `{{ARGO_NAMESPACE}}`,
`{{ARGO_EVENTS_NAMESPACE}}`, `{{CHAOS_ALLOWED_NAMESPACES}}`, `{{CHAT_MODEL_CONFIG}}`,
`{{EMBEDDING_MODEL_CONFIG}}`, `{{GRAFANA_MCP_REMOTE_SERVER_NAME}}`,
`{{GITOPS_MCP_REMOTE_SERVER_NAME}}`, `{{GITLAB_HOST}}`, `{{GITLAB_SANDBOX_PROJECT}}`,
`{{GITLAB_TOKEN_SECRET}}`, `{{GITLAB_SOURCE_BRANCH_PREFIX}}`, `{{HITL_FRONT_DOOR}}`,
`{{KB_REPO_URL}}`, `{{KB_SOURCE_PATH}}`, `{{MEMORY_MCP_NAME}}`, `{{STORAGE_CLASS}}`,
`{{INTERNAL_REGISTRY}}`, `{{ENV}}`, `{{MAX_CONCURRENT}}`, `{{QUIET_PERIOD}}`,
`{{CLUSTER_SELECTION_LABELS}}`, `{{MAX_SELECTED_CLUSTERS}}`,
`{{FLEET_INVENTORY_SOURCE}}`.

Images that may need mirroring: Litmus 3.28 stack (`litmuschaos/*:3.28.0/3.28.1`,
`mongo:6`, `argoproj/workflow-controller`, `argoproj/argoexec`),
`ghcr.io/kagent-dev/doc2vec/mcp:2.11.0`, `bitnami/kubectl`, `python:3.x`,
`alpine`, kagent + Argo executor runtime images.

CRDs / controllers required: `agents.kagent.dev`, `modelconfigs.kagent.dev`,
`remotemcpservers.kagent.dev`, `workflows.argoproj.io`, `cronworkflows.argoproj.io`,
Argo Events EventSource/Sensor, Litmus chaos operator CRDs (`ChaosEngine`,
`ChaosResult`), Flux/Argo CD, plus optional `ChaosTest`/`ReliabilitySuite` CRDs if
spike 1 promotes them.

GitLab permissions: sandbox project, feature-branch create, draft MR, issue
create/comment — no default-branch push.

Grafana/observability permissions: Grafana MCP read-only (datasources, dashboards,
PromQL/LogQL, deeplinks), annotation write only via the separate write-capable
reporting workflow SA, not the triage agents.

---

## 18. Open Questions

1. Promote `ChaosTest`/`ReliabilitySuite` to CRDs in v1, or keep as Git config
   objects rendered by Argo? (Affects spike 1 scope.)
2. Single chaos-injection SA across all allowed namespaces, or one per env tier?
3. Suite aggregate scoring — weighted mean only, or weighted mean with a hard
   floor on any critical failure mode?
4. Where do raw evidence artefacts live beyond Git retention — object storage,
   and with what retention?
5. Who are the named approvers per env tier for the HITL gate, and does staging
   need a stricter approver set than dev/test?

---

## Final Summary (hand-back block)

- **Recommended architecture:** chaos design loop layered on the existing
  smart-triage fan-out; chaos run = controlled trigger for the triage system;
  GitOps-first durable scheduling; HITL before every mutation; eval scores every
  run; Grafana Alloy / Alloy Operator collects lifecycle telemetry.
- **Agent/skill list:** new — `chaos-designer-agent`, `chaos-test-manager-agent`,
  `chaos-scheduler-agent`, `reliability-suite-designer-agent`,
  `reliability-reporting-agent`, `review-manager-agent`, `fleet-selector-skill`;
  reused — lifecycle eval, memory-curator path, GitLab/GitOps specialist,
  `grafana-evidence-agent`, querydoc knowledge specialist, 8 triage specialists.
- **Workflow sequence:** §9.1 and §9.2.
- **Reliability suite spec:** §5.
- **Grafana/Alloy observability design:** §11.
- **Reporting + review-manager design:** §12–§13.
- **First 4–6 build spikes:** §15.
- **First demo scenario:** §16 (pod-delete in `chaos-demo` as process proof;
  fleet selection remains dry-run unless explicitly approved).
- **Proof markers:** as refined from the planning prompt — `CHAOS_REQUEST_PARSED`,
  `CHAOS_SPEC_DRAFTED`, `RELIABILITY_SUITE_DRAFTED`, `KNOWLEDGE_CONTEXT_ATTACHED`,
  `MEMORY_CONTEXT_ATTACHED`, `CLUSTER_SELECTION_RECORDED`, `HITL_STATUS`,
  `GITLAB_BRANCH`, `GITLAB_MR`, `CHAOS_INJECTION_STARTED/COMPLETED`,
  `SMART_TRIAGE_FANOUT`, `EVAL_SCORE`,
  `SCORE_THRESHOLD: 8`, `REVIEW_MANAGER_TRIGGERED`, `ALLOY_TELEMETRY_CAPTURED`,
  `TEST_REPORT_CREATED`, `KB_UPDATE_PROPOSED`, `MEMORY_PROPOSAL_CREATED`,
  `OUTPUT_SANITIZED`.
- **Risks + mitigations:** premature CRD complexity → start as config objects;
  agent hallucinating unsafe targets → allowlist + admission policy + stop-ask;
  randomisation blast radius → hard concurrency/quiet-period/blackout caps;
  noisy review-manager routing → tune benchmark + flaky-test detection; telemetry
  label gaps → mandatory label set enforced at emit.
- **Files Codex should create/modify next (spike 1–3):**
  - `chaos/reliability/schemas/chaos-test.schema.yaml` (new)
  - `chaos/reliability/examples/pod-delete.chaostest.yaml` (new)
  - `agents/chaos-designer/agent.yaml` (new)
  - `agents/chaos-test-manager/agent.yaml` (new)
  - `platform/argo-workflows/templates/chaos-test-lifecycle.yaml` (new)
  - `observability/agent-evals/lifecycle-cases/chaos-pod-delete.yaml` (new)
  - `WORK-CHAOS-TEST-MANAGER-EXECUTION-REVIEW.md` (new, after execution pass)
  - `WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md` (new, after execution pass)
  - `README.md` Quick-Navigation row for the chaos test manager (modify)
```
