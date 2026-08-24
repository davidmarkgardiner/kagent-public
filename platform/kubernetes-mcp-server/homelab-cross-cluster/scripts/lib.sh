#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
POC_NAMESPACE="kubernetes-mcp-poc"
POC_LABEL_KEY="app.kubernetes.io/part-of"
POC_LABEL_VALUE="homelab-cross-cluster-poc"
POC_LABEL_SELECTOR="${POC_LABEL_KEY}=${POC_LABEL_VALUE}"
HOST_ALIAS="red-homelab"
TARGET_ALIAS="proxmox-homelab"
READER_NAME="kubernetes-mcp-reader"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"
}

require_runtime_dir() {
  [[ -n "${RUNTIME_DIR:-}" && -d "${RUNTIME_DIR}" ]] || die "RUNTIME_DIR must name an existing private directory"
  [[ "$(basename "${RUNTIME_DIR}")" == homelab-mcp-poc.* ]] || die "RUNTIME_DIR has an unexpected name"
}

require_live_inputs() {
  [[ "${HOST_CONTEXT:-}" == "kind-homelab" ]] || die "HOST_CONTEXT must be the explicitly authorized host context"
  [[ "${TARGET_CONTEXT:-}" == "proxmox-k8s" ]] || die "TARGET_CONTEXT must be the explicitly authorized target context"
  [[ "${HOST_CONTEXT}" != "${TARGET_CONTEXT}" ]] || die "host and target contexts must be distinct"
}

resource_name_or_empty() {
  local context="$1"
  shift
  kubectl --context "${context}" get "$@" --ignore-not-found -o name 2>/dev/null
}

require_absent() {
  local context="$1"
  local kind="$2"
  local name="$3"
  local namespace="${4:-}"
  local found
  if [[ -n "${namespace}" ]]; then
    found="$(resource_name_or_empty "${context}" -n "${namespace}" "${kind}" "${name}")" || die "could not verify POC resource absence"
  else
    found="$(resource_name_or_empty "${context}" "${kind}" "${name}")" || die "could not verify POC resource absence"
  fi
  [[ -z "${found}" ]] || die "a POC resource already exists; refusing to adopt it"
}

apply_silently() {
  kubectl "$@" >/dev/null 2>&1 || die "a bounded Kubernetes apply step failed"
}
