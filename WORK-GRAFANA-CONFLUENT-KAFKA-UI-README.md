# Work Grafana Kafka REST Proxy UI Setup

Use this when configuring a Grafana Alerting contact point to publish alerts to
Confluent Cloud through the `Kafka REST Proxy` integration.

This is separate from the raw REST smoke test. The smoke test proves the
endpoint and credentials. This README maps those same values into the Grafana
UI.

## Values You Need

Collect these from the Confluent onboarding email, Confluent Cloud UI, or the
working raw REST test:

```text
Confluent REST endpoint:  {{CONFLUENT_REST_ENDPOINT}}
Confluent cluster ID:     {{CONFLUENT_CLUSTER_ID}}
Kafka topic:              {{CONFLUENT_TOPIC}}
Kafka API key / username: {{CONFLUENT_API_KEY}}
Kafka API secret:         {{CONFLUENT_API_SECRET}}
```

Example shapes:

```text
Confluent REST endpoint:
  https://{{PKC_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud:443

Confluent cluster ID:
  lkc-{{CLUSTER_ID}}

Kafka topic:
  {{DEV_ALERTS_TOPIC}}

Kafka API key / username:
  {{CONFLUENT_KAFKA_API_KEY}}

Kafka API secret:
  {{CONFLUENT_KAFKA_API_SECRET}}
```

## Grafana UI Fields

Grafana path:

```text
Alerting -> Contact points -> New contact point
```

Fill the contact point like this:

```text
Name:
  confluent-kafka-rest-dev

Integration:
  Kafka REST Proxy

Kafka REST Proxy:
  {{CONFLUENT_REST_ENDPOINT}}/kafka

Topic:
  {{CONFLUENT_TOPIC}}

Username:
  {{CONFLUENT_API_KEY}}

Password:
  {{CONFLUENT_API_SECRET}}

API version:
  v3

Cluster ID:
  {{CONFLUENT_CLUSTER_ID}}
```

Concrete placeholder example:

```text
Name:
  confluent-kafka-rest-dev

Integration:
  Kafka REST Proxy

Kafka REST Proxy:
  https://{{PKC_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud:443/kafka

Topic:
  {{DEV_ALERTS_TOPIC}}

Username:
  {{CONFLUENT_KAFKA_API_KEY}}

Password:
  {{CONFLUENT_KAFKA_API_SECRET}}

API version:
  v3

Cluster ID:
  lkc-{{CLUSTER_ID}}
```

## Important Endpoint Rules

Use the REST endpoint, not the broker endpoint:

```text
Correct:
  https://{{PKC_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud:443/kafka

Wrong:
  SASL_SSL://{{PKC_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud:9092

Wrong:
  {{PKC_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud:9092
```

Do not paste the full produce URL into Grafana. Grafana builds that itself.

```text
Correct Grafana field:
  https://{{PKC_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud:443/kafka

Wrong Grafana field:
  https://{{PKC_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud:443/kafka/v3/clusters/{{CLUSTER_ID}}/topics/{{TOPIC}}/records
```

Do not use the Schema Registry endpoint in this field:

```text
Wrong:
  https://{{SCHEMA_REGISTRY_ID}}.{{REGION}}.{{CLOUD}}.confluent.cloud
```

## Which Credentials Go In Username And Password?

Use the exact pair that succeeds with the raw REST produce test:

```bash
curl -u "$CONFLUENT_API_KEY:$CONFLUENT_API_SECRET" \
  -X POST \
  "${CONFLUENT_REST_ENDPOINT%/}/kafka/v3/clusters/${CONFLUENT_CLUSTER_ID}/topics/${CONFLUENT_TOPIC}/records" \
  -H "Content-Type: application/json" \
  --data '{"value":{"type":"JSON","data":{"source":"smoke"}}}'
```

If that command succeeds, then in Grafana:

```text
Username = $CONFLUENT_API_KEY
Password = $CONFLUENT_API_SECRET
```

If your team says "SPN credentials", confirm what that means:

```text
Works in Grafana:
  Confluent Kafka API key + API secret for the target Kafka cluster.

Usually does not work directly in Grafana:
  Azure client ID + Azure client secret, unless Confluent has explicitly made
  those exact values valid as Basic auth credentials for the Kafka REST API.
```

If Azure SPN credentials are only used to obtain Confluent credentials, Grafana
needs the resulting Confluent Kafka API key and secret, not the Azure SPN pair.

## What Grafana Sends

Grafana sends a Confluent REST v3 produce request to:

```text
{{CONFLUENT_REST_ENDPOINT}}/kafka/v3/clusters/{{CONFLUENT_CLUSTER_ID}}/topics/{{CONFLUENT_TOPIC}}/records
```

The record value is Grafana-shaped JSON, roughly:

```json
{
  "client": "Grafana",
  "description": "[FIRING:1] AlertName ...",
  "details": "**Firing**\n\nValue: B=1, C=1\nLabels:\n - alertname = AlertName\n - severity = warning\nAnnotations:\n - summary = Example alert\n",
  "alert_state": "alerting",
  "client_url": "https://{{GRAFANA_HOST}}/alerting/list",
  "incident_key": "{{GROUP_KEY_HASH}}"
}
```

This is why a dev topic with schema validation disabled is the easiest first
test. Broker-side schema validation expects Confluent Schema Registry wire
format, not only a JSON object that looks valid.

## If Grafana Gives 401

Most likely causes:

```text
1. Username/password are not the Confluent Kafka API key and secret.
2. Credentials are for Schema Registry, not Kafka REST produce.
3. Credentials are for a different Confluent environment or cluster.
4. The API key has no write permission for the topic.
5. Azure SPN client ID/secret were entered instead of Confluent Kafka API credentials.
6. There is a proxy/security layer in front of the REST endpoint requiring different auth.
```

Fast isolation test:

```bash
curl -sS -o /tmp/confluent-test.out -w 'HTTP=%{http_code}\n' \
  -u "$CONFLUENT_API_KEY:$CONFLUENT_API_SECRET" \
  -X POST \
  "${CONFLUENT_REST_ENDPOINT%/}/kafka/v3/clusters/${CONFLUENT_CLUSTER_ID}/topics/${CONFLUENT_TOPIC}/records" \
  -H "Content-Type: application/json" \
  --data '{"value":{"type":"JSON","data":{"source":"grafana-auth-smoke"}}}'

cat /tmp/confluent-test.out
```

Expected:

```text
HTTP=200
error_code=200
topic_name={{CONFLUENT_TOPIC}}
partition_id=<present>
offset=<present>
```

Interpretation:

```text
curl succeeds, Grafana fails:
  Check the exact Grafana fields, Grafana server egress/proxy, and whether the
  Grafana instance can reach the Confluent REST endpoint.

curl returns 401:
  The credentials are wrong for Kafka REST API Basic auth.

curl returns 403 or Confluent error about authorization:
  The credentials authenticate but lack topic write permission.

curl returns 404:
  Endpoint, /kafka path, cluster ID, or topic name is wrong.
```

## Minimal Evidence To Capture

```text
Grafana contact point name:
Kafka REST Proxy host: redacted
Topic:
Cluster ID: redacted
Username type: Confluent Kafka API key / other
Grafana test result:
Raw curl result:
HTTP status:
Confluent error_code:
partition_id:
offset:
```

