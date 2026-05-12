#!/usr/bin/env bash
# smoke-test-rbac.sh — verify RBAC scope for both service accounts
# Usage: bash scripts/smoke-test-rbac.sh [--context <kube-context>]
#
# Tests (Codex verification gap #2):
#   kagent SA:
#     ✓ CAN   create workflows in argo ns
#     ✓ CAN   get configmaps in argo ns
#     ✓ CAN   get uk8sclusterpublics (read-only)
#     ✗ CANNOT create uk8sclusterpublics (must go via workflow)
#     ✗ CANNOT create uk8scertificationv2s
#
#   argo-workflow-executor SA:
#     ✓ CAN   create uk8sclusterpublics in uk8s-nextgen
#     ✓ CAN   create uk8scertificationv2s in uk8s-nextgen
#     ✓ CAN   create configmaps in argo ns

set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-{{CLUSTER_NAME}}}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --context) CONTEXT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

KC="kubectl --context $CONTEXT"
PASS=0
FAIL=0

check() {
  local LABEL="$1"
  local EXPECT="$2"  # "yes" or "no"
  shift 2
  RESULT=$($KC auth can-i "$@" 2>/dev/null | tr -d '[:space:]') || true
  if [ "$RESULT" = "$EXPECT" ]; then
    echo "  ✓ $LABEL"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $LABEL (expected=$EXPECT got=$RESULT)"
    FAIL=$((FAIL + 1))
  fi
}

echo "================================================"
echo "  RBAC Smoke Test"
echo "  Context: $CONTEXT"
echo "================================================"
echo ""

echo "── kagent SA (namespace: kagent) ────────────────"
KAGENT_SA="--as=system:serviceaccount:kagent:kagent"

check "kagent CAN create workflows in argo" \
  "yes" create workflows.argoproj.io -n argo $KAGENT_SA

check "kagent CAN get configmaps in argo" \
  "yes" get configmaps -n argo $KAGENT_SA

check "kagent CAN get uk8sclusterpublics (status reads)" \
  "yes" get uk8sclusterpublics -n uk8s-nextgen $KAGENT_SA

check "kagent CANNOT create uk8sclusterpublics (must go via workflow)" \
  "no" create uk8sclusterpublics -n uk8s-nextgen $KAGENT_SA

check "kagent CANNOT create uk8scertificationv2s" \
  "no" create uk8scertificationv2s -n uk8s-nextgen $KAGENT_SA

echo ""
echo "── argo-workflow-executor SA (namespace: argo) ───"
WORKFLOW_SA="--as=system:serviceaccount:argo:argo-workflow-executor"

check "workflow-executor CAN create uk8sclusterpublics in uk8s-nextgen" \
  "yes" create uk8sclusterpublics -n uk8s-nextgen $WORKFLOW_SA

check "workflow-executor CAN create uk8scertificationv2s in uk8s-nextgen" \
  "yes" create uk8scertificationv2s -n uk8s-nextgen $WORKFLOW_SA

check "workflow-executor CAN create configmaps in argo" \
  "yes" create configmaps -n argo $WORKFLOW_SA

check "workflow-executor CAN get secrets named platform-defaults in argo" \
  "yes" get secrets/platform-defaults -n argo $WORKFLOW_SA

echo ""
echo "================================================"
echo "  RBAC Result: $PASS passed, $FAIL failed"
echo "================================================"

if [ $FAIL -gt 0 ]; then
  echo ""
  echo "Fix: kubectl apply -f workflow/rbac.yaml --context $CONTEXT"
  exit 1
fi
