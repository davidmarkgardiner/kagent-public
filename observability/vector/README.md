# Vector and Confluent Event Management

This folder captures a public-safe design note for using
[Vector](https://github.com/vectordotdev/vector) to improve the existing
Confluent Cloud observability pipeline.

The current proof of concept is documented in
[`../confluent-cloud-pipeline/README.md`](../confluent-cloud-pipeline/README.md).
It already separates Kubernetes events and Alertmanager events into distinct
Confluent topics, then uses Argo Events to trigger Argo Workflows:

```text
Alloy / Alertmanager bridge
  -> Confluent Cloud topics
  -> Argo Events Kafka EventSource
  -> Argo Events Sensor
  -> Argo Workflow
```

## Recommendation

Use Vector as an optional event normalization and noise-reduction layer around
Confluent. Do not replace Argo Sensors in the first pass.

Vector is strongest at event transport, parsing, remapping, filtering, and
lightweight deduplication. Argo Sensors are still the right boundary for
creating Argo Workflows from accepted events.

Recommended first shape for alerts:

```text
Alertmanager
  -> Confluent raw topic: alertmanager-events
  -> Vector in the management cluster
  -> Confluent normalized topic: alertmanager-events-triage
  -> Argo Events Kafka EventSource
  -> Argo Sensor
  -> Argo Workflow
```

Vector acts as both a Kafka consumer and Kafka producer. It reads the raw
Alertmanager event from Confluent, sorts it out into a smaller automation-ready
shape, and writes that cleaned event back to a separate Confluent topic. Argo
then watches the cleaned topic rather than the raw topic.

For Kubernetes events the same pattern can be added later:

```text
Alloy
  -> Confluent raw topic: k8s-events
  -> Vector in the management cluster
  -> Confluent normalized topic: k8s-events-triage
  -> Argo Events Kafka EventSource
  -> Argo Sensor
  -> Argo Workflow
```

## What Vector Adds

| Area | Current shape | Vector enhancement |
|---|---|---|
| Payload contracts | Alloy, Alertmanager, and Grafana-native Kafka payloads have different shapes. | Normalize each source into a common triage envelope before Argo sees it. |
| Filtering | Some filtering happens in Alloy, Sensor filters, or workflow code. | Move source-agnostic filtering into a visible event pipeline. |
| Deduplication | Current workflow-level dedupe uses a ConfigMap cache in Argo. | Suppress repeated events before they create workflows, using a `dedupe_key` contract. |
| Topic design | Raw source topics are routed directly to workflow triggers. | Keep raw topics for audit/replay and publish normalized topics for automation. |
| Workflow complexity | Workflows parse and classify incoming records. | Workflows receive a smaller, stable event shape. |

## Proposed Triage Envelope

Vector should publish normalized records with a small, explicit contract:

```json
{
  "schema_version": "observability.triage.v1",
  "source": "alloy|alertmanager|grafana",
  "cluster": "{{CLUSTER_NAME}}",
  "environment": "{{ENVIRONMENT}}",
  "severity": "critical|warning|info",
  "event_type": "kubernetes-event|prometheus-alert|grafana-alert",
  "reason": "CrashLoopBackOff",
  "object_kind": "Pod",
  "namespace": "default",
  "name": "example-pod",
  "dedupe_key": "{{CLUSTER_NAME}}:default:Pod:example:CrashLoopBackOff",
  "event_time": "2026-06-29T00:00:00Z",
  "raw_topic": "k8s-events",
  "raw": {}
}
```

The `raw` field should preserve the original payload for audit and debugging.
Downstream Argo Sensors should filter against the normalized top-level fields,
not nested source-specific payloads.

## Deduplication Position

Vector can reduce duplicate workflow submissions, but it should not be the only
durable dedupe layer for high-value incident handling.

Use Vector for:

- Short-window suppression of repeated noisy events.
- Contract-based dedupe keys before events reach Argo.
- Reducing duplicate Workflow objects and alert fatigue.

Keep workflow or downstream dedupe for:

- Durable 24-hour incident grouping.
- Human-in-the-loop remediation safety.
- Cases where a Vector restart should not reset incident memory.

## Argo Integration

Vector should not replace Argo Sensors initially.

Keep Argo Sensors because they provide the clear Kubernetes-native trigger
boundary:

- Kafka event accepted.
- Filter matched.
- Workflow object created.
- Rate limit and retry strategy applied.

Vector should replace the parsing and normalization work around the Sensor, not
the Sensor's job of submitting Workflows.

Target Argo change for the first alert spike:

```text
EventSource topic: alertmanager-events-triage
Sensor filters: body.schema_version, body.severity, body.event_type, body.source
Workflow parameter: normalized event payload
```

## Pros and Cons

### Pros

- Cleaner event contracts for multiple observability producers.
- Less workflow churn from duplicate events.
- Better raw-vs-normalized topic separation.
- Easier onboarding for Grafana-native Kafka payloads.
- More reusable Confluent event management pattern.

### Cons

- Adds another runtime to operate and monitor.
- Deduplication state is not a durable incident database.
- Requires careful schema ownership.
- May overlap with Alloy if deployed too broadly.
- Needs security review for Confluent credentials and namespace placement.

## Suggested Spike

1. Deploy Vector in the management cluster with read access to raw Confluent
   topics and write access to new triage topics.
2. Start with `alertmanager-events` because its payload contract is smaller
   than OTLP Kubernetes events.
3. Configure Vector to consume `alertmanager-events`, normalize each record,
   optionally suppress obvious duplicates, and publish `alertmanager-events-triage`.
4. Add one Argo EventSource/Sensor pair that consumes only
   `alertmanager-events-triage`.
5. Compare workflow count, duplicate suppression, and operator readability
   against the current direct Sensor path.
6. Only then repeat the pattern for `k8s-events`.

In short:

```text
Alertmanager sends raw events to Kafka.
Vector turns raw events into automation-ready events.
Argo acts only on the cleaned topic.
```

## Visual Explainer

Open [`vector-confluent-event-management.html`](vector-confluent-event-management.html)
in a browser for the visual version of this recommendation.

## Validation Notes

This folder is a design artifact only. It does not deploy Vector or change the
existing Confluent pipeline.

Before implementation:

- Validate the Vector Kafka source and sink settings against the target
  Confluent Cloud cluster.
- Validate any Vector Kubernetes manifests with the target cluster policy.
- Keep all real endpoints, API keys, tenant IDs, and private names out of this
  public repo.
