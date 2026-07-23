# Cluster Health Sentinel

Certification runs on a schedule. If anything fails, a generic agent investigates
and a GitLab ticket gets filed with its findings.

Single cluster. No fleet, no Alertmanager, no LGTM dependency — if the
observability team wants to feed alerts to the agent, they can call it directly;
that path is theirs.

## Why this exists

Triage routing today is namespace-keyed: a warning event fires, the sensor routes
it to the agent that owns that namespace. That is right when the failing
namespace *is* the problem, and useless when node pressure, IP exhaustion or a
degraded addon surfaces as symptoms across ten namespaces at once — every agent
investigates its own slice and none sees the shared cause. Nothing catches what
is *brewing* either, because there is no event to route.

You cannot route "something is wrong with the cluster and we don't know what" to
a specialist — that is the whole difficulty. So there is one generic destination
that works it out, then delegates once it knows.

## Flow

```
CronWorkflow (*/15)  →  cluster-certification
                          ├── check-control-plane   /readyz
                          ├── check-nodes           Ready, pressure, cordoned
                          ├── check-addons          desired vs ready
                          ├── check-dns             resolve + kube-dns endpoints
                          ├── check-storage         PVCs bound
                          ├── check-baseline        ← drift, not pass/fail
                          ├── aggregate             one JSON report
                          ├── agent-triage          ← only if something failed
                          │     A2A → cluster-health-orchestrator
                          │     (report inlined in the prompt)
                          └── file-ticket           GitLab, REPORT_MODE-gated
```

## Files

| File | What |
|---|---|
| `01-rbac.yaml` | Read-only ClusterRole (no secrets, no pod logs), bound to both the collector SA and `argo-events-sa` |
| `02-collector-configmap.yaml` | `collect.py` — the baseline collector/detector. **Lives in `argo-events`**, see below |
| `03-certification-workflow.yaml` | The checks, the agent call, the ticket |
| `04-cronworkflow.yaml` | The schedule. Ships `suspend: true` |
| `05-orchestrator-agent.yaml` | The generic agent — read-only tools + 6 specialist sub-agents |
| `06-baselines-configmap.yaml` | Thresholds for `check-baseline` |
| `07-fault-injection.yaml` | Injection cases with acceptance criteria |

## Deploy

```bash
kubectl apply -f 01-rbac.yaml -f 02-collector-configmap.yaml -f 06-baselines-configmap.yaml
kubectl apply -f 03-certification-workflow.yaml -f 04-cronworkflow.yaml
kubectl apply -f 05-orchestrator-agent.yaml --dry-run=server   # validate CRD first
kubectl apply -f 05-orchestrator-agent.yaml
kubectl -n kagent wait --for=condition=Ready agent/cluster-health-orchestrator --timeout=180s

# run once, by hand, and read it before scheduling anything
kubectl -n argo-events create -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata: {generateName: cert-run-, namespace: argo-events}
spec:
  workflowTemplateRef: {name: cluster-certification}
  serviceAccountName: argo-events-sa
EOF
```

## Going live

Two switches, both deliberate:

```bash
# 1. let it file tickets (default is log-only: agent runs, verdict goes to the log, no ticket)
kubectl -n argo-events patch cm cluster-certification-config --type merge \
  -p '{"data":{"report-mode":"ticket"}}'

# 2. let it run on a schedule (ships suspended)
kubectl -n argo-events patch cronworkflow cluster-certification --type merge \
  -p '{"spec":{"suspend":false}}'
```

Run in `log-only` for **1–2 weeks** first. Every threshold in
`06-baselines-configmap.yaml` is currently a guess — `node_cpu_commit` at 90 is
what fires on RED, and it was picked by intuition, not evidence. Reverting either
switch is the rollback; no redeploy.

## Two things that will bite you

**The collector ConfigMap must live where the workflow runs.** It is in
`argo-events`, not `kagent`, because a ConfigMap volume cannot cross namespaces.
Put it in `kagent` and `check-baseline` hangs in `PodInitializing` forever with
no useful error. The snapshots it *writes* still go to `kagent` — that is an API
call, not a mount, so it crosses fine.

**`argo-events-sa` has no cluster reads by default.** `01-rbac.yaml` binds the
read-only ClusterRole to it. Without that, the checks catch the 403, emit
`status: "error"` and exit 0 — the report says "error" instead of reporting the
cluster. Correct behaviour, useless outcome.

## Behaviours worth knowing

**A check that could not run is `error`, never `passed`.** Absence of evidence is
not evidence of health, and the aggregate treats `error` as a failure worth the
agent's attention.

**The baseline is the only check that sees drift.** Everything else is pass/fail
on current state, so a Ready node passes at 93.6% CPU commit with no scheduling
headroom left — nothing is broken, but the next deployment fails. That gap is
why `check-baseline` exists.

**A blind collector reports `unknown`, never `healthy`.** If a core section
(nodes, scheduling, control_plane) cannot be read, the verdict is `unknown` and
the pointer holds the last real verdict. Otherwise losing API access looks
exactly like a recovery.

**Noise is excluded at source, and stays visible.** On RED, 858 of 859 warning
events were Kyverno `PolicyViolation` from Audit-only policies that enforce
nothing — and Kyverno emits a duplicate event against the ClusterPolicy object
for every real violation, so the count is 2× the truth. Excluded events are
counted under `events.excluded` rather than silently dropped. **This list is
environment-specific — re-derive it, do not copy RED's.**

**The agent is handed the report, not asked to find it.** It opens with the
evidence in context and spends its tool budget only on what the report is silent
on. On RED that let it check whether alarming restart counts (kindnet 75) were
acute or chronic — they were 47 days old — instead of burning turns re-deriving
basics.

## Proven on RED

```
control-plane  passed        nodes    passed (1/1 Ready)
addons         passed        dns      passed (resolves, 2 endpoints)
storage        passed        baseline FAILED ← verdict=warning, transitioned=True
                                              node_cpu_commit 91.8%
→ agent-triage → ROOT_LAYER: node-pressure → GitLab issue #445
```

**5 of 6 checks passed.** Every traditional certification check was green —
`aks-certification` would have certified this cluster healthy. Only the baseline
saw it. That is the whole argument for this existing, and it is not hypothetical.

The agent's verdict then went further than any check: it found **699% CPU limit
overcommit** via its own tools, delegated to `platform-knowledge-agent` to ask
whether this had happened before (no prior record), and flagged that
`ip_capacity` being unavailable was itself an unmeasured risk — which turned out
to be a real design flaw in the collector (see below).

## Known gaps

- The baselines are guesses. That is what `log-only` is for.
- **Subnet-level** IP exhaustion needs Azure workload identity
  (`infra/workload-identity/`) and reports `unavailable`. Per-node pod-CIDR and
  max-pods headroom now collect on any cluster — that was originally written off
  as an Azure-only question, which was wrong: every node publishes
  `spec.podCIDR` and `status.allocatable.pods`. The orchestrator agent caught
  that mistake in its own report.
- No metrics-server on RED, so `kubectl top` is impossible and requested-vs-actual
  is unanswerable. `check-baseline` uses requests-vs-allocatable — the scheduler's
  own view — which is what predicts `FailedScheduling` anyway.
- `07-fault-injection.yaml` has never been run.
- RED is single-node kind; multi-node behaviour is untested.
- Related but separate: `aks-certification` and `uk8s-cluster-certification` both
  use `bitnami/kubectl`, which no longer pulls. Everything here uses
  `python:3.11-slim` against the API instead. **23 other YAML manifests in this
  repo still carry that dead reference.**
