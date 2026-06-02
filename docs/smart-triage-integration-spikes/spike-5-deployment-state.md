# Spike 5 — Deployment State

**Implementation order: 3 of 5.**

**Status:** implemented and live-proven as a public-safe contract proof on
2026-06-01.

Evidence:

- Workflow: `smart-triage-alert-b8gkz`, `Succeeded`, `14/14`.
- Marker: `SPECIALIST_DEPLOYMENT: completed`.
- Verdict: `VERDICT: bad_deploy`.
- Read-only check: no mutating `toolNames` present.
- Proof helper:
  `a2a/smart-triage-fanout-demo/scripts/prove-deployment-readonly.sh`.

## Objective

Correlate runtime symptoms with GitOps/release state from Flux, Argo CD, Helm
release metadata, or the work-standard deployment controller — so the commander
can distinguish a bad deploy from a runtime/platform issue. Read-only.

## Existing Repo Reuse (do not rebuild)

- Fan-out specialist contract + `call-specialist` A2A transport:
  `a2a/smart-triage-fanout-demo/{agents.yaml,workflow.yaml}`.
- Eval case already models this exact failure mode — reuse/extend it:
  `observability/agent-evals/cases/flux-reconciliation-failure.yaml`.
- KRO/GitOps lifecycle context lives under `infra/kro-stack/`; AKS-MCP onboarding
  patterns exist for Kubernetes reads (out of scope to rebuild).

No deployment-state specialist exists yet — this is a greenfield read-only agent
on the established pattern.

## Proposed Architecture

```text
normalize-incident (namespace/workload from alert)
  -> fanout-deployment (NEW, read-only):
       resolve workload -> application/release
       read sync status, health, desired vs live revision, image, last deploy,
            recent rollout events  (NO sync/rollback/restart/patch)
  -> verdict: bad_deploy | runtime_or_platform | inconclusive
  -> commander folds deployment verdict into HITL packet
```

Phase 0 decision: which controller is authoritative (`{{DEPLOY_CONTROLLER}}`).
Tooling differs; the contract and markers do not:

- **Flux**: read `Kustomization`/`HelmRelease` status, `lastAppliedRevision`,
  `Ready` condition, suspend state.
- **Argo CD**: read `Application` `sync.status`, `health.status`,
  `revision`, `operationState`.
- **Helm**: read release history, revision, status, chart/app version, image.

## First Safe Proof

Read sync status, health, revision, image, and recent rollout events for **one
known non-production workload**. Do **not** sync, rollback, restart, or patch.

```bash
# Flux example (read-only):
kubectl get kustomization,helmrelease -n {{TARGET_NAMESPACE}} -o wide
kubectl get helmrelease {{RELEASE}} -n {{TARGET_NAMESPACE}} \
  -o jsonpath='{.status.lastAppliedRevision} {.status.conditions}'
# Argo CD example (read-only):
kubectl get application {{APP}} -n {{ARGOCD_NAMESPACE}} \
  -o jsonpath='{.status.sync.status} {.status.health.status} {.status.sync.revision}'
```

Proof = the specialist returns desired vs live revision + health + last deploy
time for the incident workload and a `bad_deploy`/`runtime_or_platform` verdict,
with no mutating verb in its tool list or output.

## Required MCP / Tool / Server Shape

Read-only tools only. Pick the narrowest available:

- A Flux/Argo CD/Kubernetes read MCP exposing `get`/`list`/`get_resource_yaml`
  for `Kustomization`, `HelmRelease`, `Application`, `Deployment`, `ReplicaSet`,
  and `Events`. (AKS-MCP read tools or `kagent-tool-server`
  `k8s_get_resource_yaml` per the repo's kagent tool conventions.)
- **No** `*_apply`, `*_sync`, `*_rollback`, `*_restart`, `*_patch`, `*_delete`.
  This is required to pass `infra/byo-kagent/kyverno-policies/mcp-dangerous-verb.yaml`.

## kagent Agent Contract

`kagent.dev/v1alpha2` Declarative read-only Agent. Required markers:

```text
SPECIALIST_DEPLOYMENT: completed
EVIDENCE_SOURCE: {{DEPLOY_CONTROLLER}}
APP_RESOLVED: <application/release name | NOT_FOUND>
DESIRED_REVISION: <rev>
LIVE_REVISION: <rev>
DRIFT: yes|no
HEALTH: healthy|degraded|progressing|unknown
LAST_DEPLOY: <timestamp>
IMAGE: <image:tag>
VERDICT: bad_deploy|runtime_or_platform|inconclusive
CURRENT_STATE_VERIFIED: yes
RECOMMENDATION: continue to HITL before any sync/rollback
```

`systemMessage` must forbid proposing direct sync/rollback/restart/patch and
forbid claiming any mutation happened.

## Argo Workflow Integration Point

Add `fanout-deployment` to the DAG (depends on `normalize-incident`), via the
existing `call-specialist` template. Feed output into `synthesize-incident` and
`prove-result`; add `SPECIALIST_DEPLOYMENT: completed` to the prove-result grep.

Optional: link GitLab MR context (from Spike 8 / the GitLab specialist) back to
the deployment verdict so "bad deploy" points at the offending change.

## HITL Requirement

Mandatory and unchanged. A `bad_deploy` verdict is a recommendation only; sync,
rollback, restart, and patch all stay behind HITL and are executed by a
workflow/GitOps path, never by this chat agent.

## Required Manifests / Scripts To Create

| Artifact | Purpose |
|---|---|
| `deployment-state-specialist-agent.yaml` | New read-only Agent |
| `deployment-read-remotemcpserver.yaml` (if needed) | Read-only controller MCP |
| Edit `workflow.yaml` | Add `fanout-deployment` + prove-result marker |
| `mapping/workload-to-release.md` | Namespace/workload → application/release mapping rules |
| `scripts/prove-deployment-readonly.sh` | One A2A call asserting markers + no mutation |

## Validation Commands

```bash
kubectl apply --dry-run=server -f .../deployment-state-specialist-agent.yaml
# Negative check: inspect tool names only. Do not grep the whole manifest,
# because the systemMessage should mention forbidden verbs as instructions.
yq -r '.. | .toolNames? // empty | .[]' .../deployment-state-specialist-agent.yaml \
  | grep -Eiq '(apply|delete|exec|patch|restart|sync|rollback)' \
  && echo "FAIL: mutating tool present" || echo "OK: read-only tools"
bash -n scripts/prove-deployment-readonly.sh
```

## Public-Safe Placeholders

| Placeholder | Use |
|---|---|
| `{{DEPLOY_CONTROLLER}}` | flux \| argocd \| helm \| work-standard |
| `{{ARGOCD_NAMESPACE}}` | Argo CD namespace, if used |
| `{{TARGET_NAMESPACE}}` | Non-prod incident namespace |
| `{{RELEASE}}` / `{{APP}}` | Release/application name |
| `{{DEPLOY_READ_MCP}}` | Read-only deployment MCP server name |

## Evidence To Capture

- Desired vs live revision + health + last deploy for the incident workload.
- The `VERDICT` and the evidence that supports it.
- Proof the agent issued only read verbs (tool-call log / agent logs).
- A drift case and a no-drift case.

## Failure Classes

| Class | Meaning | Evidence |
|---|---|---|
| `DEPLOY_CONTROLLER_UNAVAILABLE` | Flux/Argo CD/Helm API unreachable | MCP/agent logs, HTTP status |
| `APP_NOT_FOUND` | Workload does not map to any application/release | resolver output |
| `DRIFT_DETECTED` | Live != desired (signal, not failure) | revision diff |
| `FAILED_SYNC` | Controller reports a failed reconcile | controller status conditions |
| `STALE_RELEASE_METADATA` | Release metadata older than the live pods | timestamps |

## Rollback / Disable Path

```bash
kubectl delete -f .../deployment-state-specialist-agent.yaml --ignore-not-found
kubectl delete -f .../deployment-read-remotemcpserver.yaml --ignore-not-found
# Remove the fanout-deployment task to return the workflow to its prior shape.
```

Read-only by construction, so disabling is just removing the agent and DAG task.

## Known Risks

- Workload→release mapping is the hard part (labels/annotations vary). Define it
  explicitly in `mapping/workload-to-release.md`; `NOT_FOUND` must be a clean,
  non-fatal verdict.
- Controller diversity: Flux vs Argo CD status fields differ; keep the marker
  schema controller-agnostic and the tool list controller-specific.
- Tempting to add a "just resync" tool — do not. Mutation belongs to the
  HITL/GitOps path, and a write tool here would fail the dangerous-verb policy.

## Exit Criteria

- Specialist returns revision/health/deploy-time + verdict for one workload.
- Drift and no-drift cases both produce correct verdicts.
- Tool list provably read-only (passes the grep negative check + Kyverno policy).
- Failure classes emitted for unavailable/not-found/failed-sync/stale.
