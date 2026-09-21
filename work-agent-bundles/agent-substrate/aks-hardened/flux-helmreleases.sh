#!/usr/bin/env bash
# Prints Flux HelmReleases for the four releases, with the hardening patches
# inlined as postRenderers from the same patch files post-render.sh uses, so
# the two install paths cannot drift. Charts come from a Flux source that
# holds the unpacked charts (GitRepository or Bucket); values come from
# ConfigMaps created from substrate-values.yaml and kagent-values.yaml.
#   ./flux-helmreleases.sh > helmreleases.yaml
# Then replace {{CHART_SOURCE_KIND}}, {{CHART_SOURCE_NAME}} and the four
# {{*_CHART_PATH}} placeholders.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
patches(){ grep -v '^\s*#' "$here/$1" | grep -v '^\s*$' | sed 's/^/          /'; }
release(){
  local name=$1 ns=$2 path=$3 depends=$4 values=$5 patchfile=$6
  cat <<EOF
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: $name
  namespace: $ns
spec:
  interval: 30m
  releaseName: $name
  chart:
    spec:
      chart: "$path"
      sourceRef:
        kind: "{{CHART_SOURCE_KIND}}"
        name: "{{CHART_SOURCE_NAME}}"
        namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
EOF
  if [[ -n $depends ]]; then
    printf '  dependsOn:\n'
    for d in $depends; do printf '    - name: %s\n      namespace: %s\n' "${d%/*}" "${d#*/}"; done
  fi
  if [[ -n $values ]]; then
    printf '  valuesFrom:\n    - kind: ConfigMap\n      name: %s\n      valuesKey: values.yaml\n' "$values"
  fi
  if [[ -n $patchfile ]]; then
    printf '  postRenderers:\n    - kustomize:\n        patches:\n'
    patches "$patchfile"
  fi
}
release substrate-crds ate-system '{{SUBSTRATE_CRDS_CHART_PATH}}' '' '' ''
release substrate ate-system '{{SUBSTRATE_CHART_PATH}}' 'substrate-crds/ate-system' substrate-values substrate-postrender-patches.yaml
release kagent-crds kagent '{{KAGENT_CRDS_CHART_PATH}}' '' '' ''
release kagent kagent '{{KAGENT_CHART_PATH}}' 'kagent-crds/kagent substrate/ate-system' kagent-values kagent-postrender-patches.yaml
