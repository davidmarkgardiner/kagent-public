#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEMO_DIR="$ROOT_DIR/a2a/platform-memory-showcase-demo"
KUBE_CONTEXT="${KUBE_CONTEXT:-}"
MODEL_CONFIG="${MODEL_CONFIG:-default-model-config}"

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

echo "== Platform memory showcase demo =="
if [[ -n "$KUBE_CONTEXT" ]]; then
  echo "Kubernetes context: $KUBE_CONTEXT"
else
  echo "Kubernetes context: $(kubectl config current-context)"
fi
echo "ModelConfig: $MODEL_CONFIG"

"${KUBECTL[@]}" get modelconfig -n kagent "$MODEL_CONFIG" >/dev/null
"${KUBECTL[@]}" get remotemcpserver -n kagent memory-mcp >/dev/null

echo "-- applying memory showcase agents"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/agents.yaml"
"${KUBECTL[@]}" patch agent -n kagent \
  demo-memory-seeder-agent \
  demo-memory-triage-agent \
  --type=json \
  -p="[{\"op\":\"replace\",\"path\":\"/spec/declarative/modelConfig\",\"value\":\"$MODEL_CONFIG\"}]"
"${KUBECTL[@]}" wait --for=condition=Ready -n kagent \
  agent/demo-memory-seeder-agent \
  agent/demo-memory-triage-agent \
  --timeout=240s

echo "-- applying workflow RBAC"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/workflow-rbac.yaml"

echo "-- submitting memory showcase workflow"
WF_NAME="$("${ARGO[@]}" submit -n argo "$DEMO_DIR/workflow.yaml" -o name | sed 's|^workflow/||' | tr -d '[:space:]')"
echo "workflow: $WF_NAME"

echo "-- waiting for workflow to suspend at the human review gate"
SUSPENDED=false
for _ in $(seq 1 120); do
  PHASE="$("${KUBECTL[@]}" get wf -n argo "$WF_NAME" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  SUSPEND_PHASE="$("${KUBECTL[@]}" get wf -n argo "$WF_NAME" -o json 2>/dev/null \
    | jq -r '.status.nodes // {} | to_entries[] | select(.value.type=="Suspend") | .value.phase' \
    | head -1)"
  if [[ "$SUSPEND_PHASE" == "Running" ]]; then
    SUSPENDED=true
    echo "workflow is waiting for human review"
    break
  fi
  if [[ "$PHASE" == "Failed" || "$PHASE" == "Error" ]]; then
    "${ARGO[@]}" get -n argo "$WF_NAME"
    exit 1
  fi
  sleep 2
done

if [[ "$SUSPENDED" != "true" ]]; then
  echo "workflow did not reach suspend gate" >&2
  "${ARGO[@]}" get -n argo "$WF_NAME"
  exit 1
fi

echo "-- resuming workflow to simulate human approval"
"${ARGO[@]}" resume -n argo "$WF_NAME"

echo "-- waiting for workflow completion"
for _ in $(seq 1 120); do
  PHASE="$("${KUBECTL[@]}" get wf -n argo "$WF_NAME" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  case "$PHASE" in
    Succeeded)
      echo "PASS: platform memory showcase workflow succeeded"
      "${ARGO[@]}" get -n argo "$WF_NAME" | head -80
      exit 0
      ;;
    Failed|Error)
      "${ARGO[@]}" get -n argo "$WF_NAME"
      exit 1
      ;;
  esac
  sleep 5
done

echo "workflow did not complete within timeout" >&2
"${ARGO[@]}" get -n argo "$WF_NAME"
exit 1
