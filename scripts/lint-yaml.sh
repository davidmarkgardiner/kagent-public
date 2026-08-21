#!/usr/bin/env bash
# lint-yaml.sh — validate every Kubernetes manifest under k8s/ is syntactically
# valid YAML. Offline syntax check only; no cluster or network access.
#
# Modes:
#   (default)  one OK/FAIL line per file, then a summary line.
#   --quiet    suppress successful-file lines; print failures and the summary.
#   --json     emit exactly one JSON object on stdout with checked, failed,
#              failures (relative paths). Stderr stays empty on success.
set -euo pipefail

quiet=0
json=0

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --quiet) quiet=1; shift ;;
    --json)  json=1;  shift ;;
    *) printf 'lint-yaml.sh: unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
K8S_DIR="${ROOT}/k8s"

if [[ ! -d "${K8S_DIR}" ]]; then
  printf 'lint-yaml.sh: no such directory: %s\n' "${K8S_DIR}" >&2
  exit 1
fi

status=0
checked=0
failed=0
failures=()

while IFS= read -r -d '' file; do
  rel_path="${file#"${ROOT}"/}"
  if python3 -c '
import sys, yaml
with open(sys.argv[1], "r", encoding="utf-8") as f:
    list(yaml.safe_load_all(f))
' "${file}" >/dev/null 2>&1; then
    [[ "${quiet}" -eq 0 && "${json}" -eq 0 ]] && printf 'OK %s\n' "${rel_path}"
  else
    [[ "${json}" -eq 0 ]] && printf 'FAIL %s\n' "${rel_path}"
    failures+=("${rel_path}")
    status=1
    failed=$((failed + 1))
  fi
  checked=$((checked + 1))
done < <(python3 -c '
import os, sys
root = sys.argv[1]
paths = []
for directory, _, filenames in os.walk(root):
    paths.extend(os.path.join(directory, name) for name in filenames if name.endswith((".yaml", ".yml")))
for path in sorted(paths):
    sys.stdout.buffer.write(os.fsencode(path) + b"\0")
' "${K8S_DIR}")

if [[ "${checked}" -eq 0 ]]; then
  printf 'lint-yaml.sh: no *.yaml or *.yml files found under %s\n' "${K8S_DIR}" >&2
fi

# JSON encoding is delegated to python3 so every control character, quote,
# backslash, and Unicode codepoint in a failing filename is escaped per
# RFC 8259. Counts pass as argv integers; each failing relative path is its
# own argv element (POSIX argv is byte-safe for every byte that can legally
# appear in a filename; NUL is excluded because NUL cannot appear in a path).
# ensure_ascii=False emits raw UTF-8 for non-ASCII codepoints (still RFC 8259
# valid) to keep the output readable; the compact separators are required
# by the existing --json grep-based contract in the README.
if [[ "${json}" -eq 1 ]]; then
  json_args=("${checked}" "${failed}")
  if [[ "${#failures[@]}" -gt 0 ]]; then
    json_args+=("${failures[@]}")
  fi
  python3 -c '
import json, sys
obj = {"checked": int(sys.argv[1]), "failed": int(sys.argv[2]), "failures": sys.argv[3:]}
sys.stdout.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
' "${json_args[@]}"
  exit "${status}"
fi

if [[ "${checked}" -gt 0 ]]; then
  printf '%d file(s) checked, %d failed\n' "${checked}" "${failed}"
fi

exit "${status}"
