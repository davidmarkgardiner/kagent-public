# MIL-30 K-Agent Path Comparison Plan

## Scope

Validate both K-Agent event-flow paths on `proxmox-k8s` and stop at the
consumer pod:

- Path A: Alertmanager -> Redpanda -> Argo Events Kafka EventSource -> Sensor
  -> consumer pod.
- Path B: Alertmanager -> Argo Events webhook EventSource -> Sensor ->
  consumer pod.

The test confirms payload integrity, delivery reliability, and rough latency
for a small synthetic sample. It does not exercise K-Agent triage.

## Method

1. Target Kubernetes with `kubectl --context proxmox-k8s`.
2. Apply the Redpanda Kafka overlay and confirm Redpanda, bridge, EventSource,
   Sensor, topic bootstrap job, and consumer trigger support are healthy.
3. Apply the webhook overlay and confirm EventSource Service, EventSource, and
   Sensor are healthy.
4. Use distinct run labels and pod names so new consumer logs are unambiguous
   without deleting prior evidence pods.
5. Send three synthetic Alertmanager payloads per path with distinct run labels.
6. Capture sender timestamps, HTTP responses, EventSource/Sensor logs, and
   resulting consumer pod logs.
7. Compare:
   - first-send-to-first-consumer latency observed from the client clock and
     consumer `consumed_at` timestamps;
   - success count and duplicate/missed/malformed event count;
   - whether `pod_name`, `alert_count`, standard Alertmanager keys, and full
     JSON payload are preserved;
   - operational overhead and failure surface from deployed resource counts.

## Success Criteria

- Three successful consumer pods are created for each path.
- Every consumer log parses as JSON.
- Every consumer log reports `alert_count: 1`.
- Every consumer log reports the expected pod name.
- Every consumer log contains standard Alertmanager envelope keys.
- Redpanda path logs retain full Alertmanager JSON under `alert_json`.
- Webhook path logs retain the native Alertmanager envelope fields.
