#!/usr/bin/env bash
set -euo pipefail

context=${1:-red}
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
chart_dir=$(mktemp -d -t kagent-tenant-charts.XXXXXX)
trap 'rm -rf "$chart_dir"' EXIT
agw_crds_chart=''
kagent_crds_chart=''
agw_chart=''
kagent_chart=''

pull_locked_chart() {
  local component=$1 reference=$2 version=$3 output_var=$4 expected actual output archive
  expected=$(awk -F '\t' -v component="$component" '$1 == component {print $3}' "$root/platform/versions.lock")
  [[ $expected == sha256:* ]] || { echo "missing digest lock for $component" >&2; exit 2; }
  output=$(helm pull "$reference" --version "$version" --destination "$chart_dir" 2>&1)
  actual=$(printf '%s\n' "$output" | awk '/^Digest: sha256:/ {print $2}' | tail -1)
  [[ $actual == "$expected" ]] || { echo "digest mismatch for $component: expected $expected, got ${actual:-missing}" >&2; exit 2; }
  archive="$chart_dir/$(basename "${reference#oci://}")-$version.tgz"
  [[ -n $archive ]] || { echo "downloaded chart archive missing for $component" >&2; exit 2; }
  printf -v "$output_var" '%s' "$archive"
}

if [[ ${ALLOW_CLUSTER_SCOPED_UPGRADE:-} != yes ]]; then
  echo "Set ALLOW_CLUSTER_SCOPED_UPGRADE=yes after reviewing preflight evidence." >&2
  exit 2
fi

kubectl --context "$context" get crd gateways.gateway.networking.k8s.io httproutes.gateway.networking.k8s.io referencegrants.gateway.networking.k8s.io >/dev/null \
  || { echo "Gateway API CRDs are required; install the reviewed standard or experimental bundle first." >&2; exit 2; }

for namespace in agentgateway-system kagent tenant-gateway-system tenant-kagent-system team-event team-chat team-rogue; do
  kubectl --context "$context" create namespace "$namespace" --dry-run=client -o yaml | kubectl --context "$context" apply -f -
done

pull_locked_chart agentgateway-crds-chart oci://cr.agentgateway.dev/charts/agentgateway-crds v1.5.0 agw_crds_chart
pull_locked_chart kagent-crds-chart oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds 0.10.1 kagent_crds_chart
pull_locked_chart agentgateway-chart oci://cr.agentgateway.dev/charts/agentgateway v1.5.0 agw_chart
pull_locked_chart kagent-chart oci://ghcr.io/kagent-dev/kagent/helm/kagent 0.10.1 kagent_chart

# Upgrade the existing CRD releases in place. Helm will not let a second release own the same CRDs.
helm upgrade --install agentgateway-crds "$agw_crds_chart" \
  --kube-context "$context" --namespace agentgateway-system --wait --timeout 5m
helm upgrade --install kagent-crds "$kagent_crds_chart" \
  --kube-context "$context" --namespace kagent --wait --timeout 5m

helm upgrade --install tenant-agentgateway "$agw_chart" \
  --kube-context "$context" --namespace tenant-gateway-system \
  --values "$root/platform/helm/agentgateway-values.yaml" --wait --timeout 10m

helm upgrade --install tenant-kagent "$kagent_chart" \
  --kube-context "$context" --namespace tenant-kagent-system \
  --values "$root/platform/helm/kagent-values.yaml" --wait --timeout 15m

kubectl --context "$context" wait --for=condition=Accepted gatewayclass/tenant-agentgateway --timeout=180s
kubectl --context "$context" -n tenant-gateway-system rollout status deployment/tenant-agentgateway --timeout=180s
kubectl --context "$context" -n tenant-kagent-system rollout status deployment/tenant-kagent-controller --timeout=300s

printf 'Parallel controllers installed. Shared ai-gateway and kagent releases were not changed.\n'
