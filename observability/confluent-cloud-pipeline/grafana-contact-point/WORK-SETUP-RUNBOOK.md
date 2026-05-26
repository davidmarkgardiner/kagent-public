# Work Setup Runbook - Grafana to Confluent Kafka REST

This runbook repeats the validated local configuration in a work environment
without copying local-only hostnames, cluster names, or secrets.

Use this path when the desired producer is Grafana Alerting itself:

```text
Grafana Alerting -> Kafka REST Proxy contact point -> Confluent Cloud Kafka REST API v3 -> Kafka topic
```

If the downstream workflow expects an Alertmanager webhook payload, use the
`alertmanager-shim/` bridge instead, or add a normalizer before the Argo Sensor.
Grafana's native Kafka contact point publishes a Grafana record, not an
Alertmanager envelope.

## Inputs To Collect

Fill these values from the work environment:

```bash
export GRAFANA_URL='{{WORK_GRAFANA_URL}}'
export GRAFANA_USER='{{WORK_GRAFANA_USER}}'
export GRAFANA_PASSWORD='{{WORK_GRAFANA_PASSWORD}}'

export CONFLUENT_CLUSTER_ID='{{CONFLUENT_CLUSTER_ID}}'
export CONFLUENT_REST_ENDPOINT='{{CONFLUENT_REST_ENDPOINT}}'
export CONFLUENT_ALERTS_TOPIC='{{CONFLUENT_ALERTS_TOPIC}}'
export CONFLUENT_SA_KEY='{{CONFLUENT_KAFKA_API_KEY}}'
export CONFLUENT_SA_SECRET='{{CONFLUENT_KAFKA_API_SECRET}}'
```

`CONFLUENT_REST_ENDPOINT` is the Confluent Cloud REST endpoint, not the Kafka
bootstrap broker endpoint. The Grafana field must use this endpoint with
`/kafka` appended.

## Preconditions

- Grafana version supports the `Kafka REST Proxy` contact point with username
  and password fields.
- The Confluent API key can write to `{{CONFLUENT_ALERTS_TOPIC}}`.
- The Grafana server can reach `{{CONFLUENT_REST_ENDPOINT}}` over HTTPS.
- Local machine has `curl`, `jq`, and optionally `confluent` CLI.
- Secrets stay outside git. Use a local env file or secret manager.

## Configure By Script

Create a local env file outside the repo, or export the values in the shell.

```bash
mkdir -p {{LOCAL_SECRET_DIR}}
cat > {{LOCAL_SECRET_DIR}}/grafana-confluent.env <<'EOF'
GRAFANA_URL='{{WORK_GRAFANA_URL}}'
GRAFANA_USER='{{WORK_GRAFANA_USER}}'
GRAFANA_PASSWORD='{{WORK_GRAFANA_PASSWORD}}'
CONFLUENT_CLUSTER_ID='{{CONFLUENT_CLUSTER_ID}}'
CONFLUENT_REST_ENDPOINT='{{CONFLUENT_REST_ENDPOINT}}'
CONFLUENT_ALERTS_TOPIC='{{CONFLUENT_ALERTS_TOPIC}}'
CONFLUENT_SA_KEY='{{CONFLUENT_KAFKA_API_KEY}}'
CONFLUENT_SA_SECRET='{{CONFLUENT_KAFKA_API_SECRET}}'
EOF
chmod 600 {{LOCAL_SECRET_DIR}}/grafana-confluent.env
```

Run the contact point script:

```bash
set -a
. {{LOCAL_SECRET_DIR}}/grafana-confluent.env
set +a

GRAFANA_CONTACT_POINT_NAME='{{CONTACT_POINT_NAME}}' \
GRAFANA_CONTACT_POINT_UID='{{CONTACT_POINT_UID}}' \
GRAFANA_KAFKA_TOPIC="$CONFLUENT_ALERTS_TOPIC" \
observability/confluent-cloud-pipeline/grafana-contact-point/01-configure-kafka-rest-contact-point.sh
```

Suggested stable names:

```text
GRAFANA_CONTACT_POINT_NAME=confluent-kafka-rest-alerts
GRAFANA_CONTACT_POINT_UID=confluent-kafka-rest-alerts
```

## Configure By UI

Use this mapping if the work process requires manual UI configuration:

```text
Grafana page: Alerting -> Contact points -> New contact point
Name: {{CONTACT_POINT_NAME}}
Integration: Kafka REST Proxy
Kafka REST Proxy: {{CONFLUENT_REST_ENDPOINT}}/kafka
Topic: {{CONFLUENT_ALERTS_TOPIC}}
Username: {{CONFLUENT_KAFKA_API_KEY}}
Password: {{CONFLUENT_KAFKA_API_SECRET}}
API version: v3
Cluster ID: {{CONFLUENT_CLUSTER_ID}}
```

Save the contact point, then use Grafana's Test button. If the Test button
succeeds but downstream workflows do not fire, inspect payload filters before
debugging Kafka transport.

## Validate Transport

First verify Grafana is reachable:

```bash
curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  "$GRAFANA_URL/api/health" | jq '{database, version}'
```

Read the contact point back without printing secrets:

```bash
curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  "$GRAFANA_URL/api/v1/provisioning/contact-points" |
  jq '.[] | select(.name=="{{CONTACT_POINT_NAME}}") |
    {
      uid,
      name,
      type,
      settings: {
        apiVersion: .settings.apiVersion,
        kafkaTopic: .settings.kafkaTopic,
        hasRestProxy: (.settings.kafkaRestProxy != null),
        hasUsername: (.settings.username != null),
        hasPassword: (.settings.password != null)
      },
      provenance
    }'
```

Expected:

```text
type: kafka
apiVersion: v3
kafkaTopic: {{CONFLUENT_ALERTS_TOPIC}}
hasRestProxy: true
hasUsername: true
hasPassword: true
```

Optionally prove Confluent REST v3 directly with the same endpoint and
credentials:

```bash
REST_BASE="${CONFLUENT_REST_ENDPOINT%/}/kafka/v3/clusters/${CONFLUENT_CLUSTER_ID}/topics/${CONFLUENT_ALERTS_TOPIC}/records"

curl -fsS -u "$CONFLUENT_SA_KEY:$CONFLUENT_SA_SECRET" \
  -X POST "$REST_BASE" \
  -H 'Content-Type: application/json' \
  --data '{
    "value": {
      "type": "JSON",
      "data": {
        "source": "manual-work-smoke",
        "status": "firing",
        "message": "Grafana Confluent REST credentials smoke"
      }
    }
  }' | jq '{error_code, topic_name, partition_id, offset}'
```

Expected:

```text
HTTP success
error_code: 200
topic_name: {{CONFLUENT_ALERTS_TOPIC}}
partition_id: non-null
offset: non-null
```

## Route A Test Alert

Create a temporary notification policy route for one smoke alert name. Save the
current policy first:

```bash
curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  "$GRAFANA_URL/api/v1/provisioning/policies" \
  > /tmp/work-grafana-policy-before-kafka-smoke.json
```

Add a scoped route:

```bash
jq '.routes = ((.routes // []) + [{
  "receiver": "{{CONTACT_POINT_NAME}}",
  "object_matchers": [["alertname", "=", "ConfluentKafkaRestSmokeTest"]],
  "group_wait": "10s",
  "group_interval": "30s",
  "repeat_interval": "5m"
}])' /tmp/work-grafana-policy-before-kafka-smoke.json \
  > /tmp/work-grafana-policy-kafka-smoke.json

curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -X PUT "$GRAFANA_URL/api/v1/provisioning/policies" \
  -H 'Content-Type: application/json' \
  --data-binary @/tmp/work-grafana-policy-kafka-smoke.json
```

Create a short-lived Grafana-managed rule that evaluates `vector(1)` and has:

```text
title: ConfluentKafkaRestSmokeTest
label route_to: confluent-kafka-rest
label severity: warning
label namespace: {{WORK_TEST_NAMESPACE}}
```

Wait one evaluation interval, then verify the record in one of these places:

```bash
# Confluent CLI, if available
confluent kafka topic consume "$CONFLUENT_ALERTS_TOPIC" \
  --from-beginning \
  --group "verify-work-grafana-$(date +%s)" \
  --cluster "$CONFLUENT_CLUSTER_ID" \
  --print-offset
```

```bash
# Argo Events, if Kafka EventSource is consuming this topic
kubectl --context {{WORK_K8S_CONTEXT}} -n {{ARGO_EVENTS_NAMESPACE}} logs \
  -l eventsource-name={{CONFLUENT_EVENTSOURCE_NAME}} --tail=200 |
  grep -E 'ConfluentKafkaRestSmokeTest|alertmanager-events|Succeeded to publish an event'
```

## Cleanup Test Route

Remove the temporary smoke route and restore the original policy:

```bash
curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -X PUT "$GRAFANA_URL/api/v1/provisioning/policies" \
  -H 'Content-Type: application/json' \
  --data-binary @/tmp/work-grafana-policy-before-kafka-smoke.json
```

Delete the temporary smoke alert rule from Grafana after capturing evidence.
Keep the contact point if it is the intended work configuration.

## Downstream Payload Caveat

The native Grafana Kafka record has fields like:

```text
body.client
body.description
body.details
body.alert_state
body.client_url
body.incident_key
```

It does not have:

```text
body.source
body.alertmanager.status
body.alertmanager.alerts
```

If an Argo Sensor is currently filtering for the bridge envelope, it will discard
native Grafana Kafka records with an error like:

```text
data filter error (path 'body.source' does not exist)
```

For work, choose one:

- Keep using the Alertmanager bridge for existing Alertmanager triage workflows.
- Add a native Grafana Kafka Sensor that filters on `body.client=Grafana` and
  `body.alert_state=alerting`.
- Add a normalizer service that converts Grafana Kafka records into the existing
  Alertmanager payload contract.

## Evidence To Capture

Record these in the work ticket or handoff:

```text
Grafana version:
Contact point name and UID:
Kafka topic:
Confluent cluster ID: redacted
REST endpoint host: redacted
Contact point read-back: redacted
Direct REST smoke result: HTTP/error_code/topic/partition/offset
Grafana smoke alert name:
Kafka/EventSource evidence timestamp:
Downstream workflow result or explicit payload-shape caveat:
Cleanup completed:
```
