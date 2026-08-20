#!/usr/bin/env sh
set -eu

root="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
repo="$(CDPATH='' cd -- "$root/../../.." && pwd)"

python3 -m unittest discover -s "$root/tests" -v
python3 "$root/lifecycle.py" --database "$(mktemp)" --validate \
  "$root/examples/canonical-finding.json"
kubectl kustomize "$root" >/dev/null
if grep -Fq '.notify // true' "$root/../workflow-template.yaml"; then
  echo "workflow must preserve an explicit notify=false lifecycle decision" >&2
  exit 1
fi
"$repo/scripts/public-safe-scan.sh" "$root"

echo "SMART_TRIAGE_FINDING_LIFECYCLE_VERIFY_OK"
