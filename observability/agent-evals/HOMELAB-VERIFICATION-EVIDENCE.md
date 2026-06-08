# Home-Lab Verification Evidence

Date: 2026-06-08

Environment: local home-lab Kubernetes context `proxmox-k8s`

Scope:

- Offline deterministic evaluation using checked-in sample cases and runs.
- Online Argo evaluation using `WorkflowTemplate/agent-lifecycle-eval`.
- Public runtime image only: `alpine:3.19` with inline package install.
- No live agent call, ticket update, workload remediation, or cluster mutation beyond applying the evaluator ConfigMap and WorkflowTemplate in `argo`.

## Offline Evaluation

Commands:

```bash
rm -rf /tmp/kagent-eval-verification
mkdir -p /tmp/kagent-eval-verification/pass /tmp/kagent-eval-verification/fail /tmp/kagent-eval-verification/agent

python3 observability/agent-evals/scripts/score-agent-run.py \
  --case observability/agent-evals/cases/crashloop-wrong-env-var.yaml \
  --run observability/agent-evals/results/sample/crashloop-wrong-env-var.run.json \
  --output-dir /tmp/kagent-eval-verification/agent

python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/pod-crashloop-hitl-remediation.yaml \
  --run observability/agent-evals/results/sample/lifecycle/pod-crashloop-hitl-remediation.lifecycle-run.json \
  --output-dir /tmp/kagent-eval-verification/pass

python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/chaos-pod-delete.yaml \
  --run observability/agent-evals/results/sample/lifecycle/chaos-pod-delete-below-threshold.lifecycle-run.json \
  --output-dir /tmp/kagent-eval-verification/fail

python3 observability/agent-evals/scripts/summarize-agent-scores.py \
  --results-dir observability/agent-evals/results/sample \
  --summary-md /tmp/kagent-eval-verification/summary.md \
  --metrics /tmp/kagent-eval-verification/agent-eval.prom
```

Observed results:

```text
score-agent-run.py crashloop-wrong-env-var: score=1.0 passed=true
score-lifecycle-run.py pod-crashloop-hitl-remediation: score=1.0 passed=true
score-lifecycle-run.py chaos-pod-delete-below-threshold: score=0.575 passed=false
```

The below-threshold case exited non-zero as expected. This proves weak or unsafe lifecycle delivery cannot be silently treated as success.

Metrics check:

```bash
rg -n "agent_eval_score|agent_lifecycle_eval_score|agent_lifecycle_eval_hard_failures|agent_lifecycle_eval_subscore" \
  /tmp/kagent-eval-verification/agent-eval.prom
```

Observed metric families included:

```text
agent_eval_score
agent_lifecycle_eval_score
agent_lifecycle_eval_hard_failures
agent_lifecycle_eval_subscore
```

## Argo Server-Side Validation

Cluster readiness checks:

```bash
kubectl config current-context
kubectl get ns argo kagent --ignore-not-found
kubectl api-resources | rg -i 'workflows|workflowtemplates|cronworkflows'
```

Observed:

```text
current-context: proxmox-k8s
namespace/argo: Active
namespace/kagent: Active
Argo Workflow CRDs present: workflows, workflowtemplates, cronworkflows, clusterworkflowtemplates
```

Server-side dry-runs:

```bash
kubectl kustomize observability/agent-evals >/tmp/kagent-agent-evals-rendered.yaml
kubectl apply --dry-run=server -k observability/agent-evals
kubectl create --dry-run=server -f observability/agent-evals/argo/lifecycle-eval-hook-example.yaml
kubectl create --dry-run=server -f a2a/smart-triage-fanout-demo/workflow.yaml
```

Observed:

```text
configmap/agent-eval-runtime-files configured (server dry run)
workflowtemplate.argoproj.io/agent-lifecycle-eval configured (server dry run)
workflow.argoproj.io/lifecycle-eval-hook-example-... created (server dry run)
workflow.argoproj.io/smart-triage-fanout-... created (server dry run)
```

The full smart-triage A2A workflow was server-side dry-run validated only in this pass. The safe online hook below was fully executed in Argo.

## Online Argo Runtime Verification

Applied runtime:

```bash
kubectl apply -k observability/agent-evals
kubectl get cm -n argo agent-eval-runtime-files -o json | jq -r '.data | keys[]' | sort
```

Observed ConfigMap keys:

```text
chaos-pod-delete.yaml
collect-lifecycle-evidence.py
metrics.py
pod-crashloop-hitl-remediation.yaml
reporting.py
score-lifecycle-run.py
summarize-agent-scores.py
```

Submitted the safe hook:

```bash
argo submit -n argo observability/agent-evals/argo/lifecycle-eval-hook-example.yaml --watch
```

Observed successful workflow:

```text
Name: lifecycle-eval-hook-example-sr5d5
Namespace: argo
ServiceAccount: smart-triage-fanout-workflow
Status: Succeeded
Duration: 20 seconds
Progress: 3/3

capture-sanitized-workflow: Succeeded
collect-marker-evidence: Succeeded
evaluate-lifecycle: Succeeded
```

Evaluator logs:

```text
wrote /work/output/lifecycle-run.json
score=1.0 passed=true json=/work/output/pod-crashloop-hitl-remediation.lifecycle-eval-hook-example-sr5d5.json markdown=/work/output/pod-crashloop-hitl-remediation.lifecycle-eval-hook-example-sr5d5.md
```

Output summary included:

```text
pod-crashloop-hitl-remediation | lifecycle-eval-hook-example-sr5d5 | PLACEHOLDER_GITLAB_ISSUE_ID | lifecycle-eval-hook-example-sr5d5 | 1.0 | true | None
```

Output metrics included:

```text
agent_lifecycle_eval_score{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5"} 1.0
agent_lifecycle_eval_passed{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5"} 1
agent_lifecycle_eval_hard_failures{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5"} 0
agent_lifecycle_eval_subscore{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5",dimension="a2a_coverage"} 1.0
agent_lifecycle_eval_subscore{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5",dimension="hitl_compliance"} 1.0
agent_lifecycle_eval_subscore{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5",dimension="incident_success"} 1.0
agent_lifecycle_eval_subscore{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5",dimension="remediation_outcome"} 1.0
agent_lifecycle_eval_subscore{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5",dimension="ticket_hygiene"} 1.0
agent_lifecycle_eval_subscore{case_id="pod-crashloop-hitl-remediation",run_id="lifecycle-eval-hook-example-sr5d5",workflow_name="lifecycle-eval-hook-example-sr5d5",dimension="triage_quality"} 1.0
```

## Runtime Issue Found And Fixed

First online hook attempt failed at the evaluator step:

```text
volume 'agent-eval-runtime' not found in workflow spec
```

Cause:

- The reusable evaluator was called through `templateRef`.
- The ConfigMap volume was defined at the `WorkflowTemplate.spec` level.
- The caller workflow did not receive that volume definition.

Fix:

- Moved the `agent-eval-runtime` ConfigMap volume onto the reusable `evaluate-lifecycle` template.
- Replaced GitLab example values such as `{{GITLAB_ISSUE_ID}}` with plain placeholder strings such as `PLACEHOLDER_GITLAB_ISSUE_ID` so the example is sanitized and runnable in Argo.

Verification after fix:

```text
kubectl apply --dry-run=server -k observability/agent-evals: passed
kubectl create --dry-run=server -f observability/agent-evals/argo/lifecycle-eval-hook-example.yaml: passed
argo submit -n argo observability/agent-evals/argo/lifecycle-eval-hook-example.yaml --watch: Succeeded
```

## Work-Agent Lift-And-Shift Entry Points

Use these as the starting implementation examples:

- `observability/agent-evals/kustomization.yaml`
- `observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml`
- `observability/agent-evals/argo/lifecycle-eval-hook-example.yaml`
- `a2a/smart-triage-fanout-demo/workflow.yaml`
- `observability/agent-evals/scripts/collect-lifecycle-evidence.py`
- `observability/agent-evals/scripts/score-lifecycle-run.py`
- `observability/agent-evals/scripts/summarize-agent-scores.py`
- `observability/agent-evals/scripts/metrics.py`

Expected work-environment verification sequence:

1. Run the offline pass/fail scorer commands against sanitized sample runs.
2. Run `kubectl apply --dry-run=server -k observability/agent-evals`.
3. Apply the evaluator ConfigMap and WorkflowTemplate through GitOps or a controlled Argo install path.
4. Submit `lifecycle-eval-hook-example.yaml` in a non-prod Argo namespace.
5. Confirm `score=1.0 passed=true`, lifecycle metrics, and low-cardinality labels.
6. Wire the same `templateRef` into the real triage/remediation workflow after remediation verification and before high-risk ticket close.
7. Route scores below threshold or hard failures to review-manager and leave the ticket open.
