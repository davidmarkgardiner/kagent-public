#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEMO_DIR="$ROOT_DIR/a2a/smart-triage-fanout-demo"
KUBE_CONTEXT="${KUBE_CONTEXT:-}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need kubectl
need argo
need jq

KUBECTL=(kubectl)
ARGO=(argo)
if [[ -n "$KUBE_CONTEXT" ]]; then
  KUBECTL+=(--context "$KUBE_CONTEXT")
  ARGO+=(--context "$KUBE_CONTEXT")
fi

classify_failure() {
  local workflow="$1"
  echo "-- failure classification"
  "${ARGO[@]}" get -n argo "$workflow" || true
  "${KUBECTL[@]}" logs -n argo -l "workflows.argoproj.io/workflow=$workflow" \
    -c main --tail=160 || true
}

echo "== Selective smart-triage fixture =="
if [[ -n "$KUBE_CONTEXT" ]]; then
  echo "Kubernetes context: $KUBE_CONTEXT"
else
  echo "Kubernetes context: $(kubectl config current-context)"
fi

echo "-- applying lifecycle, selective WorkflowTemplate and RBAC"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/workflow-rbac.yaml"
"${KUBECTL[@]}" apply -k "$DEMO_DIR/finding-lifecycle"
"${KUBECTL[@]}" rollout status -n argo deployment/smart-triage-finding-lifecycle --timeout=120s
"${KUBECTL[@]}" apply -k "$DEMO_DIR/selective-orchestrator"

payload="$(jq -c . "$DEMO_DIR/selective-orchestrator/fixtures/crashloop-alert.json")"
echo "-- submitting focused public-safe fixture"
WF_NAME="$("${ARGO[@]}" submit -n argo "$DEMO_DIR/workflow.yaml" \
  -p alert_source=manual-fixture \
  -p alert_payload="$payload" \
  -o name | sed 's|^workflow/||' | tr -d '[:space:]')"
echo "workflow: $WF_NAME"

for _ in $(seq 1 90); do
  phase="$("${KUBECTL[@]}" get workflow -n argo "$WF_NAME" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  case "$phase" in
    Succeeded)
      "${KUBECTL[@]}" get workflow -n argo "$WF_NAME" -o json | jq -r '
        .status.nodes[] | select(.outputs.parameters) |
        .outputs.parameters | map({key:.name,value:.value}) | from_entries |
        "STATUS: \(.status)\nSELECTED: \(."selected-specialists")\nMETRICS: \(.metrics)\nLIFECYCLE: \(."lifecycle-decision")"'
      echo "PASS: selective smart-triage fixture succeeded"
      exit 0
      ;;
    Failed|Error)
      classify_failure "$WF_NAME"
      exit 1
      ;;
  esac
  sleep 2
done

echo "workflow did not complete within timeout" >&2
classify_failure "$WF_NAME"
exit 1
