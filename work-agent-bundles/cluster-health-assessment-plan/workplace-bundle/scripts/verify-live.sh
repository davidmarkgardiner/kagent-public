#!/usr/bin/env bash
set -euo pipefail

WORKER_CONTEXT="${1:?usage: verify-live.sh WORKER_CONTEXT MANAGER_CONTEXT RENDER_DIR AKS_MCP_SERVER_NAME}"
MANAGER_CONTEXT="${2:?usage: verify-live.sh WORKER_CONTEXT MANAGER_CONTEXT RENDER_DIR AKS_MCP_SERVER_NAME}"
RENDER_DIR="${3:?usage: verify-live.sh WORKER_CONTEXT MANAGER_CONTEXT RENDER_DIR AKS_MCP_SERVER_NAME}"
AKS_MCP_SERVER_NAME="${4:?usage: verify-live.sh WORKER_CONTEXT MANAGER_CONTEXT RENDER_DIR AKS_MCP_SERVER_NAME}"

for field in \
  agentgatewaypolicy.spec.traffic.jwtAuthentication \
  agentgatewaypolicy.spec.traffic.authorization; do
  kubectl --context "$MANAGER_CONTEXT" explain "$field" >/dev/null
done

worker_cluster_uid="$(kubectl --context "$WORKER_CONTEXT" get namespace kube-system -o jsonpath='{.metadata.uid}')"
manager_cluster_uid="$(kubectl --context "$MANAGER_CONTEXT" get namespace kube-system -o jsonpath='{.metadata.uid}')"
if test "$worker_cluster_uid" != "$manager_cluster_uid"; then
  echo "this bundle is single-cluster only; worker and manager contexts identify different clusters" >&2
  exit 1
fi

kubectl --context "$WORKER_CONTEXT" apply --dry-run=server --validate=strict -f "$RENDER_DIR/worker.yaml" >/dev/null
kubectl --context "$MANAGER_CONTEXT" apply --dry-run=server --validate=strict -f "$RENDER_DIR/manager.yaml" >/dev/null

kubectl --context "$MANAGER_CONTEXT" -n kagent get remotemcpserver "$AKS_MCP_SERVER_NAME" -o yaml >/dev/null
echo "Server dry-runs, agentgateway schema and manager dependency checks passed"
