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
grep -Fq 'resources: ["pods/log"]' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
grep -q 'PROMETHEUS_REMOTE_WRITE_URL' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
grep -q 'LOKI_PUSH_URL' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"

PROM_UID="$(jq -r '.panels[] | select(.datasource.type == "prometheus") | .datasource.uid' "${ROOT_DIR}/observability/grafana/dashboards/k-agent-metrics.json" | sort -u)"
LOKI_UID="$(jq -r '.panels[] | select(.datasource.type == "loki") | .datasource.uid' "${ROOT_DIR}/observability/grafana/dashboards/k-agent-metrics.json" | sort -u)"
grep -q "uid: ${PROM_UID}" "${ROOT_DIR}/observability/grafana/provisioning/datasources/k-agent-lgtm.yaml"
grep -q "uid: ${LOKI_UID}" "${ROOT_DIR}/observability/grafana/provisioning/datasources/k-agent-lgtm.yaml"

if [[ -n "${CONTEXT}" ]]; then
  need curl

  echo "==> Live read-only checks for context ${CONTEXT}"
  if [[ -z "$(kubectl --context "${CONTEXT}" -n kagent get deploy \
    -l app.kubernetes.io/name=kagent,app.kubernetes.io/component=controller -o name)" ]]; then
    echo "kagent controller deployment not found by labels" >&2
    exit 1
  fi
  kubectl --context "${CONTEXT}" -n monitoring get deploy alloy >/dev/null 2>&1 || \
    kubectl --context "${CONTEXT}" -n monitoring get deploy k-agent-alloy >/dev/null

  echo "==> kagent pods"
  kubectl --context "${CONTEXT}" -n kagent get pods

  echo "==> gateway metrics sample"
  if kubectl --context "${CONTEXT}" -n kgateway-system get deploy ai-gateway >/dev/null 2>&1; then
    PF_LOG="$(mktemp)"
    kubectl --context "${CONTEXT}" -n kgateway-system port-forward deploy/ai-gateway 19091:9091 >"${PF_LOG}" 2>&1 &
    PF_PID=$!
    trap 'kill "${PF_PID}" >/dev/null 2>&1 || true; wait "${PF_PID}" 2>/dev/null || true; rm -f "${PF_LOG}"' EXIT
    sleep 2
    curl -fsS http://127.0.0.1:19091/metrics 2>/dev/null | \
      grep -E 'envoy_cluster_external_upstream_rq|agentgateway_gen_ai_client_token_usage' | head -20 || true
    kill "${PF_PID}" >/dev/null 2>&1 || true
    wait "${PF_PID}" 2>/dev/null || true
    rm -f "${PF_LOG}"
    trap - EXIT
  fi

  echo "==> Alloy recent delivery errors"
  kubectl --context "${CONTEXT}" -n monitoring logs deploy/alloy --tail=80 2>/dev/null | \
    grep -Ei 'remote_write|loki.write|error|failed|status 405|connection refused' || true
fi

echo "OK"
