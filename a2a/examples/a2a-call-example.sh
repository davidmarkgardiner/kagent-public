#!/usr/bin/env bash
# Example: call a kagent agent via A2A protocol

KAGENT_URL="${KAGENT_URL:-http://kagent-controller.kagent:8083}"
AGENT_NAME="${AGENT_NAME:-k8s-agent}"
AGENT_NAMESPACE="${AGENT_NAMESPACE:-kagent}"

# Note: trailing slash on the URL is REQUIRED — omitting it returns 404
A2A_URL="${KAGENT_URL}/api/a2a/${AGENT_NAMESPACE}/${AGENT_NAME}/"

MESSAGE="${1:-Describe the health of the cluster}"

PAYLOAD=$(python3 -c "
import json, sys
msg = sys.argv[1]
print(json.dumps({
    'jsonrpc': '2.0',
    'id': 'example-001',
    'method': 'message/send',
    'params': {
        'message': {
            'role': 'user',
            'parts': [{'kind': 'text', 'text': msg}]
        }
    }
}))
" "$MESSAGE")

curl -s -X POST "$A2A_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -c "
import json, sys
resp = json.load(sys.stdin)
artifacts = resp.get('result', {}).get('artifacts', [])
for a in artifacts:
    for part in a.get('parts', []):
        print(part.get('text', ''))
"
