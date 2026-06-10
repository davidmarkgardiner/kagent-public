# Grafana Kafka REST Proxy Contact Point

This option configures Grafana Alerting to publish directly to Confluent Cloud
through Grafana's `Kafka REST Proxy` contact point.

Use this when you want the Grafana-native path:

```text
Grafana Alerting -> Kafka REST Proxy contact point -> Confluent Cloud Kafka REST API v3 -> alertmanager-events
```

Keep the `alertmanager-shim/` bridge when you need a stable local HTTP endpoint,
payload normalization, explicit retry behavior, Kubernetes-native rollout
visibility, or compatibility with the existing Alertmanager triage workflow.

## Required Grafana Fields

Grafana's Kafka integration uses these provisioning keys:

- `kafkaRestProxy`: Confluent REST endpoint with `/kafka` appended.
- `kafkaTopic`: Kafka topic, normally `alertmanager-events`.
- `username`: Confluent Kafka API key.
- `password`: Confluent Kafka API secret.
- `apiVersion`: `v3`.
- `kafkaClusterId`: Confluent Kafka cluster ID.

For Confluent Cloud, `kafkaRestProxy` must look like:

```text
https://{{CONFLUENT_REST_ENDPOINT_HOST}}:443/kafka
```

Grafana appends the v3 produce path:

```text
/v3/clusters/{{CONFLUENT_CLUSTER_ID}}/topics/{{CONFLUENT_ALERTS_TOPIC}}/records
```

Confluent Cloud receives the effective request at:

```text
/kafka/v3/clusters/{{CONFLUENT_CLUSTER_ID}}/topics/{{CONFLUENT_ALERTS_TOPIC}}/records
```

## Payload Shape

The native Kafka contact point does not emit an Alertmanager webhook payload.
Grafana publishes a Kafka v3 record like:

```json
{
  "value": {
    "type": "JSON",
    "data": {
      "client": "Grafana",
      "description": "{{TEMPLATED_DESCRIPTION}}",
      "details": "{{TEMPLATED_DETAILS}}",
      "alert_state": "alerting",
      "client_url": "{{GRAFANA_ALERTING_URL}}",
      "incident_key": "{{GROUP_KEY_HASH}}"
    }
  }
}
```

Argo Events' Kafka EventSource exposes the record body to Sensors under `body`.
The existing `management-cluster/03-sensor-alertmanager.yaml` filters for the
bridge envelope:

```text
body.source = alertmanager
body.alertmanager.status = firing
```

That filter intentionally does not match the native Grafana Kafka record. Use a
separate native Grafana Kafka Sensor or add a normalizer if this path should
trigger the same triage workflow.

## Configure

Run after `00-cluster-bootstrap.sh` has created `confluent.io/.bootstrap.env`.
The script derives `CONFLUENT_REST_ENDPOINT` with the Confluent CLI if older
bootstrap files do not contain it.

```bash
GRAFANA_URL=http://127.0.0.1:13030 \
GRAFANA_USER=admin \
GRAFANA_PASSWORD='{{GRAFANA_ADMIN_PASSWORD}}' \
observability/confluent-cloud-pipeline/grafana-contact-point/01-configure-kafka-rest-contact-point.sh
```

Defaults:

```text
contact point name: confluent-kafka-rest-alerts
contact point uid:  confluent-kafka-rest-alerts
topic:              $CONFLUENT_ALERTS_TOPIC
api version:        v3
```

Override them with:

```bash
GRAFANA_CONTACT_POINT_NAME='{{CONTACT_POINT_NAME}}'
GRAFANA_CONTACT_POINT_UID='{{CONTACT_POINT_UID}}'
GRAFANA_KAFKA_TOPIC='{{TOPIC_NAME}}'
```

The script creates or updates the contact point only. Add it to a notification
policy or select it from an alert rule's notification settings when you want
alerts to flow through this path.

For a repeatable work-environment setup, use `WORK-SETUP-RUNBOOK.md`.

After the contact point connects successfully, use
`ALERT-FIRING-CONSUME-SCHEMA-RUNBOOK.md` to prove real alert firing, consume the
Kafka records from the cluster side, capture the actual Grafana payload, and
decide whether schema validation can stay consumer-side or requires a
normalizing producer/bridge.

The draft consumer-side JSON Schema for the native Grafana Kafka record is:

```text
grafana-kafka-alert.schema.json
```
