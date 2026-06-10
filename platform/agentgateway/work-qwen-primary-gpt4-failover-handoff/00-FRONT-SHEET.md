# Qwen Primary / GPT-4 Secondary Failover Handoff

## TL;DR

This file is retained as the original automatic-failover handoff. The current
recommended path is now [`80-QWEN-CAPACITY-CONTROL.md`](80-QWEN-CAPACITY-CONTROL.md):
measure Qwen capacity, then throttle/dedupe Argo/Kafka/Alloy workflows before
they exceed that capacity.

Do not duplicate every kagent agent just to work around failover yet. Automatic
gateway failover is blocked in the work stage until Qwen TLS-session limits and
runtime per-provider authentication support are resolved.

Original target pattern:

```text
kagent -> agentgateway /llm/v1 -> Qwen primary -> GPT-4 secondary
```

Do not make every kagent agent decide between models. Put model selection,
retry, telemetry, and failover at agentgateway.

## Work Auth Shape

The target environment has two LLM services:

| Priority | Service | Model | Auth |
|---|---|---|---|
| Primary | OpenAI-as-a-service | Qwen | Service principal secret -> token refresher Job -> Kubernetes Secret |
| Secondary | AI-as-a-service | GPT-4 | UAMI -> token refresher Job -> Kubernetes Secret |

Both token refreshers write a Secret with this exact shape:

```yaml
stringData:
  Authorization: "Bearer <access-token>"
```

agentgateway then uses per-provider `secretRef` auth for both providers. This
keeps one priority-group `AgentgatewayBackend` possible even when native UAMI
auth is not available per provider in the installed CRD.

## Folder Contents

| File | Purpose |
|---|---|
| `00-FRONT-SHEET.md` | This handoff summary. |
| `10-token-refreshers.yaml` | Qwen service-principal token refresher and GPT-4 UAMI token refresher. |
| `20-agentgateway-failover-route.yaml` | `/llm/v1` route, Qwen primary backend group, GPT-4 fallback backend group, retry policy. |
| `30-kagent-modelconfig.yaml` | kagent `ModelConfig` pointed at `/llm/v1`. |
| `40-observability-alerts.yaml` | Prometheus alerts for 429s, gateway errors, slow route, and triage workflow failures. |
| `50-loki-log-rules.yaml` | Managed-Loki rule-sync alerts for rate-limit logs and A2A non-completion logs. |
| `60-mock-429-primary.yaml` | Temporary mock primary backend that always returns HTTP 429 for failover testing. |
| `70-grafana-queries.md` | PromQL/LogQL panels to add or use in Explore. |
| `schema-gate.sh` | Checks installed CRD support and runs server-side dry-run. |
| `smoke-failover.sh` | Simulates bad-host and mock-429 failover safely on the dedicated failover backend. |
| `bench-agentgateway.sh` | Bench test direct `/llm/v1` gateway capacity with concurrent requests. |
| `bench-kagent-a2a.sh` | Bench test kagent A2A calls with concurrent agent invocations. |
| `REVIEW-FEEDBACK.md` | Review notes and live-validation risks to close in the work cluster. |

## Implementation Order

1. Replace every `{{PLACEHOLDER}}` value in this folder.
2. Run `./schema-gate.sh`.
3. Apply `10-token-refreshers.yaml` to the management cluster.
4. Run both token refresh jobs once and confirm both token Secrets exist.
5. Apply `20-agentgateway-failover-route.yaml` to the management cluster.
6. Apply `30-kagent-modelconfig.yaml` to the kagent worker cluster.
7. Patch one low-risk kagent agent to `agentgateway-qwen-primary-gpt4-fallback`.
8. Run `./smoke-failover.sh --mode bad-host`.
9. Run `./smoke-failover.sh --mode mock-429`.
10. Run sequential and concurrent bench tests.
11. Apply observability files once the metrics/log rule-sync path is confirmed.

## Completion Criteria

- `kubectl apply --dry-run=server` passes for manifests in the target clusters.
- Qwen token refresher writes `qwen-primary-token`.
- GPT-4 UAMI token refresher writes `gpt4-secondary-token`.
- Normal `/llm/v1/chat/completions` returns from Qwen.
- Bad-host failover test returns HTTP 200 from the fallback path.
- Mock-429 test returns HTTP 200 from the fallback path or documents the installed
  agentgateway version limitation.
- The work-cluster agentgateway version is confirmed to advance from primary to
  fallback on retryable upstream errors. The local upstream clone has an e2e test
  for health-eviction failover, but the local validation CRD did not expose
  backend health policy.
- `agentgateway_gen_ai_client_token_usage_*` shows model traffic through the gateway.
- Grafana shows 429s, route latency, model request rate, token usage, and workflow failures.
- kagent triage workflows produce a clear alert when an A2A call fails or does not complete.

## Important Caveat

On the local `proxmox-k8s` validation cluster checked on 2026-06-03,
`AgentgatewayPolicy.spec.backend.health` was not accepted by the installed CRD.
That means this bundle does not rely on backend health eviction. It relies on
priority groups plus route retry on `429, 500, 502, 503, 504`.

If the work cluster has a newer CRD that supports backend health policy, add a
version-gated health policy for:

```text
response.code == 429 || response.code >= 500
```

Do not assume that field exists. Validate it first.
