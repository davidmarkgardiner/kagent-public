#!/usr/bin/env bash
# Run on the lab host. Two real model calls; no ServiceNow mutation.
set -euo pipefail
LAB_CONTEXT="${1:?Usage: bash run.sh KUBECTL_CONTEXT}"
POC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$POC_DIR/../../../.." && pwd)"
HELPER="${A2A_HELPER:-$REPO_ROOT/scripts/kagent-a2a-invoke.sh}"
K=(kubectl --context "$LAB_CONTEXT")
for binary in kubectl python3 curl jq; do
  command -v "$binary" >/dev/null || { echo "Missing: $binary" >&2; exit 1; }
done
[[ -f "$HELPER" ]] || { echo "Set A2A_HELPER to the repository helper" >&2; exit 1; }
"${K[@]}" get modelconfigs.kagent.dev approved-model -n classic-agents >/dev/null
"${K[@]}" get service classic-controller -n classic-system >/dev/null
"${K[@]}" get service standalone-deepseek-model -n agent-flow-demo >/dev/null
"${K[@]}" get gatewayclass agentgateway >/dev/null

# Refuse to take ownership of a previous or unrelated installation.
for object in \
  'namespaces incident-ingress-poc' \
  'agents.kagent.dev incident-ingress-poc -n classic-agents' \
  'serviceaccounts incident-ingress-poc -n classic-agents' \
  'deployments incident-ingress-poc -n classic-agents' \
  'networkpolicies incident-ingress-poc-model -n agent-flow-demo' \
  'referencegrants incident-ingress-poc -n classic-system'; do
  read -r -a words <<< "$object"
  existing=$("${K[@]}" get "${words[@]}" --ignore-not-found -o name)
  [[ -z "$existing" ]] || { echo "Already exists: $existing; stop and inspect" >&2; exit 1; }
done

cleanup() {
  "${K[@]}" delete -f "$POC_DIR/resources.yaml" --ignore-not-found --wait=false
}
trap cleanup EXIT
"${K[@]}" create namespace incident-ingress-poc --save-config
"${K[@]}" apply --dry-run=server -f "$POC_DIR/resources.yaml"
"${K[@]}" apply -f "$POC_DIR/resources.yaml"
"${K[@]}" wait --for=condition=Ready agents.kagent.dev/incident-ingress-poc -n classic-agents --timeout=60s
"${K[@]}" wait --for=condition=Programmed gateway/incident-ingress-poc -n incident-ingress-poc --timeout=60s
"${K[@]}" rollout status deployment/incident-ingress-poc -n incident-ingress-poc --timeout=60s
python3 "$POC_DIR/verify.py" --context "$LAB_CONTEXT" --helper "$HELPER"
