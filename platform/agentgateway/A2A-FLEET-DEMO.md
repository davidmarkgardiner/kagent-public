# A2A cross-cluster fleet-agent demo (PR 4 runbook)

Companion runbook for `service-a2a-fleet-agent.yaml`,
`route-a2a-fleet-agent.yaml`, and `policy-a2a-fleet-agent.yaml`.

## Headline claim — what plan B actually ships

> "A worker-cluster kagent agent can escalate to a management-cluster
> fleet/incident agent **through agentgateway**, which provides routing,
> URL rewrite, rate limiting, request timeout, and telemetry on the
> escalation path. Identity is enforced **outside** agentgateway at the
> Istio AuthorizationPolicy layer because the installed agentgateway
> CRD release does not ship `AgentgatewayPolicy.spec.backend.a2a`."

Do NOT make the stronger "gateway-side authorization" claim in the PR
description. The earlier draft of this runbook did; reviewer flagged it
correctly. Add a gateway-layer authz claim only after either:
- a future agentgateway release ships `backend.a2a.authorization`, or
- an HTTP-layer authz primitive on `AgentgatewayPolicy.traffic.*`
  (e.g. `apiKeyAuthentication`, `jwtAuthentication`, `authorization`) is
  proven in PR 0 and wired into this policy.

## Schema verdict captured (proxmox-k8s, 2026-05-14)

| Capability | Verdict | Evidence |
|---|---|---|
| `AgentgatewayBackend.spec.a2a` | NOT SUPPORTED | `kubectl explain` → field does not exist |
| Service `appProtocol: agentgateway.dev/a2a` routed via HTTPRoute | NOT SUPPORTED on this release | no CRD primitive accepts it; demo uses plain HTTP routing |
| `AgentgatewayPolicy.spec.backend.a2a.authorization` | NOT SUPPORTED | `kubectl explain` → field does not exist |
| Cross-namespace HTTPRoute → Service via ReferenceGrant | supported | applied successfully (`allow-agentgateway-to-kagent-controller`) |

## Identity model — read before any apply

| Layer | What it actually guarantees on this CRD release | Where it lives |
|---|---|---|
| Istio AuthorizationPolicy (ingress) | Source IP allow-list of worker-cluster egress; planned upgrade paths to shared API key + JWT | `istio-authorization-policy.yaml` — and the `/a2a/fleet/*` path must be present in the `paths:` list (verify before applying PR 4) |
| AgentgatewayPolicy (gateway) | **No identity check on plan B.** Only rate limit + timeout + telemetry | `policy-a2a-fleet-agent.yaml` |
| kagent A2A handler (controller) | Routes to the agent encoded in the URL path | `route-a2a-fleet-agent.yaml` rewrite |

If `istio-authorization-policy.yaml` is **not** applied on this cluster,
there is currently no identity gate at all — the `/a2a/fleet/*` path is
reachable by anyone who can reach the gateway. Treat that as a P0 to
fix before any production demo.

## Pre-flight checklist

- [ ] `istio-authorization-policy.yaml` is applied AND its `paths:`
  list includes `/a2a/fleet/*` (the cleanup committed in this PR set
  adds it; older versions of the file did not).
- [ ] A fleet/incident agent exists in `kagent` namespace (e.g.
  `sre-triage-agent` on proxmox-k8s, 2026-05-14).
- [ ] `parentRefs.name` in `route-a2a-fleet-agent.yaml` matches the
  real Gateway name on the target cluster (`ai-gateway` per the repo's
  `gateway-resources.yaml`; `agent-gw` on proxmox-k8s — see
  DEMO-SCHEMA-GATE.md Inventory caveat 1).
- [ ] `REPLACE_WITH_FLEET_AGENT_NAME` in the route rewrite is set.

## Apply order

```bash
# Management cluster
kubectl apply -f service-a2a-fleet-agent.yaml      # ReferenceGrant
kubectl apply -f route-a2a-fleet-agent.yaml        # HTTPRoute (cluster-tweak parentRefs first)
kubectl apply -f policy-a2a-fleet-agent.yaml       # rate limit + timeout
kubectl apply -f istio-authorization-policy.yaml   # if not already applied
```

## Smoke test — local port-forward (allow path)

```bash
GATEWAY_SVC=agent-gw          # or ai-gateway on a repo-aligned cluster
GATEWAY_PORT=8081             # confirm with `kubectl get svc -n agentgateway-system`
kubectl port-forward -n agentgateway-system svc/$GATEWAY_SVC 18081:$GATEWAY_PORT &

curl -s -X POST http://localhost:18081/a2a/fleet/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send",
       "params":{"message":{"role":"user",
                            "parts":[{"kind":"text","text":"status"}]}}}' \
  | jq '.result.artifacts[0].parts[0].text, .error'
```

Expected: 200 with a reply from the fleet agent (proves route + rewrite
+ ReferenceGrant + kagent A2A all wire up).

**Limitation**: port-forward bypasses the Istio ingress entirely, so
this test does not prove the identity gate. It only proves the gateway
data path. See "Smoke test — real ingress" below for the identity
verification.

## Smoke test — real ingress (must also pass before claiming end-to-end)

The Istio AuthorizationPolicy only sees requests that arrive through
the actual ingress listener, not port-forwards. Test from off-cluster:

```bash
# Find the ingress IP (per README.md gotcha #6)
INGRESS_IP=$(kubectl get svc -n aks-istio-ingress aks-istio-ingressgateway-external \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
HOST=agentgateway.<wildcard-domain>

# Allowed-source curl — should succeed
curl -s --resolve "$HOST:443:$INGRESS_IP" -X POST https://$HOST/a2a/fleet/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send",
       "params":{"message":{"role":"user",
                            "parts":[{"kind":"text","text":"status"}]}}}' \
  | jq '.result.artifacts[0].parts[0].text, .error'
```

## Trailing-slash variants

`PathPrefix: /a2a/fleet/` is what the HTTPRoute matches. Observed
behaviour on proxmox-k8s (kagent v0.8.0-beta4, agentgateway CRD
v1alpha1, 2026-05-14):

| Request path | Status | What happened |
|---|---|---|
| `/a2a/fleet/` | 200 | Canonical. Reaches `sre-triage-agent` and returns a real artifact. |
| `/a2a/fleet` | 301 | Envoy auto-redirects to `/a2a/fleet/`. Client must follow (e.g. `curl -L`). |
| `/a2a/fleet/foo` | 200 | Tail `foo` appended after the rewrite target → `/api/a2a/kagent/<fleet>/foo`. Useful only if the kagent controller serves a sub-path; otherwise harmless. |

```bash
for path in "/a2a/fleet/" "/a2a/fleet" "/a2a/fleet/foo"; do
  curl -s -o /dev/null -w "%-25s status=%{http_code}\n" -X POST \
    http://localhost:18081$path \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":"1","method":"message/send",
         "params":{"message":{"role":"user","parts":[{"kind":"text","text":"x"}]}}}' \
    --output-document /dev/null
done
```

Recommendations:
- Always document `/a2a/fleet/` (with trailing slash) as the canonical
  URL in worker-side configuration.
- POST clients that do not follow redirects automatically will see a
  301 and must either re-issue the request or use the canonical URL.
- A `RequestRedirect` HTTPRoute filter is **not** needed on this
  release — the gateway already auto-redirects.

## Authorization-failure tests — what plan B can actually verify

The agentgateway policy does **not** reject requests on identity. The
only gateway-side rejections plan B can demonstrate today:

```bash
# 1. Rate-limit rejection (gateway enforces this — local rateLimit 2/s burst 5).
#    Fire >5 requests faster than 1/s for a few seconds and look for 429s.
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:18081/a2a/fleet/ \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":"'"$i"'","method":"message/send",
         "params":{"message":{"role":"user","parts":[{"kind":"text","text":"x"}]}}}'
done
# Expected: a mix of 200s and 429s.

# 2. Request-timeout rejection (gateway enforces this — traffic.timeouts.request 120s).
#    Use a Codex-style long-running request that exceeds the budget to observe
#    the gateway returning a 504 instead of a hung connection.

# 3. Source-IP rejection (Istio enforces this).
#    Run from a pod or cluster that is NOT in the
#    istio-authorization-policy.yaml remoteIpBlocks allow-list,
#    using the ingress host (NOT port-forward). Expected: 403 from Envoy.

# 4. Path rejection (Istio enforces this).
#    If /a2a/fleet/* is missing from the Istio policy paths list,
#    requests to that path return 403 regardless of source IP.
```

Earlier drafts of this runbook included a CEL-rejection deny test for
mismatched `x-kagent-cluster` / `x-kagent-agent`. That test cannot pass
on plan B and has been removed. Re-introduce it only if a future
agentgateway release ships HTTP- or A2A-level authz primitives.

## Worker-side mechanism — still TBD

A kagent `type: Agent` with `tools[].type: McpServer` is the only worker
pattern this repo has demonstrated for remote calls. There is no proven
kagent shape for "agent A as a tool of agent B over a remote A2A URL".
Until that is confirmed, the worker side calls the remote fleet agent
via one of:

- A purpose-built escalation tool exposed as an MCP server on the
  worker cluster that forwards JSON-RPC to
  `https://agentgateway.<wildcard-domain>/a2a/fleet/`.
- A direct A2A call from a script/operator outside kagent for the
  manual smoke test (good enough to prove the gateway shape works,
  which is what the proxmox-k8s 2026-05-14 verification did).

Record the chosen approach in the PR description before merging. Do
not add a worker-cluster `type: Agent` referencing a remote A2A URL
until that pattern is confirmed against kagent docs/source.

## End-to-end test (worker → management)

Only meaningful once the worker-side mechanism is in place. The
sequence:

```bash
TEST_AGENT=triage-agent           # worker-side agent that calls the escalation tool
kubectl port-forward -n kagent svc/kagent-controller 8083:8083 &
curl -s -X POST "http://localhost:8083/api/a2a/kagent/$TEST_AGENT/" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send",
       "params":{"message":{"role":"user",
                            "parts":[{"kind":"text",
                                      "text":"escalate to fleet: pod oomkilled in payments-prod"
                                    }]}}}' \
  | jq '.result.artifacts[0].parts[0].text, .error'
```

Trace expected: worker triage agent → escalation tool → cross-cluster
HTTPS to management gateway → Istio AuthorizationPolicy → agentgateway
data plane → URL rewrite → kagent-controller in management cluster →
fleet agent reply propagated back.

## Plan A reactivation (future-proofing)

If a future agentgateway release ships either A2A primitive:

1. Drop `service-a2a-fleet-agent.yaml`'s ReferenceGrant-only shape and
   add the Service facade + `appProtocol: agentgateway.dev/a2a`
   manifest from the earlier draft.
2. Add `backend.a2a.authorization` (or HTTP authz, whichever is
   supported) to `policy-a2a-fleet-agent.yaml` with the CEL
   `x-kagent-cluster` + `x-kagent-agent` check as defense in depth
   over the Istio identity gate.
3. Restore the CEL deny tests in "Authorization-failure tests" above.

## Rollback

```bash
kubectl delete -f policy-a2a-fleet-agent.yaml
kubectl delete -f route-a2a-fleet-agent.yaml
kubectl delete -f service-a2a-fleet-agent.yaml

# Optional — only if the Istio path additions are scoped to this PR set
# and you want to revert them too. Leave them in place if other demos
# are still using /llm/v1 or /openapi-mcp/argo.
# kubectl apply -f istio-authorization-policy.yaml
```

Plus on the worker: remove the escalation tool / MCP server registration
created during this PR. No kagent core resources are touched.
