#!/usr/bin/env bash
set -euo pipefail

context=${1:-red}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
evidence_root=${TENANT_EVIDENCE_DIR:-$(mktemp -d -t kagent-tenant-preflight.XXXXXX)}
evidence_dir="$evidence_root/run-$stamp/preflight"
mkdir -p "$evidence_dir"

for command in kubectl helm jq yq openssl python3; do
  command -v "$command" >/dev/null || { echo "missing required command: $command" >&2; exit 1; }
done

kubectl --context "$context" version -o json > "$evidence_dir/kubernetes-version.json"
helm --kube-context "$context" list -A -o json > "$evidence_dir/helm-releases.json"
empty_list='{"apiVersion":"v1","kind":"List","items":[]}'
if kubectl --context "$context" api-resources --api-group=gateway.networking.k8s.io -o name | grep -qx gateways.gateway.networking.k8s.io; then
  kubectl --context "$context" get gatewayclass,gateway,httproute -A -o json > "$evidence_dir/gateway-inventory.json"
else
  printf '%s\n' "$empty_list" > "$evidence_dir/gateway-inventory.json"
fi
if kubectl --context "$context" api-resources --api-group=agentgateway.dev -o name | grep -qx agentgatewaybackends.agentgateway.dev; then
  kubectl --context "$context" get agentgatewaybackend,agentgatewaypolicy -A -o json > "$evidence_dir/agentgateway-inventory.json"
else
  printf '%s\n' "$empty_list" > "$evidence_dir/agentgateway-inventory.json"
fi
if kubectl --context "$context" api-resources --api-group=kagent.dev -o name | grep -qx agents.kagent.dev; then
  kubectl --context "$context" get agent,remotemcpserver,modelconfig -A -o json > "$evidence_dir/kagent-inventory.json"
else
  printf '%s\n' "$empty_list" > "$evidence_dir/kagent-inventory.json"
fi
if kubectl --context "$context" api-resources --api-group=kagent.dev -o name | grep -qx sandboxagents.kagent.dev; then
  kubectl --context "$context" -n kagent get sandboxagent machinist-security-review -o json > "$evidence_dir/substrate-agent.json"
  kubectl --context "$context" -n kagent get actortemplate -l kagent.dev/sandbox-agent=machinist-security-review -o json > "$evidence_dir/substrate-actor-templates.json"
  kubectl --context "$context" -n kagent get workerpool kagent-default -o json > "$evidence_dir/substrate-worker-pool.json"
  substrate_ready=$(jq -n \
    --slurpfile agent "$evidence_dir/substrate-agent.json" \
    --slurpfile templates "$evidence_dir/substrate-actor-templates.json" \
    --slurpfile pool "$evidence_dir/substrate-worker-pool.json" '
      ([$agent[0].status.conditions[]? | select((.type == "Accepted" or .type == "Ready") and .status == "True")] | length) == 2
      and ($templates[0].items | length) == 1
      and $templates[0].items[0].status.phase == "Ready"
      and ($templates[0].items[0].status.goldenSnapshot | length) > 0
      and $pool[0].status.replicas == $pool[0].spec.replicas')
else
  substrate_ready=false
fi
kubectl --context "$context" get crd agentgatewaybackends.agentgateway.dev agentgatewaypolicies.agentgateway.dev agents.kagent.dev remotemcpservers.kagent.dev modelconfigs.kagent.dev --ignore-not-found -o yaml > "$evidence_dir/crds-before.yaml"
kubectl --context "$context" get crd agentgatewaybackends.agentgateway.dev agentgatewaypolicies.agentgateway.dev agents.kagent.dev remotemcpservers.kagent.dev modelconfigs.kagent.dev --ignore-not-found -o json \
  | jq '[.items[] | {name:.metadata.name,served:[.spec.versions[] | select(.served) | .name],stored:.status.storedVersions}]' \
  > "$evidence_dir/crd-served-stored-versions.json"

gateway_has_jwt=$(kubectl --context "$context" get crd agentgatewaypolicies.agentgateway.dev --ignore-not-found -o json \
  | jq -r 'if .spec then any(.spec.versions[].schema.openAPIV3Schema; tostring | contains("jwtAuthentication")) else false end')
kagent_has_v1alpha2=$(kubectl --context "$context" get crd agents.kagent.dev --ignore-not-found -o json \
  | jq -r 'if .spec then any(.spec.versions[]; .name=="v1alpha2" and .served==true) else false end')

# Render the pinned CRD charts and preserve an exact, non-mutating cluster diff.
helm template agentgateway-crds oci://cr.agentgateway.dev/charts/agentgateway-crds --version v1.5.0 \
  > "$evidence_dir/agentgateway-crds-v1.5.0.yaml"
helm template kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds --version 0.10.1 \
  > "$evidence_dir/kagent-crds-0.10.1.yaml"
for item in agentgateway-crds-v1.5.0 kagent-crds-0.10.1; do
  diff_code=0
  kubectl --context "$context" diff --server-side -f "$evidence_dir/$item.yaml" > "$evidence_dir/$item.diff" 2>&1 || diff_code=$?
  if (( diff_code > 1 )); then
    echo "kubectl diff failed for $item with exit $diff_code" >&2
    exit "$diff_code"
  fi
done

printf 'Preflight evidence: %s\n' "$evidence_dir"
printf 'Current agentgateway chart: '
helm --kube-context "$context" -n agentgateway-system list --filter '^agentgateway$' -o json | jq -r '.[0].chart // "not installed"'
printf 'Current kagent chart: '
helm --kube-context "$context" -n kagent list --filter '^kagent$' -o json | jq -r '.[0].chart // "not installed"'
printf 'Required agentgateway JWT schema present: %s\n' "$gateway_has_jwt"
printf 'Required kagent v1alpha2 schema present: %s\n' "$kagent_has_v1alpha2"
printf 'Existing platform Substrate specialist ready: %s\n' "$substrate_ready"
[[ $substrate_ready == true ]] || { echo 'red profile requires the existing platform-owned machinist-security-review specialist' >&2; exit 2; }
printf 'Review the preserved CRD diffs before setting ALLOW_CLUSTER_SCOPED_UPGRADE=yes.\n'
