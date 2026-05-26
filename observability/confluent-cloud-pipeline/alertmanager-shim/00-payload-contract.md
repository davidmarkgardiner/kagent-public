# Alertmanager Payload Contract

The Alertmanager bridge does not normalize alerts into Kubernetes-event OTLP.

It wraps the raw Alertmanager webhook payload with routing metadata and writes it to the separate `alertmanager-events` topic:

```json
{
  "source": "alertmanager",
  "cluster": "{{MGMT_KUBE_CONTEXT}}",
  "pipeline": "confluent-cloud-pipeline",
  "payload_type": "alertmanager-webhook",
  "received_at": "{{RFC3339_TIMESTAMP}}",
  "alertmanager": {
    "status": "firing",
    "alerts": []
  }
}
```

The management cluster routes these records to `alertmanager-triage`, not to `k8s-triage-critical`.

Live validation still required:

1. POST `04-test-alertmanager-payload.json` to the bridge.
2. Consume one message from `alertmanager-events`.
3. Paste the redacted record below.

## Redacted Live Record

```json
{{PASTE_REDACTED_CONFLUENT_RECORD}}
```
