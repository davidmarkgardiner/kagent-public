#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_live_inputs
require_runtime_dir
for command in kubectl jq; do
  require_command "${command}"
done

scoped_kubeconfig="${RUNTIME_DIR}/scoped-kubeconfig"
umask 077

host_token="$(kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" create token "${READER_NAME}" --duration=10m 2>/dev/null)" ||
  die "host TokenRequest failed"
target_token="$(kubectl --context "${TARGET_CONTEXT}" -n "${POC_NAMESPACE}" create token "${READER_NAME}" --duration=10m 2>/dev/null)" ||
  die "target TokenRequest failed"
[[ -n "${host_token}" && -n "${target_token}" ]] || die "TokenRequest returned an empty credential"

cluster_material() {
  kubectl config view --raw --flatten --minify --context "$1" -o json 2>/dev/null |
    jq -ec '
      .clusters[0].cluster |
      select((."insecure-skip-tls-verify" // false) == false) |
      select(.server | startswith("https://")) |
      select((."certificate-authority-data" // "") != "") |
      {server: .server, certificateAuthorityData: ."certificate-authority-data"}'
}

host_cluster="$(cluster_material "${HOST_CONTEXT}")" || die "host cluster TLS material is incomplete"
target_cluster="$(cluster_material "${TARGET_CONTEXT}")" || die "target cluster TLS material is incomplete"

jq -n \
  --argjson hostCluster "${host_cluster}" \
  --argjson targetCluster "${target_cluster}" \
  --arg hostToken "${host_token}" \
  --arg targetToken "${target_token}" \
  --arg hostAlias "${HOST_ALIAS}" \
  --arg targetAlias "${TARGET_ALIAS}" \
  '{
    apiVersion: "v1",
    kind: "Config",
    preferences: {},
    clusters: [
      {name: $hostAlias, cluster: {server: $hostCluster.server, "certificate-authority-data": $hostCluster.certificateAuthorityData}},
      {name: $targetAlias, cluster: {server: $targetCluster.server, "certificate-authority-data": $targetCluster.certificateAuthorityData}}
    ],
    users: [
      {name: "red-reader", user: {token: $hostToken}},
      {name: "proxmox-reader", user: {token: $targetToken}}
    ],
    contexts: [
      {name: $hostAlias, context: {cluster: $hostAlias, user: "red-reader"}},
      {name: $targetAlias, context: {cluster: $targetAlias, user: "proxmox-reader"}}
    ],
    "current-context": $hostAlias
  }' >"${scoped_kubeconfig}"
chmod 0600 "${scoped_kubeconfig}"

unset host_token target_token host_cluster target_cluster

kubectl --context "${HOST_CONTEXT}" -n "${POC_NAMESPACE}" create secret generic kubernetes-mcp-scoped-kubeconfig \
  --from-file="kubeconfig=${scoped_kubeconfig}" --dry-run=client -o yaml 2>/dev/null |
  kubectl --context "${HOST_CONTEXT}" apply -f - >/dev/null 2>&1 || die "scoped kubeconfig Secret creation failed"

info "credentials: PASS (two short-lived purpose-issued entries; values suppressed)"
