#!/usr/bin/env bash
# teardown-home.sh — remove all demo artifacts from the cluster
# Usage: bash scripts/teardown-home.sh [--context <kube-context>] [--purge-rbac]
#
# By default leaves RBAC in place (reusable for re-deploy).
# Pass --purge-rbac to remove it too.

set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-{{CLUSTER_NAME}}}"
PURGE_RBAC=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context)    CONTEXT="$2"; shift 2 ;;
    --purge-rbac) PURGE_RBAC=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

KC="kubectl --context $CONTEXT"

echo "================================================"
echo "  ASO Cluster Agent Demo — Teardown"
echo "  Context    : $CONTEXT"
echo "  Purge RBAC : $PURGE_RBAC"
echo "================================================"
echo ""

echo "Removing KAgent Agent..."
$KC delete agent aso-cluster-provisioner -n kagent --ignore-not-found
echo "  ✓ Agent removed"

echo "Removing WorkflowTemplate..."
$KC delete workflowtemplate provision-aks-cluster -n argo --ignore-not-found
echo "  ✓ WorkflowTemplate removed"

echo "Removing platform-defaults Secret..."
$KC delete secret platform-defaults -n argo --ignore-not-found
echo "  ✓ Secret removed"

echo "Removing any running/completed smoke-test Workflows..."
$KC delete workflows -n argo -l kro.run/smoke-test --ignore-not-found
echo "  ✓ Smoke-test workflows removed"

if [ "$PURGE_RBAC" = "true" ]; then
  echo "Removing RBAC..."
  $KC delete role kagent-workflow-submitter -n argo --ignore-not-found
  $KC delete rolebinding kagent-workflow-submitter -n argo --ignore-not-found
  $KC delete clusterrole kagent-kro-reader --ignore-not-found
  $KC delete clusterrolebinding kagent-kro-reader --ignore-not-found
  $KC delete role workflow-executor-kro-provisioner -n uk8s-nextgen --ignore-not-found
  $KC delete rolebinding workflow-executor-kro-provisioner -n uk8s-nextgen --ignore-not-found
  $KC delete role workflow-executor-status-writer -n argo --ignore-not-found
  $KC delete rolebinding workflow-executor-status-writer -n argo --ignore-not-found
  echo "  ✓ RBAC removed"
else
  echo "  (RBAC left in place — pass --purge-rbac to remove)"
fi

echo ""
echo "================================================"
echo "  Teardown complete"
echo "================================================"
