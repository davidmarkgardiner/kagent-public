#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

KUBECTL_CONTEXT="${KUBECTL_CONTEXT:-kind-homelab}"
LITMUS_NAMESPACE="${LITMUS_NAMESPACE:-litmus}"
TARGET_NAMESPACE="${TARGET_NAMESPACE:-chaos-demo}"
ARGO_EVENTS_NAMESPACE="${ARGO_EVENTS_NAMESPACE:-argo-events}"
KAGENT_NAMESPACE="${KAGENT_NAMESPACE:-kagent}"

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

require kubectl
require helm
require curl

kubectl config use-context "$KUBECTL_CONTEXT" >/dev/null

echo "==> Installing or verifying LitmusChaos"
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm/ >/dev/null 2>&1 || true
helm repo update litmuschaos >/dev/null
helm upgrade --install chaos litmuschaos/litmus \
  --namespace "$LITMUS_NAMESPACE" \
  --create-namespace
helm upgrade --install litmus-core litmuschaos/litmus-core \
  --namespace "$LITMUS_NAMESPACE" \
  --set policies.monitoring.disabled=true
if helm status litmus-kubernetes-chaos -n "$TARGET_NAMESPACE" >/dev/null 2>&1; then
  echo "litmus-kubernetes-chaos release already present"
else
  helm install litmus-kubernetes-chaos litmuschaos/kubernetes-chaos \
    --namespace "$TARGET_NAMESPACE" \
    --create-namespace \
    --set environment.runtime=containerd \
    --set environment.socketPath=/run/containerd/containerd.sock
fi

echo "==> Waiting for ChaosCenter and Litmus operator pods"
kubectl wait --for=condition=Ready pod --all -n "$LITMUS_NAMESPACE" --timeout=300s
kubectl get pods -n "$LITMUS_NAMESPACE"

echo "==> Applying target, RBAC, Argo Events, and kagent manifests"
kubectl apply -f "$ROOT/manifests/chaos-target.yaml"
kubectl apply -f "$ROOT/manifests/litmus-rbac.yaml"
kubectl apply -f "$ROOT/manifests/argo-events-litmus-rbac.yaml"
kubectl apply -f "$ROOT/manifests/modelconfig-qwen.yaml"
kubectl apply -f "$ROOT/manifests/agent-chaos-triage.yaml"
kubectl apply -f "$ROOT/manifests/eventsource-litmus.yaml"
kubectl apply -f "$ROOT/manifests/sensor-litmus-triage.yaml"

echo "==> Waiting for EventSource and Sensor deployments"
kubectl wait --for=condition=Deployed eventsource/litmus-chaos-events -n "$ARGO_EVENTS_NAMESPACE" --timeout=120s
kubectl wait --for=condition=Deployed sensor/kagent-triage-litmus -n "$ARGO_EVENTS_NAMESPACE" --timeout=120s

echo "==> Starting ChaosCenter port-forward for UI evidence on http://localhost:9091"
if ! pgrep -f "kubectl port-forward -n ${LITMUS_NAMESPACE} svc/chaos-litmus-frontend-service 9091:9091" >/dev/null 2>&1; then
  kubectl port-forward -n "$LITMUS_NAMESPACE" svc/chaos-litmus-frontend-service 9091:9091 >/tmp/litmus-chaoscenter-port-forward.log 2>&1 &
  echo $! >/tmp/litmus-chaoscenter-port-forward.pid
  sleep 3
fi
curl -fsSI http://localhost:9091 >/tmp/litmus-chaoscenter-http-headers.txt || true

echo "==> Triggering pod-delete ChaosEngine"
delete_engine litmus-pod-delete
kubectl delete chaosresult litmus-pod-delete-pod-delete -n "$TARGET_NAMESPACE" --ignore-not-found --wait=false
kubectl apply -f "$ROOT/experiments/pod-delete.yaml"
wait_for_result litmus-pod-delete-pod-delete 300
kubectl rollout status deployment/chaos-target -n "$TARGET_NAMESPACE" --timeout=120s
sleep 10

echo "==> Triggering pod-cpu-hog ChaosEngine"
delete_engine litmus-pod-cpu-hog
kubectl delete chaosresult litmus-pod-cpu-hog-pod-cpu-hog -n "$TARGET_NAMESPACE" --ignore-not-found --wait=false
kubectl apply -f "$ROOT/experiments/pod-cpu-hog.yaml"
wait_for_result litmus-pod-cpu-hog-pod-cpu-hog 300

echo "==> Current ChaosResults"
kubectl get chaosresult -n "$TARGET_NAMESPACE" -o wide

echo "==> Argo Events log excerpts"
kubectl logs -n "$ARGO_EVENTS_NAMESPACE" -l eventsource-name=litmus-chaos-events --tail=80 || true
kubectl logs -n "$ARGO_EVENTS_NAMESPACE" -l sensor-name=kagent-triage-litmus --tail=120 || true

echo "==> kagent chaos triage agent log excerpt"
kubectl logs -n "$KAGENT_NAMESPACE" -l app.kubernetes.io/name=chaos-triage-agent --tail=120 || true

echo "==> Recent Litmus triage workflows"
kubectl get workflows -n "$ARGO_EVENTS_NAMESPACE" -l app.kubernetes.io/name=kagent-triage-litmus || true

echo "==> Demo complete"
echo "ChaosCenter: http://localhost:9091"
echo "Port-forward logs: /tmp/litmus-chaoscenter-port-forward.log"
