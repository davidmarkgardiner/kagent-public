#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_runtime_dir
require_command kubectl
require_command python3

scoped_kubeconfig="${RUNTIME_DIR}/scoped-kubeconfig"
evidence_file="${RUNTIME_DIR}/evidence/rbac-summary.json"
checks_file="${RUNTIME_DIR}/rbac-checks.tsv"
[[ -s "${scoped_kubeconfig}" ]] || die "scoped kubeconfig is unavailable for RBAC verification"
: >"${checks_file}"
chmod 0600 "${checks_file}"
failures=0

check_permission() {
  local alias="$1"
  local expectation="$2"
  local verb="$3"
  local resource="$4"
  local actual
  actual="$(kubectl --kubeconfig "${scoped_kubeconfig}" --context "${alias}" auth can-i "${verb}" "${resource}" --all-namespaces 2>/dev/null)" ||
    actual="error"
  if [[ "${actual}" == "${expectation}" ]]; then
    printf '%s\t%s\tPASS\n' "${alias}" "${verb}_${resource//\//_}_${expectation}" >>"${checks_file}"
  else
    printf '%s\t%s\tFAIL\n' "${alias}" "${verb}_${resource//\//_}_${expectation}" >>"${checks_file}"
    failures=$((failures + 1))
  fi
}

for alias in "${HOST_ALIAS}" "${TARGET_ALIAS}"; do
  for verb in get list watch; do
    for resource in namespaces nodes pods pods/status events deployments.apps replicasets.apps statefulsets.apps daemonsets.apps jobs.batch cronjobs.batch; do
      check_permission "${alias}" yes "${verb}" "${resource}"
    done
  done
  check_permission "${alias}" yes get pods/log

  for resource in secrets serviceaccounts roles.rbac.authorization.k8s.io rolebindings.rbac.authorization.k8s.io clusterroles.rbac.authorization.k8s.io clusterrolebindings.rbac.authorization.k8s.io; do
    check_permission "${alias}" no get "${resource}"
  done
  check_permission "${alias}" no create serviceaccounts/token
  check_permission "${alias}" no create pods/exec
  for verb in create update patch delete; do
    for resource in pods deployments.apps jobs.batch; do
      check_permission "${alias}" no "${verb}" "${resource}"
    done
  done
done

python3 - "${checks_file}" "${evidence_file}" <<'PY'
import json
import pathlib
import sys

checks = []
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    context, check, status = line.split("\t")
    checks.append({"context": context, "check": check, "status": status})
summary = {
    "schema": "homelab-cross-cluster-rbac/v1",
    "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
    "checks": checks,
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

[[ "${failures}" -eq 0 ]] || die "RBAC allow/deny verification failed"
info "rbac: PASS ($(wc -l <"${checks_file}") independent authorization checks)"
