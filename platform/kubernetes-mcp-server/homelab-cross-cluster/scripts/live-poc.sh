#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_live_inputs
for command in kubectl jq python3 mktemp rm rg; do
  require_command "${command}"
done

RUNTIME_DIR="$(mktemp -d "${TMPDIR:-/tmp}/homelab-mcp-poc.XXXXXX")"
export RUNTIME_DIR
chmod 0700 "${RUNTIME_DIR}"
mkdir -p "${RUNTIME_DIR}/evidence"
chmod 0700 "${RUNTIME_DIR}/evidence"
teardown_complete=0

finish() {
  local status=$?
  trap - EXIT INT TERM
  if [[ "${teardown_complete}" -ne 1 ]]; then
    "${SCRIPT_DIR}/teardown.sh" >/dev/null 2>&1 || true
  fi
  if [[ -d "${RUNTIME_DIR}" && "$(basename "${RUNTIME_DIR}")" == homelab-mcp-poc.* ]]; then
    rm -rf -- "${RUNTIME_DIR}"
  fi
  exit "${status}"
}
trap finish EXIT INT TERM

"${SCRIPT_DIR}/preflight.sh"

for context in "${HOST_CONTEXT}" "${TARGET_CONTEXT}"; do
  apply_silently --context "${context}" apply -f "${BUNDLE_DIR}/manifests/namespace.yaml"
  apply_silently --context "${context}" apply -f "${BUNDLE_DIR}/manifests/reader-rbac.yaml"
done

# Apply ingress isolation before either the client or server starts. KindNet is
# known not to enforce NetworkPolicy; the bounded receipt records that fact.
apply_silently --context "${HOST_CONTEXT}" apply -f "${BUNDLE_DIR}/manifests/isolation.yaml"

kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" create configmap kubernetes-mcp-smoke-client \
  --from-file="mcp-client.py=${SCRIPT_DIR}/mcp-client.py" --dry-run=client -o yaml 2>/dev/null |
  kubectl --context "${HOST_CONTEXT}" apply -f - >/dev/null 2>&1 || die "smoke-client ConfigMap creation failed"
apply_silently --context "${HOST_CONTEXT}" apply -f "${BUNDLE_DIR}/manifests/smoke-client.yaml"
kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" wait --for=condition=Ready pod/kubernetes-mcp-smoke-client --timeout=120s >/dev/null 2>&1 ||
  die "the labelled smoke client did not become ready"

target_host="$(<"${RUNTIME_DIR}/state/target-host")"
target_port="$(<"${RUNTIME_DIR}/state/target-port")"
kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" exec kubernetes-mcp-smoke-client -- \
  python -c 'import socket,sys; connection=socket.create_connection((sys.argv[1],int(sys.argv[2])),5); connection.close()' \
  "${target_host}" "${target_port}" >/dev/null 2>&1 || die "pod-to-target API reachability failed"
unset target_host target_port
info "reachability: PASS (host pod to target API; endpoint suppressed)"

"${SCRIPT_DIR}/credentials.sh"
"${SCRIPT_DIR}/verify-rbac.sh"

kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" create configmap kubernetes-mcp-server-config \
  --from-file="server.toml=${BUNDLE_DIR}/config/server.toml" --dry-run=client -o yaml 2>/dev/null |
  kubectl --context "${HOST_CONTEXT}" apply -f - >/dev/null 2>&1 || die "server ConfigMap creation failed"
apply_silently --context "${HOST_CONTEXT}" apply -f "${BUNDLE_DIR}/manifests/server.yaml"
kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" rollout status deployment/kubernetes-mcp-server --timeout=180s >/dev/null 2>&1 ||
  die "the MCP server did not become ready"

red_fingerprint="$(<"${RUNTIME_DIR}/state/host-node-fingerprint")"
proxmox_fingerprint="$(<"${RUNTIME_DIR}/state/target-node-fingerprint")"
if ! kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" exec kubernetes-mcp-smoke-client -- \
  env RED_EXPECTED_SHA256="${red_fingerprint}" PROXMOX_EXPECTED_SHA256="${proxmox_fingerprint}" \
  python /opt/poc/mcp-client.py --endpoint "http://kubernetes-mcp-server.${POC_NAMESPACE}.svc:8080/mcp" \
  >"${RUNTIME_DIR}/evidence/client-summary.json" 2>"${RUNTIME_DIR}/client-stderr"; then
  die "deterministic MCP routing verification failed"
fi
unset red_fingerprint proxmox_fingerprint
jq -e '.status == "PASS" and .crossoverCount == 0 and (.requests | length) >= 20' \
  "${RUNTIME_DIR}/evidence/client-summary.json" >/dev/null || die "bounded MCP evidence is incomplete"

rm -f -- "${RUNTIME_DIR}/scoped-kubeconfig"
[[ ! -e "${RUNTIME_DIR}/scoped-kubeconfig" ]] || die "temporary scoped kubeconfig removal failed"

"${SCRIPT_DIR}/teardown.sh"
teardown_complete=1

jq -n \
  --slurpfile client "${RUNTIME_DIR}/evidence/client-summary.json" \
  --slurpfile rbac "${RUNTIME_DIR}/evidence/rbac-summary.json" \
  '{
    schema: "homelab-cross-cluster-proof/v1",
    status: (if $client[0].status == "PASS" and $rbac[0].status == "PASS" then "PASS" else "FAIL" end),
    contexts: $client[0].contexts,
    alternatingRequests: ($client[0].requests | length),
    crossoverCount: $client[0].crossoverCount,
    toolSurface: "allowlist-only",
    rbac: "positive-and-negative-checks-passed",
    endpoint: "ClusterIP-only",
    teardownVerified: true,
    defaultKubectlMcpUidUnchanged: true,
    networkPolicyLimitation: "KindNet manifest present; enforcement not claimed"
  }' >"${RUNTIME_DIR}/evidence/runtime-summary.json"

if rg -q '(https?://|BEGIN [A-Z ]*PRIVATE KEY|BEGIN CERTIFICATE|certificate-authority-data|client-certificate-data|client-key-data|kind-homelab|proxmox-k8s|rawPrompt|kubeconfig:)' "${RUNTIME_DIR}/evidence"; then
  die "bounded evidence redaction scan failed"
fi
python3 "${SCRIPT_DIR}/scan-evidence.py" "${RUNTIME_DIR}/evidence" >/dev/null ||
  die "bounded evidence schema scan failed"

jq -c . "${RUNTIME_DIR}/evidence/runtime-summary.json"
