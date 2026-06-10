# Workflow Rate-Limiting Patterns

## Position

Do not duplicate every namespace/networking/security agent just to add a second
model. During the Qwen capacity phase, keep one Qwen model path and control how
many jobs can reach it.

## Recommended Flow

```text
Alert/log/event -> Alloy/Kafka normalization -> Argo Events Sensor
  -> dedupe key check
  -> rate-limited Workflow creation
  -> Argo semaphore/mutex controls active kagent A2A calls
  -> kagent invocation through /api/a2a/<namespace>/<agent>/
  -> completion/failure metric and log
```

## Dedupe Key

Use a stable key before creating a workflow:

```text
dedupe_key = cluster + namespace + alertname + affected_resource + severity
dedupe_window = 10m to 30m
```

For noisy rate-limit events, include the route/backend but not a timestamp:

```text
qwen_capacity_key = cluster + route + backend + "qwen-capacity"
```

## Argo Events Sensor Control

Use trigger-level `rateLimit`. In this repo's Argo Events examples, `rateLimit`
belongs on the trigger object, not under `template`.

Shape:

```yaml
triggers:
  - template:
      name: qwen-triage-workflow
      argoWorkflow:
        operation: submit
        source:
          resource:
            apiVersion: argoproj.io/v1alpha1
            kind: Workflow
            metadata:
              generateName: qwen-triage-
            spec:
              workflowTemplateRef:
                name: qwen-triage-template
    rateLimit:
      unit: Minute
      requestsPerUnit: "{{CONFIGURED_QWEN_WORKFLOWS_PER_MINUTE}}"
```

## Argo Workflow Control

Cap active LLM work inside the workflow layer as well. Prefer a semaphore where
available; use workflow `parallelism` as a basic guard.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: qwen-triage-template
  namespace: argo
spec:
  parallelism: "{{CONFIGURED_QWEN_ACTIVE_CALLS}}"
  synchronization:
    semaphore:
      configMapKeyRef:
        name: qwen-capacity-limits
        key: active-calls
  entrypoint: triage
  templates:
    - name: triage
      steps:
        - - name: call-kagent-qwen
            template: call-kagent-qwen
```

Example semaphore ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: qwen-capacity-limits
  namespace: argo
data:
  active-calls: "{{CONFIGURED_KAGENT_A2A_ACTIVE_CALLS}}"
```

## Kafka/Event Hub Control

Kafka is the cleanest place to prevent bursts from becoming many workflows.

Recommended controls:

- Use a Qwen triage topic or route key for model-triggering events.
- Set consumer concurrency to the measured `configured_limit`.
- Partition by the dedupe key so repeated events for the same incident are
  ordered and can be collapsed.
- Keep retries bounded and delayed; do not immediately re-enqueue `429` events.
- Track consumer lag as a backpressure signal.

Capacity rule:

```text
max_active_consumers_for_kagent_a2a <= configured_limit
```

If multiple consumers can create workflows, divide the limit across them.

## Alloy Control

Alloy should normalize and forward telemetry; it should not amplify a storm.

Use Alloy for:

- filtering only agentgateway/kagent/Argo capacity signals;
- adding route/backend/model labels where possible;
- forwarding to Kafka/Event Hub or Alertmanager with stable labels;
- reducing duplicate logs before they become workflow triggers.

Avoid using Alloy as the only rate limiter for model calls. Alloy can slow or
shape telemetry, but Argo/Kafka still need hard concurrency limits.

## Retry Policy

For Qwen capacity events:

```text
429 or reset:
  do not retry immediately
  sleep/backoff at least 60s
  retry no more than 2 times
  keep the same dedupe key
  alert if still failing after retry budget
```

For read-only triage:

```text
timeout:
  one retry is acceptable if the queue is below configured limit
```

For write-capable remediation:

```text
never auto-retry blindly
require idempotency or HITL approval
```

## Alerts To Wire

Alert when:

- any Qwen 429s happen for more than 2 minutes;
- p95 latency approaches the workflow deadline;
- gateway timeouts/resets increase;
- Kafka consumer lag keeps growing for Qwen triage topic;
- Argo queued workflows exceed the configured active-call limit;
- kagent/A2A call does not complete;
- agentgateway metrics disappear.

## Acceptance Criteria

- Benchmark-derived `configured_limit` exists in the work ticket.
- Kafka/Argo cannot create more than `configured_limit` active Qwen calls.
- Dedupe key prevents repeated alerts from creating repeated workflows.
- Grafana shows traffic, queue, and workflow behavior on the same time range.
- Alerts fire on 429s and non-completion before user-facing impact grows.
