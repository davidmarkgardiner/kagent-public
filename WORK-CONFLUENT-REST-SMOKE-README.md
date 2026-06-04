# Work Confluent REST Smoke Test

Use this to prove the work Confluent Dev endpoint, credentials, cluster ID, and
topic write permission before wiring Grafana, Alertmanager, or Argo Events.

## Inputs

Set these from the Confluent onboarding email or work secret store:

```bash
export CONFLUENT_REST_ENDPOINT='{{CONFLUENT_REST_ENDPOINT}}'
export CONFLUENT_CLUSTER_ID='{{CONFLUENT_CLUSTER_ID}}'
export CONFLUENT_TOPIC='{{CONFLUENT_TOPIC}}'
export CONFLUENT_API_KEY='{{CONFLUENT_API_KEY}}'
export CONFLUENT_API_SECRET='{{CONFLUENT_API_SECRET}}'
```

Notes:

- `CONFLUENT_REST_ENDPOINT` is the Kafka REST endpoint, not the broker bootstrap endpoint.
- Do not commit API keys or secrets. Use a local shell, password manager, or approved secret store.
- For Confluent Cloud REST v3, the request URL includes `/kafka/v3/...`.

## Payload

The REST API expects a Kafka record wrapper. Put the test message inside
`value.data`:

```json
{
  "key": {
    "type": "STRING",
    "data": "work-rest-smoke-001"
  },
  "value": {
    "type": "JSON",
    "data": {
      "source": "manual-rest-smoke",
      "status": "firing",
      "message": "Confluent REST v3 connectivity smoke",
      "environment": "dev"
    }
  }
}
```

## Curl Test

```bash
curl -sS \
  -u "$CONFLUENT_API_KEY:$CONFLUENT_API_SECRET" \
  -X POST \
  "${CONFLUENT_REST_ENDPOINT%/}/kafka/v3/clusters/${CONFLUENT_CLUSTER_ID}/topics/${CONFLUENT_TOPIC}/records" \
  -H "Content-Type: application/json" \
  --data '{
    "key": {
      "type": "STRING",
      "data": "work-rest-smoke-001"
    },
    "value": {
      "type": "JSON",
      "data": {
        "source": "manual-rest-smoke",
        "status": "firing",
        "message": "Confluent REST v3 connectivity smoke",
        "environment": "dev"
      }
    }
  }' | jq .
```

## Expected Success

```json
{
  "error_code": 200,
  "topic_name": "{{CONFLUENT_TOPIC}}",
  "partition_id": 0,
  "offset": 123,
  "timestamp": "2026-06-04T00:00:00.000Z",
  "key": {
    "type": "STRING",
    "size": 19
  },
  "value": {
    "type": "JSON",
    "size": 120
  }
}
```

The exact `partition_id`, `offset`, `timestamp`, and `size` values will differ.
The important fields are:

```text
HTTP status: 2xx
error_code: 200
topic_name: expected topic
partition_id: present
offset: present
```

## Troubleshooting

```text
401 or 403:
  Credentials are wrong, expired, or not authorized for this cluster/topic.

404:
  Check the REST endpoint, cluster ID, topic name, and the /kafka/v3 path.

error_code not 2xx:
  The REST request reached Confluent, but Kafka produce failed. Check topic ACLs.

curl cannot connect:
  Network path, proxy, firewall, or endpoint hostname issue.

JSON parse or schema error:
  Confirm the request body uses key/value wrappers with type/data fields.
```

## Evidence To Capture

Record a redacted result like:

```text
date:
environment: dev
REST endpoint host: redacted
cluster ID: redacted
topic:
HTTP status:
error_code:
partition_id:
offset:
operator:
```

