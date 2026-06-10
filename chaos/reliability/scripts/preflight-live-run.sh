#!/usr/bin/env bash
set -euo pipefail

KUBECTL_CONTEXT="${KUBECTL_CONTEXT:-${1:-}}"
ARGO_NAMESPACE="${ARGO_NAMESPACE:-argo}"
TARGET_NAMESPACE="${TARGET_NAMESPACE:-chaos-demo}"
EXISTING_DRYRUN_NAMESPACE="${EXISTING_DRYRUN_NAMESPACE:-platform-dev-testing}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "PRECHECK_FAILED: missing required command: $1" >&2
    exit 1
  }
}

kubectl_cmd() {
  if [[ -n "$KUBECTL_CONTEXT" ]]; then
    kubectl --context "$KUBECTL_CONTEXT" "$@"
  else
    kubectl "$@"
  fi
}

require kubectl
require argo
require python3

cd "$ROOT"

echo "==> Local config validation"
python3 chaos/reliability/scripts/validate-reliability-configs.py \
  chaos/reliability/examples/pod-delete.chaostest.yaml \
  chaos/reliability/examples/sample-platform.reliabilitysuite.yaml \
  chaos/reliability/gitops/litmus-pod-delete-chaosengine.yaml

echo "==> Offline Argo lint"
argo lint --offline --kinds=workflowtemplates,cronworkflows,workflows \
  platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml \
  observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml \
  chaos/reliability/examples/chaos-test-lifecycle.workflow.yaml

echo "==> Required CRDs"
kubectl_cmd --request-timeout=10s get crd \
  workflowtemplates.argoproj.io \
  workflows.argoproj.io \
  cronworkflows.argoproj.io \
  chaosengines.litmuschaos.io \
  chaosresults.litmuschaos.io \
  agents.kagent.dev >/dev/null

kyverno_available=false
if kubectl_cmd --request-timeout=10s get crd policies.kyverno.io clusterpolicies.kyverno.io >/dev/null 2>&1 &&
  kubectl_cmd --request-timeout=10s get ns kyverno >/dev/null 2>&1; then
  kyverno_available=true
else
  echo "PRECHECK_WARNING: kyverno_not_installed_admission_policy_skipped"
fi

echo "==> Required namespaces"
kubectl_cmd --request-timeout=10s get ns \
  "$ARGO_NAMESPACE" \
  argo-events \
  kagent \
  monitoring >/dev/null

if kubectl_cmd --request-timeout=10s -n "$ARGO_NAMESPACE" get cm agent-eval-runtime-files >/dev/null 2>&1; then
  if ! kubectl_cmd --request-timeout=10s -n "$ARGO_NAMESPACE" get cm agent-eval-runtime-files \
    -o jsonpath='{.data.chaos-pod-delete\.yaml}' 2>/dev/null | grep -q 'name: chaos-pod-delete'; then
    echo "PRECHECK_WARNING: agent_eval_runtime_missing_chaos_case_apply_observability_agent_evals"
  fi
else
  echo "PRECHECK_WARNING: agent_eval_runtime_configmap_missing_apply_observability_agent_evals"
fi

echo "==> Workflow service account"
kubectl_cmd --request-timeout=20s apply --dry-run=server \
  -f chaos/reliability/gitops/argo-rbac.yaml >/dev/null

echo "==> Server dry-run: Argo lifecycle and eval templates"
kubectl_cmd --request-timeout=20s apply --dry-run=server \
  -f platform/argo-workflows/templates/chaos-test-lifecycle.yaml \
  -f platform/argo-workflows/templates/chaos-test-schedule-cronworkflow.yaml \
  -f observability/agent-evals/argo/lifecycle-eval-workflow-template.yaml >/dev/null

echo "==> Server dry-run: workflow submission example"
kubectl_cmd --request-timeout=20s create --dry-run=server \
  -f chaos/reliability/examples/chaos-test-lifecycle.workflow.yaml >/dev/null

echo "==> Server dry-run: chaos safety policy"
if [[ "$kyverno_available" == "true" ]]; then
  kubectl_cmd --request-timeout=20s apply --dry-run=server \
    -f infra/byo-kagent/kyverno-policies/validate-chaos-test-safety.yaml >/dev/null
else
  echo "PRECHECK_WARNING: kyverno_policy_server_dry_run_skipped"
fi

echo "==> Server dry-run: kagent agent CRs"
kubectl_cmd --request-timeout=20s apply --dry-run=server \
  -f agents/chaos-designer/agent.yaml \
  -f agents/chaos-test-manager/agent.yaml \
  -f agents/chaos-scheduler/agent.yaml \
  -f agents/reliability-suite-designer/agent.yaml \
  -f agents/reliability-reporting/agent.yaml \
  -f agents/review-manager/agent.yaml >/dev/null

echo "==> Server dry-run: Litmus ChaosEngine"
if kubectl_cmd --request-timeout=10s get ns "$TARGET_NAMESPACE" >/dev/null 2>&1; then
  kubectl_cmd --request-timeout=20s apply --dry-run=server \
    -k chaos/reliability/gitops >/dev/null
  opt_in="$(kubectl_cmd --request-timeout=10s -n "$TARGET_NAMESPACE" get deploy chaos-target \
    -o jsonpath='{.spec.template.metadata.labels.reliability\.platform/chaos-optin}' 2>/dev/null || true)"
  if [[ "$opt_in" != "true" ]]; then
    echo "PRECHECK_WARNING: target_opt_in_label_missing_live_cluster_apply_gitops_overlay_before_non_dry_run"
  fi
else
  kubectl_cmd --request-timeout=10s get ns "$EXISTING_DRYRUN_NAMESPACE" >/dev/null
  kubectl kustomize chaos/reliability/gitops | python3 -c 'import sys,yaml
docs = []
namespace = sys.argv[1]
for doc in yaml.safe_load_all(sys.stdin):
    if not doc or doc.get("kind") == "Namespace":
        continue
    doc.setdefault("metadata", {})["namespace"] = namespace
    if doc.get("kind") == "ChaosEngine":
        doc.setdefault("spec", {}).setdefault("appinfo", {})["appns"] = namespace
    docs.append(doc)
yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
' "$EXISTING_DRYRUN_NAMESPACE" | kubectl_cmd --request-timeout=20s apply --dry-run=server -f - >/dev/null
fi

echo "PRECHECK_PASSED: yes"
echo "OUTPUT_SANITIZED: yes"
