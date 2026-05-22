#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATEWAY_NAMESPACE="${GATEWAY_NAMESPACE:-agentgateway-system}"
GATEWAY_NAME="${GATEWAY_NAME:-agent-gw}"
GATEWAY_SERVICE="${GATEWAY_SERVICE:-agent-gw}"
GATEWAY_PORT="${GATEWAY_PORT:-8081}"
LOCAL_PORT="${LOCAL_PORT:-18081}"

cleanup_port_forward() {
  if [[ -n "${PF_PID:-}" ]]; then
    kill "$PF_PID" >/dev/null 2>&1 || true
    wait "$PF_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup_port_forward EXIT

echo "== Cluster =="
kubectl config current-context

echo "== Schema checks =="
kubectl explain agent.spec.allowedNamespaces >/dev/null
kubectl explain agent.spec.declarative.tools.headersFrom >/dev/null
if kubectl explain agentgatewaypolicy.spec.backend.a2a >/dev/null 2>&1; then
  echo "WARN: this cluster now exposes agentgatewaypolicy.spec.backend.a2a; update this demo to add gateway-side A2A authz."
else
  echo "agentgatewaypolicy.spec.backend.a2a is absent; using HTTPRoute + policy plan-B."
fi

echo "== Apply manifests =="
kubectl apply -f "$ROOT/01-namespaces.yaml"
kubectl apply -f "$ROOT/02-rbac.yaml"
kubectl apply -f "$ROOT/03-network-policy.yaml"
kubectl apply -f "$ROOT/05-specialist-agent.yaml"
kubectl apply -f "$ROOT/06-orchestrator-agent.yaml"
kubectl apply -f "$ROOT/07-rogue-agent-deny.yaml"

tmp_route="$(mktemp)"
sed "s/name: agent-gw/name: ${GATEWAY_NAME}/" "$ROOT/04-gateway-route.yaml" > "$tmp_route"
kubectl apply -f "$tmp_route"
rm -f "$tmp_route"

echo "== Wait for allowed agents =="
kubectl wait -n team-beta --for=condition=Accepted=True agent/specialist --timeout=180s
kubectl rollout status -n team-beta deploy/specialist --timeout=300s
kubectl wait -n team-alpha --for=condition=Accepted=True agent/orchestrator --timeout=180s
kubectl rollout status -n team-alpha deploy/orchestrator --timeout=300s

echo "== Negative control =="
if kubectl wait -n team-gamma --for=condition=Accepted=True agent/rogue-orchestrator --timeout=20s >/dev/null 2>&1; then
  echo "ERROR: rogue-orchestrator became Accepted=True but should be denied."
  kubectl -n team-gamma get agent rogue-orchestrator -o yaml
  exit 1
fi
kubectl -n team-gamma get agent rogue-orchestrator -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason} {.message}{"\n"}{end}' || true

echo "== Secret isolation =="
can_read_beta_secret="$(kubectl auth can-i get secret/beta-private-token \
  --as=system:serviceaccount:team-alpha:orchestrator \
  -n team-beta || true)"
if [[ "$can_read_beta_secret" == "no" ]]; then
  echo "team-alpha/orchestrator cannot read team-beta/beta-private-token"
else
  echo "ERROR: team-alpha/orchestrator can read team-beta/beta-private-token"
  exit 1
fi

echo "== Gateway route =="
kubectl -n "$GATEWAY_NAMESPACE" get httproute cross-namespace-a2a-orchestrator -o wide
kubectl -n "$GATEWAY_NAMESPACE" get agentgatewaypolicy cross-namespace-a2a-policy

echo "== Invoke through Agentgateway =="
kubectl -n "$GATEWAY_NAMESPACE" port-forward "svc/${GATEWAY_SERVICE}" "${LOCAL_PORT}:${GATEWAY_PORT}" >/tmp/cross-namespace-a2a-port-forward.log 2>&1 &
PF_PID=$!
sleep 3

response="$(curl -sS -X POST "http://127.0.0.1:${LOCAL_PORT}/a2a/team-alpha/orchestrator/" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: cross-namespace-a2a-demo" \
  -d '{"jsonrpc":"2.0","id":"cross-ns-1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Prove CROSS_NS_PROOF_001 by delegating to the beta specialist."}]}}}')"

echo "$response" | jq .
if ! echo "$response" | jq -e '.result.artifacts[].parts[].text | select(test("SPECIALIST_REPLY|team-beta/specialist"))' >/dev/null; then
  echo "ERROR: response did not include specialist proof marker."
  exit 1
fi

echo "== PASS: Agentgateway entrypoint and cross-namespace kagent A2A delegation proven =="
