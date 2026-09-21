#!/usr/bin/env bash
# Helm 3 post-renderer: applies a kustomize patch list to the rendered chart.
#   helm upgrade --install substrate <chart> -n ate-system -f substrate-values.yaml \
#     --post-renderer ./post-render.sh
#   helm upgrade --install kagent <chart> -n kagent -f kagent-values.yaml \
#     --post-renderer ./post-render.sh --post-renderer-args kagent-postrender-patches.yaml
# The patch file defaults to substrate-postrender-patches.yaml and is resolved
# relative to this script. Needs only bash and kubectl (kustomize is built in).
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
patches="$here/${1:-substrate-postrender-patches.yaml}"
[[ -f $patches ]] || { echo "post-render: patch file not found: $patches" >&2; exit 2; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cat > "$work/rendered.yaml"
{
  echo 'resources: [rendered.yaml]'
  echo 'patches:'
  grep -v '^\s*#' "$patches"
} > "$work/kustomization.yaml"
kubectl kustomize "$work"
