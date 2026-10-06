#!/usr/bin/env bash
# Run only in the target environment after Flux has reconciled the bundle.
set -euo pipefail
BUNDLE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $# -ne 4 ]]; then echo 'Usage: verify-online.sh CONTEXT AGENT_NAMESPACE CONTROLLER_NAMESPACE RECEIPT_DIRECTORY' >&2; exit 2; fi
CONTEXT=$1
NS=$2
CONTROLLER_NS=$3
RECEIPTS=$4
mkdir -p "$RECEIPTS"
for AGENT in aks-incident-specialist aks-efficiency-specialist aks-platform-specialist; do
  "$BUNDLE/scripts/shared/kagent-verify-agent.sh" --agent "$AGENT" --context "$CONTEXT" --ns "$NS" --controller-ns "$CONTROLLER_NS" --json > "$RECEIPTS/$AGENT-readiness.json"
  POD=$(kubectl --context "$CONTEXT" get pods -n "$NS" -l "aks-skills-agent=$AGENT" -o json | jq -er '[.items[] | select(.metadata.deletionTimestamp == null)] | if length == 1 then .[0].metadata.name else error("expected exactly one current agent Pod") end')
  kubectl --context "$CONTEXT" get pod "$POD" -n "$NS" -o json | jq -e '[.status.initContainerStatuses[] | select(.name == "skills-init" or .name == "verify-mounted-skills") | .state.terminated.exitCode] == [0,0]' > /dev/null
  kubectl --context "$CONTEXT" logs "$POD" -n "$NS" -c verify-mounted-skills > "$RECEIPTS/$AGENT-mounted.json"
  jq -e --arg agent "$AGENT" '.verified == true and .agent == $agent' "$RECEIPTS/$AGENT-mounted.json" > /dev/null
  "$BUNDLE/scripts/shared/kagent-a2a-invoke.sh" --agent "$AGENT" --context "$CONTEXT" --ns "$NS" --controller-ns "$CONTROLLER_NS" --text 'SKILL_PREFLIGHT: invoke every mounted skill. Return each skill name and one exact sentence from its body. Do not call evidence tools or scripts.' --receipt-file "$RECEIPTS/$AGENT-a2a.json" --json > "$RECEIPTS/$AGENT-preflight.json"
done
printf '%s\n' 'Mount and A2A receipts captured. Review actual skills tool-call traces before promotion; answer text alone is insufficient.'
