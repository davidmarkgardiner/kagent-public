#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT="${1:-}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need kubectl
need jq

echo "==> Validate dashboard JSON"
jq empty "${ROOT_DIR}/observability/grafana/dashboards/k-agent-metrics.json"

echo "==> Client-side Kubernetes dry run"
kubectl apply --dry-run=client -f "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml" >/dev/null
kubectl apply --dry-run=client -f "${ROOT_DIR}/k8s/observability/k-agent-alerts.yaml" >/dev/null

echo "==> Static contract checks"
grep -q 'agentgateway_gen_ai_client_token_usage_sum' "${ROOT_DIR}/k8s/observability/k-agent-alerts.yaml"
grep -Eq 'namespace=\\?"kagent\\?"' "${ROOT_DIR}/observability/grafana/dashboards/k-agent-metrics.json"
grep -Eq 'namespace=\\?"kgateway-system\\?"' "${ROOT_DIR}/observability/grafana/dashboards/k-agent-metrics.json"
grep -q 'PROMETHEUS_REMOTE_WRITE_URL' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
grep -q 'LOKI_PUSH_URL' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"

if [[ -n "${CONTEXT}" ]]; then
  echo "==> Live read-only checks for context ${CONTEXT}"
  kubectl --context "${CONTEXT}" -n kagent get deploy kagent-controller >/dev/null
  kubectl --context "${CONTEXT}" -n monitoring get deploy alloy >/dev/null 2>&1 || \
    kubectl --context "${CONTEXT}" -n monitoring get deploy k-agent-alloy >/dev/null

  echo "==> kagent pods"
  kubectl --context "${CONTEXT}" -n kagent get pods

  echo "==> gateway metrics sample"
  if kubectl --context "${CONTEXT}" -n kgateway-system get deploy ai-gateway >/dev/null 2>&1; then
    kubectl --context "${CONTEXT}" -n kgateway-system exec deploy/ai-gateway -- \
      wget -qO- http://127.0.0.1:9091/metrics 2>/dev/null | \
      grep -E 'envoy_cluster_external_upstream_rq|agentgateway_gen_ai_client_token_usage' | head -20 || true
  fi

  echo "==> Alloy recent delivery errors"
  kubectl --context "${CONTEXT}" -n monitoring logs deploy/alloy --tail=80 2>/dev/null | \
    grep -Ei 'remote_write|loki.write|error|failed|status 405|connection refused' || true
fi

echo "OK"
