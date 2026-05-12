#!/bin/bash
# Setup Port.io blueprints, actions, and scorecards for the IDP namespace service.
# Usage: ./setup-port-blueprints.sh <CLIENT_ID> <CLIENT_SECRET>
# Source files: /home/david/repos/argo-workflow/idp-namespace-service/port/

set -euo pipefail

CLIENT_ID="${1:?Usage: $0 <CLIENT_ID> <CLIENT_SECRET>}"
CLIENT_SECRET="${2:?Usage: $0 <CLIENT_ID> <CLIENT_SECRET>}"
PORT_DIR="/home/david/repos/argo-workflow/idp-namespace-service/port"
BASE_URL="https://api.getport.io"

echo "=== Authenticating with Port.io ==="
TOKEN=$(curl -s -X POST "${BASE_URL}/v1/auth/access_token" \
  -H "Content-Type: application/json" \
  -d "{\"clientId\":\"${CLIENT_ID}\",\"clientSecret\":\"${CLIENT_SECRET}\"}" | jq -r '.accessToken')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "ERROR: Failed to authenticate"
  exit 1
fi
echo "✓ Authenticated"

# Helper function
port_api() {
  local method="$1" path="$2" data="$3"
  local status
  status=$(curl -s -o /dev/stderr -w "%{http_code}" -X "$method" "${BASE_URL}${path}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d "$data" 2>&1)
  echo "$status"
}

echo ""
echo "=== Creating Blueprints ==="

echo -n "Creating cluster blueprint... "
port_api POST "/v1/blueprints" "$(cat ${PORT_DIR}/blueprint-cluster.json)"
echo ""

echo -n "Creating namespace blueprint... "
port_api POST "/v1/blueprints" "$(cat ${PORT_DIR}/blueprint-namespace.json)"
echo ""

echo ""
echo "=== Creating Actions ==="

for action in create-namespace delete-namespace modify-namespace; do
  echo -n "Creating action: ${action}... "
  port_api POST "/v1/actions" "$(cat ${PORT_DIR}/action-${action}.json)"
  echo ""
done

echo ""
echo "=== Creating Scorecards ==="

echo -n "Creating namespace compliance scorecard... "
port_api POST "/v1/blueprints/namespace/scorecards" "$(cat ${PORT_DIR}/scorecard-namespace.json)"
echo ""

echo ""
echo "=== Creating seed cluster entity ==="
port_api POST "/v1/blueprints/cluster/entities?upsert=true" '{
  "identifier": "homelab",
  "title": "Homelab (Kind)",
  "properties": {
    "name": "homelab",
    "region": "uksouth",
    "environment": "dev",
    "kubernetes_version": "1.35.0",
    "node_count": 1,
    "status": "Running"
  }
}'
echo ""

echo ""
echo "=== Done ==="
echo "Port.io is configured. Next steps:"
echo "1. Update webhook URLs in actions to point to your cluster"
echo "2. Create k8s secrets (git-ssh-key, git-credentials, port-credentials)"
echo "3. Deploy Argo Events resources (00-08 yaml files)"
