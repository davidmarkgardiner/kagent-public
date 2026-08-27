# kagent model failover through agentgateway

## Short answer

A kagent `Agent` references one `ModelConfig`; two separate `ModelConfig`
objects do not form an automatic fallback chain. Put both models behind one
agentgateway route and point the agent at one additional gateway-facing
`ModelConfig`.

```text
kagent Agent
  -> one ModelConfig: agentgateway-resilient
    -> one agentgateway URL
      -> priority group 0: primary model
      -> priority group 1: fallback model
```

For immediate fallback of the same request, configure both:

1. backend health eviction for provider `429` and `5xx` responses; and
2. route retry so the request that caused the eviction is attempted again.

This runbook assumes “49” means HTTP `429 Too Many Requests`. HTTP 49 is not a
standard response status.

## What to do with the two existing ModelConfigs

Keep the existing direct configs for isolated testing and manual rollback:

| Config | Purpose |
|---|---|
| `{{PRIMARY_DIRECT_MODELCONFIG}}` | Test or temporarily select the primary route directly |
| `{{FALLBACK_DIRECT_MODELCONFIG}}` | Test or temporarily select the fallback route directly |
| `agentgateway-resilient` | Normal agent route; agentgateway selects primary or fallback |

Do not expect kagent to move from the first object to the second at runtime.
The `Agent` schema has one `spec.declarative.modelConfig` value.

## 1. Verify the installed schemas

Agentgateway fields are version-sensitive. Run these against the cluster where
agentgateway is installed before rendering or applying manifests:

```bash
kubectl --context "{{AGENTGATEWAY_CONTEXT}}" explain \
  agentgatewaybackend.spec.ai.groups

kubectl --context "{{AGENTGATEWAY_CONTEXT}}" explain \
  agentgatewaypolicy.spec.backend.health

kubectl --context "{{AGENTGATEWAY_CONTEXT}}" explain \
  agentgatewaypolicy.spec.traffic.retry

kubectl --context "{{KAGENT_CONTEXT}}" explain \
  modelconfig.spec.openAI
```

Stop if `groups`, `backend.health`, `unhealthyCondition`, `eviction`, or
`traffic.retry` are absent. Do not substitute fields copied from a different
agentgateway release.

## 2. Put the models into ordered priority groups

Reuse the provider and authentication blocks from the two already-proven
`AgentgatewayBackend` resources. The first group is the primary; the second is
the fallback. The following example uses two OpenAI-compatible providers:

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayBackend
metadata:
  name: kagent-model-failover
  namespace: agentgateway-system
spec:
  ai:
    groups:
      - providers:
          - name: primary
            openai:
              model: "{{PRIMARY_MODEL}}"
            host: "{{PRIMARY_PROVIDER_HOST}}"
            port: 443
            policies:
              auth:
                secretRef:
                  name: "{{PRIMARY_PROVIDER_SECRET}}"
              tls:
                sni: "{{PRIMARY_PROVIDER_HOST}}"
      - providers:
          - name: fallback
            openai:
              model: "{{FALLBACK_MODEL}}"
            host: "{{FALLBACK_PROVIDER_HOST}}"
            port: 443
            policies:
              auth:
                secretRef:
                  name: "{{FALLBACK_PROVIDER_SECRET}}"
              tls:
                sni: "{{FALLBACK_PROVIDER_HOST}}"
```

Provider names must be unique. If the fallback is Azure OpenAI, Anthropic, or
another supported provider, use its validated provider block rather than
forcing it into the `openai` example. Do not commit provider credentials.

## 3. Expose one route to kagent

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: kagent-model-failover
  namespace: agentgateway-system
spec:
  parentRefs:
    - name: "{{AGENTGATEWAY_GATEWAY_NAME}}"
      namespace: agentgateway-system
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /llm/v1
      backendRefs:
        - name: kagent-model-failover
          namespace: agentgateway-system
          group: agentgateway.dev
          kind: AgentgatewayBackend
```

If `/llm/v1` is already in use, update the existing backend and route rather
than creating a competing path.

## 4. Evict an unhealthy primary

The health policy targets the `AgentgatewayBackend`, not the `HTTPRoute`.
`consecutiveFailures: 1` gives the requested immediate behavior: the first
qualifying response evicts the primary so a retry can select the next group.

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayPolicy
metadata:
  name: kagent-model-failover-health
  namespace: agentgateway-system
spec:
  targetRefs:
    - group: agentgateway.dev
      kind: AgentgatewayBackend
      name: kagent-model-failover
  backend:
    health:
      unhealthyCondition: "response.code == 429 || response.code >= 500"
      eviction:
        duration: 30s
        consecutiveFailures: 1
        restoreHealth: 100
```

For a less sensitive production policy, increase `consecutiveFailures` to 2 or
3. That reduces flapping, but the first one or two requests can fail before the
primary is evicted. A provider `Retry-After` header on a 429 can override the
configured eviction duration.

## 5. Retry the request that triggered eviction

Eviction changes selection for later attempts. Retry is what lets the same
client request reach the fallback after a 429 or 503 from the primary.

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayPolicy
metadata:
  name: kagent-model-failover-retry
  namespace: agentgateway-system
spec:
  targetRefs:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      name: kagent-model-failover
  traffic:
    timeouts:
      request: 120s
    retry:
      attempts: 1
      backoff: 100ms
      codes:
        - 429
        - 500
        - 502
        - 503
        - 504
```

`attempts: 1` means one retry after the initial request. Add a provider-specific
status such as 529 only after confirming that the installed CRD accepts it and
the provider actually returns it. Do not retry authentication, authorization,
or invalid-request responses such as 400, 401, or 403.

## 6. Point kagent at the resilient route

Create a third `ModelConfig` for the combined route. Keep its timeout longer
than agentgateway's total request timeout.

```yaml
apiVersion: kagent.dev/v1alpha2
kind: ModelConfig
metadata:
  name: agentgateway-resilient
  namespace: kagent
spec:
  provider: OpenAI
  model: "{{PRIMARY_MODEL}}"
  apiKeySecret: "{{KAGENT_GATEWAY_CLIENT_SECRET}}"
  apiKeySecretKey: api-key
  openAI:
    baseUrl: "https://{{AGENTGATEWAY_HOSTNAME}}/llm/v1"
    timeout: 150
```

The client secret authenticates kagent to the gateway. Provider credentials
stay at agentgateway. If the gateway does not require client authentication,
follow the approved placeholder-secret convention for the installed kagent
version rather than putting a provider key in the `ModelConfig`.

Move one canary agent first:

```bash
kubectl --context "{{KAGENT_CONTEXT}}" patch agent \
  "{{CANARY_AGENT}}" -n kagent --type merge \
  -p '{"spec":{"declarative":{"modelConfig":"agentgateway-resilient"}}}'

kubectl --context "{{KAGENT_CONTEXT}}" wait \
  agent/"{{CANARY_AGENT}}" -n kagent \
  --for=condition=Ready --timeout=3m
```

Do not replace `default-model-config` or patch every agent until the canary has
proved both paths.

## Failure behavior

| Failure | Expected behavior |
|---|---|
| Upstream 429 | Primary is evicted; route retry selects fallback |
| Upstream 503 or listed 5xx | Primary is evicted; route retry selects fallback |
| DNS, connection refusal, or pre-response connection failure | Retried; validate that the installed release records and evicts the failed provider |
| Gateway-local rate-limit 429 | No provider fallback; the request was rejected before backend selection |
| 400, 401, or 403 | Returned to the caller; fix request or authentication instead of hiding it with fallback |
| HTTP 200 followed by a mid-stream disconnect | Do not assume transparent failover after tokens have been emitted |
| Primary and fallback both fail | Return an error after the bounded retry; do not loop indefinitely |

The fallback must support the features the agent uses, including tool calling,
structured output, context length, and any required model-specific parameters.
A successful text-only fallback is not proof that a tool-using kagent agent is
compatible.

## 7. Validate before rollout

### Schema and admission

Render the placeholders into a temporary copy, then run server-side dry-run:

```bash
kubectl --context "{{AGENTGATEWAY_CONTEXT}}" apply --dry-run=server \
  -f "{{RENDERED_AGENTGATEWAY_MANIFEST}}"

kubectl --context "{{KAGENT_CONTEXT}}" apply --dry-run=server \
  -f "{{RENDERED_MODELCONFIG_MANIFEST}}"
```

### Direct route proof

Use an isolated test backend whose primary deliberately returns 429 or 503. Do
not exhaust a real provider quota or stop a shared model. One client call must
produce this receipt:

1. primary attempt returned the injected 429 or 503;
2. the primary was evicted;
3. one retry selected the fallback provider;
4. the final client response was 200;
5. response metadata, gateway logs, or metrics identify the fallback model;
6. no credential or provider error body appears in the saved evidence.

### kagent proof

Invoke the canary through `scripts/kagent-a2a-invoke.sh`. Test both a plain
response and a real allow-listed MCP tool call. Record the terminal A2A result,
the selected provider/model, gateway attempt count, and whether fallback was
engaged.

Do not call the setup proven from `ModelConfig` Accepted/Agent Ready alone.
Those conditions do not prove that either provider can complete a request.

## Rollback

Patch the canary back to the known-good direct config:

```bash
kubectl --context "{{KAGENT_CONTEXT}}" patch agent \
  "{{CANARY_AGENT}}" -n kagent --type merge \
  -p '{"spec":{"declarative":{"modelConfig":"{{PRIMARY_DIRECT_MODELCONFIG}}"}}}'
```

After confirming no agents reference `agentgateway-resilient`, remove only the
new failover `ModelConfig`, policies, route, and backend. Preserve the two direct
configs for diagnosis unless their owners approve removal.

## Repository starting points

- `backend-llm-failover.yaml` already contains priority groups and route retry.
- `modelconfig-llm-failover.yaml` already points kagent at `/llm/v1`.
- `FAILOVER-DEMO.md` contains the existing isolated failure-test approach.

The missing gate in older installations is often the backend health/eviction
policy in section 4. Priority groups without eviction do not provide reliable
cross-group failover.

## Upstream references

- [agentgateway model failover](https://agentgateway.dev/docs/kubernetes/latest/llm/failover/)
- [agentgateway request retries](https://agentgateway.dev/docs/kubernetes/main/resiliency/retry/retry/)
- [kagent API reference](https://kagent.dev/docs/kagent/resources/api-ref/)
- [kagent with agentgateway](https://kagent.dev/docs/kagent/supported-providers/byo-agentgateway/)
