#!/usr/bin/env bash
# smoke-test-dryrun.sh — end-to-end dry-run workflow test (no Azure resources created)
# Usage: bash scripts/smoke-test-dryrun.sh [--context <kube-context>]
#
# Submits a real Workflow to the provision-aks-cluster template with dryRun=true,
# waits for Succeeded, then asserts the KRO instance was NOT persisted.
# This is the key test that proves the dry-run is real (Codex verification gap #1).

set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-{{CLUSTER_NAME}}}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --context) CONTEXT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

KC="kubectl --context $CONTEXT"
CLUSTER_NAME="demo-smoke-$(date +%s | tail -c 5)"
MAX_WAIT=120
PASS=0
FAIL=0

echo "================================================"
echo "  Smoke Test: Dry-Run Workflow"
echo "  Context     : $CONTEXT"
echo "  Cluster name: $CLUSTER_NAME"
echo "================================================"
echo ""

# ── Submit workflow ───────────────────────────────────────────────────────────
echo "Submitting dry-run workflow..."
WF_NAME=$($KC create -f - <<YAML | sed 's|.*workflow\.argoproj\.io/\([^ ]*\).*|\1|'
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: provision-aks-${CLUSTER_NAME}-
  namespace: argo
  labels:
    kro.run/demo: "true"
    kro.run/smoke-test: "true"
    kro.run/cluster: ${CLUSTER_NAME}
spec:
  workflowTemplateRef:
    name: provision-aks-cluster
  arguments:
    parameters:
      - name: clusterName
        value: "${CLUSTER_NAME}"
      - name: region
        value: "westeurope"
      - name: size
        value: "small"
      - name: dryRun
        value: "true"
      - name: confirmedBy
        value: "smoke-test"
YAML
)

echo "  Workflow submitted: $WF_NAME"
echo ""

# ── Wait for completion ────────────────────────────────────────────────────────
echo "Waiting up to ${MAX_WAIT}s for workflow to complete..."
ELAPSED=0
PHASE=""
while [ $ELAPSED -lt $MAX_WAIT ]; do
  PHASE=$($KC get workflow "$WF_NAME" -n argo \
    -o jsonpath='{.status.phase}' 2>/dev/null || echo "Pending")
  echo "  [$ELAPSED s] phase=$PHASE"
  if [[ "$PHASE" == "Succeeded" || "$PHASE" == "Failed" || "$PHASE" == "Error" ]]; then
    break
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

if [ "$PHASE" != "Succeeded" ]; then
  echo ""
  echo "FAIL: Workflow did not Succeed (phase=$PHASE)"
  echo "  Logs: argo logs -n argo $WF_NAME --context $CONTEXT"
  FAIL=$((FAIL + 1))
else
  echo "  ✓ Workflow Succeeded"
  PASS=$((PASS + 1))
fi

# ── Assert KRO instance was NOT created (dry-run proof) ───────────────────────
echo ""
echo "Asserting UK8SClusterPublic was NOT persisted (proves dry-run is real)..."
INSTANCE_EXISTS=$($KC get uk8sclusterpublic "$CLUSTER_NAME" -n uk8s-nextgen \
  --ignore-not-found -o name 2>/dev/null || echo "")

if [ -n "$INSTANCE_EXISTS" ]; then
  echo "FAIL: UK8SClusterPublic $CLUSTER_NAME EXISTS — dry-run did not work!"
  echo "  This means real Azure resources may have been created. Investigate immediately."
  FAIL=$((FAIL + 1))
else
  echo "  ✓ UK8SClusterPublic $CLUSTER_NAME: NotFound (dry-run confirmed)"
  PASS=$((PASS + 1))
fi

# ── Assert status ConfigMap was created and has expected phase ────────────────
echo ""
echo "Checking status ConfigMap..."
CM_NAME="provision-status-$WF_NAME"
PHASE_VAL=$($KC get configmap "$CM_NAME" -n argo \
  -o jsonpath='{.data.phase}' 2>/dev/null || echo "")

if [ -z "$PHASE_VAL" ]; then
  echo "FAIL: Status ConfigMap $CM_NAME not found or has no phase"
  FAIL=$((FAIL + 1))
else
  echo "  ✓ Status ConfigMap phase: $PHASE_VAL"
  PASS=$((PASS + 1))
fi

# ── Cleanup ───────────────────────────────────────────────────────────────────
echo ""
echo "Cleaning up workflow (ConfigMap auto-GC'd via ownerRef)..."
$KC delete workflow "$WF_NAME" -n argo --ignore-not-found

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo "  Smoke Test Result: $PASS passed, $FAIL failed"
echo "================================================"

if [ $FAIL -gt 0 ]; then
  exit 1
fi
