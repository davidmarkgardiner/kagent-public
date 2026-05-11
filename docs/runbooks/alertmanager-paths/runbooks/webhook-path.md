# Runbook: Direct Webhook Path

## Path

Alertmanager -> Argo Events webhook EventSource -> Argo Events Sensor ->
consumer pod.

Use this path when the goal is the shortest operational path and Alertmanager's
own retry behavior is sufficient.

## Prerequisites

- Kubernetes cluster with `kubectl` access.
- Argo Events v1.9.10 already installed and healthy.
- Permission to create resources in namespace `kagent-poc`.
- Network path from Alertmanager to the EventSource Service.
- No production Alertmanager routes pointed at this POC until validation passes.

## Deploy

```bash
kubectl kustomize manifests/webhook
kubectl apply -k manifests/webhook
```

Wait for the EventSource and Sensor:

```bash
kubectl -n kagent-poc get eventsource alertmanager-webhook
kubectl -n kagent-poc get sensor alertmanager-webhook
kubectl -n kagent-poc get svc alertmanager-webhook-eventsource-svc
```

This overlay creates an explicit Kubernetes Service for the webhook
EventSource. Keep the Service in place even though the EventSource spec also
declares a service port; the explicit Service makes the path easier to inspect
and route.

## Wire Alertmanager

The overlay includes an `AlertmanagerConfig` contact point in
`manifests/webhook/alertmanager-contact-point.yaml`. It matches only alerts
with:

```text
namespace="kagent-poc"
kagent_path="webhook"
```

The receiver points Alertmanager at the EventSource service:

```text
http://alertmanager-webhook-eventsource-svc.kagent-poc.svc.cluster.local:12000/alertmanager
```

The sample receiver in `manifests/webhook/alertmanager-configmap.yaml` points
Alertmanager at:

```text
http://alertmanager-webhook-eventsource-svc.kagent-poc.svc.cluster.local:12000/alertmanager
```

The legacy sample receiver ConfigMap is kept for clusters that do not use the
Prometheus Operator `AlertmanagerConfig` CRD. Keep `repeat_interval` short
during testing so repeat signals are not hidden by Alertmanager de-duplication.

## Smoke Test Through Alertmanager

Port-forward the cluster Alertmanager:

```bash
kubectl -n monitoring port-forward svc/kube-prom-kube-prometheus-alertmanager 9093:9093
```

Post a synthetic alert that matches the direct webhook contact point:

```bash
curl -sS -X POST http://127.0.0.1:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  --data-binary @samples/alertmanager-api-pod-alert.json
```

Set `kagent_path` to `webhook` and use a distinct run label for repeated tests
so Alertmanager does not deduplicate the alert before the `repeatInterval`.

## Smoke Test Without Alertmanager

Port-forward the EventSource Service:

```bash
kubectl -n kagent-poc port-forward svc/alertmanager-webhook-eventsource-svc 12000:12000
```

Send the sanitized sample payload:

```bash
curl -sS -X POST http://127.0.0.1:12000/alertmanager \
  -H "Content-Type: application/json" \
  --data-binary @samples/alertmanager-pod-alert.json
```

## Observe

EventSource:

```bash
kubectl -n kagent-poc logs -l eventsource-name=alertmanager-webhook --tail=50
```

Sensor:

```bash
kubectl -n kagent-poc logs -l sensor-name=alertmanager-webhook --tail=50
```

Consumer pod:

```bash
kubectl -n kagent-poc get pods -l app.kubernetes.io/component=alert-consumer,path=webhook
kubectl -n kagent-poc logs -l app.kubernetes.io/component=alert-consumer,path=webhook --tail=20
```

Expected consumer log shape:

```json
{"alert_count":1,"alert_json":{"alerts":[{"labels":{"pod":"sample-api-7f9d6b8d9c-abcde"}}]},"consumed_at":"<utc timestamp>","path":"webhook","payload_keys":["alerts","commonAnnotations","commonLabels","externalURL","groupKey","groupLabels","receiver","status","truncatedAlerts","version"],"pod_name":"sample-api-7f9d6b8d9c-abcde"}
```

## Evidence To Capture

- Alertmanager POST timestamp.
- EventSource receive and dispatch logs.
- Sensor trigger logs.
- Consumer pod log with `pod_name`, `alert_count`, `payload_keys`, and
  `consumed_at`.
- Any retry, duplicate delivery, or malformed payload cases.

## Rollback

```bash
kubectl delete -k manifests/webhook
```

If Alertmanager was changed, remove or disable the receiver before deleting the
EventSource Service so Alertmanager does not retry into a missing endpoint.

If both overlays are deployed together, this command also deletes the shared
`common` resources. Re-apply the remaining overlay immediately or delete only
the webhook-specific resources during partial rollback.

## Notes

- This path preserves the native Alertmanager webhook body as the payload.
- The Sensor extracts `alerts.0.labels.pod` as the consumer pod name. If the
  alert does not include a `pod` label, the consumer receives `unknown-pod`.
- Direct webhook delivery has fewer moving parts but no broker-level replay.
