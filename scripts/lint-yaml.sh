#!/usr/bin/env bash
# lint-yaml.sh — validate that every Kubernetes manifest under k8s/ is
# syntactically valid YAML. Offline syntax check only: no cluster or
# network access is used or required.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
K8S_DIR="${ROOT}/k8s"

if [[ ! -d "${K8S_DIR}" ]]; then
  printf 'lint-yaml.sh: no such directory: %s\n' "${K8S_DIR}" >&2
  exit 1
fi

status=0
found_any=0

while IFS= read -r -d '' file; do
  found_any=1
  rel_path="${file#"${ROOT}"/}"

  if python3 -c '
import sys
import yaml

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    list(yaml.safe_load_all(f))
' "${file}" >/dev/null 2>&1; then
    printf 'OK %s\n' "${rel_path}"
  else
    printf 'FAIL %s\n' "${rel_path}"
    status=1
  fi
done < <(find "${K8S_DIR}" -type f \( -name '*.yaml' -o -name '*.yml' \) -print0 | sort -z)

if [[ "${found_any}" -eq 0 ]]; then
  printf 'lint-yaml.sh: no *.yaml or *.yml files found under %s\n' "${K8S_DIR}" >&2
fi

exit "${status}"
