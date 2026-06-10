# Qwen Capacity Control Front Sheet

## TL;DR

Do not create duplicate GPT-4 versions of every kagent agent yet. First measure
how much Qwen traffic the current work gateway and provider can actually handle,
then cap Argo/Kafka/Alloy-driven work below that number.

Current recommendation:

```text
1. Benchmark concurrent calls to the kagent A2A API, starting with 20 in flight.
2. Confirm each call reaches A2A state completed, not just HTTP 200.
3. Pick a safe operating limit from the first failing concurrency level.
4. Enforce that limit before workflows call kagent/Qwen.
5. Alert on 429s, resets, timeouts, missing completions, and queue backlog.
6. Revisit automatic GPT-4 failover only after gateway runtime/provider blockers are fixed.
```

## Why This Scope

The work-stage result says automatic backend failover is blocked:

- Qwen allows only one TLS session per source IP today, so a second backend or
  canary can be reset immediately.
- Per-provider authentication inside AI provider groups is accepted by CRD
  shape, but not implemented by the runtime build in use.
- Qwen needs service-principal token auth and GPT-4 needs UAMI token auth, so a
  single automatic failover backend is not reliable until runtime support exists.

That means the lowest-risk next step is not agent duplication. It is capacity
management: understand Qwen's real ceiling and avoid sending more work than the
system can complete.

## Capacity Definition

Measure the limit that matters to users:

```text
safe_qwen_concurrency = highest concurrency level where:
  A2A completed_rate >= 99%
  success_rate >= 99%
  HTTP 429 count == 0
  reset/timeout count == 0
  p95 latency remains inside the kagent workflow deadline
  no kagent/A2A completion failures are observed
```

Then set the production limit lower than the measured ceiling:

```text
configured_limit = floor(safe_qwen_concurrency * 0.7)
```

Use 70 percent as the first operating point. Raise it only after a clean week of
metrics, not after one successful benchmark run.

## What To Give The Work Agent

Use these files in order:

| File | Purpose |
|---|---|
| `81-QWEN-CAPACITY-BENCH-RUNBOOK.md` | Exact benchmark plan and evidence template. |
| `bench-kagent-a2a.sh` | Primary single-level benchmark against the kagent A2A API; defaults to 20 concurrent calls. |
| `capacity-sweep-kagent-a2a.sh` | Primary repeated concurrency sweep against kagent. |
| `capacity-sweep-agentgateway.sh` | Lower-level diagnostic sweep through `/llm/v1` if kagent-facing tests fail. |
| `bench-agentgateway.sh` | Single gateway-level benchmark with JSON output. |
| `83-HOMELAB-KAGENT-A2A-EVIDENCE.md` | Home-lab evidence showing the harness and baseline failure interpretation. |
| `82-WORKFLOW-RATE-LIMITING-PATTERNS.md` | Argo/Kafka/Alloy dedupe and throttle patterns. |
| `40-observability-alerts.yaml` | Prometheus alerts for 429s, latency, gateway errors, and workflow failures. |
| `50-loki-log-rules.yaml` | Loki log alerts for rate-limit/reset/non-completion signals. |
| `70-grafana-queries.md` | Explore/dashboard queries for Qwen saturation. |

## Control Points

Apply controls as close to the source of work as possible:

| Layer | Control | Reason |
|---|---|---|
| Kafka/Event Hub | partitioning and consumer concurrency | Prevents burst fan-out before Argo starts workflows. |
| Argo Events Sensor | trigger `rateLimit` and dedupe key | Stops repeated alerts from creating repeated agent jobs. |
| Argo Workflow | `parallelism`, mutex/semaphore, retry policy | Caps active model calls and keeps retries bounded. |
| kagent invocation | one model config for Qwen during capacity phase | Avoids multiplying agent definitions before capacity is known. |
| agentgateway | local route rate limit | Last-line overload protection, not the primary queue control. |
| Alloy | alert/log normalization and forwarding rate limit | Keeps telemetry-triggered workflows from amplifying incidents. |

## Completion Criteria

- kagent capacity sweep results are attached with CSV and per-level JSON summaries.
- A2A state `completed` is used as the success signal, not only HTTP `200`.
- The chosen `configured_limit` is documented and lower than the first failing
  concurrency level.
- Argo/Kafka/Alloy controls are configured so generated workflows cannot exceed
  `configured_limit`.
- Grafana can show Qwen request rate, 429s, resets/timeouts, p95 latency,
  workflow failures, and queue backlog.
- Alerting fires for sustained 429s or non-completion before users notice.

## Decision Point

If Qwen capacity is stable and adequate, do not implement full GPT-4 failover.
Keep GPT-4 as a manual or workflow-level exception path for critical incidents.

If Qwen capacity is too low, choose one:

- Ask the provider team to raise TLS/session and request limits.
- Add workflow-level GPT-4 fallback for read-only planning tasks only.
- Wait for an agentgateway runtime build that proves per-provider auth and
  health/failover behavior.
