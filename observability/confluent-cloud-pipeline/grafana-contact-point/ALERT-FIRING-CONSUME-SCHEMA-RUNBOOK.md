# Grafana Kafka Alert Firing, Consume, And Schema Runbook

Use this after Grafana Alerting has successfully connected to Confluent Kafka
through the native `Kafka REST Proxy` contact point.

The goal is to prove three things in order:

```text
1. Grafana is really firing an alert, not only passing a contact point test.
2. Kafka consumers at the cluster side can read the produced events.
3. The actual record shape is captured before schema validation is enabled.
```

## Current Decision

The connection test proves authentication and reachability. It does not prove
that a real Grafana alert rule is evaluating, routing, and producing the record
shape downstream consumers expect.

For the work environment, treat the next phase as an evidence loop:

```text
Grafana rule fires
  -> notification policy routes to Kafka contact point
  -> Confluent topic receives record
  -> cluster-side consumer reads record
  -> payload is saved and inspected
  -> schema strategy is chosen
```

Do not turn broker-side schema validation back on until this loop has captured
at least one real firing record and one resolved/OK record, if resolved
notifications are enabled.

## Values To Collect

Use placeholders in docs and tickets; keep real values in the approved work
secret store.

```text
Grafana URL:                 {{GRAFANA_URL}}
Grafana contact point name:  {{GRAFANA_CONTACT_POINT_NAME}}
Grafana contact point UID:   {{GRAFANA_CONTACT_POINT_UID}}
Grafana folder UID:          {{GRAFANA_FOLDER_UID}}
Confluent bootstrap:         {{CONFLUENT_BOOTSTRAP}}
Confluent REST endpoint:     {{CONFLUENT_REST_ENDPOINT}}
Confluent cluster ID:        {{CONFLUENT_CLUSTER_ID}}
Confluent topic:             {{CONFLUENT_TOPIC}}
Kafka API key:               {{CONFLUENT_KAFKA_API_KEY}}
Kafka API secret:            {{CONFLUENT_KAFKA_API_SECRET}}
Consumer group prefix:       {{CONSUMER_GROUP_PREFIX}}
Schema Registry endpoint:    {{SCHEMA_REGISTRY_ENDPOINT}}
Schema subject:              {{CONFLUENT_TOPIC}}-value
```

## Phase 1 - Prove A Real Alert Fires

The Grafana contact point `Test` button is useful, but it is not enough. Create
a temporary Grafana-managed alert rule that always evaluates as firing and route
only that alert to the Kafka contact point.

Recommended temporary rule:

```text
Name:
  ConfluentKafkaFiringSmoke

Query:
  vector(1)

Condition:
  last() of query is above 0

Evaluation interval:
  1m

Labels:
  alertname = ConfluentKafkaFiringSmoke
  route_to = confluent-kafka-rest
  severity = warning
  environment = dev

Annotation:
  summary = Grafana to Confluent Kafka firing smoke
```

Recommended temporary notification policy:

```text
Match:
  route_to = confluent-kafka-rest

Contact point:
  {{GRAFANA_CONTACT_POINT_NAME}}
```

Evidence to capture from Grafana:

```text
Alert rule name:
Alert rule UID:
Alert state: firing
Evaluation timestamp:
Notification policy route:
Contact point name:
```

Wait at least one full evaluation interval before checking Kafka.

## Phase 2 - Consume The Record From Kafka

Use a fresh consumer group for each verification run so old offsets do not hide
new events.

### Option A - Confluent CLI

```bash
export CONFLUENT_TOPIC="{{CONFLUENT_TOPIC}}"
export CONFLUENT_CLUSTER_ID="{{CONFLUENT_CLUSTER_ID}}"

confluent kafka topic consume "$CONFLUENT_TOPIC" \
  --from-beginning \
  --group "verify-grafana-alert-$(date +%Y%m%d%H%M%S)" \
  --cluster "$CONFLUENT_CLUSTER_ID" \
  --print-offset
```

Stop after the `ConfluentKafkaFiringSmoke` record appears.

### Option B - kcat From A Workstation Or Debug Pod

Use this when the Confluent CLI is not available but `kcat` is allowed.

```bash
export CONFLUENT_BOOTSTRAP="{{CONFLUENT_BOOTSTRAP}}"
export CONFLUENT_TOPIC="{{CONFLUENT_TOPIC}}"
export CONFLUENT_KAFKA_API_KEY="{{CONFLUENT_KAFKA_API_KEY}}"
export CONFLUENT_KAFKA_API_SECRET="{{CONFLUENT_KAFKA_API_SECRET}}"

kcat -b "$CONFLUENT_BOOTSTRAP" \
  -X security.protocol=SASL_SSL \
  -X sasl.mechanisms=PLAIN \
  -X sasl.username="$CONFLUENT_KAFKA_API_KEY" \
  -X sasl.password="$CONFLUENT_KAFKA_API_SECRET" \
  -t "$CONFLUENT_TOPIC" \
  -C \
  -o end \
  -c 1 \
  -f 'topic=%t partition=%p offset=%o timestamp=%T\n%s\n'
```

Start this before toggling or re-firing the smoke alert if you only want the
next event.

### Option C - Argo Events EventSource

If the cluster side will consume through Argo Events, use an EventSource like
the existing example in this repo:

```text
observability/confluent-cloud-pipeline/management-cluster/01-eventsource-confluent.yaml
```

For native Grafana records, the EventSource should use:

```yaml
jsonBody: true
topic: "{{CONFLUENT_TOPIC}}"
consumerGroup:
  groupName: "{{CONSUMER_GROUP_PREFIX}}-grafana-alerts"
```

Then check the EventSource logs:

```bash
kubectl --context {{WORK_K8S_CONTEXT}} -n {{ARGO_EVENTS_NAMESPACE}} logs \
  -l eventsource-name={{CONFLUENT_EVENTSOURCE_NAME}} --tail=200
```

Look for the topic, partition, offset, and `ConfluentKafkaFiringSmoke`.

## Phase 3 - Save The Actual Payload

Save the raw consumed record as evidence before editing schemas or sensors:

```text
evidence/work-grafana-kafka-alert-{{YYYYMMDD-HHMMSS}}.json
```

Expected native Grafana Kafka record shape, based on the repo's previous
home-lab proof:

```json
{
  "client": "Grafana",
  "description": "[FIRING:1] ConfluentKafkaFiringSmoke ...",
  "details": "**Firing**\n\nValue: ...\nLabels:\n - alertname = ConfluentKafkaFiringSmoke\n",
  "alert_state": "alerting",
  "client_url": "https://{{GRAFANA_HOST}}/alerting/list",
  "incident_key": "{{GROUP_KEY_HASH}}"
}
```

Treat this as a starting point only. The real schema must come from the consumed
work record because Grafana version, alert templates, labels, and contact point
implementation can affect the shape.

Minimum fields to confirm:

```text
client
description
details
alert_state
client_url
incident_key
```

Useful values to record separately:

```text
topic:
partition:
offset:
Kafka timestamp:
Grafana alert name:
Grafana alert state:
payload SHA256:
```

## Phase 4 - Validate The Captured JSON Locally

This repo includes a draft consumer-side schema:

```text
observability/confluent-cloud-pipeline/grafana-contact-point/grafana-kafka-alert.schema.json
```

Validate a captured payload with Python:

```bash
python3 -m venv /tmp/grafana-kafka-schema-venv
/tmp/grafana-kafka-schema-venv/bin/pip install --quiet jsonschema

/tmp/grafana-kafka-schema-venv/bin/python - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

schema_path = Path("observability/confluent-cloud-pipeline/grafana-contact-point/grafana-kafka-alert.schema.json")
payload_path = Path("{{CAPTURED_PAYLOAD_JSON}}")

schema = json.loads(schema_path.read_text())
payload = json.loads(payload_path.read_text())

validator = Draft202012Validator(schema)
errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))

if errors:
    for error in errors:
        print(f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}")
    raise SystemExit(1)

print("payload validates against draft Grafana Kafka alert schema")
PY
```

If validation fails, update the draft schema to match the real work payload
before building downstream consumers.

## Phase 5 - Decide The Schema Validation Strategy

There are two different kinds of validation. Do not mix them up.

### Consumer-Side JSON Validation

This is the simplest next step:

```text
Kafka topic accepts Grafana's native record
  -> consumer reads JSON
  -> consumer validates fields with JSON Schema
  -> consumer routes or rejects locally
```

Use this when the immediate goal is to let the cluster-side consumer prove the
payload and routing logic.

Pros:

```text
- Works with Grafana's native Kafka contact point.
- Does not require Grafana to understand Schema Registry.
- Easy to iterate while confirming the alert payload shape.
```

Cons:

```text
- Bad records can still land on the topic.
- Rejection happens in the consumer, not at the broker.
```

### Confluent Broker-Side Schema ID Validation

Confluent Cloud broker-side schema validation is schema ID validation. It checks
that the produced record includes a Schema Registry schema ID in the Confluent
wire format and that the ID is valid for the configured subject. It does not
inspect arbitrary JSON and decide whether it matches a schema.

Reference:

- <https://docs.confluent.io/cloud/current/sr/broker-side-schema-validation.html>

This matters for native Grafana Kafka:

```text
Grafana native Kafka REST contact point
  -> sends Grafana-shaped JSON
  -> does not expose Schema Registry subject/schema ID controls
  -> may fail if topic value schema validation is enabled
```

If broker-side validation is mandatory, the safer architecture is:

```text
Grafana Alerting
  -> webhook contact point
  -> internal alert bridge / normalizer
  -> Schema Registry serializer
  -> Kafka topic with broker-side schema validation enabled
```

The bridge would own:

```text
1. Grafana payload normalization.
2. Schema Registry lookup or registration.
3. Serialization using Confluent wire format.
4. Kafka produce.
5. Retry and dead-letter handling.
```

## Phase 6 - Register A Draft Schema

Only register this after Phase 3 confirms the work payload shape.

Subject convention:

```text
{{CONFLUENT_TOPIC}}-value
```

Draft JSON Schema for consumer-side validation:

```text
observability/confluent-cloud-pipeline/grafana-contact-point/grafana-kafka-alert.schema.json
```

Schema Registry REST APIs are available for Confluent Cloud, including schema
registration and compatibility checks.

Reference:

- <https://docs.confluent.io/cloud/current/sr/sr-rest-apis.html>

Public-safe registration shape:

```bash
export SCHEMA_REGISTRY_ENDPOINT="{{SCHEMA_REGISTRY_ENDPOINT}}"
export SCHEMA_REGISTRY_API_KEY="{{SCHEMA_REGISTRY_API_KEY}}"
export SCHEMA_REGISTRY_API_SECRET="{{SCHEMA_REGISTRY_API_SECRET}}"
export CONFLUENT_TOPIC="{{CONFLUENT_TOPIC}}"

jq -Rs '{schemaType:"JSON", schema:.}' \
  observability/confluent-cloud-pipeline/grafana-contact-point/grafana-kafka-alert.schema.json \
  > /tmp/grafana-kafka-alert-schema-register.json

curl -sS -u "$SCHEMA_REGISTRY_API_KEY:$SCHEMA_REGISTRY_API_SECRET" \
  -X POST \
  "$SCHEMA_REGISTRY_ENDPOINT/subjects/${CONFLUENT_TOPIC}-value/versions" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary @/tmp/grafana-kafka-alert-schema-register.json
```

Registering a schema does not automatically make Grafana emit Schema Registry
wire-format records. It only creates the schema contract. Broker-side validation
still requires the producer path to include the schema ID in the produced bytes.

## Phase 7 - Cluster-Side Consumer Contract

For the first cluster-side consumer, keep the filter simple:

```text
client == Grafana
alert_state == alerting
description contains expected alert name, or details contains expected label
```

Do not reuse the existing bridge-specific filter unless you normalize the
payload first. The bridge envelope expects:

```text
body.source
body.alertmanager.status
body.alertmanager.alerts
```

Native Grafana Kafka records instead use:

```text
body.client
body.description
body.details
body.alert_state
body.client_url
body.incident_key
```

For Argo Events, this means a native Grafana Sensor should filter on:

```yaml
filters:
  data:
    - path: body.client
      type: string
      value:
        - "Grafana"
    - path: body.alert_state
      type: string
      value:
        - "alerting"
```

Then pass either the full body or selected fields into the downstream workflow.

## Completion Checklist

```text
[ ] Grafana contact point still tests successfully.
[ ] Temporary always-firing alert rule created.
[ ] Alert state observed as firing in Grafana.
[ ] Kafka record consumed with topic/partition/offset.
[ ] Raw payload saved as evidence.
[ ] Draft schema validated against raw payload.
[ ] Resolved/OK record captured, or resolved notifications explicitly disabled.
[ ] Cluster-side consumer path chosen: CLI, Argo Events, service, or bridge.
[ ] Native Grafana Sensor or normalizer decision recorded.
[ ] Broker-side schema validation decision recorded.
[ ] Temporary alert rule and route cleaned up.
```

## Recommended Next Decision

Use consumer-side JSON validation first. It will prove the real Grafana record
shape and unblock cluster-side consumption.

Only turn Confluent broker-side schema validation back on after one of these is
true:

```text
1. The Grafana native Kafka contact point is proven to produce Schema Registry
   wire-format records accepted by Confluent schema ID validation.
2. A bridge/normalizer is introduced and it serializes records with Schema
   Registry support before producing to Kafka.
```

Based on the current evidence, expect option 2 to be the production-safe path if
broker-side schema validation is mandatory.
