# Confluent PoC Onboarding Feedback

This note is a public-safe, copyable feedback message for the Confluent team.
It focuses on making early proof-of-concept onboarding faster before teams enter
the full production onboarding process.

## TLDR

For early validation, teams need a lightweight Confluent Kafka PoC path that can
be completed within 24 hours:

- basic Kafka REST endpoint
- temporary test topic
- API key and secret with produce access
- minimal example payload
- schema validation disabled at first, or a starter schema supplied up front

Once the proof of concept works, the team can move through the normal production
onboarding, approvals, access model, schema controls, and operational handoff.

## Suggested PoC Onboarding Shape

The ideal first step is a short-lived sandbox rather than a production-grade
setup:

```text
Requester -> PoC request -> temporary Kafka REST endpoint/topic/API key
          -> connectivity and payload test
          -> schema validation test
          -> decision on production onboarding
```

Suggested defaults:

```text
Environment:
  dev / sandbox

Lifetime:
  24 to 72 hours, or auto-delete nightly if preferred

Access:
  produce-only API key scoped to the test topic

Topic:
  {{POC_TOPIC_NAME}}

REST endpoint:
  https://{{CONFLUENT_REST_ENDPOINT}}/kafka

Cluster ID:
  {{CONFLUENT_CLUSTER_ID}}

Schema:
  disabled initially, or a simple starter schema supplied with the topic

Evidence expected from requester:
  HTTP 200 from a produce request
  Kafka topic/partition/offset returned
  sample payload captured
  schema compatibility decision recorded
```

This gives both sides a fast signal on whether Confluent is a good fit for the
use case before everyone spends time on the full production process.

## Teams Message

```text
Hi Confluent team,

A bit of feedback from our onboarding experience so far.

For early-stage validation, it would be really helpful if there were a
lightweight PoC onboarding path where a team could quickly get:

- a basic Kafka REST endpoint
- a test topic
- API key / secret for producing messages
- simple example payloads
- optional schema validation switched off initially, or a very basic starter
  schema

The goal would be to let teams prove within 24 hours whether the integration is
a good fit before going through the full production onboarding process.

At the moment, we have been in Teams conversations for around two weeks, with
forms, approvals, repeated configuration questions, and daily calls. I
understand the full process may be required for production, but for a proof of
concept it makes the process feel much heavier than it needs to be.

A short-lived sandbox would probably solve most of this. For example, Confluent
could provision temporary topics/API keys that expire or are deleted nightly,
allowing teams to test connectivity, authentication, payload shape, and schema
requirements quickly. Once the PoC is proven, we can then move into the proper
production onboarding process with the right controls.

This would make it much easier for teams to validate Confluent quickly and
reduce friction on both sides.
```

## What The PoC Should Prove

Minimum success criteria:

```text
1. REST endpoint is reachable from the requester environment.
2. API key and secret authenticate successfully.
3. API key has produce permission for the test topic.
4. A simple JSON payload can be written successfully.
5. Topic, partition, and offset are returned by the produce call.
6. Schema requirements are understood before production onboarding starts.
```

The first test does not need to prove the final production schema, routing, or
full operational process. It only needs to prove that the integration path is
viable.

## Example Connectivity Test

The requester should be able to run a basic test like this after receiving the
PoC endpoint, topic, cluster ID, API key, and API secret:

```bash
curl -sS -o /tmp/confluent-poc-smoke.out -w 'HTTP=%{http_code}\n' \
  -u "$CONFLUENT_API_KEY:$CONFLUENT_API_SECRET" \
  -X POST \
  "${CONFLUENT_REST_ENDPOINT%/}/kafka/v3/clusters/${CONFLUENT_CLUSTER_ID}/topics/${CONFLUENT_TOPIC}/records" \
  -H "Content-Type: application/json" \
  --data '{"value":{"type":"JSON","data":{"source":"poc-smoke","message":"connectivity test"}}}'

cat /tmp/confluent-poc-smoke.out
```

Expected result:

```text
HTTP=200
error_code=200
topic_name={{CONFLUENT_TOPIC}}
partition_id=<present>
offset=<present>
```

If this fails with HTTP `401`, the onboarding is not yet complete from the
requester's perspective because the supplied credentials do not authenticate for
Kafka REST produce.

## Why This Helps

This separates two different needs:

```text
PoC onboarding:
  fast validation, temporary topic, scoped key, simple payload, quick feedback

Production onboarding:
  approvals, permanent access, schema governance, monitoring, support model,
  ownership, retention, and operational controls
```

Keeping those paths separate should reduce repeated forms, recurring calls, and
back-and-forth setup questions while still preserving the controls needed for
production.
