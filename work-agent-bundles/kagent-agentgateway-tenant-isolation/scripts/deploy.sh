#!/usr/bin/env bash
set -euo pipefail

context=${1:-red}
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
run_pointer="$root/.run-dir"

wait_for_current_agent_pod() {
  local ns=$1 name=$2
  for _ in {1..150}; do
    if kubectl --context "$context" -n "$ns" get pod -l "app.kubernetes.io/name=$name" -o json \
      | jq -e 'any(.items[]; .metadata.deletionTimestamp == null and any(.status.conditions[]?; .type == "Ready" and .status == "True"))' >/dev/null; then
      return 0
    fi
    sleep 2
  done
  echo "timed out waiting for current Agent Pod $ns/$name" >&2
  return 1
}

[[ -f "$root/.rendered/platform.json" ]] || "$root/scripts/render.py" --profile red
[[ -f "$run_pointer" ]] || { echo "missing runtime pointer; rerun render.py" >&2; exit 1; }
run_dir=$(cat "$run_pointer")
tokens="$run_dir/tokens.json"
[[ -f "$tokens" ]] || { echo "disposable token file no longer exists; rerun render.py" >&2; exit 1; }

kubectl --context "$context" apply -f "$root/.rendered/platform.json"

# Copy the existing red model credential without printing it. Replace this step with an approved
# ModelConfig and Secret in a workplace cluster.
model_key=$(kubectl --context "$context" -n kagent get secret agentgateway-client-key -o jsonpath='{.data.api-key}')
for ns in team-event team-chat; do
  kubectl --context "$context" -n "$ns" create secret generic tenant-model-key \
    --from-literal=api-key="$(printf '%s' "$model_key" | base64 --decode)" \
    --dry-run=client -o yaml | kubectl --context "$context" apply -f - >/dev/null
done
unset model_key

for pair in event:team-event chat:team-chat; do
  short=${pair%%:*}
  ns=${pair##*:}
  mcp_token=$(jq -r --arg key "${short}_mcp" '.[$key]' "$tokens")
  kubectl --context "$context" -n "$ns" create secret generic tenant-mcp-runtime-token \
    --from-literal=authorization="Bearer $mcp_token" \
    --dry-run=client -o yaml | kubectl --context "$context" apply -f - >/dev/null
done
event_token=$(jq -r '.event_a2a' "$tokens")
kubectl --context "$context" -n team-event create secret generic event-a2a-token \
  --from-literal=authorization="Bearer $event_token" \
  --dry-run=client -o yaml | kubectl --context "$context" apply -f - >/dev/null
unset event_token mcp_token

kubectl --context "$context" apply -f "$root/teams/event/prompt.yaml"
kubectl --context "$context" apply -f "$root/teams/event/workload.yaml"
kubectl --context "$context" apply -f "$root/teams/event/agent.yaml"
kubectl --context "$context" apply -f "$root/teams/chat/prompt.yaml"
kubectl --context "$context" apply -f "$root/teams/chat/workload.yaml"
kubectl --context "$context" apply -f "$root/teams/chat/agent.yaml"
kubectl --context "$context" apply -f "$root/teams/rogue/workload.yaml"

# Secrets are deliberately rotated by render.py. Existing Pods do not reload
# Secret-backed environment variables, so restart every token consumer before
# claiming that a repeated deploy is using the newly rendered credentials.
kubectl --context "$context" -n team-event rollout restart deployment/incident-tools >/dev/null
kubectl --context "$context" -n team-event rollout restart deployment/event-adapter >/dev/null
kubectl --context "$context" -n team-chat rollout restart deployment/release-tools >/dev/null
for item in team-event/incident-adviser team-chat/release-adviser; do
  ns=${item%%/*}
  name=${item##*/}
  kubectl --context "$context" -n "$ns" get pod -l "app.kubernetes.io/name=$name" -o name | grep -q . \
    || { echo "missing generated Pod for $ns/$name" >&2; exit 1; }
  # The kagent controller owns the Deployment template. Deleting its Pod is the
  # idempotent way to reload Secret-backed environment variables without
  # fighting controller reconciliation over a rollout annotation.
  kubectl --context "$context" -n "$ns" delete pod -l "app.kubernetes.io/name=$name" --wait=true >/dev/null
done

kubectl --context "$context" -n team-event rollout status deployment/incident-tools --timeout=180s
kubectl --context "$context" -n team-event rollout status deployment/event-adapter --timeout=180s
kubectl --context "$context" -n team-event wait --for=condition=Ready pod/event-source --timeout=180s
kubectl --context "$context" -n team-chat rollout status deployment/release-tools --timeout=180s
kubectl --context "$context" -n team-rogue wait --for=condition=Ready pod/rogue-shell --timeout=180s

for item in team-event/incident-adviser team-chat/release-adviser; do
  ns=${item%%/*}
  name=${item##*/}
  wait_for_current_agent_pod "$ns" "$name"
done

for item in team-event/incident-adviser team-chat/release-adviser; do
  ns=${item%%/*}
  name=${item##*/}
  kubectl --context "$context" -n "$ns" wait --for=jsonpath='{.status.conditions[?(@.type=="Ready")].status}'=True "agent/$name" --timeout=600s
done

printf 'Team workloads deployed. Run scripts/verify.sh %s.\n' "$context"
