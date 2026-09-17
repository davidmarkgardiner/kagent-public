#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
target="$root/platform/substrate/target-platform.env"
lock="$root/platform/substrate/images.lock.tsv"
manifest="$root/platform/substrate/security-review-sandboxagent.yaml"
versions="$root/platform/versions.lock"

# shellcheck source=/dev/null
source "$target"

for command in awk rg yq; do
  command -v "$command" >/dev/null || { echo "missing required command: $command" >&2; exit 2; }
done

rows=$(awk -F '\t' 'NR > 1 && NF {count++} END {print count + 0}' "$lock")
[[ $rows -eq $IMAGE_LOCK_ROWS ]] || { echo "expected $IMAGE_LOCK_ROWS image locks, found $rows" >&2; exit 1; }
awk -F '\t' 'NR == 1 {next} NF != 4 || $4 !~ /^sha256:[0-9a-f]{64}$/ {bad=1} END {exit bad}' "$lock" \
  || { echo 'image lock contains an invalid row or digest' >&2; exit 1; }

locked() { awk -F '\t' -v component="$1" '$1 == component {print $3}' "$versions"; }
[[ $(locked kagent-chart) == "$KAGENT_CHART_OCI_DIGEST" ]]
[[ $(locked kagent-crds-chart) == "$KAGENT_CRDS_CHART_OCI_DIGEST" ]]
[[ $(locked substrate-chart) == "$SUBSTRATE_CHART_OCI_DIGEST" ]]
[[ $(locked substrate-crds-chart) == "$SUBSTRATE_CRDS_CHART_OCI_DIGEST" ]]
[[ $(locked kagent-golang-adk) == "$KAGENT_RUNTIME_DIGEST" ]]
[[ $(locked substrate-worker) == "$SUBSTRATE_WORKER_DIGEST" ]]
[[ $(locked substrate-pause) == "$PAUSE_IMAGE_DIGEST" ]]

yq eval '.' "$manifest" >/dev/null
yq eval '.' "$root/platform/substrate/kagent-values.work.example.yaml" >/dev/null
yq eval '.' "$root/platform/substrate/substrate-values.work.example.yaml" >/dev/null
if rg -n '^[[:space:]]+tools:' "$manifest" >/dev/null; then
  echo 'read-only Substrate specialist unexpectedly declares tools' >&2
  exit 1
fi

if [[ -n ${KAGENT_CONTEXT:-} ]]; then
  kubectl --context "$KAGENT_CONTEXT" apply --dry-run=server -f "$manifest" >/dev/null
  printf 'server_dry_run_context=%s\n' "$KAGENT_CONTEXT"
else
  echo 'server_dry_run_context=not-requested'
fi
printf 'target=%s\nlocked_images=%s\nspecialist_tools=none\nverification=passed\n' "$PROFILE_NAME" "$rows"
