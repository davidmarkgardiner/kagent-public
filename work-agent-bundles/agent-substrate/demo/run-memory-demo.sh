#!/usr/bin/env bash
# Agent Substrate session-continuity demo.
#
# Three requests against one SandboxAgent:
#   1. session one: remember a synthetic marker      -> MARKER STORED
#   2. session one: ask for it back                  -> the marker
#   3. session two: ask for it                       -> NO MARKER IN THIS SESSION
# After each request the actor suspends again, and the ate-api log is searched
# for the SuspendActor witness with a new snapshot. That witness, not the
# model's answer, is what proves restore-and-suspend.
#
# Read-only apart from the demo SandboxAgent it applies (and deletes again
# unless --keep). It never touches other agents.
#
# Usage:
#   ./run-memory-demo.sh --context <ctx> [options]
#
#   --context           kubectl context (required; named explicitly on purpose)
#   --namespace         agent namespace (default kagent)
#   --agent             SandboxAgent name (default demo-sandbox-agent)
#   --model-config      ModelConfig for the agent (default default-model-config)
#   --ate-namespace     namespace of ate-api (default ate-system; use kagent
#                       when Substrate is installed as a kagent subchart)
#   --endpoint          A2A base URL. Default: port-forward the controller.
#                       With agentgateway, pass the listener URL instead.
#   --token             bearer token for --endpoint, if it requires one
#   --marker            marker to store (default ORANGE-FALCON-17)
#   --receipt-dir       output directory (default ./receipts/<timestamp>)
#   --keep              leave the SandboxAgent in place afterwards
#
# Requires kubectl and jq.
set -uo pipefail

context=""; namespace="kagent"; agent="demo-sandbox-agent"
model_config="default-model-config"; ate_namespace="ate-system"
endpoint=""; token=""; marker="ORANGE-FALCON-17"; receipt_dir=""; keep=0
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

while (( $# )); do
  case $1 in
    --context) context=$2; shift 2 ;;
    --namespace) namespace=$2; shift 2 ;;
    --agent) agent=$2; shift 2 ;;
    --model-config) model_config=$2; shift 2 ;;
    --ate-namespace) ate_namespace=$2; shift 2 ;;
    --endpoint) endpoint=$2; shift 2 ;;
    --token) token=$2; shift 2 ;;
    --marker) marker=$2; shift 2 ;;
    --receipt-dir) receipt_dir=$2; shift 2 ;;
    --keep) keep=1; shift ;;
    -h|--help) sed -n '2,32p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -n $context ]] || { echo "--context is required" >&2; exit 2; }
command -v kubectl >/dev/null || { echo "kubectl is required" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 2; }

k() { kubectl --context "$context" "$@"; }
receipt_dir=${receipt_dir:-"$here/receipts/$(date -u +%Y%m%dT%H%M%SZ)"}
mkdir -p "$receipt_dir/responses" "$receipt_dir/status"
results="$receipt_dir/results.tsv"
printf 'id\tcheck\twitness\tresult\n' > "$results"
FAILURES=0
record() { # id check witness result
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$results"
  printf '%-5s %-46s %s\n' "$4" "$2" "$3"
  [[ $4 == PASS ]] || FAILURES=$((FAILURES + 1))
}

echo "==> Context and runtime"
k version -o json > "$receipt_dir/status/version.json" 2>/dev/null
k -n "$namespace" get deploy kagent-controller -o jsonpath='{.spec.template.spec.containers[0].image}' \
  > "$receipt_dir/status/controller-image.txt" 2>/dev/null
controller_replicas=$(k -n "$namespace" get deploy kagent-controller -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
[[ ${controller_replicas:-0} -ge 1 ]] || { echo "kagent-controller has no ready replica in $namespace" >&2; exit 1; }
k get workerpool -A -o json > "$receipt_dir/status/workerpools.json" 2>/dev/null
pool=$(jq -r '.items[0] | "\(.metadata.namespace)/\(.metadata.name) replicas=\(.spec.replicas)"' \
  "$receipt_dir/status/workerpools.json" 2>/dev/null)
record R00 'WorkerPool present' "${pool:-none}" "$([[ -n ${pool:-} && $pool != null* ]] && echo PASS || echo FAIL)"

echo "==> Applying the demo SandboxAgent"
sed -e "s/^  name: demo-sandbox-agent$/  name: $agent/" \
    -e "s/^  namespace: kagent$/  namespace: $namespace/" \
    -e "s/modelConfig: default-model-config/modelConfig: $model_config/" \
    "$here/sandboxagent-demo.yaml" > "$receipt_dir/status/sandboxagent-applied.yaml"
k apply -f "$receipt_dir/status/sandboxagent-applied.yaml" >/dev/null || exit 1
cleanup() {
  if [[ $keep == 0 ]]; then
    # Deleting a SandboxAgent runs the kagent.dev/sandbox-agent-substrate-cleanup
    # finalizer, which needs a running controller. Wait for it, so the object is
    # not left Terminating if the controller is scaled down afterwards.
    k -n "$namespace" delete sandboxagent "$agent" --ignore-not-found --wait=false >/dev/null 2>&1
    local gone=0 i
    for i in $(seq 1 24); do
      if [[ -z $(k -n "$namespace" get sandboxagent "$agent" --ignore-not-found --no-headers 2>/dev/null) ]]; then
        gone=1; break
      fi
      sleep 5
    done
    if [[ $gone == 0 ]]; then
      echo "warning: $namespace/$agent is still terminating. Its finalizer needs a running kagent-controller; leave the controller up until it clears." >&2
    fi
  fi
  [[ -n ${pf_pid:-} ]] && kill "$pf_pid" 2>/dev/null
  return 0
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  ready=$(k -n "$namespace" get sandboxagent "$agent" -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}{end}' 2>/dev/null)
  [[ $ready == True ]] && break
  sleep 5
done
k -n "$namespace" get sandboxagent "$agent" -o json > "$receipt_dir/status/sandboxagent.json"
record R01 'SandboxAgent Ready' "Ready=${ready:-unknown}" "$([[ ${ready:-} == True ]] && echo PASS || echo FAIL)"

k -n "$namespace" get actortemplate -o json > "$receipt_dir/status/actortemplates.json" 2>/dev/null
tmpl=$(jq -r --arg a "$agent" '[.items[] | select(.metadata.name | startswith($a + "-"))]
  | sort_by(.metadata.creationTimestamp) | last
  | "\(.metadata.name) phase=\(.status.phase) snapshot=\(if .status.goldenSnapshot then "present" else "absent" end)"' \
  "$receipt_dir/status/actortemplates.json" 2>/dev/null)
record R02 'ActorTemplate Ready with golden snapshot' "${tmpl:-none}" \
  "$([[ ${tmpl:-} == *"phase=Ready"* && ${tmpl:-} == *"snapshot=present"* ]] && echo PASS || echo FAIL)"

# A2A endpoint: default to a port-forward straight to the controller.
if [[ -z $endpoint ]]; then
  k -n "$namespace" port-forward service/kagent-controller 28083:8083 \
    > "$receipt_dir/status/port-forward.log" 2>&1 &
  pf_pid=$!
  sleep 5
  endpoint="http://127.0.0.1:28083"
fi
url="${endpoint%/}/api/a2a-sandboxes/$namespace/$agent/"

# One A2A message/send. $1 label, $2 contextId, $3 text.
ask() {
  local label=$1 ctx=$2 text=$3 started code body
  body="$receipt_dir/responses/$label.body"
  started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$started" > "$receipt_dir/status/$label.started"
  local payload
  payload=$(jq -cn --arg ctx "$ctx" --arg text "$text" --arg id "$label-message" \
    '{jsonrpc:"2.0",id:$id,method:"message/send",params:{message:{kind:"message",role:"user",messageId:$id,contextId:$ctx,parts:[{kind:"text",text:$text}]}}}')
  code=$(curl -sS --max-time 240 -o "$body" -w '%{http_code}' \
    ${token:+-H "Authorization: Bearer $token"} \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    --data "$payload" "$url" 2>>"$receipt_dir/status/curl.err")
  echo "$code"
}
answer_of() { # strips the agent's last text part out of an A2A response
  jq -r '[.result.history[]? | select(.role=="agent") | .parts[]? | select(.kind=="text") | .text] | last // ""' "$1" 2>/dev/null
}
# Was there a successful SuspendActor with a fresh snapshot since $2?
# Suspension follows the response by a few seconds, so poll rather than sleep once.
suspend_witness() { # label since
  local label=$1
  local since=$2
  local log="$receipt_dir/status/$label-lifecycle.jsonl"
  local found=false
  local attempt
  for attempt in $(seq 1 12); do
    k -n "$ate_namespace" logs "deployment/$ATE_API_DEPLOY" --since-time="$since" > "$log" 2>/dev/null
    found=$(jq -s --arg agent "$agent" 'any(.[];
        .method == "/ateapi.Control/SuspendActor"
        and .err == null
        and (.resp.actor.status == 4)
        and ((.resp.actor.actor_template_name // "") | startswith($agent + "-")))' "$log" 2>/dev/null)
    [[ $found == true ]] && break
    sleep 5
  done
  echo "${found:-false}"
}

ATE_API_DEPLOY=$(k -n "$ate_namespace" get deploy -o name 2>/dev/null | grep -m1 'ate-api-server' | sed 's#deployment.apps/##')
[[ -n $ATE_API_DEPLOY ]] || echo "warning: ate-api deployment not found in $ate_namespace; suspend witnesses will be skipped" >&2

session_one="demo-session-01"; session_two="demo-session-02"

echo "==> Session one, request one: store the marker"
code=$(ask S1R1 "$session_one" "Please remember this marker for later in this session: $marker")
ans=$(answer_of "$receipt_dir/responses/S1R1.body")
record P01 'session one stored the marker' "$code ${ans:-no-answer}" \
  "$([[ $code == 200 && $ans == *"MARKER STORED"* ]] && echo PASS || echo FAIL)"
if [[ -n $ATE_API_DEPLOY ]]; then
  w=$(suspend_witness S1R1 "$(cat "$receipt_dir/status/S1R1.started")")
  record S01 'actor suspended after request one' "SuspendActor status:4 witness=${w:-false}" \
    "$([[ ${w:-false} == true ]] && echo PASS || echo FAIL)"
fi

echo "==> Session one, request two: ask for the marker back"
code=$(ask S1R2 "$session_one" "What marker did I ask you to remember?")
ans=$(answer_of "$receipt_dir/responses/S1R2.body")
record P02 'same session returned the marker after suspension' "$code ${ans:-no-answer}" \
  "$([[ $code == 200 && $ans == *"$marker"* ]] && echo PASS || echo FAIL)"
if [[ -n $ATE_API_DEPLOY ]]; then
  w=$(suspend_witness S1R2 "$(cat "$receipt_dir/status/S1R2.started")")
  record S02 'actor suspended again after request two' "SuspendActor status:4 witness=${w:-false}" \
    "$([[ ${w:-false} == true ]] && echo PASS || echo FAIL)"
fi

echo "==> Session two: a different session must not inherit the marker"
code=$(ask S2R1 "$session_two" "What marker did I ask you to remember? If you were not given one in this session, reply exactly NO MARKER IN THIS SESSION.")
ans=$(answer_of "$receipt_dir/responses/S2R1.body")
record P03 'second session did not inherit the marker' "$code ${ans:-no-answer}" \
  "$([[ $code == 200 && $ans != *"$marker"* ]] && echo PASS || echo FAIL)"

ctx1=$(jq -r '.result.contextId // "missing"' "$receipt_dir/responses/S1R2.body" 2>/dev/null)
ctx2=$(jq -r '.result.contextId // "missing"' "$receipt_dir/responses/S2R1.body" 2>/dev/null)
record P04 'the two sessions used different context IDs' "$ctx1 vs $ctx2" \
  "$([[ $ctx1 != "$ctx2" && $ctx1 != missing ]] && echo PASS || echo FAIL)"

k -n "$namespace" get actortemplate -o json > "$receipt_dir/status/actortemplates-after.json" 2>/dev/null
echo
echo "Receipt: $receipt_dir"
column -t -s $'\t' "$results" 2>/dev/null || cat "$results"
if (( FAILURES == 0 )); then
  echo "SUBSTRATE_DEMO: PASS"
else
  echo "SUBSTRATE_DEMO: FAIL ($FAILURES check(s))" >&2
fi
echo "Fill in RECEIPT-TEMPLATE.md from these files before sharing anything."
exit $(( FAILURES == 0 ? 0 : 1 ))
