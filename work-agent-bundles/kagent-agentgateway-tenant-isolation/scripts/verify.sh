#!/usr/bin/env bash
set -euo pipefail

context=${1:-red}
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
run_pointer="$root/.run-dir"
[[ -f "$run_pointer" ]] || { echo "missing .run-dir; run render.py and deploy.sh first" >&2; exit 2; }
run_dir=$(cat "$run_pointer")
tokens="$run_dir/tokens.json"
[[ -f "$tokens" ]] || { echo "disposable tokens are gone; rerun render.py and deploy.sh" >&2; exit 2; }

stamp=$(date -u +%Y%m%dT%H%M%SZ)
evidence_root=${TENANT_EVIDENCE_DIR:-$(mktemp -d -t kagent-tenant-evidence.XXXXXX)}
receipt_dir="$evidence_root/run-$stamp"
mkdir -p "$receipt_dir/responses" "$receipt_dir/status"
summary="$receipt_dir/summary.tsv"
printf 'id\texpected\tobserved\tresult\n' > "$summary"
failures=0

record() {
  local id=$1 expected=$2 observed=$3 result=$4
  printf '%s\t%s\t%s\t%s\n' "$id" "$expected" "$observed" "$result" >> "$summary"
  printf '%-5s %-5s %s\n' "$id" "$result" "$observed"
  if [[ $result != PASS ]]; then failures=$((failures + 1)); fi
}

expect_code() {
  local id=$1 expected=$2 token_key=$3 port=$4 payload=$5
  local body="$receipt_dir/responses/$id.body" token='' observed
  if [[ $token_key != none ]]; then token=$(jq -r --arg key "$token_key" '.[$key]' "$tokens"); fi
  if [[ -n $token ]]; then
    observed=$(curl -sS --max-time 20 -o "$body" -w '%{http_code}' -H "Authorization: Bearer $token" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' --data "$payload" "http://127.0.0.1:$port/mcp")
  else
    observed=$(curl -sS --max-time 20 -o "$body" -w '%{http_code}' -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' --data "$payload" "http://127.0.0.1:$port/mcp")
  fi
  if [[ $observed == "$expected" ]]; then record "$id" "$expected" "$observed" PASS; else record "$id" "$expected" "$observed" FAIL; fi
}

expect_a2a_code() {
  local id=$1 expected=$2 token_key=$3 port=$4 payload=$5
  local body="$receipt_dir/responses/$id.body" token='' observed
  if [[ $token_key != none ]]; then token=$(jq -r --arg key "$token_key" '.[$key]' "$tokens"); fi
  if [[ -n $token ]]; then
    observed=$(curl -sS --max-time 20 -o "$body" -w '%{http_code}' -H "Authorization: Bearer $token" -H 'Content-Type: application/json' --data "$payload" "http://127.0.0.1:$port/")
  else
    observed=$(curl -sS --max-time 20 -o "$body" -w '%{http_code}' -H 'Content-Type: application/json' --data "$payload" "http://127.0.0.1:$port/")
  fi
  if [[ $observed == "$expected" ]]; then record "$id" "$expected" "$observed" PASS; else record "$id" "$expected" "$observed" FAIL; fi
}

counter() {
  local ns=$1 deployment=$2 metric=${3:-tenant_mcp_tool_calls_total}
  kubectl --context "$context" -n "$ns" exec "deployment/$deployment" -- wget -qO- http://127.0.0.1:8080/metrics \
    | awk -v metric="$metric" '$1 == metric {print $2}'
}

wait_counter_stable() {
  local ns=$1 deployment=$2 metric=$3 previous current stable=0
  previous=$(counter "$ns" "$deployment" "$metric")
  for _ in {1..10}; do
    sleep 1
    current=$(counter "$ns" "$deployment" "$metric")
    if [[ $current == "$previous" ]]; then
      stable=$((stable + 1))
      (( stable >= 2 )) && return 0
    else
      stable=0
      previous=$current
    fi
  done
  return 1
}

token_exp=$(jq -r '.event_a2a | split(".")[1]' "$tokens" | tr '_-' '/+' | awk '{ pad=(4-length($0)%4)%4; printf "%s",$0; for(i=0;i<pad;i++) printf "=" }' | base64 --decode 2>/dev/null | jq -r '.exp')
if (( token_exp <= $(date +%s) + 300 )); then
  echo "JWTs expire in less than five minutes; rerun render.py and deploy.sh" >&2
  exit 2
fi

kubectl --context "$context" get gateway -n tenant-gateway-system tenant-gateway -o json > "$receipt_dir/status/gateway.json"
kubectl --context "$context" get httproute -n tenant-gateway-system -o json > "$receipt_dir/status/routes.json"
kubectl --context "$context" get agentgatewaypolicy -n tenant-gateway-system -o json > "$receipt_dir/status/policies.json"
kubectl --context "$context" get agentgatewaybackend -A -o json > "$receipt_dir/status/backends.json"
kubectl --context "$context" get agent -n team-event incident-adviser -o json > "$receipt_dir/status/event-agent.json"
kubectl --context "$context" get agent -n team-chat release-adviser -o json > "$receipt_dir/status/chat-agent.json"
kubectl --context "$context" get sandboxagent -n kagent machinist-security-review -o json > "$receipt_dir/status/substrate-agent.json"
kubectl --context "$context" get actortemplate -n kagent -l kagent.dev/sandbox-agent=machinist-security-review -o json > "$receipt_dir/status/substrate-actor-templates.json"
kubectl --context "$context" get workerpool -n kagent kagent-default -o json > "$receipt_dir/status/substrate-worker-pool.json"
kubectl --context "$context" -n tenant-gateway-system get deployment tenant-agentgateway -o json \
  | jq '{images:[.spec.template.spec.containers[].image],env:[.spec.template.spec.containers[].env[] | select(.name|startswith("AGW_"))]}' > "$receipt_dir/status/agentgateway-runtime.json"
kubectl --context "$context" -n tenant-kagent-system get deployment tenant-kagent-controller -o json \
  | jq '{images:[.spec.template.spec.containers[].image],env:[.spec.template.spec.containers[].env[] | select(.name=="WATCH_NAMESPACES" or .name=="AUTH_MODE")]}' > "$receipt_dir/status/kagent-runtime.json"

route_gate=$(jq -r '
  [.items[] | select(.metadata.name == "event-a2a" or .metadata.name == "event-mcp" or .metadata.name == "chat-a2a" or .metadata.name == "chat-mcp" or .metadata.name == "substrate-a2a")] as $routes
  | ($routes | length) == 5 and all($routes[];
      ([.status.parents[]?.conditions[]? | select(.type == "Accepted" and .status == "True")] | length) > 0
      and ([.status.parents[]?.conditions[]? | select(.type == "ResolvedRefs" and .status == "True")] | length) > 0)' "$receipt_dir/status/routes.json")
if [[ $route_gate == true ]]; then record S01 'exactly five routes Accepted and ResolvedRefs' '5/5 true' PASS; else record S01 'exactly five routes Accepted and ResolvedRefs' 'missing or false condition' FAIL; fi

backend_gate=$(jq -r '
  [.items[] | select(.metadata.name == "event-mcp" or .metadata.name == "chat-mcp")] as $backends
  | ($backends | length) == 2 and all($backends[];
      ([.status.conditions[]? | select(.type == "Accepted" and .status == "True")] | length) > 0)' "$receipt_dir/status/backends.json")
if [[ $backend_gate == true ]]; then record S02 'exactly two MCP backends Accepted' '2/2 true' PASS; else record S02 'exactly two MCP backends Accepted' 'missing or false condition' FAIL; fi

policy_gate=$(jq -r '
  [.items[] | select(.metadata.name == "event-a2a-auth" or .metadata.name == "event-mcp-auth" or .metadata.name == "chat-a2a-auth" or .metadata.name == "chat-mcp-auth" or .metadata.name == "substrate-a2a-auth")] as $policies
  | ($policies | length) == 5 and all($policies[];
      ([.status.ancestors[]? | select(.controllerName == "agentgateway.dev/tenant-isolation")
        | .conditions[]? | select(.type == "Accepted" and .status == "True")] | length) > 0
      and ([.status.ancestors[]? | select(.controllerName == "agentgateway.dev/tenant-isolation")
        | .conditions[]? | select(.type == "Attached" and .status == "True")] | length) > 0)' "$receipt_dir/status/policies.json")
if [[ $policy_gate == true ]]; then record S03 'exactly five canary policies Accepted and Attached' '5/5 true' PASS; else record S03 'exactly five canary policies Accepted and Attached' 'missing or false condition' FAIL; fi

substrate_gate=$(jq -n \
  --slurpfile agent "$receipt_dir/status/substrate-agent.json" \
  --slurpfile templates "$receipt_dir/status/substrate-actor-templates.json" \
  --slurpfile pool "$receipt_dir/status/substrate-worker-pool.json" '
    ([$agent[0].status.conditions[]? | select((.type == "Accepted" or .type == "Ready") and .status == "True")] | length) == 2
    and ($templates[0].items | length) == 1
    and $templates[0].items[0].status.phase == "Ready"
    and ($templates[0].items[0].status.goldenSnapshot | length) > 0
    and $pool[0].spec.replicas == 3
    and $pool[0].status.replicas == 3')
if [[ $substrate_gate == true ]]; then record S04 'existing specialist Ready with one golden template and 3/3 workers' 'Ready template:1 workers:3/3' PASS; else record S04 'existing specialist Ready with one golden template and 3/3 workers' 'missing or false condition' FAIL; fi

kubectl --context "$context" -n tenant-gateway-system port-forward service/tenant-gateway 28081:8081 28082:8082 28083:8083 28084:8084 28085:8085 >"$receipt_dir/gateway-port-forward.log" 2>&1 &
gateway_pf=$!
# shellcheck disable=SC2329  # Invoked indirectly by the EXIT trap.
cleanup() {
  kill "$gateway_pf" 2>/dev/null || true
  wait "$gateway_pf" 2>/dev/null || true
  kubectl --context "$context" -n tenant-gateway-system delete httproute refgrant-negative --ignore-not-found >/dev/null 2>&1 || true
  kubectl --context "$context" -n team-event delete agentgatewaybackend refgrant-negative --ignore-not-found >/dev/null 2>&1 || true
  kubectl --context "$context" -n team-event delete deployment label-spoof-probe --ignore-not-found >/dev/null 2>&1 || true
}
trap cleanup EXIT
sleep 2

init_payload='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"bundle-verifier","version":"1"}}}'
wait_counter_stable team-event incident-tools tenant_mcp_requests_total \
  || { echo 'MCP request counter did not quiesce before negative tests' >&2; exit 2; }
blocked_before=$(counter team-event incident-tools tenant_mcp_requests_total)
expect_code N01 401 none 28082 "$init_payload"
expect_code N02 401 wrong_audience 28082 "$init_payload"
expect_code N03 401 expired 28082 "$init_payload"
expect_code N04 403 rogue_event_mcp 28082 "$init_payload"
expect_code N05 401 chat_mcp 28082 "$init_payload"
expect_code N06 401 event_a2a 28082 "$init_payload"
blocked_after=$(counter team-event incident-tools tenant_mcp_requests_total)
if (( blocked_after == blocked_before )); then
  record N17 'six rejected requests never reached MCP backend' "request-counter:$blocked_before->$blocked_after" PASS
else
  record N17 'six rejected requests never reached MCP backend' "request-counter:$blocked_before->$blocked_after" FAIL
fi

event_before=$(counter team-event incident-tools)
event_token=$(jq -r '.event_mcp' "$tokens")
curl -sS -D "$receipt_dir/responses/P03-event-init.headers" -o "$receipt_dir/responses/P03-event-init.body" \
  -H "Authorization: Bearer $event_token" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data "$init_payload" http://127.0.0.1:28082/mcp
session=$(awk 'BEGIN{IGNORECASE=1} /^mcp-session-id:/ {gsub("\r",""); print $2}' "$receipt_dir/responses/P03-event-init.headers")
call_payload='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"lookup_incident","arguments":{"id":"INC-1001"}}}'
call_code=$(curl -sS -o "$receipt_dir/responses/P03-event-call.body" -w '%{http_code}' \
  -H "Authorization: Bearer $event_token" -H "Mcp-Session-Id: $session" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data "$call_payload" http://127.0.0.1:28082/mcp)
event_after=$(counter team-event incident-tools)
if [[ $call_code == 200 ]] && grep -q 'INC-1001' "$receipt_dir/responses/P03-event-call.body" && (( event_after == event_before + 1 )); then
  record P03 '200 fixture and counter +1' "$call_code fixture counter:$event_before->$event_after" PASS
else
  record P03 '200 fixture and counter +1' "$call_code counter:$event_before->$event_after" FAIL
fi

forbidden_request_before=$(counter team-event incident-tools tenant_mcp_requests_total)
forbidden_before=$(counter team-event incident-tools tenant_mcp_forbidden_tool_calls_total)
forbidden_payload='{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"delete_everything","arguments":{}}}'
forbidden_code=$(curl -sS -o "$receipt_dir/responses/N07-forbidden-tool.body" -w '%{http_code}' \
  -H "Authorization: Bearer $event_token" -H "Mcp-Session-Id: $session" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data "$forbidden_payload" http://127.0.0.1:28082/mcp)
forbidden_request_after=$(counter team-event incident-tools tenant_mcp_requests_total)
forbidden_after=$(counter team-event incident-tools tenant_mcp_forbidden_tool_calls_total)
if grep -Eqi 'error|denied|forbidden|not found|unknown' "$receipt_dir/responses/N07-forbidden-tool.body" \
  && (( forbidden_request_after == forbidden_request_before )) && (( forbidden_after == forbidden_before )); then
  record N07 'known forbidden MCP tool blocked before backend' "$forbidden_code request-counter:$forbidden_request_before->$forbidden_request_after forbidden-counter:$forbidden_before->$forbidden_after" PASS
else
  record N07 'known forbidden MCP tool blocked before backend' "$forbidden_code request-counter:$forbidden_request_before->$forbidden_request_after forbidden-counter:$forbidden_before->$forbidden_after" FAIL
fi
unset event_token

event_before=$(counter team-event incident-tools)
event_response=$(kubectl --context "$context" -n team-event exec pod/event-source -- curl -sS --max-time 180 \
  -w $'\nCODE:%{http_code}' -H 'Content-Type: application/json' --data '{"id":"INC-1001"}' http://event-adapter:8080/)
event_code=${event_response##*CODE:}
event_body=${event_response%$'\nCODE:'*}
printf '%s' "$event_body" > "$receipt_dir/responses/P01-event.body"
event_after=$(counter team-event incident-tools)
if jq -e . "$receipt_dir/responses/P01-event.body" >/dev/null 2>&1; then
  event_state=$(jq -r '.result.status.state // "missing"' "$receipt_dir/responses/P01-event.body")
  event_answer=$(jq -r '[.result.history[]? | select(.role=="agent") | .parts[]? | select(.kind=="text") | .text] | last // ""' "$receipt_dir/responses/P01-event.body")
else
  event_state=non-json
  event_answer=''
fi
if [[ $event_code == 200 && $event_state == completed && $event_answer == *INC-1001* ]] && (( event_after == event_before + 1 )); then
  record P01 'event to A2A to MCP completed' "$event_code $event_state counter:$event_before->$event_after" PASS
else
  record P01 'event to A2A to MCP completed' "$event_code $event_state counter:$event_before->$event_after" FAIL
fi

chat_before=$(counter team-chat release-tools)
chat_token=$(jq -r '.chat_a2a' "$tokens")
chat_payload=$(jq -cn '{jsonrpc:"2.0",id:"verify-chat",method:"message/send",params:{message:{role:"user",messageId:"verify-chat-message",parts:[{kind:"text",text:"Look up REL-204 using your tool and give one recommendation."}]}}}')
chat_code=$(curl -sS --max-time 180 -o "$receipt_dir/responses/P02-chat.body" -w '%{http_code}' \
  -H "Authorization: Bearer $chat_token" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data "$chat_payload" http://127.0.0.1:28083/)
chat_after=$(counter team-chat release-tools)
if jq -e . "$receipt_dir/responses/P02-chat.body" >/dev/null 2>&1; then
  chat_state=$(jq -r '.result.status.state // "missing"' "$receipt_dir/responses/P02-chat.body")
  chat_answer=$(jq -r '[.result.history[]? | select(.role=="agent") | .parts[]? | select(.kind=="text") | .text] | last // ""' "$receipt_dir/responses/P02-chat.body")
else
  chat_state=non-json
  chat_answer=''
fi
if [[ $chat_code == 200 && $chat_state == completed && $chat_answer == *REL-204* ]] && (( chat_after == chat_before + 1 )); then
  record P02 'chat A2A to MCP completed' "$chat_code $chat_state counter:$chat_before->$chat_after" PASS
else
  record P02 'chat A2A to MCP completed' "$chat_code $chat_state counter:$chat_before->$chat_after" FAIL
fi
unset chat_token

substrate_payload=$(jq -cn --arg context "context-verify-substrate-$stamp" \
  '{jsonrpc:"2.0",id:"verify-substrate",method:"message/send",params:{message:{kind:"message",role:"user",messageId:"verify-substrate-message",contextId:$context,parts:[{kind:"text",text:"Review this synthetic change: add a read-only health endpoint with no credentials and require tests. Return the required security headings."}]}}}')
expect_a2a_code N20 401 none 28085 "$substrate_payload"
expect_a2a_code N21 401 chat_a2a 28085 "$substrate_payload"
expect_a2a_code N22 403 rogue_substrate_a2a 28085 "$substrate_payload"

substrate_started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
substrate_token=$(jq -r '.substrate_a2a' "$tokens")
substrate_code=$(curl -sS --max-time 240 -o "$receipt_dir/responses/P04-substrate.body" -w '%{http_code}' \
  -H "Authorization: Bearer $substrate_token" -H 'Content-Type: application/json' \
  --data "$substrate_payload" http://127.0.0.1:28085/)
unset substrate_token
if jq -e . "$receipt_dir/responses/P04-substrate.body" >/dev/null 2>&1; then
  substrate_state=$(jq -r '.result.status.state // "missing"' "$receipt_dir/responses/P04-substrate.body")
  substrate_answer=$(jq -r '[.result.history[]? | select(.role=="agent") | .parts[]? | select(.kind=="text") | .text] | last // ""' "$receipt_dir/responses/P04-substrate.body")
  substrate_context=$(jq -r '.result.contextId // "missing"' "$receipt_dir/responses/P04-substrate.body")
else
  substrate_state=non-json
  substrate_answer=''
  substrate_context=missing
fi
if [[ $substrate_code == 200 && $substrate_state == completed && $substrate_answer == *TRUST_BOUNDARIES* && $substrate_answer == *SECURITY_VERDICT* && $substrate_context != missing ]]; then
  record P04 'authenticated gateway call completes in Substrate specialist' "$substrate_code $substrate_state context:$substrate_context required-headings" PASS
else
  record P04 'authenticated gateway call completes in Substrate specialist' "$substrate_code $substrate_state context:$substrate_context" FAIL
fi

sleep 5
kubectl --context "$context" -n ate-system logs deployment/ate-api-server-deployment --since-time="$substrate_started" \
  > "$receipt_dir/status/substrate-lifecycle.jsonl" 2> "$receipt_dir/status/substrate-lifecycle.stderr"
lifecycle_gate=$(jq -s 'any(.[];
  .method == "/ateapi.Control/SuspendActor"
  and .err == null
  and (.resp.actor.actor_template_name | startswith("machinist-security-review-"))
  and .resp.actor.status == 4
  and (.resp.actor.latest_snapshot_info.Data.External.snapshot_uri_prefix | startswith("gs://ate-snapshots/kagent/machinist-security-review/")))' \
  "$receipt_dir/status/substrate-lifecycle.jsonl")
if [[ $lifecycle_gate == true ]]; then record S05 'Substrate actor suspended with a new external snapshot' 'SuspendActor status:4 snapshot:present' PASS; else record S05 'Substrate actor suspended with a new external snapshot' 'successful suspend witness missing' FAIL; fi

direct_failures=0
for target in incident-tools.team-event.svc.cluster.local:8080/healthz release-tools.team-chat.svc.cluster.local:8080/healthz; do
  if kubectl --context "$context" -n team-rogue exec rogue-shell -- curl -fsS --connect-timeout 3 --max-time 5 "http://$target" >/dev/null 2>&1; then direct_failures=$((direct_failures + 1)); fi
done
if [[ $direct_failures == 0 ]]; then record N08 'both direct MCP paths denied' 'both timed out or refused' PASS; else record N08 'both direct MCP paths denied' "$direct_failures unexpectedly reachable" FAIL; fi

if kubectl --context "$context" -n team-rogue exec rogue-shell -- curl -fsS --connect-timeout 3 --max-time 5 \
  http://tenant-kagent-controller.tenant-kagent-system.svc.cluster.local:8083/health >/dev/null 2>&1; then
  record N15 'direct kagent controller path denied' 'unexpectedly reachable' FAIL
else
  record N15 'direct kagent controller path denied' 'timed out or refused' PASS
fi

if kubectl --context "$context" -n team-rogue exec rogue-shell -- curl -fsS --connect-timeout 3 --max-time 5 \
  http://kagent-controller.kagent.svc.cluster.local:8083/api/a2a-sandboxes/kagent/machinist-security-review/ >/dev/null 2>&1; then
  record N23 'rogue direct Substrate specialist path denied' 'unexpectedly reachable' FAIL
else
  record N23 'rogue direct Substrate specialist path denied' 'timed out or refused' PASS
fi

event_actor='system:serviceaccount:team-event:team-event-admin'
if kubectl --context "$context" --as="$event_actor" apply --dry-run=server -f - >"$receipt_dir/responses/N18-label-spoof.out" 2>&1 <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: label-spoof-probe
  namespace: team-event
spec:
  replicas: 1
  selector:
    matchLabels:
      app: label-spoof-probe
  template:
    metadata:
      labels:
        app: label-spoof-probe
        app.kubernetes.io/managed-by: kagent
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: curl
          image: curlimages/curl:8.16.0@sha256:463eaf6072688fe96ac64fa623fe73e1dbe25d8ad6c34404a669ad3ce1f104b6
          command: ["sh", "-c", "trap : TERM INT; sleep infinity & wait"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
EOF
then
  record N18 'tenant cannot spoof kagent label in Deployment template' 'allowed' FAIL
else
  if grep -q 'Only the platform kagent controller may create kagent-managed Deployments' "$receipt_dir/responses/N18-label-spoof.out"; then
    record N18 'tenant cannot spoof kagent label in Deployment template' 'targeted admission denial' PASS
  else
    record N18 'tenant cannot spoof kagent label in Deployment template' 'denied for an unexpected reason' FAIL
  fi
fi

if kubectl --context "$context" --as="$event_actor" apply --dry-run=server -f - >"$receipt_dir/responses/N19-byo-agent.out" 2>&1 <<'EOF'
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: byo-escape-probe
  namespace: team-event
spec:
  type: BYO
  description: Negative test for the shared platform lane
  byo:
    deployment:
      image: ghcr.io/example/tenant-agent:placeholder
EOF
then
  record N19 'shared controller lane rejects BYO Agents' 'allowed' FAIL
else
  if grep -q 'The shared platform kagent lane permits Declarative Agents only' "$receipt_dir/responses/N19-byo-agent.out"; then
    record N19 'shared controller lane rejects BYO Agents' 'targeted admission denial' PASS
  else
    record N19 'shared controller lane rejects BYO Agents' 'denied for an unexpected reason' FAIL
  fi
fi

rogue_gateway_code=$(kubectl --context "$context" -n team-rogue exec rogue-shell -- curl -sS --max-time 10 -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' --data "$init_payload" http://tenant-gateway.tenant-gateway-system.svc.cluster.local:8082/mcp)
if [[ $rogue_gateway_code == 401 ]]; then record N09 'rogue can reach policy boundary but not backend' "$rogue_gateway_code" PASS; else record N09 'rogue can reach policy boundary but not backend' "$rogue_gateway_code" FAIL; fi

actor='system:serviceaccount:team-rogue:team-rogue-admin'
rbac_failures=0
rbac_index=0
if kubectl --context "$context" --as="$actor" -n team-rogue create role denied --verb=get --resource=pods --dry-run=server >"$receipt_dir/responses/rbac-$rbac_index.out" 2>&1; then rbac_failures=$((rbac_failures + 1)); fi
rbac_index=$((rbac_index + 1))
if kubectl --context "$context" --as="$actor" -n team-rogue create rolebinding denied --role=application-editor --serviceaccount=team-rogue:rogue --dry-run=server >"$receipt_dir/responses/rbac-$rbac_index.out" 2>&1; then rbac_failures=$((rbac_failures + 1)); fi
rbac_index=$((rbac_index + 1))
if kubectl --context "$context" --as="$actor" -n team-event get secret tenant-mcp-runtime-token >"$receipt_dir/responses/rbac-$rbac_index.out" 2>&1; then rbac_failures=$((rbac_failures + 1)); fi
rbac_index=$((rbac_index + 1))
if kubectl --context "$context" --as="$actor" -n team-rogue create token rogue >"$receipt_dir/responses/rbac-$rbac_index.out" 2>&1; then rbac_failures=$((rbac_failures + 1)); fi
if [[ $rbac_failures == 0 ]]; then record N10 'RBAC and cross-tenant secret actions forbidden' 'four API requests denied' PASS; else record N10 'RBAC and cross-tenant secret actions forbidden' "$rbac_failures requests allowed" FAIL; fi

if kubectl --context "$context" --as="$actor" apply --dry-run=server -f - >"$receipt_dir/responses/N11-route.out" 2>&1 <<'EOF'
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: rogue
  namespace: team-rogue
spec:
  parentRefs:
    - name: tenant-gateway
      namespace: tenant-gateway-system
  rules: []
EOF
then
  record N11 'rogue HTTPRoute create forbidden' 'allowed' FAIL
else
  record N11 'rogue HTTPRoute create forbidden' 'forbidden' PASS
fi

if kubectl --context "$context" apply --dry-run=server -f - >"$receipt_dir/responses/N12-admission.out" 2>&1 <<'EOF'
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: cross-namespace-test
  namespace: team-rogue
spec:
  url: http://example.invalid/mcp
  allowedNamespaces:
    from: All
EOF
then
  record N12 'cross-namespace RemoteMCP denied by admission' 'allowed' FAIL
else
  record N12 'cross-namespace RemoteMCP denied by admission' 'denied' PASS
fi

if kubectl --context "$context" apply --dry-run=server -f - >"$receipt_dir/responses/N16-agent-admission.out" 2>&1 <<'EOF'
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: cross-namespace-test
  namespace: team-rogue
spec:
  type: Declarative
  declarative:
    runtime: go
    modelConfig: tenant-model
    systemMessage: test
    tools:
      - type: McpServer
        mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: tenant-mcp
          namespace: team-event
EOF
then
  record N16 'cross-namespace Agent MCP reference denied by admission' 'allowed' FAIL
else
  record N16 'cross-namespace Agent MCP reference denied by admission' 'denied' PASS
fi

if kubectl --context "$context" apply --dry-run=server -f - >"$receipt_dir/responses/N14-pss.out" 2>&1 <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: privileged-test
  namespace: team-rogue
spec:
  containers:
    - name: test
      image: busybox:1.36
      securityContext:
        privileged: true
EOF
then
  record N14 'privileged Pod rejected' 'allowed' FAIL
else
  record N14 'privileged Pod rejected' 'denied' PASS
fi

kubectl --context "$context" -n team-event apply -f - >/dev/null <<'EOF'
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayBackend
metadata:
  name: refgrant-negative
spec:
  mcp:
    targets:
      - name: negative-tools
        static:
          backendRef:
            name: incident-tools
          port: 8080
          protocol: StreamableHTTP
EOF
kubectl --context "$context" -n tenant-gateway-system apply -f - >/dev/null <<'EOF'
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: refgrant-negative
spec:
  parentRefs:
    - name: tenant-gateway
      sectionName: event-mcp
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /refgrant-negative
      backendRefs:
        - group: agentgateway.dev
          kind: AgentgatewayBackend
          name: refgrant-negative
          namespace: team-event
EOF
sleep 3
kubectl --context "$context" -n tenant-gateway-system get httproute refgrant-negative -o json > "$receipt_dir/status/refgrant-negative.json"
ref_status=$(jq -r '[.status.parents[].conditions[]? | select(.type=="ResolvedRefs")][0].status // "missing"' "$receipt_dir/status/refgrant-negative.json")
ref_reason=$(jq -r '[.status.parents[].conditions[]? | select(.type=="ResolvedRefs")][0].reason // "missing"' "$receipt_dir/status/refgrant-negative.json")
if [[ $ref_status == False && $ref_reason == RefNotPermitted ]]; then record N13 'missing exact grant rejects reference' "$ref_status $ref_reason" PASS; else record N13 'missing exact grant rejects reference' "$ref_status $ref_reason" FAIL; fi

kubectl --context "$context" get pods -A -o json \
  | jq '[.items[] | select(.metadata.namespace=="tenant-gateway-system" or .metadata.namespace=="tenant-kagent-system" or .metadata.namespace=="team-event" or .metadata.namespace=="team-chat" or .metadata.namespace=="team-rogue" or .metadata.namespace=="kagent" or .metadata.namespace=="ate-system") | {namespace:.metadata.namespace,name:.metadata.name,images:[.spec.containers[].image],phase:.status.phase}]' \
  > "$receipt_dir/status/runtime-inventory.json"

if (( failures == 0 )); then
  printf 'VERDICT\tPASS\tall implemented gates passed\tPASS\n' >> "$summary"
  printf 'Evidence: %s\n' "$receipt_dir"
  exit 0
fi

printf 'VERDICT\tPASS\t%s gate(s) failed\tFAIL\n' "$failures" >> "$summary"
printf 'Evidence: %s\n' "$receipt_dir" >&2
exit 1
