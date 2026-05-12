#!/usr/bin/env bash
# deploy-home-dryrun.sh — idempotent installer for home cluster dry-run demo
# Usage: bash scripts/deploy-home-dryrun.sh [--context <kube-context>]
#
# Steps:
#   1. Preflight: KRO controller running
#   2. KRO aggregate RBAC (wildcard on kro.run resources)
#   3. Home-cluster stub RGDs (fluxgitops, certification, certification-v2, cluster-public)
#   4. Wait for all RGDs to be Active
#   5. Ensure uk8s-nextgen namespace
#   6. platform-defaults Secret (home values from template)
#   7. Demo RBAC (kagent SA + workflow-executor SA scopes)
#   8. WorkflowTemplate
#   9. KAgent Agent
#  10. Verify agent Ready

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
CONTEXT="${KUBE_CONTEXT:-{{CLUSTER_NAME}}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context) CONTEXT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

KC="kubectl --context $CONTEXT"

echo "================================================"
echo "  ASO Cluster Agent Demo — Home Dry-Run Deploy"
echo "  Context : $CONTEXT"
echo "================================================"
echo ""

# ── 1. Preflight: KRO controller ──────────────────────────────────────────────
echo "Step 1/10: Checking KRO controller..."
if ! $KC get pods -n kro-system -l app.kubernetes.io/name=kro --no-headers 2>/dev/null | grep -q Running; then
  echo "ERROR: KRO controller not running in kro-system namespace."
  echo "Install KRO first: https://kro.run/docs/getting-started"
  exit 1
fi
echo "  ✓ KRO controller running"

# ── 2. KRO aggregate RBAC ─────────────────────────────────────────────────────
echo ""
echo "Step 2/10: Applying KRO aggregate RBAC..."
$KC apply -f "$DEMO_DIR/workflow/kro-aggregate-rbac.yaml"
echo "  ✓ kro:controller:uk8s-demo ClusterRole applied"

# ── 3. Home-cluster stub RGDs ─────────────────────────────────────────────────
echo ""
echo "Step 3/10: Applying prerequisite RGDs..."

# fluxgitops stub (replaces Azure kubernetesconfiguration CRD dependency)
$KC apply -f "$DEMO_DIR/workflow/uk8sfluxgitops-home-stub.yaml"
echo "  ✓ uk8sfluxgitops-home-stub applied"

# uk8s-certification (v1 — referenced by uk8scluster-public)
$KC apply -f "$REPO_ROOT/infra-stack/kro-stack/definitions/uk8s-certification.yaml"
echo "  ✓ uk8s-certification RGD applied"

# uk8s-certification-v2 (for cert trigger after provisioning)
$KC apply -f "$REPO_ROOT/infra-stack/kro-stack/definitions/uk8s-certification-v2.yaml"
echo "  ✓ uk8s-certification-v2 RGD applied"

# uk8scluster-public (main RGD — depends on fluxgitops + certification above)
$KC delete resourcegraphdefinition uk8sclusterpublic.kro.run --ignore-not-found 2>/dev/null || true
$KC apply -f "$REPO_ROOT/infra-stack/kro-stack/definitions/uk8scluster-public.yaml"
echo "  ✓ uk8scluster-public RGD applied"

# ── 4. Wait for RGDs to go Active ─────────────────────────────────────────────
echo ""
echo "Step 4/10: Waiting for RGDs to become Active (up to 90s)..."
ELAPSED=0
while [ $ELAPSED -lt 90 ]; do
  INACTIVE=$($KC get resourcegraphdefinition --no-headers 2>/dev/null \
    | grep -E "uk8sclusterpublic|uk8scertification|uk8sfluxgitops" \
    | grep -v "Active" | wc -l | tr -d ' ') || INACTIVE=0
  if [ "$INACTIVE" -eq 0 ]; then
    break
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

$KC get resourcegraphdefinition --no-headers -o wide 2>/dev/null \
  | grep -E "uk8scluster|uk8scertif|uk8sflux" \
  | awk '{printf "  %-50s %s\n", $1, $4}'

STILL_INACTIVE=$($KC get resourcegraphdefinition --no-headers 2>/dev/null \
  | grep -E "uk8sclusterpublic|uk8scertification" \
  | grep -v "Active" | wc -l | tr -d ' ') || STILL_INACTIVE=0
if [ "$STILL_INACTIVE" -gt 0 ]; then
  echo "  WARNING: Some RGDs still Inactive — check KRO logs:"
  echo "    kubectl logs -n kro-system deploy/kro --tail=30 --context $CONTEXT"
fi

# ── 5. Ensure uk8s-nextgen namespace ─────────────────────────────────────────
echo ""
echo "Step 5/10: Ensuring uk8s-nextgen namespace..."
$KC create namespace uk8s-nextgen --dry-run=client -o yaml | $KC apply -f -
echo "  ✓ uk8s-nextgen namespace ready"

# ── 6. platform-defaults Secret ──────────────────────────────────────────────
echo ""
echo "Step 6/10: Applying platform-defaults Secret..."
TEMPLATE_FILE="$DEMO_DIR/workflow/platform-defaults-secret.yaml.template"
$KC apply -f "$TEMPLATE_FILE"
echo "  ✓ platform-defaults Secret applied in argo namespace"

# ── 7. Demo RBAC ──────────────────────────────────────────────────────────────
echo ""
echo "Step 7/10: Applying demo RBAC..."
$KC apply -f "$DEMO_DIR/workflow/rbac.yaml"
echo "  ✓ RBAC applied"

# ── 8. WorkflowTemplate ──────────────────────────────────────────────────────
echo ""
echo "Step 8/10: Applying WorkflowTemplate..."
$KC apply -f "$DEMO_DIR/workflow/provision-aks-cluster-template.yaml"
echo "  ✓ WorkflowTemplate provision-aks-cluster applied in argo namespace"

# ── 9. KAgent Agent ──────────────────────────────────────────────────────────
echo ""
echo "Step 9/10: Applying KAgent Agent..."
$KC apply -f "$DEMO_DIR/agent/aso-provisioner-agent.yaml"
echo "  ✓ Agent aso-cluster-provisioner applied in kagent namespace"

# ── 10. Verify ────────────────────────────────────────────────────────────────
echo ""
echo "Step 10/10: Verifying deployment..."
echo -n "  Waiting for Agent to be ready"
for i in $(seq 1 30); do
  READY=$($KC get agent aso-cluster-provisioner -n kagent \
    -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
  if [ "$READY" = "True" ]; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 2
  if [ $i -eq 30 ]; then
    echo ""
    echo "  WARNING: Agent not yet Ready after 60s"
    echo "  kubectl logs -n kagent deploy/kagent-controller --context $CONTEXT | tail -20"
  fi
done

echo ""
echo "================================================"
echo "  Deploy complete!"
echo ""
echo "  Next steps:"
echo "    1. RBAC smoke test (must pass first):"
echo "       bash scripts/smoke-test-rbac.sh --context $CONTEXT"
echo ""
echo "    2. Dry-run workflow smoke test:"
echo "       bash scripts/smoke-test-dryrun.sh --context $CONTEXT"
echo ""
echo "    3. Bad-input rejection test:"
echo "       bash scripts/smoke-test-bad-inputs.sh --context $CONTEXT"
echo ""
echo "    4. Open the KAgent UI:"
echo "       https://{{INGRESS_DOMAIN}} → aso-cluster-provisioner"
echo "================================================"
