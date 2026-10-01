#!/usr/bin/env bash
# Fast, no-model readiness gate. Expects a working kubeconfig/context.
set -euo pipefail

CONTEXT="${KUBE_CONTEXT:?Set KUBE_CONTEXT to the target kubeconfig context}"
GATEWAY_NAMESPACE="${GATEWAY_NAMESPACE:-agentgateway-system}"
GATEWAY_DEPLOYMENTS="${GATEWAY_DEPLOYMENTS:-agentgateway agent-gw}"
MODEL_CONFIG_NAME="${MODEL_CONFIG_NAME:-sdlc-work-model}"
KAGENT_NAMESPACE="${KAGENT_NAMESPACE:-kagent}"
KAGENT_CONTROLLER_DEPLOYMENT="${KAGENT_CONTROLLER_DEPLOYMENT:-kagent-controller}"
K=(kubectl --context "$CONTEXT")
started=$(date +%s)

"${K[@]}" get nodes -l sdlc-rig.kagent.dev/worker=true -o json |
  jq -e '[.items[] | any(.status.conditions[]; .type == "Ready" and .status == "True")] | any' >/dev/null
printf 'PASS labelled node Ready\n'

[[ -n "$GATEWAY_DEPLOYMENTS" ]] || { echo 'GATEWAY_DEPLOYMENTS must name at least one deployment' >&2; exit 1; }
for deployment in $GATEWAY_DEPLOYMENTS; do
  "${K[@]}" -n "$GATEWAY_NAMESPACE" rollout status "deployment/$deployment" --timeout=10s >/dev/null
done
"${K[@]}" -n "$KAGENT_NAMESPACE" rollout status "deployment/$KAGENT_CONTROLLER_DEPLOYMENT" --timeout=10s >/dev/null
"${K[@]}" -n sdlc-rig rollout status deployment/sdlc-gitlab-mcp --timeout=10s >/dev/null
printf 'PASS gateway, controller, GitLab MCP Ready\n'

"${K[@]}" -n sdlc-rig get modelconfig "$MODEL_CONFIG_NAME" -o json |
  jq -e 'any(.status.conditions[]?; .type == "Accepted" and .status == "True")' >/dev/null
"${K[@]}" -n sdlc-rig get secret gitlab-project-token -o json |
  jq -e '.data | has("token")' >/dev/null
printf 'PASS model config accepted; project token key present\n'

"${K[@]}" -n sdlc-rig get agent sdlc-pm sdlc-worker-echo sdlc-builder sdlc-tester sdlc-reviewer -o json |
  jq -e '(.items | length) == 5 and all(.items[];
    any(.status.conditions[]?; .type == "Accepted" and .status == "True") and
    any(.status.conditions[]?; .type == "Ready" and .status == "True"))' >/dev/null
printf 'PASS PM and four workers Accepted + Ready\n'

elapsed=$(( $(date +%s) - started ))
printf 'PASS preflight (%ss); no model or GitLab request sent\n' "$elapsed"
