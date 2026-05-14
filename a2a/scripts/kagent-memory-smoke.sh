#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-kagent}"
CONTROLLER_SERVICE="${CONTROLLER_SERVICE:-kagent-controller}"
PORT="${PORT:-18083}"
A2A_AGENT="${A2A_AGENT:-hello-responder-agent}"
MEMORY_AGENT="${MEMORY_AGENT:-memory-api-smoke}"
USER_ID="${USER_ID:-codex-memory-$(date +%Y%m%d%H%M%S)}"

kubectl port-forward -n "$NAMESPACE" "svc/$CONTROLLER_SERVICE" "$PORT:8083" >/tmp/kagent-memory-smoke-pf.log 2>&1 &
PF_PID=$!
trap 'kill "$PF_PID" >/dev/null 2>&1 || true' EXIT
sleep 2

BASE="http://127.0.0.1:$PORT"

echo "== Controller config =="
kubectl get cm -n "$NAMESPACE" kagent-controller -o json \
  | jq -r '.data | {
      DATABASE_TYPE,
      DATABASE_VECTOR_ENABLED,
      SQLITE_DATABASE_PATH,
      IMAGE_TAG
    }'

echo
echo "== Native memory API smoke =="
echo "user_id=$USER_ID"

echo "-- initial list"
curl -sS "$BASE/api/memories?agent_name=$MEMORY_AGENT&user_id=$USER_ID" | jq .

echo "-- add one memory"
jq -nc \
  --arg agent "$MEMORY_AGENT" \
  --arg user "$USER_ID" \
  --arg content "Codex memory smoke: preferred namespace is platform-dev; scenario token homelab-memory-smoke." \
  '{
    agent_name:$agent,
    user_id:$user,
    content:$content,
    vector:([range(0;768)|0.001]),
    metadata:{source:"codex-smoke"},
    ttl_days:1
  }' \
  | curl -sS -X POST "$BASE/api/memories/sessions" \
      -H "Content-Type: application/json" \
      -d @- \
  | jq .

echo "-- list after add"
curl -sS "$BASE/api/memories?agent_name=$MEMORY_AGENT&user_id=$USER_ID" | jq .

echo "-- vector search"
jq -nc \
  --arg agent "$MEMORY_AGENT" \
  --arg user "$USER_ID" \
  '{
    agent_name:$agent,
    user_id:$user,
    vector:([range(0;768)|0.001]),
    limit:5,
    min_score:0.0
  }' \
  | curl -sS -X POST "$BASE/api/memories/search" \
      -H "Content-Type: application/json" \
      -d @- \
  | jq .

echo "-- isolation checks"
curl -sS "$BASE/api/memories?agent_name=${MEMORY_AGENT}-other&user_id=$USER_ID" | jq .
curl -sS "$BASE/api/memories?agent_name=$MEMORY_AGENT&user_id=${USER_ID}-other" | jq .

echo
echo "== A2A session continuity smoke =="
TOKEN="ORCHID-$(date +%H%M%S)"
A2A_URL="$BASE/api/a2a/$NAMESPACE/$A2A_AGENT/"
echo "token=$TOKEN"

TEXT1="The session token is $TOKEN. Reply with exactly: stored"
REQ1=$(jq -nc --arg text "$TEXT1" '{
  jsonrpc:"2.0",
  id:"turn1",
  method:"message/send",
  params:{
    message:{
      role:"user",
      messageId:"msg-turn1",
      parts:[{kind:"text",text:$text}]
    }
  }
}')
RESP1=$(curl -sS -X POST "$A2A_URL" -H "Content-Type: application/json" -d "$REQ1" -m 90)
echo "-- turn 1"
echo "$RESP1" | jq '{contextId:.result.contextId, text:.result.artifacts[0].parts[0].text, session:.result.metadata.kagent_session_id}'

CTX=$(echo "$RESP1" | jq -r '.result.contextId')
REQ2=$(jq -nc --arg ctx "$CTX" '{
  jsonrpc:"2.0",
  id:"turn2",
  method:"message/send",
  params:{
    message:{
      role:"user",
      messageId:"msg-turn2",
      contextId:$ctx,
      parts:[{kind:"text",text:"What is the session token? Reply with only the token."}]
    }
  }
}')
RESP2=$(curl -sS -X POST "$A2A_URL" -H "Content-Type: application/json" -d "$REQ2" -m 90)
echo "-- turn 2, same context"
echo "$RESP2" | jq '{contextId:.result.contextId, text:.result.artifacts[0].parts[0].text, session:.result.metadata.kagent_session_id}'

REQ3=$(jq -nc '{
  jsonrpc:"2.0",
  id:"turn3",
  method:"message/send",
  params:{
    message:{
      role:"user",
      messageId:"msg-turn3",
      parts:[{kind:"text",text:"What is the session token? Reply with only the token if you know it, otherwise reply UNKNOWN."}]
    }
  }
}')
RESP3=$(curl -sS -X POST "$A2A_URL" -H "Content-Type: application/json" -d "$REQ3" -m 90)
echo "-- turn 3, new context"
echo "$RESP3" | jq '{contextId:.result.contextId, text:.result.artifacts[0].parts[0].text, session:.result.metadata.kagent_session_id}'

echo "-- same-context persisted events"
curl -sS "$BASE/api/sessions/$CTX?user_id=admin@kagent.dev&order=asc&limit=-1" \
  | jq '{session:.data.session.id, event_count:(.data.events|length), event_authors:[.data.events[].data | fromjson | .author]}'

