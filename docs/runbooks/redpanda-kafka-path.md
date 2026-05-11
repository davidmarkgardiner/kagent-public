# Runbook: Redpanda Kafka Path

## Path

Alertmanager -> Alertmanager Kafka bridge -> Redpanda -> Argo Events Kafka
EventSource -> Argo Events Sensor -> consumer pod.

Use this path when buffering, replay, or Kafka/Event Hub parity matters more
than minimizing moving parts.

## Prerequisites

- Kubernetes cluster with `kubectl` access.
- Argo Events v1.9.10 already installed and healthy.
- Permission to create resources in namespace `kagent-poc`.
- Egress from pods to pull public container images.
- No production Alertmanager routes pointed at this POC until validation passes.

## Deploy

```bash
kubectl kustomize manifests/redpanda-kafka
kubectl apply -k manifests/redpanda-kafka
```

Wait for the core pods:

```bash
kubectl -n kagent-poc rollout status statefulset/redpanda
kubectl -n kagent-poc rollout status deployment/alertmanager-kafka-bridge
kubectl -n kagent-poc get eventsource,sensor
```

The bootstrap job creates topic `alertmanager-events`:

```bash
kubectl -n kagent-poc logs job/redpanda-create-alertmanager-topic
```

## Wire Alertmanager

The overlay includes an `AlertmanagerConfig` contact point in
`manifests/redpanda-kafka/alertmanager-contact-point.yaml`. It matches only
alerts with:

```text
namespace="kagent-poc"
kagent_path="redpanda-kafka"
```

The receiver points Alertmanager at the bridge service:

```text
http://alertmanager-kafka-bridge.kagent-poc.svc.cluster.local:8080/alertmanager
```

The legacy sample receiver ConfigMap is kept in
`manifests/redpanda-kafka/alertmanager-configmap.yaml` for clusters that do not
use the Prometheus Operator `AlertmanagerConfig` CRD. Keep `repeat_interval`
short during testing so repeat signals are not hidden by Alertmanager
de-duplication.

## Smoke Test Through Alertmanager

Port-forward the cluster Alertmanager:

```bash
kubectl -n monitoring port-forward svc/kube-prom-kube-prometheus-alertmanager 9093:9093
```

Post a synthetic alert that matches the MIL-28 contact point:

```bash
curl -sS -X POST http://127.0.0.1:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  --data-binary @samples/alertmanager-api-pod-alert.json
```

For repeated tests, change the `mil28_run` label value so Alertmanager does not
deduplicate the alert before the `repeatInterval`.

## Smoke Test Without Alertmanager

Port-forward the bridge:

```bash
kubectl -n kagent-poc port-forward svc/alertmanager-kafka-bridge 8080:8080
```

Send the sanitized sample payload:

```bash
curl -sS -X POST http://127.0.0.1:8080/alertmanager \
  -H "Content-Type: application/json" \
  --data-binary @samples/alertmanager-pod-alert.json
```

## Observe

Bridge:

```bash
kubectl -n kagent-poc logs deploy/alertmanager-kafka-bridge --tail=50
```

Kafka EventSource:

```bash
kubectl -n kagent-poc logs -l eventsource-name=alertmanager-kafka --tail=50
```

Sensor:

```bash
kubectl -n kagent-poc logs -l sensor-name=alertmanager-kafka --tail=50
```

Consumer pod:

```bash
kubectl -n kagent-poc get pods -l app.kubernetes.io/component=alert-consumer,path=redpanda-kafka
kubectl -n kagent-poc logs -l app.kubernetes.io/component=alert-consumer,path=redpanda-kafka --tail=20
```

Expected consumer log shape:

```json
{"alert_count":1,"alert_json":{"alerts":[{"labels":{"pod":"sample-api-7f9d6b8d9c-abcde"}}]},"consumed_at":"<utc timestamp>","path":"redpanda-kafka","payload_keys":["alerts","commonAnnotations","commonLabels","externalURL","groupKey","groupLabels","receiver","status","truncatedAlerts","version"],"pod_name":"sample-api-7f9d6b8d9c-abcde"}
```

## Evidence To Capture

- Alertmanager POST timestamp or bridge `received_at`.
- Redpanda topic creation job logs.
- EventSource dispatch logs.
- Sensor trigger logs.
- Consumer pod log with `pod_name`, `alert_count`, `payload_keys`, and
  `consumed_at`.
- Any failed delivery, duplicate delivery, or malformed payload cases.

## Rollback

```bash
kubectl delete -k manifests/redpanda-kafka
```

If Alertmanager was changed, remove or disable the receiver before deleting the
bridge so Alertmanager does not retry into a missing service.

If both overlays are deployed together, this command also deletes the shared
`common` resources. Re-apply the remaining overlay immediately or delete only
the Redpanda-specific resources during partial rollback.

## Notes

- Alertmanager does not produce Kafka records directly; the bridge converts
  Alertmanager webhook requests into Redpanda records.
- The bridge message preserves the full Alertmanager JSON under
  `alertmanager` and adds a top-level `pod_name` for clean Sensor
  parameterization.
- The shared EventBus manifest pins NATS JetStream to `2.10.10` with a
  single-replica stream because the POC EventBus runs one pod.
- For long-lived staging, replace the ConfigMap-mounted bridge with a pinned
  image built through the normal release path.
