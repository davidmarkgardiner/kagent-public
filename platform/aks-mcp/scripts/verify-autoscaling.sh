#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
component_dir="$(cd "${script_dir}/.." && pwd)"
chart_dir="${component_dir}/chart"
test_tmp="$(mktemp -d /tmp/aks-mcp-autoscaling.XXXXXX)"
trap 'rm -rf "${test_tmp}"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_kind_count() {
  local file="$1"
  local kind="$2"
  local expected="$3"
  local actual
  actual="$(awk -v wanted="${kind}" '$0 ~ /^kind: / && $2 == wanted { count++ } END { print count + 0 }' "${file}")"
  [[ "${actual}" == "${expected}" ]] || fail "${kind} count in ${file}: expected ${expected}, got ${actual}"
}

helm lint "${chart_dir}"

helm template aks-mcp "${chart_dir}" --namespace aks-mcp \
  >"${test_tmp}/default.yaml"

helm template aks-mcp "${chart_dir}" --namespace aks-mcp \
  --set autoscaling.mode=hpa \
  --set vpa.enabled=true \
  --set podDisruptionBudget.enabled=true \
  >"${test_tmp}/hpa.yaml"

helm template aks-mcp "${chart_dir}" --namespace aks-mcp \
  -f "${chart_dir}/values-autoscaling-aks.yaml" \
  >"${test_tmp}/keda.yaml"

assert_kind_count "${test_tmp}/default.yaml" HorizontalPodAutoscaler 0
assert_kind_count "${test_tmp}/default.yaml" ScaledObject 0
assert_kind_count "${test_tmp}/default.yaml" VerticalPodAutoscaler 0
assert_kind_count "${test_tmp}/default.yaml" NetworkPolicy 0

assert_kind_count "${test_tmp}/hpa.yaml" HorizontalPodAutoscaler 1
assert_kind_count "${test_tmp}/hpa.yaml" ScaledObject 0
assert_kind_count "${test_tmp}/hpa.yaml" VerticalPodAutoscaler 1

assert_kind_count "${test_tmp}/keda.yaml" HorizontalPodAutoscaler 0
assert_kind_count "${test_tmp}/keda.yaml" ScaledObject 1
assert_kind_count "${test_tmp}/keda.yaml" TriggerAuthentication 1
assert_kind_count "${test_tmp}/keda.yaml" VerticalPodAutoscaler 1
assert_kind_count "${test_tmp}/keda.yaml" PodDisruptionBudget 1
assert_kind_count "${test_tmp}/keda.yaml" NetworkPolicy 1

grep -q 'minReplicaCount: 2' "${test_tmp}/keda.yaml" || fail "KEDA minimum is not 2"
grep -q 'maxReplicaCount: 10' "${test_tmp}/keda.yaml" || fail "KEDA maximum is not 10"
grep -q 'updateMode: "Off"' "${test_tmp}/keda.yaml" || fail "VPA is not recommendation-only"
grep -q 'ignoreNullValues: "false"' "${test_tmp}/keda.yaml" || fail "null metric results do not fail closed"
grep -q 'image: "ghcr.io/azure/aks-mcp:v0.0.16"' "${test_tmp}/default.yaml" || fail "default image does not use Chart.appVersion"
grep -q 'image: "ghcr.io/azure/aks-mcp:v0.0.16"' "${test_tmp}/keda.yaml" || fail "HTTP-capable image is not pinned"
grep -q 'replicas: 1' "${test_tmp}/default.yaml" || fail "fixed replica count is missing when autoscaling is disabled"
if grep -q '^  replicas:' "${test_tmp}/hpa.yaml"; then
  fail "Deployment replicas is rendered while HPA owns scaling"
fi
if grep -q '^  replicas:' "${test_tmp}/keda.yaml"; then
  fail "Deployment replicas is rendered while KEDA owns scaling"
fi
grep -q 'kubernetes.io/metadata.name: agentgateway-system' "${test_tmp}/keda.yaml" || fail "AKS production ingress is not restricted to the gateway namespace"
grep -q 'app: agentgateway' "${test_tmp}/keda.yaml" || fail "AKS production ingress is not restricted to gateway pods"

if helm template invalid "${chart_dir}" --set autoscaling.mode=both >"${test_tmp}/invalid-mode.out" 2>&1; then
  fail "invalid autoscaling mode was accepted"
fi

if helm template invalid "${chart_dir}" --set autoscaling.mode=keda >"${test_tmp}/missing-query.out" 2>&1; then
  fail "KEDA mode without a Prometheus endpoint/query was accepted"
fi

if helm template invalid "${chart_dir}" --set autoscaling.mode=hpa --set app.transport=stdio >"${test_tmp}/stdio.out" 2>&1; then
  fail "stdio transport with horizontal autoscaling was accepted"
fi

if helm template invalid "${chart_dir}" --set autoscaling.mode=hpa --set app.transport=sse >"${test_tmp}/sse.out" 2>&1; then
  fail "SSE transport with horizontal autoscaling was accepted"
fi

if helm template invalid "${chart_dir}" --set autoscaling.mode=hpa --set oauth.enabled=true >"${test_tmp}/oauth.out" 2>&1; then
  fail "OAuth with horizontal autoscaling was accepted"
fi

if helm template invalid "${chart_dir}" \
  --set autoscaling.mode=keda \
  --set autoscaling.keda.prometheus.serverAddress=http://prometheus \
  --set autoscaling.keda.prometheus.query=up \
  --set autoscaling.keda.authentication.create=true \
  --set autoscaling.keda.authentication.kind=ClusterTriggerAuthentication \
  --set autoscaling.keda.authentication.azureWorkloadIdentity.identityId=placeholder \
  >"${test_tmp}/created-cluster-auth.out" 2>&1; then
  fail "created TriggerAuthentication accepted a cluster-scoped reference kind"
fi

if helm template invalid "${chart_dir}" --set vpa.enabled=true --set vpa.updateMode=Auto >"${test_tmp}/vpa.out" 2>&1; then
  fail "mutating VPA mode was accepted"
fi

echo "PASS: AKS-MCP default, HPA fallback, KEDA, VPA Off, and guardrail renders"
