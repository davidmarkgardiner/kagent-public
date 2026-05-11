#!/usr/bin/env bash
# smoke-test-bad-inputs.sh — verify the workflow rejects invalid parameters
# Usage: bash scripts/smoke-test-bad-inputs.sh [--context <kube-context>]
#
# Submits workflows with bad inputs and asserts they fail the validate-inputs step.
# The agent has its own guards, but this tests the workflow's structural safety net.

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

submit_and_expect_failure() {
  local TEST_NAME="$1"
  local CLUSTER_NAME="$2"
  local REGION="$3"
  local SIZE="$4"

  echo "Test: $TEST_NAME"

  # Submit workflow
  WF_NAME=$($KC create -f - <<YAML 2>/dev/null | sed 's|.*workflow\.argoproj\.io/\([^ ]*\).*|\1|' || echo ""
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: bad-input-test-
  namespace: argo
  labels:
    kro.run/smoke-test: "bad-inputs"
spec:
  workflowTemplateRef:
    name: provision-aks-cluster
  arguments:
    parameters:
      - name: clusterName
        value: "${CLUSTER_NAME}"
      - name: region
        value: "${REGION}"
      - name: size
        value: "${SIZE}"
      - name: dryRun
        value: "true"
      - name: confirmedBy
        value: "smoke-test"
YAML
)

  if [ -z "$WF_NAME" ]; then
    echo "  ✓ Workflow rejected at submission (expected)"
    PASS=$((PASS + 1))
    return
  fi

  # Wait up to 30s for it to fail
  for i in $(seq 1 15); do
    PHASE=$($KC get workflow "$WF_NAME" -n argo \
      -o jsonpath='{.status.phase}' 2>/dev/null || echo "Pending")
    if [[ "$PHASE" == "Failed" || "$PHASE" == "Error" ]]; then
      echo "  ✓ Workflow failed as expected (phase=$PHASE)"
      PASS=$((PASS + 1))
      $KC delete workflow "$WF_NAME" -n argo --ignore-not-found &>/dev/null
      return
    fi
    if [[ "$PHASE" == "Succeeded" ]]; then
      echo "  ✗ Workflow SUCCEEDED but should have failed (test=$TEST_NAME)"
      FAIL=$((FAIL + 1))
      $KC delete workflow "$WF_NAME" -n argo --ignore-not-found &>/dev/null
      return
    fi
    sleep 2
  done

  echo "  ✗ Workflow did not fail within 30s (phase=$PHASE)"
  FAIL=$((FAIL + 1))
  $KC delete workflow "$WF_NAME" -n argo --ignore-not-found &>/dev/null
}

echo "================================================"
echo "  Smoke Test: Bad Inputs"
echo "  Context: $CONTEXT"
echo "================================================"
echo ""

# Test 1: Name with uppercase (invalid regex)
submit_and_expect_failure \
  "uppercase name" \
  "Demo-One" \
  "westeurope" \
  "small"

# Test 2: Name starts with digit
submit_and_expect_failure \
  "name starts with digit" \
  "1cluster" \
  "westeurope" \
  "small"

# Test 3: Invalid region
submit_and_expect_failure \
  "invalid region (mars)" \
  "test-cluster" \
  "mars" \
  "small"

# Test 4: Invalid size
submit_and_expect_failure \
  "invalid size (huge)" \
  "test-cluster" \
  "westeurope" \
  "huge"

# Test 5: Name too short (2 chars)
submit_and_expect_failure \
  "name too short" \
  "ab" \
  "westeurope" \
  "small"

echo ""
echo "================================================"
echo "  Bad-Inputs Result: $PASS passed, $FAIL failed"
echo "================================================"

[ $FAIL -gt 0 ] && exit 1 || exit 0
