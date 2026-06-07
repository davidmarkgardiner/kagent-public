# Grafana Alerting To Kafka With OAuth

This note captures the current decision for connecting Grafana Alerting to
Confluent Kafka when a Kafka API key/secret is not available in the work
environment.

## TLDR

Grafana's native `Kafka REST Proxy` contact point does not currently expose an
OAuth client-credentials flow.

The native Kafka contact point is designed around:

```text
Kafka REST Proxy URL
Topic
Username
Password
API version
Cluster ID
```

That means this path is expected to work:

```text
Grafana Alerting
  -> Kafka REST Proxy contact point
  -> Confluent Kafka REST endpoint
  -> Basic auth with Confluent Kafka API key and secret
```

This path is not supported directly by the native Kafka contact point:

```text
Grafana Alerting
  -> Kafka REST Proxy contact point
  -> OAuth client credentials token request
  -> Confluent Kafka REST endpoint
```

If the work environment cannot issue or use a Confluent Kafka API key/secret,
the practical design is to put a small internal bridge between Grafana and
Confluent.

## Evidence Checked

Grafana's published contact point documentation lists `Kafka REST Proxy` as a
supported contact point integration, but each integration owns its own supported
settings:

- <https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/>

The current Grafana alerting Kafka receiver schema exposes these Kafka fields:

```text
kafkaRestProxy
kafkaTopic
username
password
apiVersion
kafkaClusterId
```

It does not expose OAuth fields such as:

```text
client_id
client_secret
token_url
scope
audience
grant_type
token refresh settings
```

Reference:

- <https://pkg.go.dev/github.com/grafana/alerting/receivers/kafka/v1>

Grafana's generic webhook contact point can send either HTTP Basic auth or an
`Authorization` header credential. That can be useful for calling an internal
bridge, but it is still not the same as Grafana performing an OAuth
client-credentials token exchange and refresh cycle itself.

Reference:

- <https://grafana.com/docs/grafana-cloud/alerting-and-irm/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/>

## Recommended Design If OAuth Is Required

Use Grafana's generic webhook contact point and send alerts to a small internal
bridge service:

```text
Grafana Alerting
  -> Webhook contact point
  -> internal Kafka alert bridge
  -> OAuth client-credentials token request
  -> Confluent Kafka REST API or Kafka producer
  -> Kafka topic
```

The bridge owns the parts Grafana cannot currently do natively:

```text
1. OAuth client-credentials token acquisition.
2. Token caching and refresh.
3. Grafana alert payload normalization.
4. Schema Registry serialization, if schema validation is enabled.
5. Kafka produce call.
6. Retry, timeout, and dead-letter behavior.
7. Redacted request/response evidence for support.
```

## Why A Bridge Is Probably Better For Work

The bridge is more moving parts than the native contact point, but it gives us
control over the production concerns that are already appearing in testing:

```text
Authentication:
  OAuth client credentials can be handled outside Grafana.

Schema:
  Grafana's native Kafka payload can be converted into the exact schema expected
  by the Confluent topic.

Debugging:
  The bridge can log redacted status codes, Kafka topic/partition/offset, and
  schema errors.

Operations:
  Retries, dead-letter records, and support handoff can be made explicit.
```

## What To Ask The Platform / Confluent Team

There are two viable routes:

```text
Option A - Native Grafana Kafka contact point
  Provide a scoped Confluent Kafka API key and secret for the target topic.
  This is the simplest path if API keys are allowed.

Option B - Webhook plus bridge
  Confirm OAuth client-credentials details for a bridge service:
    - token URL
    - client ID
    - client secret source
    - scopes / audience
    - Confluent REST endpoint
    - cluster ID
    - topic
    - schema requirements
```

If API keys are blocked by policy, Option B is the realistic path.

## Teams Message

```text
Hi team,

I've checked the Grafana Alerting Kafka REST Proxy path again.

The native Grafana Kafka REST Proxy contact point appears to support the
standard Kafka REST fields:

- Kafka REST Proxy URL
- topic
- username
- password
- API version
- cluster ID

I cannot see support for an OAuth client-credentials flow in that native Kafka
contact point. In other words, Grafana does not appear to have fields for token
URL, client ID, client secret, scope/audience, token refresh, etc. So if we
cannot use a Confluent Kafka API key/secret at work, I do not think the native
Grafana Kafka contact point will connect directly using OAuth today.

The practical fallback would be:

Grafana Alerting -> Webhook contact point -> internal bridge service ->
OAuth client-credentials flow -> Confluent Kafka REST/Kafka producer -> topic

That bridge would handle token acquisition/refresh, payload transformation,
schema serialization if required, Kafka produce, retries, and redacted logging.

So the decision point is:

1. If the platform/Confluent team can provide a scoped Kafka API key/secret for
   the topic, we can use the native Grafana Kafka REST Proxy contact point.
2. If API keys are blocked and OAuth is mandatory, we should build or request a
   small bridge service and use Grafana's webhook contact point instead.

My recommendation is to ask for a clear answer on whether a scoped Confluent
Kafka API key/secret can be issued for this integration. If not, we should stop
trying to force the native Kafka contact point and move to the webhook-plus-
bridge design.
```

## Open Questions

```text
1. Is a scoped Confluent Kafka API key/secret allowed for Grafana?
2. If not, what OAuth token endpoint, scopes, and audience should a bridge use?
3. Is the target endpoint Confluent Kafka REST v3, another REST facade, or a
   standard Kafka broker producer path?
4. Will schema validation be enabled for the final topic?
5. If schema validation is enabled, which service should own serialization:
   Grafana, a bridge service, or an upstream event-normalization service?
```
