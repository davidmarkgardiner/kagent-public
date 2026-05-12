# Grafana to Argo Alerting Pipeline

This package proves two Grafana alert delivery paths into Argo Events while preserving why-context in the delivered payload.

## Architecture

```text
Path 1: direct

Grafana contact point
  -> Argo EventSource webhook /grafana/direct
  -> Argo Sensor grafana-alert-router
  -> Workflow grafana-alert-direct-*

Path 2: routed through Redpanda

Grafana contact point
  -> Redpanda Connect HTTP receiver /grafana/redpanda
  -> Redpanda topic grafana.alerts
  -> Argo EventSource Kafka consumer
  -> Argo Sensor grafana-alert-router
  -> Workflow grafana-alert-redpanda-*
```

## Files

| File | Purpose |
| --- | --- |
| `observability/grafana/provisioning/alerting/alert-rules.yaml` | Grafana provisioning for log error, Kubernetes Warning event, and pod CPU threshold alerts. |
| `observability/grafana/provisioning/alerting/contact-points.yaml` | Webhook contact points for direct Argo and webhook-to-Redpanda delivery. |
| `observability/grafana/provisioning/alerting/notification-policies.yaml` | Routes alerts with `pipeline_path=both` to both contact points. |
| `argo/eventsources/grafana-alert-webhook-eventsource.yaml` | Argo webhook EventSource for direct Grafana posts. |
| `argo/eventsources/grafana-alert-redpanda-eventsource.yaml` | Argo Kafka EventSource consuming Redpanda topic `grafana.alerts`. |
| `argo/eventbus/default-eventbus.yaml` | Default Argo Events EventBus required by EventSources and Sensors. |
| `argo/sensors/grafana-alert-sensor.yaml` | Sensor that submits a small Workflow for either source. |
| `k8s/redpanda/redpanda-single-node.yaml` | Optional single-node Redpanda for environments without an existing broker. |
| `k8s/alerting/redpanda-connect-grafana-webhook.yaml` | HTTP receiver that publishes Grafana webhook bodies to Redpanda. |
| `scripts/observability/verify-alerting-pipeline.sh` | Dry-run, apply, send, consume, and log collection helper. |
| `testdata/observability/*.json` | Captured sample Grafana webhook payloads for the three alert types. |

## Pros And Cons

|  | Direct (Path 1) | Via Redpanda (Path 2) |
| -- | -- | -- |
| Latency | Lower | Higher due to broker hop |
| Reliability | Single point between Grafana and Argo EventSource | Buffered by Redpanda; replay possible while retained |
| Fan-out | Manual through multiple contact points | Natural through multiple consumers on the topic |
| Ordering | Not applicable beyond individual HTTP requests | Partition-guaranteed for records with the same key |
| Ops complexity | Low | Higher because Redpanda and receiver are in the path |
| Audit trail | Grafana notification history and Argo logs | Grafana history plus Redpanda retained topic messages |

## Setup

1. Deploy Argo Events and Argo Workflows in namespace `argo`.
2. Ensure Redpanda is reachable from namespace `argo` at `redpanda.redpanda.svc.cluster.local:9092`, or update `REDPANDA_BROKERS` in `k8s/alerting/redpanda-connect-grafana-webhook.yaml` and `url` in `argo/eventsources/grafana-alert-redpanda-eventsource.yaml`. If no broker exists, deploy the included single-node broker:

   ```sh
   scripts/observability/verify-alerting-pipeline.sh apply-redpanda
   ```

3. Apply the cluster resources:

   ```sh
   kubectl apply -f argo/eventbus
   kubectl apply -f k8s/alerting
   kubectl apply -f argo/eventsources
   kubectl apply -f argo/sensors
   ```

4. Expose the direct Argo EventSource service to Grafana. For local verification:

   ```sh
   scripts/observability/verify-alerting-pipeline.sh port-forward-direct
   ```

5. Expose the Redpanda webhook receiver to Grafana. For local verification:

   ```sh
   scripts/observability/verify-alerting-pipeline.sh port-forward-redpanda-webhook
   ```

6. Provision Grafana with:

   ```text
   observability/grafana/provisioning/alerting/*.yaml
   ```

   Set `ARGO_DIRECT_WEBHOOK_URL` to the exposed `/grafana/direct` URL and `GRAFANA_REDPANDA_WEBHOOK_URL` to the exposed `/grafana/redpanda` URL. Set `GRAFANA_PUBLIC_URL` to the public Grafana base URL used in panel links.

## Verification

Run schema/server validation first:

```sh
scripts/observability/verify-alerting-pipeline.sh dry-run
```

For direct delivery:

```sh
scripts/observability/verify-alerting-pipeline.sh port-forward-direct
scripts/observability/verify-alerting-pipeline.sh send-direct testdata/observability/grafana-log-error-alert.json
scripts/observability/verify-alerting-pipeline.sh logs
```

Expected result: `grafana-alert-webhook` EventSource logs show the POST body and the Sensor creates a `grafana-alert-direct-*` Workflow.

For Redpanda delivery:

```sh
scripts/observability/verify-alerting-pipeline.sh port-forward-redpanda-webhook
scripts/observability/verify-alerting-pipeline.sh send-redpanda testdata/observability/grafana-metric-threshold-alert.json
scripts/observability/verify-alerting-pipeline.sh consume-redpanda
scripts/observability/verify-alerting-pipeline.sh logs
```

Expected result: `rpk topic consume grafana.alerts` shows the enriched message, `grafana-alert-redpanda` EventSource consumes it, and the Sensor creates a `grafana-alert-redpanda-*` Workflow.

## Alert Why-Context

Each alert includes these fields through Grafana labels, annotations, and standard webhook fields:

| Field | Source |
| --- | --- |
| `alertname` | `labels.alertname`, also `commonLabels.alertname` |
| `summary` | `annotations.summary`, also `commonAnnotations.summary` |
| `description` | `annotations.description`, also `commonAnnotations.description` |
| `severity` | `labels.severity` |
| `namespace`, `pod`, `node` | labels when applicable |
| `grafana_panel_url` | annotations |
| `runbook_url` | annotations |
| firing duration/timestamps | `startsAt`, `endsAt`, alert rule `for`, and type-specific annotations |

## Sample Payloads

### Log Error

```json
{
  "alertname": "Kubernetes log error rate spike",
  "summary": "Error logs are above 0.1 lines/sec in payments/checkout-api-7f9d9c4b6c-n7p2v.",
  "description": "Loki saw 0.420 error log lines/sec for 5m in pod payments/checkout-api-7f9d9c4b6c-n7p2v, above threshold 0.1 for at least 2m.",
  "severity": "warning",
  "namespace": "payments",
  "pod": "checkout-api-7f9d9c4b6c-n7p2v",
  "log_line_excerpt": "level=error msg=\"payment authorization failed\" order_id=ord_123 gateway=stripe",
  "error_rate": "0.420 lines/sec",
  "window": "5m",
  "grafana_panel_url": "https://grafana.example.com/d/kubernetes-logs/kubernetes-logs?orgId=1&var-namespace=payments&var-pod=checkout-api-7f9d9c4b6c-n7p2v",
  "runbook_url": "https://runbooks.example.com/kubernetes/log-error-rate"
}
```

### Kubernetes Event

```json
{
  "alertname": "Kubernetes warning event observed",
  "summary": "Kubernetes Warning event BackOff on Pod/checkout-api-7f9d9c4b6c-n7p2v.",
  "description": "Kubernetes emitted 7 Warning events in 5m for Pod/checkout-api-7f9d9c4b6c-n7p2v in namespace payments.",
  "severity": "warning",
  "namespace": "payments",
  "pod": "checkout-api-7f9d9c4b6c-n7p2v",
  "event_reason": "BackOff",
  "involved_object": "Pod/checkout-api-7f9d9c4b6c-n7p2v",
  "message": "Back-off restarting failed container checkout-api",
  "count": "7",
  "first_timestamp": "2026-05-12T09:55:00Z",
  "last_timestamp": "2026-05-12T10:00:00Z",
  "grafana_panel_url": "https://grafana.example.com/d/kubernetes-events/kubernetes-events?orgId=1&var-namespace=payments&var-reason=BackOff",
  "runbook_url": "https://runbooks.example.com/kubernetes/warning-events"
}
```

### Metric Threshold

```json
{
  "alertname": "Pod CPU threshold breach",
  "summary": "Pod payments/checkout-api-7f9d9c4b6c-n7p2v is above 85% CPU limit.",
  "description": "Metric container_cpu_usage_seconds_total / kube_pod_container_resource_limits is 93.7% for payments/checkout-api-7f9d9c4b6c-n7p2v on aks-nodepool1-12345678-vmss000001, threshold 85%, 8.7 percentage points over, breaching for at least 5m.",
  "severity": "critical",
  "namespace": "payments",
  "pod": "checkout-api-7f9d9c4b6c-n7p2v",
  "node": "aks-nodepool1-12345678-vmss000001",
  "metric_name": "container_cpu_usage_seconds_total",
  "current_value": "93.7%",
  "threshold": "85%",
  "percentage_over": "8.7 percentage points",
  "duration_breaching": "5m",
  "grafana_panel_url": "https://grafana.example.com/d/kubernetes-compute-resources-pod/kubernetes-compute-resources-pod?orgId=1&var-namespace=payments&var-pod=checkout-api-7f9d9c4b6c-n7p2v",
  "runbook_url": "https://runbooks.example.com/kubernetes/pod-cpu-threshold"
}
```
