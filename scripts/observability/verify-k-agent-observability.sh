#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT=""
SYNTHETIC_ALERT=0

usage() {
  cat <<'USAGE'
Usage: scripts/observability/verify-k-agent-observability.sh [--context KUBE_CONTEXT] [--synthetic-alert]

Checks the K-Agent + Agent Gateway observability artifact set. With a
context, it also runs live Kubernetes Prometheus/Loki/Argo checks. The
synthetic alert mode creates and deletes a temporary PrometheusRule that must
route through Alertmanager -> Argo Events -> k-agent-alert-triage.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context)
      CONTEXT="${2:?missing context}"
      shift 2
      ;;
    --synthetic-alert)
      SYNTHETIC_ALERT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "${CONTEXT}" ]]; then
        CONTEXT="$1"
        shift
      else
        echo "unknown argument: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need kubectl
need jq

DASHBOARDS=(
  "${ROOT_DIR}/observability/grafana/dashboards/k-agent-agentgateway-public-ready.json"
  "${ROOT_DIR}/observability/grafana/dashboards/k-agent-metrics.json"
  "${ROOT_DIR}/observability/prometheus-alertmanager/enhanced/08-grafana-dashboard.json"
)

YAML_FILES=(
  "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
  "${ROOT_DIR}/k8s/observability/k-agent-alerts.yaml"
  "${ROOT_DIR}/k8s/observability/k-agent-agentgateway-scrape.yaml"
  "${ROOT_DIR}/k8s/observability/k-agent-alertmanager-eventsource.yaml"
  "${ROOT_DIR}/k8s/observability/k-agent-alertmanager-triage-route.yaml"
  "${ROOT_DIR}/k8s/observability/k-agent-alert-triage-sensor.yaml"
  "${ROOT_DIR}/observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml"
)

echo "==> Validate dashboard JSON"
for file in "${DASHBOARDS[@]}"; do
  jq empty "${file}"
done

echo "==> Client-side Kubernetes dry run"
for file in "${YAML_FILES[@]}"; do
  kubectl apply --dry-run=client -f "${file}" >/dev/null
done

echo "==> Static contract checks"
grep -q 'agentgateway_gen_ai_client_token_usage_sum' "${ROOT_DIR}/k8s/observability/k-agent-alerts.yaml"
grep -q 'kagent_path: webhook' "${ROOT_DIR}/k8s/observability/k-agent-alerts.yaml"
grep -q 'name: path-b-alertmanager-webhook' "${ROOT_DIR}/k8s/observability/k-agent-alertmanager-eventsource.yaml"
grep -q 'path-b-alertmanager-webhook-eventsource-svc.argo-events.svc' "${ROOT_DIR}/k8s/observability/k-agent-alertmanager-triage-route.yaml"
grep -q 'sre-triage-agent' "${ROOT_DIR}/k8s/observability/k-agent-alert-triage-sensor.yaml"
grep -q 'agentgateway-system' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
grep -q 'kgateway-system' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
grep -q 'PROMETHEUS_REMOTE_WRITE_URL' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
grep -q 'LOKI_PUSH_URL' "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml"
grep -q 'shipto.lgtm: "true"' "${ROOT_DIR}/observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml"
grep -q 'lgtm.engine: loki' "${ROOT_DIR}/observability/managed-lgtm-integration/alerting/03-lokirules-k-agent-agentgateway.yaml"
grep -q 'match_expression' "${ROOT_DIR}/observability/managed-lgtm-integration/alloy-snippets/04-rule-sync.alloy"

for file in \
  "${ROOT_DIR}/observability/grafana/dashboards/k-agent-agentgateway-public-ready.json" \
  "${ROOT_DIR}/observability/grafana/dashboards/k-agent-metrics.json"; do
  jq -e '.templating.list[] | select(.name == "datasource_prom" and .type == "datasource")' "${file}" >/dev/null
  jq -e '.templating.list[] | select(.name == "datasource_loki" and .type == "datasource")' "${file}" >/dev/null
  if jq -e '.. | objects | select(.datasource?.uid == "kagent-mimir" or .datasource?.uid == "kagent-loki")' "${file}" >/dev/null; then
    echo "hardcoded dashboard datasource UID remains in ${file}" >&2
    exit 1
  fi
done

if [[ -z "${CONTEXT}" ]]; then
  echo "OK"
  exit 0
fi

need curl

echo "==> Server-side Kubernetes dry run for context ${CONTEXT}"
for file in \
  "${ROOT_DIR}/k8s/observability/k-agent-alloy.yaml" \
  "${ROOT_DIR}/k8s/observability/k-agent-alerts.yaml" \
  "${ROOT_DIR}/k8s/observability/k-agent-agentgateway-scrape.yaml" \
  "${ROOT_DIR}/k8s/observability/k-agent-alertmanager-eventsource.yaml" \
  "${ROOT_DIR}/k8s/observability/k-agent-alertmanager-triage-route.yaml" \
  "${ROOT_DIR}/k8s/observability/k-agent-alert-triage-sensor.yaml"; do
  kubectl --context "${CONTEXT}" apply --dry-run=server -f "${file}" >/dev/null
done

pf_pids=()
cleanup() {
  for pid in "${pf_pids[@]:-}"; do
    kill "${pid}" >/dev/null 2>&1 || true
    wait "${pid}" 2>/dev/null || true
  done
  if [[ "${SYNTHETIC_ALERT}" == "1" ]]; then
    kubectl --context "${CONTEXT}" -n monitoring delete prometheusrule k-agent-observability-synthetic-test --ignore-not-found >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

start_pf() {
  local ns="$1"
  local resource="$2"
  local local_port="$3"
  local remote_port="$4"
  local log
  log="$(mktemp)"
  kubectl --context "${CONTEXT}" -n "${ns}" port-forward "${resource}" "${local_port}:${remote_port}" >"${log}" 2>&1 &
  pf_pids+=("$!")
  sleep 2
}

prom_query() {
  curl -fsS -G --data-urlencode "query=$1" http://127.0.0.1:19090/api/v1/query
}

loki_query() {
  curl -fsS -G --data-urlencode "query=$1" --data-urlencode limit=1 http://127.0.0.1:19100/loki/api/v1/query_range
}

expect_prom_nonzero() {
  local query="$1"
  local value
  value="$(prom_query "${query}" | jq -r '.data.result[0].value[1] // "0"')"
  echo "${query} => ${value}"
  awk -v v="${value}" 'BEGIN { exit !(v+0 > 0) }'
}

expect_loki_streams() {
  local query="$1"
  local count
  count="$(loki_query "${query}" | jq '.data.result | length')"
  echo "${query} => ${count} stream(s)"
  [[ "${count}" -gt 0 ]]
}

start_pf monitoring svc/kube-prom-kube-prometheus-prometheus 19090 9090
start_pf monitoring svc/loki 19100 3100

echo "==> Live Prometheus checks"
expect_prom_nonzero 'count(up{namespace=~"agentgateway-system|kgateway-system"} == 1)'
expect_prom_nonzero 'count(kube_pod_status_phase{namespace="kagent",phase="Running"} == 1)'
expect_prom_nonzero 'count(kube_pod_status_phase{namespace="chaos-demo",pod=~".*(pod-delete|pod-cpu-hog|litmus).*",phase="Succeeded"} == 1)'
prom_query 'sum by (namespace,pod,envoy_response_code_class) (rate(envoy_cluster_external_upstream_rq_xx{namespace=~"agentgateway-system|kgateway-system"}[5m]))' | jq -e '.data.result | length > 0' >/dev/null

echo "==> Live Loki checks"
expect_loki_streams '{namespace=~"kagent"}'
expect_loki_streams '{namespace=~"agentgateway-system|kgateway-system"}'
expect_loki_streams '{namespace=~"argo|argo-events|kagent-poc"} |~ "(?i)(alertmanager|k-agent-alert-triage|path-b-alert|K_AGENT_ALERT_TRIAGE|workflow|consumer)"'

if [[ "${SYNTHETIC_ALERT}" == "1" ]]; then
  echo "==> Synthetic Alertmanager -> Argo Events -> triage workflow check"
  RUN_ID="verify-$(date +%s)"
  BEFORE_WORKFLOWS="$(kubectl --context "${CONTEXT}" -n argo get wf -l app.kubernetes.io/name=k-agent-alert-triage --no-headers 2>/dev/null | wc -l | tr -d ' ')"
  kubectl --context "${CONTEXT}" -n monitoring delete prometheusrule k-agent-observability-synthetic-test --ignore-not-found >/dev/null
  sleep 20
  kubectl --context "${CONTEXT}" apply -f - >/dev/null <<YAML
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: k-agent-observability-synthetic-test
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  groups:
    - name: k-agent-observability-synthetic-test
      rules:
        - alert: KagentObservabilitySyntheticTest
          expr: vector(1)
          labels:
            severity: warning
            team: ai-platform
            route_to: triage
            kagent_path: webhook
            namespace: monitoring
            run_id: ${RUN_ID}
          annotations:
            summary: Synthetic K-Agent observability route test
            description: Temporary rule used by verify-k-agent-observability.sh.
YAML
  alert_seen=0
  for _ in $(seq 1 24); do
    if prom_query "ALERTS{alertname=\"KagentObservabilitySyntheticTest\",alertstate=\"firing\",kagent_path=\"webhook\",route_to=\"triage\",run_id=\"${RUN_ID}\"}" | jq -e '.data.result | length > 0' >/dev/null; then
      alert_seen=1
      break
    fi
    sleep 10
  done
  [[ "${alert_seen}" == "1" ]]

  for _ in $(seq 1 42); do
    wf_count="$(kubectl --context "${CONTEXT}" -n argo get wf -l app.kubernetes.io/name=k-agent-alert-triage --no-headers 2>/dev/null | wc -l | tr -d ' ')"
    latest="$(kubectl --context "${CONTEXT}" -n argo get wf -l app.kubernetes.io/name=k-agent-alert-triage --sort-by=.metadata.creationTimestamp --no-headers 2>/dev/null | tail -1 || true)"
    phase="$(awk '{print $2}' <<<"${latest}")"
    echo "latest triage workflow: ${latest:-none}"
    if [[ "${wf_count}" -gt "${BEFORE_WORKFLOWS}" && "${phase}" == "Succeeded" ]]; then
      break
    fi
    if [[ "${wf_count}" -gt "${BEFORE_WORKFLOWS}" && "${phase}" == "Failed" ]]; then
      exit 1
    fi
    sleep 10
  done

  latest="$(kubectl --context "${CONTEXT}" -n argo get wf -l app.kubernetes.io/name=k-agent-alert-triage --sort-by=.metadata.creationTimestamp --no-headers | tail -1)"
  [[ "$(awk '{print $2}' <<<"${latest}")" == "Succeeded" ]]
fi

echo "OK"
