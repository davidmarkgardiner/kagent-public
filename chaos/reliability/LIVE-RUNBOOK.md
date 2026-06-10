# Chaos Test Manager Live Runbook

This runbook is the Proxmox/non-production execution path for the first
`chaos-demo-pod-delete` lifecycle run. It keeps durable changes GitOps-first and
uses server dry-runs before any live submission.

## 1. Select Context

```bash
export KUBECTL_CONTEXT={{KUBE_CONTEXT}}
export ARGO_NAMESPACE=argo
export TARGET_NAMESPACE=chaos-demo
```

Confirm the target is not production:

```bash
kubectl --context "$KUBECTL_CONTEXT" config view --minify
kubectl --context "$KUBECTL_CONTEXT" get ns argo argo-events kagent monitoring chaos-demo
```

Kyverno is optional for this Proxmox demo path. If the target cluster has
Kyverno installed, preflight also server-dry-runs the chaos safety policy.

## 2. Run Preflight

```bash
bash chaos/reliability/scripts/preflight-live-run.sh "$KUBECTL_CONTEXT"
```

Expected terminal markers:

```text
PRECHECK_PASSED: yes
OUTPUT_SANITIZED: yes
```

If `chaos-demo` does not exist yet, the script validates the Litmus
`ChaosEngine` shape through a validation-only namespace remap. Create the real
namespace and target only through the approved lower-env GitOps/demo path before
running chaos.

## 3. Install Or Sync Required Manifests

Apply only in a disposable lower environment, or preferably merge the equivalent
GitOps MR and wait for reconciliation.

Non-injection prerequisites:

```bash
kubectl --context "$KUBECTL_CONTEXT" apply \
  -f chaos/reliability/gitops/chaos-target.yaml \
  -f chaos/reliability/gitops/litmus-rbac.yaml \
  -f chaos/reliability/gitops/argo-rbac.yaml \
  -f platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  -f platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml

kubectl --context "$KUBECTL_CONTEXT" apply -k observability/agent-evals
```

Server dry-run the reusable Workflow submission:

```bash
kubectl --context "$KUBECTL_CONTEXT" apply --dry-run=server \
  -f observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml \
  -f platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  -f platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml

kubectl --context "$KUBECTL_CONTEXT" create --dry-run=server \
  -f chaos/reliability/examples/chaos-test-lifecycle.workflow.yaml
```

Do not apply `chaos/reliability/gitops/litmus-pod-delete-chaosengine.yaml` in
the prerequisite step. That manifest has `engineState: active` and is the
GitOps object that starts the Litmus experiment once synced.

The GitOps MR for the complete demo should include:

- `chaos/reliability/gitops/chaos-target.yaml`
- `chaos/reliability/gitops/litmus-rbac.yaml`
- `chaos/reliability/gitops/argo-rbac.yaml`
- `chaos/reliability/gitops/litmus-pod-delete-chaosengine.yaml`

## 4. Submit Dry-Run Workflow

```bash
kubectl --context "$KUBECTL_CONTEXT" create \
  -f chaos/reliability/examples/chaos-test-lifecycle.workflow.yaml
```

Watch it:

```bash
argo --context "$KUBECTL_CONTEXT" -n argo list \
  -l app.kubernetes.io/name=chaos-test-lifecycle
```

Dry-run should stop before injection and emit:

```text
CHAOS_INJECTION_STARTED: no
SMART_TRIAGE_FANOUT: not_started
EVAL_SCORE: pending
OUTPUT_SANITIZED: yes
```

## 5. Submit Non-Dry-Run After HITL

Only after the GitOps MR is approved/synced and human approval is recorded,
submit a private copy of `examples/chaos-test-lifecycle.workflow.yaml` with:

- `dry_run: "false"`
- `gitlab_mr_url: {{GITLAB_MR_URL}}`
- `approval_id: {{APPROVAL_ID}}`
- optional `chaos_result_name` if Litmus generates a non-default result name

Do not commit the private copy if it contains environment-specific URLs.

## 6. Capture Evidence

```bash
kubectl --context "$KUBECTL_CONTEXT" -n chaos-demo get chaosengine,chaosresult
kubectl --context "$KUBECTL_CONTEXT" -n chaos-demo get deploy chaos-target -o wide
kubectl --context "$KUBECTL_CONTEXT" -n argo get workflows \
  -l app.kubernetes.io/name=chaos-test-lifecycle
```

Append the sanitized outcome to
`WORK-CHAOS-TEST-MANAGER-LIVE-EVIDENCE.md` using these markers:

```text
HITL_STATUS: resumed
GITLAB_BRANCH: {{GITLAB_SOURCE_BRANCH_PREFIX}}/chaos-{{TEST_NAME}}
GITLAB_MR: {{GITLAB_MR_URL}}
CHAOS_INJECTION_STARTED: yes
CHAOS_INJECTION_COMPLETED: yes
SMART_TRIAGE_FANOUT: started
EVAL_SCORE: {{SCORE}}
SCORE_THRESHOLD: 8
REVIEW_MANAGER_TRIGGERED: {{yes|no}}
ALLOY_TELEMETRY_CAPTURED: yes
TEST_REPORT_CREATED: yes
KB_UPDATE_PROPOSED: {{yes|no}}
MEMORY_PROPOSAL_CREATED: {{yes|no}}
OUTPUT_SANITIZED: yes
```
