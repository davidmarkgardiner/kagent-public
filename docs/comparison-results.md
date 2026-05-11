# Comparison Results

## Current Status

The repository contains manifests and runbooks for both paths. MIL-28 captured
live end-to-end evidence for the Redpanda Kafka path on `proxmox-k8s`; direct
webhook path measurements remain pending in this workspace.

Do not treat this document as proof of production behavior until both paths are
validated under the same alert load and Alertmanager timing settings.

## Summary

| Dimension | Redpanda Kafka path | Direct webhook path |
|---|---|---|
| Latency | MIL-28 observed Alertmanager API POST at `12:22:54Z`, bridge delivery/EventSource/Sensor/consumer at `12:23:16Z`. This includes Alertmanager grouping behavior, not just Kafka transit. | Pending measurement. Expected to be lower because Alertmanager posts straight to the EventSource. |
| Reliability | Confirmed Kafka consumer group `kagent-alertmanager-poc` reached `TOTAL-LAG 0` after three test records. Redpanda can absorb short Sensor/EventSource outages after the bridge accepts the alert. | Simpler but depends on Alertmanager retry behavior and EventSource availability at delivery time. |
| Payload fidelity | Confirmed. Consumer pod `kafka-alert-consumer-7ppgf` logged `pod_name` and full parsed Alertmanager JSON under `alert_json`. | Native Alertmanager body is passed directly to Argo Events with no bridge envelope. |
| Operations overhead | Higher: Redpanda, topic bootstrap, bridge deployment, Kafka EventSource, and broker health checks. | Lower: one webhook EventSource, explicit Service, Sensor, and consumer pod trigger. |
| Best fit | Staging where broker parity, replay, or later Event Hub replacement matters. | Fast POC, lower maintenance, and environments where transient loss can be handled by Alertmanager retry. |

## Decision Frame

Start staging with both paths enabled long enough to capture comparable
evidence. If staging only needs proof that Alertmanager payloads can trigger a
consumer pod, the direct webhook path should be the default. Keep the Redpanda
path when the follow-on architecture needs broker semantics or Kafka-compatible
Event Hub parity.

## Measurement Plan

For each path, send the same sanitized Alertmanager payload three times and
record:

- POST timestamp from the sender.
- EventSource dispatch timestamp from EventSource logs.
- Sensor trigger timestamp from Sensor logs.
- Consumer `consumed_at` timestamp from pod logs.
- Consumer `pod_name`, `alert_count`, and `payload_keys`.
- Delivery outcome: success, retry, duplicate, malformed, or missed.

Use this table during staging:

| Run | Path | POST time | EventSource time | Sensor time | Consumer time | Outcome | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Redpanda Kafka | Pending | Pending | Pending | Pending | Pending |  |
| 2 | Redpanda Kafka | 2026-05-11T12:22:54Z | 2026-05-11T12:23:16Z | 2026-05-11T12:23:16Z | 2026-05-11T12:23:16.687680Z | Success | Alertmanager grouped two active synthetic alerts. Evidence: `docs/mil-28-path-a-evidence.md`. |
| 3 | Redpanda Kafka | Pending | Pending | Pending | Pending | Pending |  |
| 1 | Direct webhook | Pending | Pending | Pending | Pending | Pending |  |
| 2 | Direct webhook | Pending | Pending | Pending | Pending | Pending |  |
| 3 | Direct webhook | Pending | Pending | Pending | Pending | Pending |  |

## Payload Fidelity Checks

The consumer log must prove:

- `pod_name` is populated from the alert payload or bridge envelope.
- `alert_count` matches the Alertmanager payload.
- `payload_keys` includes the standard Alertmanager envelope keys.
- The full Alertmanager JSON remains parseable by the consumer.

## Reliability Checks

Redpanda Kafka path:

- Stop the Sensor briefly, send a payload, restart the Sensor, and confirm the
  event is still consumed from the topic.
- Restart the bridge and confirm Alertmanager or curl receives clear failures
  during downtime.
- Confirm duplicate behavior after retry.

Direct webhook path:

- Stop the EventSource briefly and confirm Alertmanager retry behavior in the
  target Alertmanager configuration.
- Restart the Sensor and confirm new events trigger consumer pods.
- Confirm duplicate behavior after retry.

## References

- Argo Events webhook EventSource documentation:
  https://argoproj.github.io/argo-events/eventsources/setup/webhook/
- Argo Events trigger parameterization documentation:
  https://argoproj.github.io/argo-events/tutorials/02-parameterization/
- Argo Events Kubernetes object trigger documentation:
  https://argoproj.github.io/argo-events/sensors/triggers/k8s-object-trigger/
- Argo Events Kafka EventSource examples:
  https://raw.githubusercontent.com/argoproj/argo-events/stable/examples/event-sources/kafka.yaml
