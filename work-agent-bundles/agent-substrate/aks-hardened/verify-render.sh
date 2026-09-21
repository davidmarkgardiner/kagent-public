#!/usr/bin/env bash
# Pre-flight gate: renders both releases from the unpacked charts with the
# hardening applied and runs check-hardening.py over the result. Run it before
# every install and on every chart version bump; a workload that a new chart
# version adds without a matching patch fails here instead of at admission.
#   ./verify-render.sh <substrate-chart-dir> <kagent-chart-dir> [extra -f values...]
# Optional server-side admission check against the target cluster (needs the
# namespaces and CRDs to exist; runs Kyverno/Gatekeeper/Pod Security in dry-run):
#   VERIFY_SERVER=1 ./verify-render.sh ...
# Never apply the output of this script: `helm template` cannot see existing
# Secrets, so it renders fresh certificates every time.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
substrate_chart=${1:?substrate chart dir}; kagent_chart=${2:?kagent chart dir}; shift 2
out=$(mktemp -d); trap 'rm -rf "$out"' EXIT
if grep -q '{{' "$here/substrate-values.yaml" "$here/kagent-values.yaml" "$here/workerpool.yaml" && [[ $# -eq 0 ]]; then
  echo 'verify-render: replace the {{PLACEHOLDER}} values first (or pass them with -f); the chart puts the issuer unquoted into container args' >&2
  exit 2
fi
helm template substrate "$substrate_chart" -n ate-system -f "$here/substrate-values.yaml" "$@" \
  --post-renderer "$here/post-render.sh" > "$out/substrate.yaml"
helm template kagent "$kagent_chart" -n kagent -f "$here/kagent-values.yaml" "$@" \
  --post-renderer "$here/post-render.sh" --post-renderer-args kagent-postrender-patches.yaml > "$out/kagent.yaml"
for f in "$out/substrate.yaml" "$out/kagent.yaml" "$here/workerpool.yaml"; do cat "$f"; printf '\n---\n'; done \
  | python3 "$here/check-hardening.py"
if [[ ${VERIFY_SERVER:-0} == 1 ]]; then
  # The Substrate chart also renders two objects into kube-system, so no -n here.
  kubectl apply --dry-run=server -f "$out/substrate.yaml" -f "$here/workerpool.yaml" >/dev/null
  kubectl apply --dry-run=server -f "$out/kagent.yaml" >/dev/null
  echo 'SERVER_DRY_RUN: PASS'
fi
