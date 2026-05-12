# MIL-28 Path A Evidence

## Environment

- Date: 2026-05-11
- Cluster: `{{CLUSTER_NAME}}`
- Namespace: `kagent-poc`
- Argo Events controller observed: `quay.io/argoproj/argo-events:v1.9.6`
- Branch: `symphony/MIL-28-redpanda-kafka-path`

The intake requested Argo Events `v1.9.10`; the live cluster was already
running `v1.9.6`. The Path A resources were validated against the installed
controller and CRDs.

## Deployment Evidence

```text
kubectl --context {{CLUSTER_NAME}} apply -k manifests/redpanda-kafka
namespace/kagent-poc created
service/redpanda created
deployment.apps/alertmanager-kafka-bridge created
statefulset.apps/redpanda created
eventbus.argoproj.io/default created
eventsource.argoproj.io/alertmanager-kafka created
sensor.argoproj.io/alertmanager-kafka created
job.batch/redpanda-create-alertmanager-topic created
alertmanagerconfig.monitoring.coreos.com/kagent-redpanda-kafka created
```

Final resource state:

```text
alertmanager-kafka-bridge              1/1 Running
alertmanager-kafka-eventsource-srm5f   1/1 Running
alertmanager-kafka-sensor-vrf7b        1/1 Running
eventbus-default-js-0                  3/3 Running
redpanda-0                             1/1 Running
redpanda-create-alertmanager-topic     Complete 1/1
```

The Redpanda topic bootstrap job confirmed topic `alertmanager-events`.

## Alertmanager Contact Point

The Prometheus Operator merged the scoped contact point into Alertmanager:

```text
receiver: kagent-poc/kagent-redpanda-kafka/kagent-redpanda-kafka
matchers:
- kagent_path="redpanda-kafka"
- namespace="kagent-poc"
url: http://alertmanager-kafka-bridge.kagent-poc.svc.cluster.local:8080/alertmanager
```

Synthetic alert POST:

```text
run_id=mil28-fulljson-20260511T122254Z
POST http://127.0.0.1:19093/api/v2/alerts
HTTP/1.1 200 OK
```

## Pipeline Evidence

Bridge accepted Alertmanager webhook delivery:

```text
2026-05-11T12:23:16.034363518Z 10.244.126.8 - "POST /alertmanager HTTP/1.1" 202 -
```

Redpanda consumer group drained the topic:

```text
GROUP                  kagent-alertmanager-poc
STATE                  Stable
TOTAL-LAG              0
TOPIC                  alertmanager-events
CURRENT-OFFSET         3
LOG-END-OFFSET         3
```

Argo Kafka EventSource published the Kafka record:

```text
2026-05-11T12:23:16.030509629Z Succeeded to publish an event
eventID=alertmanager-kafka:alertmanager:redpanda.kagent-poc.svc.cluster.local:9092:alertmanager-events:0:2
```

Sensor created the consumer pod:

```text
2026-05-11T12:23:16.030788379Z Triggering actions after receiving dependency alertmanager
2026-05-11T12:23:16.042273995Z Successfully processed trigger 'alertmanager-kafka-consumer'
```

Consumer pod:

```text
kafka-alert-consumer-7ppgf   Succeeded   2026-05-11T12:23:16Z
```

Consumer log included `pod_name` and full parsed Alertmanager JSON:

```json
{
  "alert_count": 2,
  "alert_json": {
    "alerts": [
      {
        "labels": {
          "alertname": "MIL28PodCrashLooping",
          "kagent_path": "redpanda-kafka",
          "mil28_run": "mil28-fulljson-20260511T122254Z",
          "namespace": "kagent-poc",
          "pod": "sample-api-7f9d6b8d9c-abcde",
          "severity": "warning"
        },
        "status": "firing"
      }
    ],
    "receiver": "kagent-poc/kagent-redpanda-kafka/kagent-redpanda-kafka",
    "status": "firing",
    "version": "4"
  },
  "consumed_at": "2026-05-11T12:23:16.687680+00:00",
  "path": "redpanda-kafka",
  "pod_name": "sample-api-7f9d6b8d9c-abcde"
}
```

`alert_count` was `2` because Alertmanager grouped two active synthetic alerts
for the same `alertname`, `namespace`, and `pod`. The full log line included
both alert objects.

## Fixes Required During Validation

- Added a scoped `AlertmanagerConfig` contact point for `kagent_path=redpanda-kafka`.
- Set the single-node EventBus stream config to `replicas: 1`; the controller
  default was three stream replicas, which a one-pod JetStream EventBus cannot
  create.
- Pinned generated EventSource/Sensor pods to `k8s-worker1` after `k8s-worker2`
  returned `failed to create watcher: too many open files`.
- Updated the consumer pod to log full parsed Alertmanager JSON in `alert_json`.
