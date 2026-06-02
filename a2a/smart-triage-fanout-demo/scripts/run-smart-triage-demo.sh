#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEMO_DIR="$ROOT_DIR/a2a/smart-triage-fanout-demo"
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

classify_failure() {
  local wf_name="$1"
  echo "-- failure classification"
  "${ARGO[@]}" get -n argo "$wf_name" || true
  local failed_pods
  failed_pods="$("${KUBECTL[@]}" get pods -n argo -l "workflows.argoproj.io/workflow=$wf_name" \
    -o jsonpath='{range .items[?(@.status.phase!="Succeeded")]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)"
  if [[ -z "$failed_pods" ]]; then
    echo "FAILURE_CLASS: UNKNOWN_NO_FAILED_POD"
    return
  fi
  while IFS= read -r pod; do
    [[ -z "$pod" ]] && continue
    echo "failed pod: $pod"
    "${KUBECTL[@]}" logs -n argo "pod/$pod" -c main --tail=120 || true
  done <<< "$failed_pods"
  echo "FAILURE_CLASS: inspect pod logs for A2A_TRANSPORT_ERROR, A2A_TASK_TIMEOUT, MODEL_BACKEND_UNAVAILABLE, MCP_UNAVAILABLE, or SPECIALIST_CONTRACT_FAILED"
}

echo "== Smart triage fan-out demo =="
if [[ -n "$KUBE_CONTEXT" ]]; then
  echo "Kubernetes context: $KUBE_CONTEXT"
else
  echo "Kubernetes context: $(kubectl config current-context)"
fi
echo "ModelConfig: $MODEL_CONFIG"

"${KUBECTL[@]}" get modelconfig -n kagent "$MODEL_CONFIG" >/dev/null

echo "-- applying smart-triage fan-out agents"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/agents.yaml"
"${KUBECTL[@]}" patch agent -n kagent \
  smart-triage-kubernetes-specialist \
  smart-triage-network-specialist \
  smart-triage-grafana-specialist \
  smart-triage-gitops-specialist \
  smart-triage-incident-commander \
  --type=json \
  -p="[{\"op\":\"replace\",\"path\":\"/spec/declarative/modelConfig\",\"value\":\"$MODEL_CONFIG\"}]"
"${KUBECTL[@]}" wait --for=condition=Ready -n kagent \
  agent/smart-triage-kubernetes-specialist \
  agent/smart-triage-network-specialist \
  agent/smart-triage-grafana-specialist \
  agent/smart-triage-gitops-specialist \
  agent/smart-triage-incident-commander \
  --timeout=300s

echo "-- applying workflow RBAC"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/workflow-rbac.yaml"

echo "-- submitting smart-triage fan-out workflow"
WF_NAME="$("${ARGO[@]}" submit -n argo "$DEMO_DIR/workflow.yaml" -o name | sed 's|^workflow/||' | tr -d '[:space:]')"
echo "workflow: $WF_NAME"

echo "-- waiting for workflow to suspend at the human review gate"
SUSPENDED=false
for _ in $(seq 1 180); do
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
    classify_failure "$WF_NAME"
    exit 1
  fi
  sleep 2
done

if [[ "$SUSPENDED" != "true" ]]; then
  echo "workflow did not reach suspend gate" >&2
  classify_failure "$WF_NAME"
  exit 1
fi

echo "-- resuming workflow to simulate human approval"
"${ARGO[@]}" resume -n argo "$WF_NAME"

echo "-- waiting for workflow completion"
for _ in $(seq 1 180); do
  PHASE="$("${KUBECTL[@]}" get wf -n argo "$WF_NAME" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  case "$PHASE" in
    Succeeded)
      echo "PASS: smart triage fan-out workflow succeeded"
      "${ARGO[@]}" get -n argo "$WF_NAME" | head -100
      exit 0
      ;;
    Failed|Error)
      classify_failure "$WF_NAME"
      exit 1
      ;;
  esac
  sleep 5
done

echo "workflow did not complete within timeout" >&2
classify_failure "$WF_NAME"
exit 1
