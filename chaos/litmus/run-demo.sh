#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

KUBECTL_CONTEXT="${KUBECTL_CONTEXT:-}"
LITMUS_NAMESPACE="${LITMUS_NAMESPACE:-litmus}"
TARGET_NAMESPACE="${TARGET_NAMESPACE:-chaos-demo}"
ARGO_EVENTS_NAMESPACE="${ARGO_EVENTS_NAMESPACE:-argo-events}"
WORKFLOW_NAMESPACE="${WORKFLOW_NAMESPACE:-argo}"
KAGENT_NAMESPACE="${KAGENT_NAMESPACE:-kagent}"
RESET_LITMUS_MONGODB="${RESET_LITMUS_MONGODB:-auto}"
DEMO_AVOID_NODE="${DEMO_AVOID_NODE:-}"
avoid_node_was_unschedulable=""

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

delete_engine() {
  local engine_name="$1"
  kubectl delete chaosengine "$engine_name" -n "$TARGET_NAMESPACE" --ignore-not-found --wait=false
  sleep 5
  if kubectl get chaosengine "$engine_name" -n "$TARGET_NAMESPACE" >/dev/null 2>&1; then
    kubectl patch chaosengine "$engine_name" -n "$TARGET_NAMESPACE" --type=merge -p '{"metadata":{"finalizers":[]}}' >/dev/null || true
  fi
}

wait_for_result() {
  local result_name="$1"
  local timeout="${2:-240}"
  local start
  start="$(date +%s)"

  while true; do
    if kubectl get chaosresult "$result_name" -n "$TARGET_NAMESPACE" >/dev/null 2>&1; then
      verdict="$(kubectl get chaosresult "$result_name" -n "$TARGET_NAMESPACE" -o jsonpath='{.status.experimentStatus.verdict}' 2>/dev/null || true)"
      phase="$(kubectl get chaosresult "$result_name" -n "$TARGET_NAMESPACE" -o jsonpath='{.status.experimentStatus.phase}' 2>/dev/null || true)"
      echo "chaosresult/$result_name phase=${phase:-unknown} verdict=${verdict:-unknown}"
      if [[ "$verdict" == "Pass" || "$verdict" == "Fail" ]]; then
        return 0
      fi
    fi

    if (( "$(date +%s)" - start > timeout )); then
      echo "timed out waiting for chaosresult/$result_name to finish" >&2
      kubectl get chaosresult -n "$TARGET_NAMESPACE" || true
      return 1
    fi

    sleep 5
  done
}

latest_workflow_name() {
  kubectl get workflows -n "$WORKFLOW_NAMESPACE" \
    -l app.kubernetes.io/name=kagent-triage-litmus \
    --sort-by=.metadata.creationTimestamp \
    -o name 2>/dev/null | tail -n 1 | sed 's#^.*/##'
}

wait_for_new_workflow_success() {
  local previous_workflow="$1"
  local timeout="${2:-300}"
  local start
  local workflow=""
  local phase=""
  start="$(date +%s)"

  while true; do
    workflow="$(latest_workflow_name || true)"
    if [[ -n "$workflow" && "$workflow" != "$previous_workflow" ]]; then
      break
    fi
    if (( "$(date +%s)" - start > timeout )); then
      echo "timed out waiting for a new Litmus triage workflow" >&2
      kubectl get workflows -n "$WORKFLOW_NAMESPACE" -l app.kubernetes.io/name=kagent-triage-litmus || true
      return 1
    fi
    sleep 3
  done

  echo "==> Waiting for workflow/$workflow"
  while true; do
    phase="$(kubectl get workflow "$workflow" -n "$WORKFLOW_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
    if [[ "$phase" == "Succeeded" ]]; then
      kubectl get workflow "$workflow" -n "$WORKFLOW_NAMESPACE"
      return 0
    fi
    if [[ "$phase" == "Failed" || "$phase" == "Error" ]]; then
      kubectl get workflow "$workflow" -n "$WORKFLOW_NAMESPACE" -o wide || true
      kubectl logs -n "$WORKFLOW_NAMESPACE" -l workflows.argoproj.io/workflow="$workflow" --all-containers --tail=200 || true
      return 1
    fi
    if (( "$(date +%s)" - start > timeout )); then
      echo "timed out waiting for workflow/$workflow to finish" >&2
      kubectl get workflow "$workflow" -n "$WORKFLOW_NAMESPACE" -o wide || true
      return 1
    fi
    sleep 5
  done
}

cleanup() {
  if [[ -n "$DEMO_AVOID_NODE" && "$avoid_node_was_unschedulable" == "false" ]]; then
    kubectl uncordon "$DEMO_AVOID_NODE" >/dev/null 2>&1 || true
  fi
}

require kubectl
require helm
require curl

if [[ -n "$KUBECTL_CONTEXT" ]]; then
  kubectl config use-context "$KUBECTL_CONTEXT" >/dev/null
else
  KUBECTL_CONTEXT="$(kubectl config current-context 2>/dev/null || true)"
fi

if [[ -z "$KUBECTL_CONTEXT" ]]; then
  echo "no kubectl context selected; set KUBECTL_CONTEXT or configure a current context" >&2
  exit 1
fi

trap cleanup EXIT

echo "==> Installing or verifying LitmusChaos"
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm/ >/dev/null 2>&1 || true
helm repo update litmuschaos >/dev/null
kubectl create namespace "$LITMUS_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
reset_mongodb="$RESET_LITMUS_MONGODB"
if [[ "$reset_mongodb" == "auto" ]]; then
  reset_mongodb="false"
  current_replicas="$(kubectl get statefulset chaos-mongodb -n "$LITMUS_NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || true)"
  if [[ "$current_replicas" != "" && "$current_replicas" != "1" ]] ||
    kubectl get statefulset chaos-mongodb-arbiter -n "$LITMUS_NAMESPACE" >/dev/null 2>&1 ||
    kubectl get deployment chaos-mongodb -n "$LITMUS_NAMESPACE" >/dev/null 2>&1; then
    reset_mongodb="true"
  fi
fi
if [[ "$reset_mongodb" == "true" ]]; then
  kubectl delete deployment/chaos-mongodb statefulset/chaos-mongodb statefulset/chaos-mongodb-arbiter \
    -n "$LITMUS_NAMESPACE" --ignore-not-found --wait=false >/dev/null
  kubectl delete pod -n "$LITMUS_NAMESPACE" \
    -l app.kubernetes.io/name=mongodb,app.kubernetes.io/instance=chaos \
    --ignore-not-found --wait=true --timeout=120s >/dev/null || true
  kubectl delete pvc -n "$LITMUS_NAMESPACE" \
    -l app.kubernetes.io/name=mongodb,app.kubernetes.io/instance=chaos \
    --ignore-not-found --wait=false >/dev/null
fi
if kubectl get secret chaos-mongodb -n "$LITMUS_NAMESPACE" >/dev/null 2>&1 &&
  [[ "$(kubectl get secret chaos-mongodb -n "$LITMUS_NAMESPACE" -o jsonpath='{.data.mongodb-replica-set-key}' 2>/dev/null || true)" != "bGl0bXVzcmVwbGljYXNldGtleQ==" ]]; then
  kubectl patch secret chaos-mongodb -n "$LITMUS_NAMESPACE" \
    --type=merge \
    -p '{"data":{"mongodb-replica-set-key":"bGl0bXVzcmVwbGljYXNldGtleQ=="}}' >/dev/null
  kubectl delete pod -n "$LITMUS_NAMESPACE" \
    -l app.kubernetes.io/name=mongodb,app.kubernetes.io/instance=chaos \
    --ignore-not-found --wait=false >/dev/null
fi
helm upgrade --install chaos litmuschaos/litmus \
  --namespace "$LITMUS_NAMESPACE" \
  --create-namespace \
  --version 3.28.0 \
  --set 'portal.frontend.tolerations[0].key=node-role.kubernetes.io/control-plane' \
  --set 'portal.frontend.tolerations[0].operator=Exists' \
  --set 'portal.frontend.tolerations[0].effect=NoSchedule' \
  --set 'portal.server.tolerations[0].key=node-role.kubernetes.io/control-plane' \
  --set 'portal.server.tolerations[0].operator=Exists' \
  --set 'portal.server.tolerations[0].effect=NoSchedule' \
  --set mongodb.architecture=replicaset \
  --set mongodb.replicaCount=1 \
  --set mongodb.arbiter.enabled=false
helm upgrade --install litmus-core litmuschaos/litmus-core \
  --namespace "$LITMUS_NAMESPACE" \
  --version 3.28.1 \
  --set policies.monitoring.disabled=true \
  --set resources.requests.cpu=200m \
  --set resources.requests.memory=256Mi \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=512Mi \
  --set 'tolerations[0].key=node-role.kubernetes.io/control-plane' \
  --set 'tolerations[0].operator=Exists' \
  --set 'tolerations[0].effect=NoSchedule'
if helm status litmus-kubernetes-chaos -n "$TARGET_NAMESPACE" >/dev/null 2>&1; then
  echo "litmus-kubernetes-chaos release already present"
else
  helm install litmus-kubernetes-chaos litmuschaos/kubernetes-chaos \
    --namespace "$TARGET_NAMESPACE" \
    --create-namespace \
    --version 3.28.1 \
    --set environment.runtime=containerd \
    --set environment.socketPath=/run/containerd/containerd.sock
fi

echo "==> Waiting for ChaosCenter and Litmus operator pods"
kubectl rollout status deployment/chaos-litmus-auth-server -n "$LITMUS_NAMESPACE" --timeout=300s
kubectl rollout status deployment/chaos-litmus-frontend -n "$LITMUS_NAMESPACE" --timeout=300s
kubectl rollout status deployment/chaos-litmus-server -n "$LITMUS_NAMESPACE" --timeout=300s
kubectl rollout status deployment/litmus -n "$LITMUS_NAMESPACE" --timeout=300s
if kubectl get deployment/chaos-mongodb -n "$LITMUS_NAMESPACE" >/dev/null 2>&1; then
  kubectl rollout status deployment/chaos-mongodb -n "$LITMUS_NAMESPACE" --timeout=300s
else
  kubectl rollout status statefulset/chaos-mongodb -n "$LITMUS_NAMESPACE" --timeout=300s
fi
if kubectl get statefulset/chaos-mongodb-arbiter -n "$LITMUS_NAMESPACE" >/dev/null 2>&1; then
  kubectl rollout status statefulset/chaos-mongodb-arbiter -n "$LITMUS_NAMESPACE" --timeout=300s
fi
kubectl get pods -n "$LITMUS_NAMESPACE"

echo "==> Applying target, RBAC, Argo Events, and kagent manifests"
kubectl apply -f "$ROOT/manifests/chaos-target.yaml"
kubectl apply -f "$ROOT/manifests/litmus-rbac.yaml"
kubectl apply -f "$ROOT/manifests/argo-events-litmus-rbac.yaml"
kubectl apply -f "$ROOT/manifests/modelconfig-qwen.yaml"
kubectl apply -f "$ROOT/manifests/agent-chaos-triage.yaml"
kubectl apply -f "$ROOT/manifests/eventsource-litmus.yaml"
kubectl apply --server-side --force-conflicts -f "$ROOT/manifests/sensor-litmus-triage.yaml"

echo "==> Waiting for kagent chaos triage agent"
kubectl rollout status deployment/chaos-triage-agent -n "$KAGENT_NAMESPACE" --timeout=300s

echo "==> Waiting for EventSource and Sensor deployments"
kubectl wait --for=condition=Deployed eventsource/litmus-chaos-events -n "$ARGO_EVENTS_NAMESPACE" --timeout=120s
kubectl wait --for=condition=Deployed sensor/kagent-triage-litmus -n "$ARGO_EVENTS_NAMESPACE" --timeout=120s

if [[ -n "$DEMO_AVOID_NODE" ]] && kubectl get node "$DEMO_AVOID_NODE" >/dev/null 2>&1; then
  avoid_node_was_unschedulable="$(kubectl get node "$DEMO_AVOID_NODE" -o jsonpath='{.spec.unschedulable}' 2>/dev/null || true)"
  if [[ "$avoid_node_was_unschedulable" != "true" ]]; then
    avoid_node_was_unschedulable="false"
    kubectl cordon "$DEMO_AVOID_NODE" >/dev/null
  fi
fi

echo "==> Starting ChaosCenter port-forward for UI evidence on http://localhost:9091"
if ! pgrep -f "kubectl --context ${KUBECTL_CONTEXT} port-forward -n ${LITMUS_NAMESPACE} svc/chaos-litmus-frontend-service 9091:9091" >/dev/null 2>&1; then
  kubectl --context "$KUBECTL_CONTEXT" port-forward -n "$LITMUS_NAMESPACE" svc/chaos-litmus-frontend-service 9091:9091 >/tmp/litmus-chaoscenter-port-forward.log 2>&1 &
  echo $! >/tmp/litmus-chaoscenter-port-forward.pid
  sleep 3
fi
curl --retry 10 --retry-all-errors --retry-delay 2 -fsSI http://localhost:9091 >/tmp/litmus-chaoscenter-http-headers.txt

echo "==> Triggering pod-delete ChaosEngine"
previous_workflow="$(latest_workflow_name || true)"
delete_engine litmus-pod-delete
kubectl delete chaosresult litmus-pod-delete-pod-delete -n "$TARGET_NAMESPACE" --ignore-not-found --wait=false
kubectl apply -f "$ROOT/experiments/pod-delete.yaml"
wait_for_result litmus-pod-delete-pod-delete 300
kubectl rollout status deployment/chaos-target -n "$TARGET_NAMESPACE" --timeout=120s
wait_for_new_workflow_success "$previous_workflow" 360
sleep 10

echo "==> Triggering pod-cpu-hog ChaosEngine"
previous_workflow="$(latest_workflow_name || true)"
delete_engine litmus-pod-cpu-hog
kubectl delete chaosresult litmus-pod-cpu-hog-pod-cpu-hog -n "$TARGET_NAMESPACE" --ignore-not-found --wait=false
kubectl apply -f "$ROOT/experiments/pod-cpu-hog.yaml"
wait_for_result litmus-pod-cpu-hog-pod-cpu-hog 300
wait_for_new_workflow_success "$previous_workflow" 360

echo "==> Current ChaosResults"
kubectl get chaosresult -n "$TARGET_NAMESPACE" -o wide

echo "==> Argo Events log excerpts"
kubectl logs -n "$ARGO_EVENTS_NAMESPACE" -l eventsource-name=litmus-chaos-events --tail=80 || true
kubectl logs -n "$ARGO_EVENTS_NAMESPACE" -l sensor-name=kagent-triage-litmus --tail=120 || true

echo "==> kagent chaos triage agent log excerpt"
kubectl logs -n "$KAGENT_NAMESPACE" -l app.kubernetes.io/name=chaos-triage-agent --tail=120 || true

echo "==> Recent Litmus triage workflows"
kubectl get workflows -n "$WORKFLOW_NAMESPACE" -l app.kubernetes.io/name=kagent-triage-litmus || true

echo "==> Demo complete"
echo "ChaosCenter: http://localhost:9091"
echo "Port-forward logs: /tmp/litmus-chaoscenter-port-forward.log"
