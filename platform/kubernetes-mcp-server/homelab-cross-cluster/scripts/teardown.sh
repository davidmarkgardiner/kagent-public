#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_live_inputs
require_runtime_dir
require_command kubectl

cleanup_failed=0

delete_owned() {
  local context="$1"
  local kind="$2"
  local name="$3"
  local namespace="${4:-}"
  local found label
  if [[ -n "${namespace}" ]]; then
    found="$(kubectl --context "${context}" -n "${namespace}" get "${kind}" "${name}" --ignore-not-found -o name 2>/dev/null)" || {
      cleanup_failed=1
      return
    }
  else
    found="$(kubectl --context "${context}" get "${kind}" "${name}" --ignore-not-found -o name 2>/dev/null)" || {
      cleanup_failed=1
      return
    }
  fi
  [[ -n "${found}" ]] || return 0

  if [[ -n "${namespace}" ]]; then
    label="$(kubectl --context "${context}" -n "${namespace}" get "${kind}" "${name}" -o "jsonpath={.metadata.labels.${POC_LABEL_KEY//./\\.}}" 2>/dev/null)" || {
      cleanup_failed=1
      return
    }
    if [[ "${label}" == "${POC_LABEL_VALUE}" ]]; then
      kubectl --context "${context}" -n "${namespace}" delete "${kind}" "${name}" --wait=true --timeout=120s >/dev/null 2>&1 || cleanup_failed=1
    else
      cleanup_failed=1
    fi
  else
    label="$(kubectl --context "${context}" get "${kind}" "${name}" -o "jsonpath={.metadata.labels.${POC_LABEL_KEY//./\\.}}" 2>/dev/null)" || {
      cleanup_failed=1
      return
    }
    if [[ "${label}" == "${POC_LABEL_VALUE}" ]]; then
      kubectl --context "${context}" delete "${kind}" "${name}" --wait=true --timeout=120s >/dev/null 2>&1 || cleanup_failed=1
    else
      cleanup_failed=1
    fi
  fi
}

for context in "${HOST_CONTEXT}" "${TARGET_CONTEXT}"; do
  delete_owned "${context}" clusterrolebinding "${POC_RBAC_NAME}"
  delete_owned "${context}" clusterrole "${POC_RBAC_NAME}"
  delete_owned "${context}" namespace "${POC_NAMESPACE}"
done

for context in "${HOST_CONTEXT}" "${TARGET_CONTEXT}"; do
  for resource in "namespace/${POC_NAMESPACE}" "clusterrole/${POC_RBAC_NAME}" "clusterrolebinding/${POC_RBAC_NAME}"; do
    found="$(kubectl --context "${context}" get "${resource}" --ignore-not-found -o name 2>/dev/null)" || cleanup_failed=1
    [[ -z "${found:-}" ]] || cleanup_failed=1
  done
done

uid_file="${RUNTIME_DIR}/state/original-kubectl-mcp-uid"
if [[ -s "${uid_file}" ]]; then
  original_uid="$(<"${uid_file}")"
  current_uid="$(kubectl --context "${HOST_CONTEXT}" -n default get deployment kubectl-mcp -o jsonpath='{.metadata.uid}' 2>/dev/null)" || cleanup_failed=1
  [[ -n "${original_uid}" && "${current_uid:-}" == "${original_uid}" ]] || cleanup_failed=1
else
  cleanup_failed=1
fi

[[ "${cleanup_failed}" -eq 0 ]] || die "teardown or preserved-workload verification failed"
info "teardown: PASS (POC resources absent; default/kubectl-mcp UID unchanged)"
