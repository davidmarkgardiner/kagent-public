# Comparison Results

## Current Status

MIL-30 validated both event-flow paths on `{{CLUSTER_NAME}}` with three synthetic
Alertmanager API alerts per path. Both paths delivered all test alerts to
consumer pods and preserved the full Alertmanager envelope.

Detailed evidence: `docs/mil-30-comparison-evidence.md`.

## Summary

| Dimension | Redpanda Kafka path | Direct webhook path |
|---|---|---|
| Latency | 3/3 delivered; average sender-to-consumer latency was 751.307 ms. EventSource/Sensor processing happened within tens of milliseconds; pod startup dominated total time. | 3/3 delivered; average sender-to-consumer latency was 667.616 ms. This was about 84 ms faster than the Kafka path in the small MIL-30 sample. |
| Reliability | 3/3 success, no misses or duplicates observed. Redpanda consumer group `kagent-alertmanager-poc` ended `Stable` with `TOTAL-LAG 0`. | 3/3 success, no misses or duplicates observed. Reliability depends on EventSource availability and Alertmanager retry behavior because there is no broker buffer. |
| Payload fidelity | Confirmed. Consumer logs included `pod_name`, `alert_count: 1`, standard Alertmanager envelope keys, and full parsed JSON under `alert_json`. | Confirmed. Consumer logs included `pod_name`, `alert_count: 1`, standard Alertmanager envelope keys, and full parsed JSON under `alert_json`. |
| Operations overhead | Higher: Redpanda StatefulSet, topic bootstrap Job, Alertmanager-to-Kafka bridge, bridge Service, Kafka EventSource, Sensor, AlertmanagerConfig, and lag checks. | Lower: webhook EventSource, explicit Service, Sensor, AlertmanagerConfig, and shared EventBus/RBAC. |
| Ops burden | Requires broker lifecycle, topic management, lag monitoring, and packaging the bridge as a real image for durable staging or production use. | Fewer moving parts and easier to reason about, but no broker-level replay or durable inspection point. |
| Best fit | Use when Kafka-compatible Event Hub parity, replay, or decoupling is required. | Use as the default POC/staging path when the goal is the lowest operational burden and Alertmanager retry is acceptable. |

## Measurement Table

| Run | Path | POST time | EventSource time | Sensor time | Consumer time | Latency | Outcome |
|---|---|---|---|---|---:|---:|---|
| 1 | Redpanda Kafka | 2026-05-11T13:12:41.586417149Z | 2026-05-11T13:12:41.611407682Z | 2026-05-11T13:12:41.686574469Z | 2026-05-11T13:12:42.394743Z | 808.326 ms | Success |
| 2 | Redpanda Kafka | 2026-05-11T13:12:43.763762634Z | 2026-05-11T13:12:43.771655769Z | 2026-05-11T13:12:43.784179638Z | 2026-05-11T13:12:44.446971Z | 683.209 ms | Success |
| 3 | Redpanda Kafka | 2026-05-11T13:12:45.918564852Z | 2026-05-11T13:12:45.926489354Z | 2026-05-11T13:12:45.932886132Z | 2026-05-11T13:12:46.680950Z | 762.386 ms | Success |
| 1 | Direct webhook | 2026-05-11T13:12:48.086996211Z | 2026-05-11T13:12:48.103060514Z | 2026-05-11T13:12:48.113872348Z | 2026-05-11T13:12:48.764059Z | 677.063 ms | Success |
| 2 | Direct webhook | 2026-05-11T13:12:50.201933436Z | 2026-05-11T13:12:50.207838833Z | 2026-05-11T13:12:50.218205157Z | 2026-05-11T13:12:50.869470Z | 667.537 ms | Success |
| 3 | Direct webhook | 2026-05-11T13:12:52.366434529Z | 2026-05-11T13:12:52.372433336Z | 2026-05-11T13:12:52.381550297Z | 2026-05-11T13:12:53.024681Z | 658.247 ms | Success |

## Decision Frame

Use the direct webhook path as the default staging path when the immediate goal
is proving that Alertmanager payloads can trigger a K-Agent-ready consumer pod
with the least operational burden.

Keep the Redpanda Kafka path when the architecture needs Kafka-compatible Event
Hub parity, replay, buffering across downstream outages, or an inspectable
broker boundary.

## Caveats

- MIL-30 was a small three-run comparison, not a load test.
- Failure/retry drills were not executed in this ticket.
- The live cluster ran Argo Events `v1.9.6`; the intake requested `v1.9.10`.
  Re-run after upgrade if strict version parity is required.
- The webhook EventSource and Sensor initially failed on one worker with
  `failed to create watcher: too many open files`. The manifests now pin those
  pods to the same worker already used by the Kafka Argo pods, but the long-term
  fix is correcting node file watcher limits.

## References

- `docs/mil-30-comparison-plan.md`
- `docs/mil-30-comparison-evidence.md`
- `docs/runbooks/redpanda-kafka-path.md`
- `docs/runbooks/webhook-path.md`
