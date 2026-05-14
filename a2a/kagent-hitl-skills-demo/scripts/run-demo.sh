#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEMO_DIR="$ROOT_DIR/a2a/kagent-hitl-skills-demo"
MOCK_BOT_PORT="${MOCK_BOT_PORT:-18080}"
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

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$MOCK_BOT_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  for candidate in 18081 18082 18083 18084 18085; do
    if ! lsof -nP -iTCP:"$candidate" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "local port $MOCK_BOT_PORT is busy; using $candidate for mock-bot port-forward"
      MOCK_BOT_PORT="$candidate"
      break
    fi
  done
fi

echo "== MIL-126 demo: A2A + HITL + skills =="
if [[ -n "$KUBE_CONTEXT" ]]; then
  echo "Kubernetes context: $KUBE_CONTEXT"
else
  echo "Kubernetes context: $(kubectl config current-context)"
fi
echo "ModelConfig: $MODEL_CONFIG"

"${KUBECTL[@]}" get modelconfig -n kagent "$MODEL_CONFIG" >/dev/null

echo "-- applying three demo kagent agents"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/agents.yaml"
"${KUBECTL[@]}" patch agent -n kagent \
  demo-skill-loader-agent \
  demo-hitl-approval-agent \
  demo-a2a-coordinator-agent \
  --type=json \
  -p="[{\"op\":\"replace\",\"path\":\"/spec/declarative/modelConfig\",\"value\":\"$MODEL_CONFIG\"}]"
"${KUBECTL[@]}" wait --for=condition=Ready -n kagent \
  agent/demo-skill-loader-agent \
  agent/demo-hitl-approval-agent \
  agent/demo-a2a-coordinator-agent \
  --timeout=240s

echo "-- applying HITL EventSource and Sensor"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/workflow-rbac.yaml"
"${KUBECTL[@]}" apply -f "$ROOT_DIR/platform/teams-hitl/eventsource.yaml"
"${KUBECTL[@]}" apply -f "$ROOT_DIR/platform/teams-hitl/sensor.yaml"

echo "-- publishing mock bot source as a ConfigMap"
"${KUBECTL[@]}" create configmap mock-bot-src -n argo \
  --from-file=app.py="$ROOT_DIR/platform/teams-hitl/mock-bot/app.py" \
  --from-file=requirements.txt="$ROOT_DIR/platform/teams-hitl/mock-bot/requirements.txt" \
  --dry-run=client -o yaml | "${KUBECTL[@]}" apply -f -

echo "-- deploying mock approval bot"
"${KUBECTL[@]}" apply -f "$DEMO_DIR/mock-bot-runtime.yaml"
"${KUBECTL[@]}" rollout status deploy/mock-bot -n argo --timeout=240s

echo "-- submitting A2A/HITL workflow"
WF_NAME="$("${ARGO[@]}" submit -n argo "$DEMO_DIR/workflow.yaml" -o name | sed 's|^workflow/||' | tr -d '[:space:]')"
echo "workflow: $WF_NAME"

echo "-- waiting for workflow to suspend at the human approval gate"
for _ in $(seq 1 90); do
  PHASE="$("${KUBECTL[@]}" get wf -n argo "$WF_NAME" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  SUSPEND_PHASE="$("${KUBECTL[@]}" get wf -n argo "$WF_NAME" -o json 2>/dev/null \
    | jq -r '.status.nodes // {} | to_entries[] | select(.value.type=="Suspend") | .value.phase' \
    | head -1)"
  if [[ "$SUSPEND_PHASE" == "Running" ]]; then
    echo "workflow is waiting for human approval"
    break
  fi
  if [[ "$PHASE" == "Failed" || "$PHASE" == "Error" ]]; then
    "${ARGO[@]}" get -n argo "$WF_NAME"
    exit 1
  fi
  sleep 2
done

"${KUBECTL[@]}" port-forward -n argo svc/mock-bot "$MOCK_BOT_PORT:8080" >/tmp/mil-126-mock-bot-pf.log 2>&1 &
PF_PID=$!
cleanup() {
  kill "$PF_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT
for _ in $(seq 1 20); do
  if ! kill -0 "$PF_PID" >/dev/null 2>&1; then
    cat /tmp/mil-126-mock-bot-pf.log >&2 || true
    exit 1
  fi
  if curl -fsS --max-time 3 "http://localhost:$MOCK_BOT_PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "-- finding pending approval request"
APPROVAL_ID=""
for _ in $(seq 1 30); do
  PENDING="$(curl -fsS --max-time 5 "http://localhost:$MOCK_BOT_PORT/pending" || echo "[]")"
  APPROVAL_ID="$(echo "$PENDING" | jq -r --arg wf "$WF_NAME" '.[] | select(.workflow_name==$wf) | .approval_id' | head -1)"
  if [[ -n "$APPROVAL_ID" ]]; then
    break
  fi
  sleep 2
done

if [[ -z "$APPROVAL_ID" ]]; then
  echo "no pending approval found for workflow $WF_NAME" >&2
  curl -sS "http://localhost:$MOCK_BOT_PORT/pending" | jq .
  exit 1
fi

echo "approval id: $APPROVAL_ID"
echo "-- approving through mock bot"
curl -sS -X POST "http://localhost:$MOCK_BOT_PORT/decide/$APPROVAL_ID?decision=approved&approver=mil-126-demo" | jq .

echo "-- waiting for workflow completion"
for _ in $(seq 1 120); do
  PHASE="$("${KUBECTL[@]}" get wf -n argo "$WF_NAME" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  case "$PHASE" in
    Succeeded)
      echo "PASS: workflow succeeded after A2A calls and HITL approval"
      "${ARGO[@]}" get -n argo "$WF_NAME" | head -40
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
