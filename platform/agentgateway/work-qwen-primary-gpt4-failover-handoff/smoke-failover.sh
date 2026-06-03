#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="normal"
CONTEXT="${KUBE_CONTEXT:-}"
NAMESPACE="${AGENTGATEWAY_NAMESPACE:-agentgateway-system}"
SERVICE="${AGENTGATEWAY_SERVICE:-ai-gateway}"
SERVICE_PORT="${AGENTGATEWAY_SERVICE_PORT:-80}"
LOCAL_PORT="${LOCAL_PORT:-18080}"
BACKEND="${FAILOVER_BACKEND:-work-llm-failover-backend}"
MODEL="${MODEL:-qwen-smoke}"
PROMPT="${PROMPT:-reply with exactly: ok}"

usage() {
  cat <<'USAGE'
Usage:
  ./smoke-failover.sh --mode normal
  ./smoke-failover.sh --mode bad-host
  ./smoke-failover.sh --mode mock-429

Environment:
  KUBE_CONTEXT              optional kubectl context
  AGENTGATEWAY_NAMESPACE    default agentgateway-system
  AGENTGATEWAY_SERVICE      default ai-gateway
  AGENTGATEWAY_SERVICE_PORT default 80
  LOCAL_PORT                default 18080
  FAILOVER_BACKEND          default work-llm-failover-backend
  MODEL                     default qwen-smoke
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

kc() {
  if [[ -n "${CONTEXT}" ]]; then
    kubectl --context "${CONTEXT}" "$@"
  else
    kubectl "$@"
  fi
}

ORIGINAL_HOST=""
ORIGINAL_PORT=""
ORIGINAL_PROVIDER=""
cleanup() {
  if [[ -n "${PF_PID:-}" ]]; then
    kill "${PF_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${ORIGINAL_PROVIDER}" ]]; then
    kc patch agentgatewaybackend "${BACKEND}" -n "${NAMESPACE}" --type=json \
      -p="[{\"op\":\"replace\",\"path\":\"/spec/ai/groups/0/providers/0\",\"value\":${ORIGINAL_PROVIDER}}]" >/dev/null
    echo "restored primary provider to ${ORIGINAL_HOST}:${ORIGINAL_PORT}"
  fi
  if [[ "${MODE}" == "mock-429" ]]; then
    kc delete -f "${DIR}/60-mock-429-primary.yaml" --ignore-not-found >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ "${MODE}" == "bad-host" || "${MODE}" == "mock-429" ]]; then
  command -v jq >/dev/null 2>&1 || {
    echo "jq is required for provider patch/restore safety" >&2
    exit 2
  }
  ORIGINAL_PROVIDER="$(kc get agentgatewaybackend "${BACKEND}" -n "${NAMESPACE}" -o json | jq -c '.spec.ai.groups[0].providers[0]')"
  ORIGINAL_HOST="$(kc get agentgatewaybackend "${BACKEND}" -n "${NAMESPACE}" -o jsonpath='{.spec.ai.groups[0].providers[0].host}')"
  ORIGINAL_PORT="$(kc get agentgatewaybackend "${BACKEND}" -n "${NAMESPACE}" -o jsonpath='{.spec.ai.groups[0].providers[0].port}')"
fi

if [[ "${MODE}" == "bad-host" ]]; then
  PATCHED_PROVIDER="$(printf '%s' "${ORIGINAL_PROVIDER}" | jq -c '.host = "qwen-primary.invalid.local" | .port = 443')"
  kc patch agentgatewaybackend "${BACKEND}" -n "${NAMESPACE}" --type=json \
    -p="[{\"op\":\"replace\",\"path\":\"/spec/ai/groups/0/providers/0\",\"value\":${PATCHED_PROVIDER}}]"
  echo "patched primary provider to an invalid host"
elif [[ "${MODE}" == "mock-429" ]]; then
  kc apply -f "${DIR}/60-mock-429-primary.yaml"
  kc rollout status deploy/mock-llm-429 -n "${NAMESPACE}" --timeout=90s
  PATCHED_PROVIDER="$(
    printf '%s' "${ORIGINAL_PROVIDER}" |
      jq -c '.host = "mock-llm-429.agentgateway-system.svc.cluster.local" | .port = 8080 | del(.policies.tls)'
  )"
  kc patch agentgatewaybackend "${BACKEND}" -n "${NAMESPACE}" --type=json \
    -p="[{\"op\":\"replace\",\"path\":\"/spec/ai/groups/0/providers/0\",\"value\":${PATCHED_PROVIDER}}]"
  echo "patched primary provider to plaintext mock 429 service"
elif [[ "${MODE}" != "normal" ]]; then
  echo "unsupported mode: ${MODE}" >&2
  exit 2
fi

kc port-forward -n "${NAMESPACE}" "svc/${SERVICE}" "${LOCAL_PORT}:${SERVICE_PORT}" >/tmp/work-llm-failover-portforward.log 2>&1 &
PF_PID=$!
sleep 2

BODY="$(mktemp)"
STATUS="$(
  curl -sS -o "${BODY}" -w "%{http_code}" \
    -X POST "http://127.0.0.1:${LOCAL_PORT}/llm/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"${PROMPT}\"}],\"max_tokens\":20}"
)"

echo "status=${STATUS}"
cat "${BODY}"
echo

if [[ "${STATUS}" != "200" ]]; then
  echo "failover smoke failed: expected HTTP 200" >&2
  exit 1
fi

echo "failover smoke passed for mode=${MODE}"
