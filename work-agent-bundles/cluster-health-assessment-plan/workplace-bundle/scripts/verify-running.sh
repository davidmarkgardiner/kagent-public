#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

WORKER_CONTEXT="${1:?usage: verify-running.sh WORKER_CONTEXT MANAGER_CONTEXT VALUES_JSON}"
MANAGER_CONTEXT="${2:?usage: verify-running.sh WORKER_CONTEXT MANAGER_CONTEXT VALUES_JSON}"
VALUES_JSON="${3:?usage: verify-running.sh WORKER_CONTEXT MANAGER_CONTEXT VALUES_JSON}"
NAMESPACES_FILE="$BUNDLE_DIR/fox-mesh/namespaces.json"
EXPECTED="$(jq -r '.namespaces | length' "$NAMESPACES_FILE")"
MCP_SA_NAME="$(jq -er .AKS_MCP_SERVICE_ACCOUNT_NAME "$VALUES_JSON")"
MCP_SA_NAMESPACE="$(jq -er .AKS_MCP_SERVICE_ACCOUNT_NAMESPACE "$VALUES_JSON")"
AGENTGATEWAY_NAMESPACE="$(jq -er .AGENTGATEWAY_NAMESPACE "$VALUES_JSON")"
AGENTGATEWAY_SERVICE_NAME="$(jq -er .AGENTGATEWAY_SERVICE_NAME "$VALUES_JSON")"
AGENTGATEWAY_PORT="$(jq -er .AGENTGATEWAY_PORT "$VALUES_JSON")"
AGENTGATEWAY_TARGET_PORT="$(jq -er .AGENTGATEWAY_TARGET_PORT "$VALUES_JSON")"
AGENTGATEWAY_AUDIENCE="$(jq -er .AGENTGATEWAY_AUDIENCE "$VALUES_JSON")"
KAGENT_NAMESPACE="$(jq -er .KAGENT_NAMESPACE "$VALUES_JSON")"
KAGENT_CONTROLLER_SERVICE_NAME="$(jq -er .KAGENT_CONTROLLER_SERVICE_NAME "$VALUES_JSON")"

for bin in kubectl jq curl; do
  command -v "$bin" >/dev/null 2>&1 || { echo "$bin is required" >&2; exit 1; }
done

worker_cluster_uid="$(kubectl --context "$WORKER_CONTEXT" get namespace kube-system -o jsonpath='{.metadata.uid}')"
manager_cluster_uid="$(kubectl --context "$MANAGER_CONTEXT" get namespace kube-system -o jsonpath='{.metadata.uid}')"
if test "$worker_cluster_uid" != "$manager_cluster_uid"; then
  echo "this bundle is single-cluster only; worker and manager contexts identify different clusters" >&2
  exit 1
fi

assessor="system:serviceaccount:cluster-health-system:cluster-health-assessor"
bridge="system:serviceaccount:cluster-health-system:cluster-health-alert-bridge"
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$assessor" get nodes)" = yes
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$assessor" get secrets -n cluster-health-system)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$assessor" create pods -n cluster-health-system)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$bridge" get secrets -n cluster-health-system)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$bridge" list pods -A)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$bridge" create configmaps -n cluster-health-system)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$bridge" update configmap/cluster-health-alert-state -n cluster-health-system)" = yes

mcp="system:serviceaccount:${MCP_SA_NAMESPACE}:${MCP_SA_NAME}"
first_namespace="$(jq -er '.namespaces[0]' "$NAMESPACES_FILE")"
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" get pods -n "$first_namespace")" = yes
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" get pods/log -n "$first_namespace")" = yes
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" get nodes)" = yes
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" get secrets -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" get configmaps -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" create pods -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" create pods/exec -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" create pods/attach -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" update pods/ephemeralcontainers -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" create pods/portforward -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" create serviceaccounts/token -n "$first_namespace")" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" get nodes/proxy)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" create nodes/proxy)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" list secrets -A)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" list roles.rbac.authorization.k8s.io -A)" = no
test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" list clusterroles.rbac.authorization.k8s.io)" = no
while IFS= read -r namespace; do
  expected_access=no
  if jq -e --arg namespace "$namespace" '.namespaces | index($namespace) != null' "$NAMESPACES_FILE" >/dev/null; then
    expected_access=yes
  fi
  test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" get pods -n "$namespace")" = "$expected_access"
  for denied in \
    "get secrets" "list secrets" "watch secrets" \
    "get configmaps" "list configmaps" "watch configmaps" \
    "create pods" "create pods/exec" "create pods/attach" "create pods/portforward" \
    "update pods/ephemeralcontainers" "create serviceaccounts/token"; do
    verb="${denied%% *}"
    resource="${denied#* }"
    test "$(kubectl --context "$WORKER_CONTEXT" auth can-i --as="$mcp" "$verb" "$resource" -n "$namespace")" = no
  done
done < <(kubectl --context "$WORKER_CONTEXT" get namespaces -o json | jq -r '.items[].metadata.name')

expected_namespaces="$(jq -cS '.namespaces | sort' "$NAMESPACES_FILE")"
actual_namespaces="$(kubectl --context "$WORKER_CONTEXT" get rolebindings -A -o json | \
  jq -cS --arg name "$MCP_SA_NAME" --arg namespace "$MCP_SA_NAMESPACE" '
    [.items[] | select(any(.subjects[]?; .kind == "ServiceAccount" and .name == $name and .namespace == $namespace)) | .metadata.namespace] | unique | sort')"
test "$actual_namespaces" = "$expected_namespaces"

cluster_bindings="$(kubectl --context "$WORKER_CONTEXT" get clusterrolebindings -o json | \
  jq -cS --arg name "$MCP_SA_NAME" --arg namespace "$MCP_SA_NAMESPACE" '
    [.items[] | select(any(.subjects[]?; .kind == "ServiceAccount" and .name == $name and .namespace == $namespace)) | .metadata.name] | sort')"
test "$cluster_bindings" = '["cluster-health-investigator-node-read"]'

fox_json="$(kubectl --context "$WORKER_CONTEXT" -n cluster-health-system get deployment \
  -l app.kubernetes.io/part-of=cluster-health-fox-mesh -o json)"
jq -e --argjson expected "$EXPECTED" '
  (.items | length) == $expected and
  all(.items[]; (.spec.replicas == 1) and (.status.readyReplicas == 1) and
      (.status.updatedReplicas == 1) and (.status.availableReplicas == 1))
' <<<"$fox_json" >/dev/null

kubectl --context "$WORKER_CONTEXT" -n cluster-health-system rollout status \
  deployment/cluster-health-alert-bridge --timeout=120s >/dev/null

pointer="$(kubectl --context "$WORKER_CONTEXT" -n cluster-health-system get \
  configmap cluster-health-latest -o jsonpath='{.data.pointer\.json}')"
snapshot_name="$(jq -er '.snapshot' <<<"$pointer")"
snapshot="$(kubectl --context "$WORKER_CONTEXT" -n cluster-health-system get \
  configmap "$snapshot_name" -o jsonpath='{.data.snapshot\.json}')"
jq -e '
  (.cluster_id | type == "string" and length > 0) and
  (.source_generation | type == "string" and length > 0) and
  (.snapshot_seq | type == "number") and
  (.completed_at | fromdateiso8601 | (now - .) >= 0 and (now - .) <= 900) and
  (.display_score | type == "number" and . >= 0 and . <= 100) and
  (.gate.active | type == "boolean") and
  (.coverage.complete | type == "boolean")
' <<<"$snapshot" >/dev/null

missing_state=0
while IFS= read -r namespace; do
  if ! kubectl --context "$WORKER_CONTEXT" -n "$namespace" get \
    configmap fox-autonomous-monitor-state >/dev/null 2>&1; then
    echo "missing Fox state ConfigMap: $namespace/fox-autonomous-monitor-state" >&2
    missing_state=$((missing_state + 1))
  fi
done < <(jq -r '.namespaces[]' "$NAMESPACES_FILE")
test "$missing_state" -eq 0

kubectl --context "$MANAGER_CONTEXT" -n argo-events get \
  eventsource/cluster-health-kafka sensor/cluster-health-investigation \
  workflowtemplate/cluster-health-investigation >/dev/null
kubectl --context "$MANAGER_CONTEXT" -n kagent get \
  remotemcpserver >/dev/null
kubectl --context "$MANAGER_CONTEXT" -n "$AGENTGATEWAY_NAMESPACE" get \
  httproute/cluster-health-investigator-a2a \
  agentgatewaypolicy/cluster-health-investigator-a2a >/dev/null
route_count="$(kubectl --context "$MANAGER_CONTEXT" get httproutes -A -o json | \
  jq --arg service "$KAGENT_CONTROLLER_SERVICE_NAME" --arg namespace "$KAGENT_NAMESPACE" '
    [.items[] as $route |
      select(any($route.spec.rules[]?.backendRefs[]?;
        .name == $service and (.namespace // $route.metadata.namespace) == $namespace))] | length')"
test "$route_count" -eq 1
authorization_policy_count="$(kubectl --context "$MANAGER_CONTEXT" get agentgatewaypolicies -A -o json | \
  jq --arg route cluster-health-investigator-a2a --arg gateway "$(jq -er .AGENTGATEWAY_GATEWAY_NAME "$VALUES_JSON")" '
    [.items[] |
      select(.spec.traffic.authorization != null) |
      select(any(.spec.targetRefs[]?;
        (.kind == "HTTPRoute" and .name == $route) or
        (.kind == "Gateway" and .name == $gateway))] | length')"
test "$authorization_policy_count" -eq 1

service_target_port="$(kubectl --context "$MANAGER_CONTEXT" -n "$AGENTGATEWAY_NAMESPACE" get \
  service "$AGENTGATEWAY_SERVICE_NAME" -o json | jq -er --argjson port "$AGENTGATEWAY_PORT" \
  '.spec.ports[] | select(.port == $port) | .targetPort')"
test "$service_target_port" = "$AGENTGATEWAY_TARGET_PORT"

sensor="system:serviceaccount:argo-events:cluster-health-sensor"
test "$(kubectl --context "$MANAGER_CONTEXT" auth can-i --as="$sensor" create workflows.argoproj.io -n argo-events)" = yes
test "$(kubectl --context "$MANAGER_CONTEXT" auth can-i --as="$sensor" create pods -n argo-events)" = no

kubectl --context "$MANAGER_CONTEXT" -n kagent wait \
  --for=condition=Accepted agent/cluster-health-investigator --timeout=120s >/dev/null
kubectl --context "$MANAGER_CONTEXT" -n kagent wait \
  --for=condition=Ready agent/cluster-health-investigator --timeout=120s >/dev/null

verify_port="${AGENTGATEWAY_VERIFY_PORT:-18080}"
kubectl --context "$MANAGER_CONTEXT" -n "$AGENTGATEWAY_NAMESPACE" port-forward \
  "service/${AGENTGATEWAY_SERVICE_NAME}" "${verify_port}:${AGENTGATEWAY_PORT}" >/dev/null 2>&1 &
port_forward_pid=$!
cleanup_port_forward() {
  kill "$port_forward_pid" 2>/dev/null || true
  wait "$port_forward_pid" 2>/dev/null || true
}
trap cleanup_port_forward EXIT
gateway_ready=false
for _ in $(seq 1 15); do
  no_token_status="$(curl --silent --output /dev/null --max-time 2 --write-out '%{http_code}' \
    -X POST "http://127.0.0.1:${verify_port}/a2a/cluster-health/" || true)"
  if test "$no_token_status" = 401; then
    gateway_ready=true
    break
  fi
  sleep 1
done
test "$gateway_ready" = true

auth_scheme='Bear''er'
wrong_audience_credential="$(kubectl --context "$MANAGER_CONTEXT" -n argo-events create token \
  cluster-health-investigation-workflow --audience wrong-audience --duration 10m)"
wrong_audience_status="$(printf 'Authorization: %s %s\n' "$auth_scheme" "$wrong_audience_credential" | \
  curl --silent --output /dev/null --max-time 5 --write-out '%{http_code}' \
  -X POST -H @- "http://127.0.0.1:${verify_port}/a2a/cluster-health/" || true)"
test "$wrong_audience_status" = 401

wrong_subject_credential="$(kubectl --context "$MANAGER_CONTEXT" -n argo-events create token \
  default --audience "$AGENTGATEWAY_AUDIENCE" --duration 10m)"
wrong_subject_status="$(printf 'Authorization: %s %s\n' "$auth_scheme" "$wrong_subject_credential" | \
  curl --silent --output /dev/null --max-time 5 --write-out '%{http_code}' \
  -X POST -H @- "http://127.0.0.1:${verify_port}/a2a/cluster-health/" || true)"
test "$wrong_subject_status" = 403

workflow_credential="$(kubectl --context "$MANAGER_CONTEXT" -n argo-events create token \
  cluster-health-investigation-workflow --audience "$AGENTGATEWAY_AUDIENCE" --duration 10m)"
positive_status="$(printf 'Authorization: %s %s\n' "$auth_scheme" "$workflow_credential" | \
  curl --silent --output /dev/null --max-time 15 --write-out '%{http_code}' \
  -X POST -H @- \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":"auth-probe","method":"tasks/get","params":{"id":"auth-probe-does-not-exist"}}' \
  "http://127.0.0.1:${verify_port}/a2a/cluster-health/" || true)"
test "$positive_status" = 200

for probe in \
  "GET /a2a/cluster-health/" \
  "POST /a2a/cluster-health/extra" \
  "POST /api/a2a/kagent/cluster-health-investigator/"; do
  method="${probe%% *}"
  path="${probe#* }"
  probe_status="$(printf 'Authorization: %s %s\n' "$auth_scheme" "$workflow_credential" | \
    curl --silent --output /dev/null --max-time 5 --write-out '%{http_code}' \
    -X "$method" -H @- \
    "http://127.0.0.1:${verify_port}${path}" || true)"
  test "$probe_status" = 404 -o "$probe_status" = 405
done
cleanup_port_forward
trap - EXIT

echo "Running cluster-health deployment verification passed"
