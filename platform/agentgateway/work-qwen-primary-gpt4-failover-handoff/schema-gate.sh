#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT="${KUBE_CONTEXT:-}"

kc() {
  if [[ -n "${CONTEXT}" ]]; then
    kubectl --context "${CONTEXT}" "$@"
  else
    kubectl "$@"
  fi
}

echo "== Context =="
kc config current-context

echo
echo "== Required CRDs =="
API_RESOURCES="$(kc api-resources -o name)"
for resource in \
  agentgatewaybackends.agentgateway.dev \
  agentgatewaypolicies.agentgateway.dev \
  httproutes.gateway.networking.k8s.io \
  modelconfigs.kagent.dev \
  prometheusrules.monitoring.coreos.com; do
  if grep -qx "${resource}" <<<"${API_RESOURCES}"; then
    echo "ok: ${resource}"
  else
    echo "missing: ${resource}"
  fi
done

echo
echo "== agentgateway auth fields =="
kc explain agentgatewaybackend.spec.ai.groups.providers.policies.auth --recursive 2>/dev/null || true

echo
echo "== route retry fields =="
kc explain agentgatewaypolicy.spec.traffic.retry --recursive 2>/dev/null || true

echo
echo "== backend health field check =="
if kc explain agentgatewaypolicy.spec.backend.health >/tmp/agentgateway-backend-health.explain 2>&1; then
  echo "backend health policy appears supported"
  cat /tmp/agentgateway-backend-health.explain
else
  echo "backend health policy is not supported by this installed CRD"
fi

echo
echo "== Server dry-run =="
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

render_for_dry_run() {
  local src="$1"
  local dst="${TMP_DIR}/$(basename "${src}")"
  sed \
    -e 's/{{TOKEN_REFRESHER_IMAGE}}/mcr.microsoft.com\/azure-cli:2.58.0/g' \
    -e 's/{{QWEN_TENANT_ID}}/00000000-0000-0000-0000-000000000000/g' \
    -e 's/{{QWEN_CLIENT_ID}}/11111111-1111-1111-1111-111111111111/g' \
    -e 's/{{QWEN_CLIENT_SECRET}}/placeholder-client-secret/g' \
    -e 's/{{QWEN_AAD_SCOPE}}/api:\/\/qwen-placeholder\/.default/g' \
    -e 's/{{GPT4_UAMI_CLIENT_ID}}/22222222-2222-2222-2222-222222222222/g' \
    -e 's/{{GPT4_AAD_SCOPE}}/https:\/\/cognitiveservices.azure.com\/.default/g' \
    -e 's/{{QWEN_MODEL}}/qwen-placeholder/g' \
    -e 's/{{QWEN_OPENAI_HOST}}/qwen-openai.placeholder.invalid/g' \
    -e 's/{{GPT4_OPENAI_RESOURCE}}/gpt4-resource-placeholder/g' \
    -e 's/{{GPT4_DEPLOYMENT_NAME}}/gpt-4-placeholder/g' \
    -e 's/{{GPT4_AZURE_OPENAI_API_VERSION}}/2024-10-21/g' \
    -e 's/{{AGENTGATEWAY_GATEWAY_NAME}}/ai-gateway/g' \
    -e 's/{{AGENTGATEWAY_HOSTNAME}}/agentgateway.placeholder.invalid/g' \
    "${src}" > "${dst}"
  printf '%s\n' "${dst}"
}

for file in \
  10-token-refreshers.yaml \
  20-agentgateway-failover-route.yaml \
  30-kagent-modelconfig.yaml \
  40-observability-alerts.yaml \
  60-mock-429-primary.yaml; do
  echo "-- ${file}"
  rendered="$(render_for_dry_run "${DIR}/${file}")"
  kc apply --dry-run=server -f "${rendered}"
done

echo
echo "NOTE: 50-loki-log-rules.yaml contains LogQL and is intended for managed Loki rule sync."
echo "Do not server-dry-run it against vanilla Prometheus."
