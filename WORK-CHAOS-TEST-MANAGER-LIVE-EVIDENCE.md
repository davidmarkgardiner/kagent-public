# Chaos Test Manager Evidence

Date: 2026-06-03

This file records evidence from the first execution pass. It is local skeleton
evidence only; it is not evidence of a live chaos injection.

## Local Evidence

| Check | Result |
|---|---|
| YAML parse for new/modified skeleton files | Passed |
| `ChaosTest` example schema validation | Passed |
| `ReliabilitySuite` example schema validation | Passed |
| Local reliability config policy gate | Passed |
| GitOps ChaosEngine kustomize render | Passed |
| Kyverno safety policy bundle kustomize render | Passed |
| `kubectl kustomize observability/agent-evals` | Passed |
| Offline Argo lint for chaos lifecycle + eval workflow templates | Passed |
| Offline Argo lint for suspended chaos schedule CronWorkflow | Passed |
| Grafana chaos lifecycle dashboard JSON parse | Passed |
| Synthetic `chaos-pod-delete` lifecycle scoring | Passed, no hard failures |
| `git diff --check` | Passed |
| New-file public-safety regex sweep | Passed |

## Interim Cluster Server Dry-Run Evidence

An alternate compatible non-production Kubernetes cluster was reachable after
the initial local pass. The cluster endpoint is intentionally omitted from this
public/sanitized evidence file.

| Check | Result |
|---|---|
| Required CRDs present: Argo WorkflowTemplate/CronWorkflow, Litmus ChaosEngine/ChaosResult, Kyverno Policy/ClusterPolicy, kagent Agent | Passed |
| Required namespaces present: `argo`, `argo-events`, `kagent`, `kyverno`, `monitoring` | Passed |
| Argo chaos lifecycle WorkflowTemplate server dry-run | Passed |
| Suspended chaos schedule CronWorkflow server dry-run | Passed |
| Agent lifecycle eval WorkflowTemplate server dry-run | Passed |
| Six chaos/reliability kagent Agent CRs server dry-run | Passed |
| Kyverno chaos safety ClusterPolicy server dry-run against installed `kyverno.io/v1` API | Passed |
| Litmus ChaosEngine server dry-run against installed Litmus CRD | Passed using a validation-only namespace remap to an existing non-production namespace |
| Live-run preflight helper against interim cluster | Passed |

Kyverno returned an operational warning that the reports controller service
account needs `get`, `list`, and `watch` on `litmuschaos.io/v1alpha1/ChaosEngine`
for background reporting. Admission/schema validation still passed.

## Target Cluster Dry-Run Evidence

The originally unavailable Proxmox-backed Kubernetes context became reachable
later on 2026-06-03. The API endpoint is intentionally omitted from this
public/sanitized evidence file.

| Check | Result |
|---|---|
| Target cluster node readiness | Passed |
| Required namespaces present: `argo`, `argo-events`, `kagent`, `monitoring`, `chaos-demo` | Passed |
| Required CRDs present: Argo WorkflowTemplate/Workflow/CronWorkflow, Litmus ChaosEngine/ChaosResult, kagent Agent | Passed |
| Kyverno admission policy availability | Skipped; Kyverno is not installed on this target cluster |
| Target workload readiness | Passed, `chaos-demo/chaos-target` rolled out 2/2 |
| Target workload opt-in label | Passed after applying non-injection prerequisites |
| Dedicated workflow service account and read-only Litmus RBAC | Applied |
| Chaos lifecycle WorkflowTemplate | Applied |
| Suspended schedule CronWorkflow | Applied |
| Agent lifecycle eval WorkflowTemplate | Present and configured |
| Dry-run chaos lifecycle Workflow | Succeeded |
| Dry-run HITL suspend/resume | Passed |
| Dry-run Litmus injection guard | Passed; injection skipped |

No new Litmus experiment was started during the dry-run pass. Existing
`ChaosEngine`, `ChaosResult`, and Litmus job records in `chaos-demo` were from
prior completed runs.

## Target Cluster Live Chaos Evidence

The target Proxmox-backed Kubernetes cluster ran the first lower-env
`chaos-demo-pod-delete` scenario on 2026-06-03.

| Check | Result |
|---|---|
| Preflight immediately before live run | Passed |
| HITL gate reached before non-dry-run continuation | Passed |
| Active Litmus `ChaosEngine` created | Passed |
| `ChaosResult` terminal phase | `Completed` |
| `ChaosResult` verdict | `Pass` |
| Target workload recovery | Passed, `chaos-demo/chaos-target` recovered to 2/2 Ready |
| Smart triage/evidence marker collection | Passed |
| Lifecycle eval score | `score=1.0 passed=true` |
| Final lifecycle eval workflow | Succeeded |
| New Litmus job created for this run | `pod-delete-{{RUN_SUFFIX}}`, completed |

The first non-dry-run workflow observed the Litmus pass and collected markers,
then failed at the final eval step because the calling workflow template did not
include the `agent-eval-runtime` volume. The template was patched, the
`observability/agent-evals` ConfigMap was applied so it included
`chaos-pod-delete.yaml`, and a second lifecycle workflow completed the
evaluation against the already-passed `ChaosResult`. No second Litmus job was
created by the eval rerun.

Final live markers:

Note: the Litmus `ChaosResult`, workload recovery, and lifecycle eval are live
target-cluster evidence. The `SMART_TRIAGE_FANOUT`, `SPECIALIST_*`, and
`GRAFANA_EVIDENCE` markers in this run are template-emitted skeleton markers
from `platform/argo-workflows/templates/chaos-test-lifecycle.yaml`; the chaos
workflow did not yet call the live smart-triage fan-out or Grafana MCP path.

```text
CHAOS_SPEC_DRAFTED: yes
CHAOS_POLICY_VALIDATED: yes
HITL_REQUIRED: yes
HITL_STATUS: resumed
HITL_EVIDENCE_SOURCE: workflow_parameter
GITOPS_SYNC_STATUS: observed
CHAOS_INJECTION_STARTED: yes
CHAOS_INJECTION_COMPLETED: yes
CHAOS_RESULT_VERDICT: Pass
SMART_TRIAGE_FANOUT: started
INCIDENT_SYNTHESIS: completed
SPECIALIST_MARKERS_SOURCE: synthetic_template_contract
SPECIALIST_KUBERNETES: completed
SPECIALIST_NETWORK: completed
SPECIALIST_GRAFANA: completed
SPECIALIST_GITOPS: completed
VERIFICATION_PASSED: yes
EVAL_SCORE: 1.0
EVAL_PASSED: true
SCORE_THRESHOLD: 8
OUTPUT_SANITIZED: yes
```

## Commands Run

```bash
python3 - <<'PY'
import pathlib, yaml
paths = [...]
for path in paths:
    with open(path, encoding='utf-8') as f:
        list(yaml.safe_load_all(f))
    print(f'YAML_OK {path}')
PY
```

```bash
python3 -m venv /tmp/kagent-jsonschema.XXXXXX/venv
/tmp/kagent-jsonschema.XXXXXX/venv/bin/pip install --quiet jsonschema pyyaml
/tmp/kagent-jsonschema.XXXXXX/venv/bin/python - <<'PY'
from jsonschema import Draft202012Validator
...
PY
```

Output:

```text
SCHEMA_OK chaos/reliability/examples/pod-delete.chaostest.yaml
SCHEMA_OK chaos/reliability/examples/sample-platform.reliabilitysuite.yaml
```

```bash
python3 chaos/reliability/scripts/validate-reliability-configs.py \
  chaos/reliability/examples/pod-delete.chaostest.yaml \
  chaos/reliability/examples/sample-platform.reliabilitysuite.yaml \
  chaos/reliability/gitops/litmus-pod-delete-chaosengine.yaml
```

Output:

```text
RELIABILITY_CONFIG_VALID: yes checked=3
OUTPUT_SANITIZED: yes
```

```bash
kubectl kustomize chaos/reliability/gitops
kubectl kustomize infra/byo-kagent/kyverno-policies
```

Result: rendered successfully. The Kyverno bundle includes
`validate-chaos-test-safety`.

```bash
kubectl kustomize observability/agent-evals
```

Result: rendered successfully and included `chaos-pod-delete.yaml` in the
`agent-eval-runtime-files` ConfigMap.

```bash
argo lint --offline --kinds=workflowtemplates \
  platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml
```

Output:

```text
no linting errors found
```

```bash
argo lint --offline --kinds=workflowtemplates,cronworkflows \
  platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml \
  observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml
```

Output:

```text
no linting errors found
```

```bash
python3 -m json.tool \
  observability/chaos-test-manager/grafana/chaos-test-lifecycle-dashboard.json
```

Result: parsed successfully.

```bash
PYTHONPATH=observability/agent-evals/scripts \
python3 observability/agent-evals/scripts/collect-lifecycle-evidence.py \
  --evidence /tmp/.../markers.txt \
  --output /tmp/.../lifecycle-run.json \
  --case-id chaos-pod-delete \
  --run-id local-skeleton \
  --workflow-name chaos-test-lifecycle-skeleton \
  --incident-id '{{GITLAB_MR_URL}}' \
  --namespace chaos-demo \
  --workload chaos-target \
  --failure-mode pod-delete \
  --ticket-system GitLab \
  --ticket-id '{{GITLAB_MR_URL}}' \
  --ticket-url '{{GITLAB_MR_URL}}' \
  --remediation-mode gitops_or_workflow_only

PYTHONPATH=observability/agent-evals/scripts \
python3 observability/agent-evals/scripts/score-lifecycle-run.py \
  --case observability/agent-evals/lifecycle-cases/chaos-pod-delete.yaml \
  --run /tmp/.../lifecycle-run.json \
  --output-dir /tmp/.../out
```

Output:

```text
score=1.0 passed=true
hard_failures=[]
warnings=[]
```

## Interim Server Dry-Run Commands

```bash
kubectl --context {{INTERIM_KUBECONFIG_CONTEXT}} --request-timeout=10s \
  get crd workflowtemplates.argoproj.io cronworkflows.argoproj.io \
  chaosengines.litmuschaos.io chaosresults.litmuschaos.io \
  policies.kyverno.io clusterpolicies.kyverno.io agents.kagent.dev
```

Result: all required CRDs were present.

```bash
kubectl --context {{INTERIM_KUBECONFIG_CONTEXT}} --request-timeout=20s \
  apply --dry-run=server \
  -f platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  -f platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml \
  -f observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml
```

Output:

```text
workflowtemplate.argoproj.io/chaos-test-lifecycle created (server dry run)
cronworkflow.argoproj.io/chaos-demo-pod-delete-schedule created (server dry run)
workflowtemplate.argoproj.io/agent-lifecycle-eval created (server dry run)
```

```bash
kubectl --context {{INTERIM_KUBECONFIG_CONTEXT}} --request-timeout=20s \
  apply --dry-run=server \
  -f agents/chaos-designer/agent.yaml \
  -f agents/chaos-test-manager/agent.yaml \
  -f agents/chaos-scheduler/agent.yaml \
  -f agents/reliability-suite-designer/agent.yaml \
  -f agents/reliability-reporting/agent.yaml \
  -f agents/review-manager/agent.yaml
```

Output:

```text
agent.kagent.dev/chaos-designer-agent created (server dry run)
agent.kagent.dev/chaos-test-manager-agent created (server dry run)
agent.kagent.dev/chaos-scheduler-agent created (server dry run)
agent.kagent.dev/reliability-suite-designer-agent created (server dry run)
agent.kagent.dev/reliability-reporting-agent created (server dry run)
agent.kagent.dev/review-manager-agent created (server dry run)
```

```bash
kubectl --context {{INTERIM_KUBECONFIG_CONTEXT}} --request-timeout=20s \
  apply --dry-run=server \
  -f infra/byo-kagent/kyverno-policies/validate-chaos-test-safety.yaml
```

Output:

```text
clusterpolicy.kyverno.io/validate-chaos-test-safety created (server dry run)
```

```bash
kubectl kustomize chaos/reliability/gitops | \
  {{VALIDATION_ONLY_NAMESPACE_REMAP_TO_EXISTING_NON_PROD_NAMESPACE}} | \
  kubectl --context {{INTERIM_KUBECONFIG_CONTEXT}} --request-timeout=20s \
    apply --dry-run=server -f -
```

Output:

```text
chaosengine.litmuschaos.io/chaos-demo-pod-delete-pod-delete created (server dry run)
```

```bash
KUBECTL_CONTEXT={{INTERIM_KUBECONFIG_CONTEXT}} \
  bash chaos/reliability/scripts/preflight-live-run.sh
```

Output:

```text
RELIABILITY_CONFIG_VALID: yes checked=3
OUTPUT_SANITIZED: yes
no linting errors found
PRECHECK_PASSED: yes
OUTPUT_SANITIZED: yes
```

## Target Dry-Run Commands

```bash
KUBECTL_CONTEXT={{TARGET_KUBECONFIG_CONTEXT}} \
  bash chaos/reliability/scripts/preflight-live-run.sh
```

Output:

```text
RELIABILITY_CONFIG_VALID: yes checked=3
OUTPUT_SANITIZED: yes
no linting errors found
PRECHECK_WARNING: kyverno_not_installed_admission_policy_skipped
PRECHECK_WARNING: kyverno_policy_server_dry_run_skipped
PRECHECK_PASSED: yes
OUTPUT_SANITIZED: yes
```

```bash
kubectl --context {{TARGET_KUBECONFIG_CONTEXT}} apply \
  -f chaos/reliability/gitops/chaos-target.yaml \
  -f chaos/reliability/gitops/litmus-rbac.yaml \
  -f chaos/reliability/gitops/argo-rbac.yaml \
  -f platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  -f platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml \
  -f observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml
```

Result: non-injection prerequisites and templates applied successfully. The
`ChaosEngine` manifest was not applied in this step.

```bash
kubectl --context {{TARGET_KUBECONFIG_CONTEXT}} create \
  -f chaos/reliability/examples/chaos-test-lifecycle.workflow.yaml -o name

argo --context {{TARGET_KUBECONFIG_CONTEXT}} -n argo \
  resume {{DRY_RUN_WORKFLOW_NAME}}

argo --context {{TARGET_KUBECONFIG_CONTEXT}} -n argo \
  watch {{DRY_RUN_WORKFLOW_NAME}}
```

Output markers:

```text
CHAOS_SPEC_DRAFTED: yes
CHAOS_POLICY_VALIDATED: yes
HITL_REQUIRED: yes
HITL_STATUS: resumed
GITOPS_SYNC_STATUS: dry_run_skipped
CHAOS_INJECTION_STARTED: no
CHAOS_INJECTION_COMPLETED: no
CHAOS_RESULT_STATUS: dry_run_skipped
SMART_TRIAGE_FANOUT: not_started
EVAL_SCORE: pending
SCORE_THRESHOLD: 8
TEST_REPORT_CREATED: no
OUTPUT_SANITIZED: yes
```

## Remaining Live Checks

The originally configured Kubernetes API was unreachable from this machine
during the first execution pass. It later became reachable and the first
lower-env pod-delete chaos run completed successfully. These checks are still
not claimed as passed:

- GitOps/MR creation and HITL resume against the target environment.
- Grafana/Alloy telemetry capture from real metrics, review-manager routing,
  and final per-test report MR generation.
- Kyverno admission behavior on the Proxmox-backed target cluster, because
  Kyverno is not installed there.

An interim non-offline Argo lint attempt reached the cluster, but failed because
the referenced `agent-lifecycle-eval` WorkflowTemplate was not installed there.
Offline lint with both local WorkflowTemplates in the argument list passed.

Latest reachability check:

```bash
kubectl --request-timeout=5s get ns argo argo-events kagent chaos-demo
```

Result: failed with the configured Kubernetes API endpoint unreachable.

## Live Evidence To Capture Next

When a compatible non-production cluster is reachable, append:

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
