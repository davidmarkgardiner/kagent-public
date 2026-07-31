#!/usr/bin/env bash
#
# Deploy the AKS fleet patching + seccomp policy set.
#
# Creates two custom policy definitions, one initiative that also pulls in three
# Azure built-ins, and (optionally) an assignment at the chosen scope.
#
# Usage:
#   ./deploy.sh --mg <management-group-id> [--assign] [--min-node-image 202506]
#   ./deploy.sh --sub <subscription-id>    [--assign] [--min-node-image 202506]
#
# Everything is Audit-effect by default. Nothing is blocked. --assign is the only
# step that changes fleet compliance state; without it the definitions are just
# registered and you can assign from the portal.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCOPE_KIND=""
SCOPE_ID=""
DO_ASSIGN="false"
MIN_NODE_IMAGE="202506"
ASSIGNMENT_NAME="aks-fleet-patching-seccomp"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mg)             SCOPE_KIND="mg";  SCOPE_ID="$2"; shift 2 ;;
    --sub)            SCOPE_KIND="sub"; SCOPE_ID="$2"; shift 2 ;;
    --assign)         DO_ASSIGN="true"; shift ;;
    --min-node-image) MIN_NODE_IMAGE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SCOPE_KIND" || -z "$SCOPE_ID" ]]; then
  echo "Error: pass either --mg <management-group-id> or --sub <subscription-id>" >&2
  exit 1
fi

if [[ "$SCOPE_KIND" == "mg" ]]; then
  SCOPE_ARGS=(--management-group "$SCOPE_ID")
  DEFINITION_SCOPE="/providers/Microsoft.Management/managementGroups/${SCOPE_ID}"
  ASSIGN_SCOPE="$DEFINITION_SCOPE"
else
  SCOPE_ARGS=(--subscription "$SCOPE_ID")
  DEFINITION_SCOPE="/subscriptions/${SCOPE_ID}"
  ASSIGN_SCOPE="$DEFINITION_SCOPE"
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "==> Scope: ${DEFINITION_SCOPE}"

# ---------------------------------------------------------------------------
# 1. Custom policy definitions
# ---------------------------------------------------------------------------

create_definition() {
  local file="$1"
  local name
  name="$(jq -r '.name' "$file")"
  echo "==> Creating/updating policy definition: ${name}"
  jq '.properties.policyRule'  "$file" > "${WORK_DIR}/${name}.rule.json"
  jq '.properties.parameters'  "$file" > "${WORK_DIR}/${name}.params.json"
  jq '.properties.metadata'    "$file" > "${WORK_DIR}/${name}.metadata.json"

  az policy definition create \
    --name "$name" \
    --display-name "$(jq -r '.properties.displayName' "$file")" \
    --description  "$(jq -r '.properties.description'  "$file")" \
    --mode         "$(jq -r '.properties.mode'         "$file")" \
    --rules    "@${WORK_DIR}/${name}.rule.json" \
    --params   "@${WORK_DIR}/${name}.params.json" \
    --metadata "@${WORK_DIR}/${name}.metadata.json" \
    "${SCOPE_ARGS[@]}" \
    --output none
}

create_definition "${SCRIPT_DIR}/policy-node-image-freshness.json"
create_definition "${SCRIPT_DIR}/policy-node-seccomp-default.json"
create_definition "${SCRIPT_DIR}/policy-watched-identity-attached.json"

# ---------------------------------------------------------------------------
# 2. Initiative (policy set definition)
#    policyDefinitionId cannot contain ARM expressions, so substitute the scope.
# ---------------------------------------------------------------------------

SET_FILE="${SCRIPT_DIR}/initiative-aks-patching-and-seccomp.json"
SET_NAME="$(jq -r '.name' "$SET_FILE")"

sed "s|__DEFINITION_SCOPE__|${DEFINITION_SCOPE}|g" "$SET_FILE" > "${WORK_DIR}/set.json"

if grep -q "__DEFINITION_SCOPE__" "${WORK_DIR}/set.json"; then
  echo "Error: placeholder substitution failed" >&2
  exit 1
fi

jq '.properties.policyDefinitions' "${WORK_DIR}/set.json" > "${WORK_DIR}/set.defs.json"
jq '.properties.parameters'        "${WORK_DIR}/set.json" > "${WORK_DIR}/set.params.json"
jq '.properties.metadata'          "${WORK_DIR}/set.json" > "${WORK_DIR}/set.metadata.json"

echo "==> Creating/updating initiative: ${SET_NAME}"
az policy set-definition create \
  --name "$SET_NAME" \
  --display-name "$(jq -r '.properties.displayName' "${WORK_DIR}/set.json")" \
  --description  "$(jq -r '.properties.description'  "${WORK_DIR}/set.json")" \
  --definitions "@${WORK_DIR}/set.defs.json" \
  --params      "@${WORK_DIR}/set.params.json" \
  --metadata    "@${WORK_DIR}/set.metadata.json" \
  "${SCOPE_ARGS[@]}" \
  --output none

# ---------------------------------------------------------------------------
# 3. Assignment (optional)
# ---------------------------------------------------------------------------

if [[ "$DO_ASSIGN" != "true" ]]; then
  echo
  echo "Definitions registered. Re-run with --assign to assign at ${ASSIGN_SCOPE}."
  echo
  echo "Note: aks-watched-identity-attached-audit is NOT part of the initiative."
  echo "It is assigned separately once you know which identity you are hunting."
  echo "See README section 10."
  exit 0
fi

cat > "${WORK_DIR}/assign-params.json" <<EOF
{
  "minimumNodeImageDate": { "value": "${MIN_NODE_IMAGE}" }
}
EOF

echo "==> Assigning initiative at ${ASSIGN_SCOPE}"
az policy assignment create \
  --name "$ASSIGNMENT_NAME" \
  --display-name "AKS fleet: node patching currency and seccomp posture" \
  --policy-set-definition "${DEFINITION_SCOPE}/providers/Microsoft.Authorization/policySetDefinitions/${SET_NAME}" \
  --scope "$ASSIGN_SCOPE" \
  --params "@${WORK_DIR}/assign-params.json" \
  --output none

echo
echo "Assigned. First compliance scan can take up to 30 minutes."
echo "Force an evaluation now with:"
echo "  az policy state trigger-scan --no-wait"
