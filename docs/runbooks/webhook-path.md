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

The sample receiver in `manifests/webhook/alertmanager-configmap.yaml` points
Alertmanager at:

```text
http://alertmanager-webhook-eventsource-svc.kagent-poc.svc.cluster.local:12000/alertmanager
```

Adapt that receiver into the target Alertmanager deployment through the local
configuration mechanism. Keep `repeat_interval` short during testing so repeat
signals are not hidden by Alertmanager de-duplication.

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
{"alert_count":1,"consumed_at":"<utc timestamp>","path":"webhook","payload_keys":["alerts","commonAnnotations","commonLabels","externalURL","groupKey","groupLabels","receiver","status","truncatedAlerts","version"],"pod_name":"sample-api-7f9d6b8d9c-abcde"}
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
