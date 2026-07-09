# OpenAI-Compatible External Providers

This POC connects kagent to Kimi, Z.AI GLM, and MiniMax through agentgateway.
The key point from upstream kagent is that `ModelConfig` already supports
`provider: OpenAI` with a custom `openAI.baseUrl`, so these providers do not
need native kagent provider implementations as long as the exposed endpoint is
OpenAI-compatible.

## Recommended Path

Use this path for the POC:

```text
kagent Agent
  -> kagent ModelConfig provider=OpenAI
  -> agentgateway service route
  -> AgentgatewayBackend
  -> external OpenAI-compatible provider
```

This keeps provider secrets, TLS, request timeout, telemetry, rate limit, and
future failover policy at the gateway layer instead of spreading them across
individual agent configs.

## Files

| File | Cluster | Purpose |
| --- | --- | --- |
| `backend-openai-compatible-external-models.yaml` | agentgateway cluster | Kimi, Z.AI GLM, and MiniMax `AgentgatewayBackend` plus `HTTPRoute` resources. |
| `modelconfig-openai-compatible-external-models.yaml` | kagent cluster | kagent `ModelConfig` objects pointing at the agentgateway routes. |

## Provider Mapping

| Provider | Gateway route | Upstream path prefix | Model |
| --- | --- | --- | --- |
| Kimi | `/kimi/v1` | `/coding/v1` | `kimi-for-coding` |
| Z.AI GLM | `/zai/v1` | `/api/paas/v4` | `glm-4.6` |
| MiniMax | `/minimax/v1` | `/v1` | `MiniMax-M2.7` |

## Verification Status

As of the 2026-07-09 smoke work, Kimi is the only route proven through the
agentgateway and kagent A2A path. Z.AI GLM and MiniMax are included as
OpenAI-compatible candidates, but must pass the low-token route smoke before
being used for triage agents.

The provider prefix is set in the `HTTPRoute` URL rewrite instead of
`AgentgatewayBackend.spec.ai.provider.path`. That shape works with the older
agentgateway CRD installed on the Proxmox POC cluster and remains valid for the
newer CRD shape.

## Secret Setup

Load provider keys locally and create Kubernetes secrets without printing the
values:

```bash
set -a
. /path/to/provider.env
set +a

kubectl -n agentgateway-system create secret generic kimi-api-secret \
  --from-literal=Authorization="Bearer ${KIMI_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n agentgateway-system create secret generic zai-api-secret \
  --from-literal=Authorization="Bearer ${ZAI_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n agentgateway-system create secret generic minimax-api-secret \
  --from-literal=Authorization="Bearer ${MINIMAX_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n kagent create secret generic agentgateway-client-key \
  --from-literal=api-key="not-required" \
  --dry-run=client -o yaml | kubectl apply -f -
```

The `agentgateway-client-key` value is only a kagent client placeholder when
agentgateway owns the provider auth. Replace it if the gateway requires a real
client credential.

## Low-Token Smoke

Port-forward the gateway service, then probe each route with a tiny completion:

```bash
kubectl -n agentgateway-system port-forward svc/ai-gateway 8081:8081

curl -sS http://127.0.0.1:8081/kimi/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"kimi-for-coding","messages":[{"role":"user","content":"Reply with OK only."}],"max_tokens":32}'

curl -sS http://127.0.0.1:8081/zai/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"glm-4.6","messages":[{"role":"user","content":"Reply with OK only."}],"max_tokens":5,"temperature":0}'

curl -sS http://127.0.0.1:8081/minimax/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"MiniMax-M2.7","messages":[{"role":"user","content":"Reply with OK only."}],"max_tokens":5,"temperature":0}'
```

Expected result for a working route is HTTP 200 and a short response. HTTP 401
or 403 usually means secret/auth shape is wrong. HTTP 429 from the provider
means the route reached the provider but the account is out of quota or balance.

## Rollout Guardrail

Patch one smoke-test Agent first:

```bash
kubectl -n kagent patch agent {{SMOKE_AGENT_NAME}} --type merge \
  -p '{"spec":{"modelConfig":"agentgateway-kimi"}}'
```

Run the alert-triage smoke with low token settings before changing
`default-model-config`. If MiniMax emits provider-specific thinking tags,
prefer a gateway-side proxy or route-specific prompt policy before using it for
triage summaries.
