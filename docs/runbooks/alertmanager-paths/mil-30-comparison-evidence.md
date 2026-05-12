# MIL-30 K-Agent Path Comparison Evidence

## Environment

- Target context: `{{CLUSTER_NAME}}`
- Namespace: `kagent-poc`
- Test time: 2026-05-11T13:12Z
- Alert delivery: synthetic Alertmanager API alerts posted through a local
  port-forward to the cluster Alertmanager service
- Argo Events image observed in EventSource and Sensor logs: `v1.9.6`

The intake requested Argo Events `v1.9.10`. Treat the results below as live
path evidence on the current cluster, with a required re-run after an Argo
Events upgrade if strict version parity is required.

## What Changed For This Test

- Added a scoped direct-webhook `AlertmanagerConfig` so alerts with
  `kagent_path="webhook"` route through Alertmanager to the webhook
  EventSource.
- Updated the webhook consumer to log the full parsed Alertmanager envelope
  under `alert_json`, matching the Redpanda Kafka consumer.
- Pinned the webhook EventSource and Sensor to the same worker used by the
  Kafka Argo pods. Initial webhook pods on another worker failed with
  `failed to create watcher: too many open files`.

## Summary Metrics

| Path | Runs | Successes | Misses | Duplicates observed | Latency avg | Latency min | Latency max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Redpanda Kafka | 3 | 3 | 0 | 0 | 751.307 ms | 683.209 ms | 808.326 ms |
| Direct webhook | 3 | 3 | 0 | 0 | 667.616 ms | 658.247 ms | 677.063 ms |

The direct webhook path was about 84 ms faster on average in this small sample.
Most observed time is Kubernetes pod creation/startup time; both EventSources
and Sensors handled events within tens of milliseconds after Alertmanager
delivery.

## Run Details

| Run | Path | POST time | EventSource time | Sensor time | Consumer time | Sender-to-consumer latency | Outcome |
|---|---|---|---|---|---:|---:|---|
| 1 | Redpanda Kafka | 2026-05-11T13:12:41.586417149Z | 2026-05-11T13:12:41.611407682Z | 2026-05-11T13:12:41.686574469Z | 2026-05-11T13:12:42.394743Z | 808.326 ms | Success |
| 2 | Redpanda Kafka | 2026-05-11T13:12:43.763762634Z | 2026-05-11T13:12:43.771655769Z | 2026-05-11T13:12:43.784179638Z | 2026-05-11T13:12:44.446971Z | 683.209 ms | Success |
| 3 | Redpanda Kafka | 2026-05-11T13:12:45.918564852Z | 2026-05-11T13:12:45.926489354Z | 2026-05-11T13:12:45.932886132Z | 2026-05-11T13:12:46.680950Z | 762.386 ms | Success |
| 1 | Direct webhook | 2026-05-11T13:12:48.086996211Z | 2026-05-11T13:12:48.103060514Z | 2026-05-11T13:12:48.113872348Z | 2026-05-11T13:12:48.764059Z | 677.063 ms | Success |
| 2 | Direct webhook | 2026-05-11T13:12:50.201933436Z | 2026-05-11T13:12:50.207838833Z | 2026-05-11T13:12:50.218205157Z | 2026-05-11T13:12:50.869470Z | 667.537 ms | Success |
| 3 | Direct webhook | 2026-05-11T13:12:52.366434529Z | 2026-05-11T13:12:52.372433336Z | 2026-05-11T13:12:52.381550297Z | 2026-05-11T13:12:53.024681Z | 658.247 ms | Success |

## Payload Fidelity

Each consumer pod logged:

- `alert_count: 1`
- the expected `pod_name`
- standard Alertmanager envelope keys:
  `alerts`, `commonAnnotations`, `commonLabels`, `externalURL`, `groupKey`,
  `groupLabels`, `receiver`, `status`, `truncatedAlerts`, `version`
- full parsed Alertmanager JSON under `alert_json`

Representative Redpanda Kafka consumer fields:

```json
{
  "alert_count": 1,
  "path": "redpanda-kafka",
  "pod_name": "mil30-redpanda-kafka-1",
  "payload_keys": ["alerts", "commonAnnotations", "commonLabels", "externalURL", "groupKey", "groupLabels", "receiver", "status", "truncatedAlerts", "version"],
  "alert_json": {
    "receiver": "kagent-poc/kagent-redpanda-kafka/kagent-redpanda-kafka",
    "alerts": [
      {
        "labels": {
          "kagent_path": "redpanda-kafka",
          "mil30_run": "mil30-20260511T131241Z-redpanda-kafka-1",
          "pod": "mil30-redpanda-kafka-1"
        }
      }
    ]
  }
}
```

Representative direct webhook consumer fields:

```json
{
  "alert_count": 1,
  "path": "webhook",
  "pod_name": "mil30-webhook-1",
  "payload_keys": ["alerts", "commonAnnotations", "commonLabels", "externalURL", "groupKey", "groupLabels", "receiver", "status", "truncatedAlerts", "version"],
  "alert_json": {
    "receiver": "kagent-poc/kagent-direct-webhook/kagent-direct-webhook",
    "alerts": [
      {
        "labels": {
          "kagent_path": "webhook",
          "mil30_run": "mil30-20260511T131241Z-webhook-1",
          "pod": "mil30-webhook-1"
        }
      }
    ]
  }
}
```

## Reliability Evidence

- Alertmanager API returned HTTP `200` for all six synthetic alerts.
- Redpanda bridge accepted all three Kafka-path Alertmanager webhooks with
  HTTP `202`.
- Kafka EventSource published offsets `6`, `7`, and `8` for the MIL-30 runs.
- Redpanda consumer group `kagent-alertmanager-poc` ended `Stable` with
  `TOTAL-LAG 0`.
- Webhook EventSource published three events and the webhook Sensor processed
  all three Kubernetes triggers successfully.

## Comparison Matrix

| Dimension | Redpanda Kafka path | Direct webhook path |
|---|---|---|
| Latency | Average 751.307 ms over three runs. Adds bridge and broker hop, but the observed extra cost was modest compared with pod startup. | Average 667.616 ms over three runs. Lowest overhead path in this sample. |
| Reliability | 3/3 delivered; Kafka consumer group reached `TOTAL-LAG 0`. Broker can buffer after the bridge accepts a webhook. | 3/3 delivered. Simpler, but delivery depends on EventSource availability plus Alertmanager retry behavior. |
| Payload integrity | Full Alertmanager envelope preserved under `alert_json`; bridge also provides top-level `pod_name`. | Full Alertmanager envelope preserved directly under `alert_json`; Sensor extracts `alerts.0.labels.pod`. |
| Operations overhead | Highest: Redpanda StatefulSet, topic bootstrap Job, bridge Deployment and Service, Kafka EventSource, Sensor, AlertmanagerConfig, lag checks. | Lowest: webhook EventSource, explicit Service, Sensor, AlertmanagerConfig, and shared EventBus/RBAC. |
| Ops burden | Requires broker lifecycle, topic health, consumer lag monitoring, and bridge packaging for production use. | Requires fewer moving parts, but no broker-level replay or durable inspection point. |
| Best fit | Use when Kafka/Event Hub parity, replay, or decoupling is required. | Use as default POC/staging path when lowest operational burden is preferred. |

## Caveats

- This was a small three-run sample per path, not a load or soak test.
- Failure/retry drills were not executed during MIL-30.
- The cluster ran Argo Events `v1.9.6`; re-run after upgrading if `v1.9.10`
  is mandatory.
- The initial webhook deployment exposed node-level file watcher exhaustion on
  one worker. The current manifest pins webhook Argo pods to the healthy worker,
  matching the Kafka path, but long-term operations should fix the node limit
  rather than rely on pinning.
