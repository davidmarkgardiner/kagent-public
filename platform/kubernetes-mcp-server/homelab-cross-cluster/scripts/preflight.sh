#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_live_inputs
require_runtime_dir
for command in kubectl jq python3 sha256sum sort awk grep gitleaks; do
  require_command "${command}"
done

mkdir -p "${RUNTIME_DIR}/state"
chmod 0700 "${RUNTIME_DIR}/state"

for context in "${HOST_CONTEXT}" "${TARGET_CONTEXT}"; do
  kubectl config get-contexts -o name 2>/dev/null | grep -Fx -- "${context}" >/dev/null || die "an authorized input context is unavailable"
  kubectl --context "${context}" get --raw /readyz >/dev/null 2>&1 || die "an authorized cluster is not ready"
  kubectl --context "${context}" get --raw /api/v1 2>/dev/null |
    jq -e 'any(.resources[]; .name == "serviceaccounts/token" and any(.verbs[]; . == "create"))' >/dev/null ||
    die "TokenRequest discovery is unavailable"
  [[ "$(kubectl --context "${context}" auth can-i create serviceaccounts/token --namespace "${POC_NAMESPACE}" 2>/dev/null)" == "yes" ]] ||
    die "the operator cannot create the bounded TokenRequest"
done

host_identity="$(kubectl --context "${HOST_CONTEXT}" get namespace kube-system -o jsonpath='{.metadata.uid}' 2>/dev/null)" ||
  die "could not read the host cluster identity"
target_identity="$(kubectl --context "${TARGET_CONTEXT}" get namespace kube-system -o jsonpath='{.metadata.uid}' 2>/dev/null)" ||
  die "could not read the target cluster identity"
[[ -n "${host_identity}" && -n "${target_identity}" && "${host_identity}" != "${target_identity}" ]] ||
  die "host and target cluster identities are not distinct"
unset host_identity target_identity

node_count() {
  kubectl --context "$1" get nodes -o json 2>/dev/null | jq -er '.items | length'
}

node_fingerprint() {
  kubectl --context "$1" get nodes -o json 2>/dev/null |
    jq -er '.items[].metadata.uid' |
    LC_ALL=C sort |
    sha256sum |
    awk '{print $1}'
}

host_count="$(node_count "${HOST_CONTEXT}")" || die "could not establish the host node count"
target_count="$(node_count "${TARGET_CONTEXT}")" || die "could not establish the target node count"
[[ "${host_count}" == "1" ]] || die "the host cluster does not have the required one-node shape"
[[ "${target_count}" == "3" ]] || die "the target cluster does not have the required three-node shape"

node_fingerprint "${HOST_CONTEXT}" >"${RUNTIME_DIR}/state/host-node-fingerprint"
node_fingerprint "${TARGET_CONTEXT}" >"${RUNTIME_DIR}/state/target-node-fingerprint"

original_uid="$(kubectl --context "${HOST_CONTEXT}" -n default get deployment kubectl-mcp -o jsonpath='{.metadata.uid}' 2>/dev/null)" ||
  die "default/kubectl-mcp is unavailable"
[[ -n "${original_uid}" ]] || die "default/kubectl-mcp has no UID"
printf '%s\n' "${original_uid}" >"${RUNTIME_DIR}/state/original-kubectl-mcp-uid"
unset original_uid

for context in "${HOST_CONTEXT}" "${TARGET_CONTEXT}"; do
  require_absent "${context}" namespace "${POC_NAMESPACE}"
  require_absent "${context}" clusterrole kubernetes-mcp-poc-reader
  require_absent "${context}" clusterrolebinding kubernetes-mcp-poc-reader
done

target_url="$(kubectl config view --raw --flatten --minify --context "${TARGET_CONTEXT}" -o json 2>/dev/null |
  jq -er '.clusters[0].cluster.server')" || die "could not resolve the target API endpoint"
python3 - "${target_url}" "${RUNTIME_DIR}/state/target-host" "${RUNTIME_DIR}/state/target-port" <<'PY'
import pathlib
import sys
import urllib.parse

parsed = urllib.parse.urlparse(sys.argv[1])
if parsed.scheme != "https" or not parsed.hostname:
    raise SystemExit("target endpoint must be an HTTPS URL")
pathlib.Path(sys.argv[2]).write_text(parsed.hostname + "\n", encoding="utf-8")
pathlib.Path(sys.argv[3]).write_text(str(parsed.port or 443) + "\n", encoding="utf-8")
PY
unset target_url
chmod 0600 "${RUNTIME_DIR}/state/"*

info "preflight: PASS (aliases=${HOST_ALIAS},${TARGET_ALIAS}; nodes=1,3)"
