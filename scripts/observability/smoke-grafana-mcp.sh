#!/usr/bin/env bash
set -euo pipefail

CONTEXT=""
NAMESPACE="kagent"
SERVICE="kagent-grafana-mcp"
LOCAL_PORT="18000"
PROM_DATASOURCE_UID="prometheus"
PROM_QUERY="count(up)"
LOKI_DATASOURCE_UID=""
LOKI_QUERY='{namespace="kagent"}'

usage() {
  cat <<'USAGE'
Usage: scripts/observability/smoke-grafana-mcp.sh --context KUBE_CONTEXT [options]

Options:
  --namespace NAMESPACE          Namespace with the Grafana MCP service. Default: kagent
  --service SERVICE              Grafana MCP service name. Default: kagent-grafana-mcp
  --local-port PORT              Local port for port-forward. Default: 18000
  --prom-datasource-uid UID      Prometheus datasource UID. Default: prometheus
  --prom-query QUERY             PromQL smoke query. Default: count(up)
  --loki-datasource-uid UID      Also run a Loki LogQL smoke query with this datasource UID
  --loki-query QUERY             LogQL smoke query. Default: {namespace="kagent"}

This script tests the Grafana MCP server through its streamable HTTP endpoint:
initialize, tools/list, list_datasources, query_prometheus, and optionally
query_loki_logs. It does not read or print Grafana tokens.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context)
      CONTEXT="${2:?missing context}"
      shift 2
      ;;
    --namespace)
      NAMESPACE="${2:?missing namespace}"
      shift 2
      ;;
    --service)
      SERVICE="${2:?missing service}"
      shift 2
      ;;
    --local-port)
      LOCAL_PORT="${2:?missing local port}"
      shift 2
      ;;
    --prom-datasource-uid)
      PROM_DATASOURCE_UID="${2:?missing datasource UID}"
      shift 2
      ;;
    --prom-query)
      PROM_QUERY="${2:?missing PromQL query}"
      shift 2
      ;;
    --loki-datasource-uid)
      LOKI_DATASOURCE_UID="${2:?missing datasource UID}"
      shift 2
      ;;
    --loki-query)
      LOKI_QUERY="${2:?missing LogQL query}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${CONTEXT}" ]]; then
  echo "missing required --context" >&2
  usage >&2
  exit 1
fi

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need curl
need jq
need kubectl

pf_log="$(mktemp)"
cleanup() {
  if [[ -n "${pf_pid:-}" ]]; then
    kill "${pf_pid}" >/dev/null 2>&1 || true
    wait "${pf_pid}" 2>/dev/null || true
  fi
  rm -f "${pf_log}"
}
trap cleanup EXIT

kubectl --context "${CONTEXT}" -n "${NAMESPACE}" port-forward "svc/${SERVICE}" "${LOCAL_PORT}:8000" >"${pf_log}" 2>&1 &
pf_pid="$!"
sleep 2

if ! kill -0 "${pf_pid}" >/dev/null 2>&1; then
  cat "${pf_log}" >&2
  exit 1
fi

mcp_post() {
  local session_id="$1"
  local payload="$2"
  if [[ -n "${session_id}" ]]; then
    curl -fsS -X POST "http://127.0.0.1:${LOCAL_PORT}/mcp" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -H "Mcp-Session-Id: ${session_id}" \
      --data-binary "${payload}"
  else
    curl -i -fsS -X POST "http://127.0.0.1:${LOCAL_PORT}/mcp" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      --data-binary "${payload}"
  fi
}

init_payload="$(jq -cn '{
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2025-06-18",
    capabilities: {},
    clientInfo: {name: "grafana-mcp-smoke", version: "0.1"}
  }
}')"

init_response="$(mcp_post "" "${init_payload}")"
session_id="$(printf '%s\n' "${init_response}" | awk -F': ' 'tolower($1)=="mcp-session-id" {gsub(/\r/,"",$2); print $2}')"
if [[ -z "${session_id}" ]]; then
  echo "MCP initialize did not return a session id" >&2
  printf '%s\n' "${init_response}" >&2
  exit 1
fi

echo "==> MCP initialized"
printf '%s\n' "${init_response}" | sed -n '/^{/,$p' | jq -r '.result.serverInfo | "\(.name) \(.version)"'

tools_payload="$(jq -cn '{jsonrpc:"2.0", id:2, method:"tools/list", params:{}}')"
tools_response="$(mcp_post "${session_id}" "${tools_payload}")"
echo "==> Required tools"
for tool in list_datasources query_prometheus; do
  printf '%s\n' "${tools_response}" | jq -e --arg tool "${tool}" '.result.tools[] | select(.name == $tool)' >/dev/null
  echo "${tool}"
done
if [[ -n "${LOKI_DATASOURCE_UID}" ]]; then
  printf '%s\n' "${tools_response}" | jq -e '.result.tools[] | select(.name == "query_loki_logs")' >/dev/null
  echo "query_loki_logs"
fi

datasources_payload="$(jq -cn '{
  jsonrpc: "2.0",
  id: 3,
  method: "tools/call",
  params: {name: "list_datasources", arguments: {}}
}')"
datasources_text="$(mcp_post "${session_id}" "${datasources_payload}" | jq -r '.result.content[0].text')"
echo "==> Grafana datasources"
printf '%s\n' "${datasources_text}" | jq -r '.datasources[] | [.name, .type, .uid] | @tsv'

prom_payload="$(jq -cn \
  --arg uid "${PROM_DATASOURCE_UID}" \
  --arg expr "${PROM_QUERY}" \
  '{
    jsonrpc: "2.0",
    id: 4,
    method: "tools/call",
    params: {
      name: "query_prometheus",
      arguments: {
        datasourceUid: $uid,
        expr: $expr,
        queryType: "instant",
        endTime: "now"
      }
    }
  }')"
prom_text="$(mcp_post "${session_id}" "${prom_payload}" | jq -r '.result.content[0].text')"
echo "==> Prometheus query"
printf '%s\n' "${prom_text}" | jq -r --arg expr "${PROM_QUERY}" '"\($expr) => " + (.data[0].value[1] // "no result")'

if [[ -n "${LOKI_DATASOURCE_UID}" ]]; then
  loki_payload="$(jq -cn \
    --arg uid "${LOKI_DATASOURCE_UID}" \
    --arg logql "${LOKI_QUERY}" \
    '{
      jsonrpc: "2.0",
      id: 5,
      method: "tools/call",
      params: {
        name: "query_loki_logs",
        arguments: {
          datasourceUid: $uid,
          logql: $logql,
          limit: 2
        }
      }
    }')"
  loki_response="$(mcp_post "${session_id}" "${loki_payload}")"
  if printf '%s\n' "${loki_response}" | jq -e '.result.isError == true' >/dev/null; then
    printf '%s\n' "${loki_response}" | jq -r '.result.content[0].text' >&2
    exit 1
  fi
  echo "==> Loki query"
  printf '%s\n' "${loki_response}" | jq -r '.result.content[0].text' | jq -r --arg logql "${LOKI_QUERY}" '
    if (.data | type) == "array" then
      "\($logql) => " + ((.metadata.linesReturned // (.data | length)) | tostring) + " line(s)"
    else
      "\($logql) => " + ((.data.result | length) | tostring) + " stream(s)"
    end'
fi
