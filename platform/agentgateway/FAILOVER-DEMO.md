# Failover demo — `/llm/v1` local-primary → Azure OpenAI fallback

Companion runbook for `backend-llm-failover.yaml`. Designed to be safe on
clusters that share KubeAI / vLLM with real agents. Read PR 0
(`DEMO-SCHEMA-GATE.md`) before any apply.

## Decision tree (set this before you run anything)

`AgentgatewayBackend.spec.ai.groups[]` confirmed to accept a mix of
`openai` and `azureopenai` providers in one backend?

| Verdict (from PR 0) | Pattern to use |
|---|---|
| supported | Apply `backend-llm-failover.yaml` as written: one backend, two priority groups. |
| not supported | Apply two backends (`backend-kubeai.yaml`, `backend-azure-openai.yaml`) and use the **route-level fallback pattern** in §5 of this runbook. |

Do not silently fall back to one provider — the demo's claim is that the
gateway is the failover decision point, so the failover surface must be
visible in the manifest.

## 1. Apply

```bash
kubectl apply --dry-run=server -f backend-llm-failover.yaml
kubectl apply -f backend-llm-failover.yaml
kubectl get agentgatewaybackend llm-failover-backend -n agentgateway-system -o yaml
kubectl get httproute llm-failover-route -n agentgateway-system -o yaml
```

Wait for the HTTPRoute and AgentgatewayBackend to report Accepted/Programmed.

## 2. Happy-path probe (local primary)

```bash
kubectl port-forward -n agentgateway-system svc/ai-gateway 8080:80 &
curl -s -X POST http://localhost:8080/llm/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<local-model>","messages":[{"role":"user","content":"ping"}],"max_tokens":20}' \
  | jq '.choices[0].message.content, .model'
```

Expected:
- 200 OK, response from the local KubeAI model.
- `agentgateway_gen_ai_client_token_usage_*` increments under the local
  `gen_ai_request_model` label.

## 3. Rate-limit fallback probe

The production goal is "second model if the primary model is rate-limited".
Do not prove that by exhausting a real provider quota. Use a temporary provider
or mock endpoint that returns HTTP 429, then confirm the fallback group serves a
200 response.

Minimum proof:

```bash
# Use a dedicated demo backend or a temporary mock primary that returns 429.
# Then call the same kagent-facing route.
curl -s -o /tmp/llm-failover.out -w "%{http_code}\n" \
  -X POST http://localhost:8080/llm/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"any","messages":[{"role":"user","content":"ping"}],"max_tokens":20}'

cat /tmp/llm-failover.out | jq '.model, .choices[0].message.content'
```

Expected:
- final client response is HTTP 200, not 429.
- fallback provider/model appears in token or request metrics.
- `agentgateway_requests_total{route=~".*llm.*",status="429"}` may show the
  primary attempt if the installed version records per-attempt status. If not,
  use gateway logs and provider labels to prove the fallback.

If the final response remains 429, first check whether it is the gateway's own
`rateLimit.local` policy. Gateway-local 429s occur before backend selection and
will not trigger provider fallback; raise that limit or split local overload
protection from provider-quota fallback. If it is an upstream provider 429 and
the gateway still does not select the fallback group, check whether the
installed CRD supports `AgentgatewayPolicy.spec.backend.health`; the
`proxmox-k8s` CRD checked on 2026-06-03 did not accept that field, so the
applyable demo relies on route retry plus priority groups.

## 4. Safe failover trigger options

Pick the **least disruptive** option that actually exercises the fallback
group. The first option in this list is the default — only use the later
options with explicit approval.

### 4a. Temporary bad-host overlay (default, no impact to shared models)

Patch the primary group's `host` to a name that won't resolve. The
fallback group should serve the request instead, with zero impact on real
KubeAI traffic on the cluster.

```bash
kubectl patch agentgatewaybackend llm-failover-backend -n agentgateway-system --type=json \
  -p='[{"op":"replace","path":"/spec/ai/groups/0/providers/0/host","value":"kubeai.kubeai.svc.cluster.local.invalid"}]'

# Then re-run the happy-path probe — expect 200 from the Azure deployment.
curl -s -X POST http://localhost:8080/llm/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"any","messages":[{"role":"user","content":"ping"}],"max_tokens":20}' \
  | jq '.model'

# Revert when done:
kubectl patch agentgatewaybackend llm-failover-backend -n agentgateway-system --type=json \
  -p='[{"op":"replace","path":"/spec/ai/groups/0/providers/0/host","value":"kubeai.kubeai.svc.cluster.local"}]'
```

### 4b. Dedicated test backend (no shared model touched)

If 3a is not acceptable in your environment (e.g. webhook rejects the
malformed host), create a second `AgentgatewayBackend` named
`llm-failover-backend-demo` that points at an intentionally-broken host
and a second `HTTPRoute` named `llm-failover-route-demo` at `/llm/v1-demo`.
Run the probe against `/llm/v1-demo`. Delete both when done.

### 4c. Scale shared KubeAI to zero — **requires explicit approval**

Per the plan's non-negotiables, do not run this without authorization.
Scaling shared KubeAI to zero affects every agent on the cluster.

## 5. Route-level fallback pattern (only if §0 verdict is "not supported")

If the installed CRD does not allow mixing provider types in one backend:

1. Keep `backend-kubeai.yaml` and `backend-azure-openai.yaml` as separate
   backends.
2. Add a single `HTTPRoute` at `/llm/v1` with **two** `backendRefs` where
   the local backend has weight 100 and the Azure backend has weight 0.
3. Wire Envoy retry behavior via `AgentgatewayPolicy.spec.traffic.retry`
   (verify the field exists with `kubectl explain`) so 5xx and connect
   errors retry against the Azure backend.
4. Document the route-level pattern in this file under "Pattern variant".

Do not pretend it's group-level failover when it isn't — the runbook and
README must describe whichever pattern is actually applied.

## 6. Verifying failover from metrics

Wait until step 3 has driven real traffic; then look for both providers
appearing under `gen_ai_request_model`:

```promql
sum by (gen_ai_request_model, gen_ai_system) (
  rate(agentgateway_gen_ai_client_token_usage_count[5m])
)
```

Once you have observed labels for both the local and Azure providers,
edit `monitoring.yaml` to add a tightly-labelled `LLMFailoverEngaged`
alert. **Do not** add the alert before observing the actual labels — the
plan explicitly forbids guessing label names.

## 7. Rollback

```bash
kubectl delete -f backend-llm-failover.yaml
# kagent ModelConfigs still pointing at /azure/v1 or /openai/v1 are
# unaffected — only the /llm/v1 endpoint goes away.
```
