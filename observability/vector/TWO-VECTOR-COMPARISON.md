# One Vector vs Two Vector Alert Pipeline

This note compares two possible Grafana alert ingestion designs for the
Confluent / Vector / Argo path.

The key question is whether Grafana should publish directly to Kafka and let one
Vector pipeline normalize the record, or whether Grafana should send a webhook
to a first Vector instance, then a second Vector instance consumes from Kafka
before Argo.

## Option A - Kafka First, One Vector

This is the simpler recommended platform path.

```text
Grafana Alerting
  -> Kafka REST Proxy contact point
  -> Confluent raw topic: alertmanager-events
  -> Vector
  -> Confluent triage topic: alertmanager-events-triage
  -> Argo Events Kafka EventSource
  -> Argo Sensor
  -> Argo Workflow
```

What Vector owns:

```text
source: kafka alertmanager-events
transform: parse / normalize / filter / short-window dedupe
sink: kafka alertmanager-events-triage
```

Why this is attractive:

- Grafana can produce directly with the Kafka REST Proxy contact point.
- Kafka captures the raw alert before any transformation.
- Vector can catch up from Kafka if it restarts.
- There is one Vector runtime to deploy, monitor, and upgrade.
- Argo consumes only the cleaned topic.
- Replay and audit are straightforward.

Main tradeoff:

- Grafana needs Kafka REST endpoint access and a scoped Kafka API key/secret.

Use this when the Kafka contact point is allowed and the team wants the fewest
moving parts.

## Option B - Two Vector Instances

This is the colleague-proposed split: Grafana sends to Vector first, then Kafka,
then another Vector, then Kafka again for Argo.

```text
Grafana Alerting
  -> Webhook contact point
  -> Vector A: HTTP ingress / producer
  -> Confluent raw topic: grafana-alerts-raw
  -> Vector B: Kafka consumer / normalizer / router
  -> Confluent triage topic: alertmanager-events-triage
  -> Argo Events Kafka EventSource
  -> Argo Sensor
  -> Argo Workflow
```

Vector A owns ingress:

```text
source: http_server
transform: parse Grafana webhook payload, add metadata
sink: kafka grafana-alerts-raw
```

Vector B owns automation shaping:

```text
source: kafka grafana-alerts-raw
transform: normalize / filter / dedupe / schema check
sink: kafka alertmanager-events-triage
```

The two Vector instances should communicate through Kafka, not through an
internal Vector-to-Vector link. Kafka gives the handoff a durable replay point
and keeps each Vector instance independently movable.

## How The Two-Vector Design Would Look

```text
┌────────────────────┐
│ Grafana Alerting   │
│ webhook contact    │
└─────────┬──────────┘
          │ HTTP webhook
          v
┌────────────────────┐
│ Vector A           │
│ ingress producer   │
│ http -> kafka      │
└─────────┬──────────┘
          │ Kafka produce
          v
┌────────────────────┐
│ Kafka raw topic    │
│ grafana-alerts-raw │
└─────────┬──────────┘
          │ Kafka consume
          v
┌────────────────────┐
│ Vector B           │
│ normalizer/router  │
│ kafka -> kafka     │
└─────────┬──────────┘
          │ Kafka produce
          v
┌────────────────────────────┐
│ Kafka triage topic         │
│ alertmanager-events-triage │
└─────────┬──────────────────┘
          │ Kafka consume
          v
┌────────────────────┐
│ Argo EventSource   │
│ Argo Sensor        │
│ Argo Workflow      │
└────────────────────┘
```

## When Two Vector Instances Help

The split has value only if there is a concrete operational reason:

- Grafana must not hold Kafka credentials.
- Grafana must use a webhook contact point for policy reasons.
- OAuth, custom auth, or network controls are easier in Vector A.
- Ingress and normalization are owned by different teams.
- The ingress component may move closer to Grafana later.
- The normalizer may move closer to Argo later.
- Independent rollout or scaling is required.
- A bad normalizer rollout should not break Grafana's ability to land raw
  events in Kafka.

## Costs Of Two Vector Instances

- Two Vector deployments to operate.
- More credentials and network policy.
- Extra Kafka topic.
- Extra latency.
- More dashboards and alerts.
- More failure modes.
- Harder debugging because an alert now crosses more boundaries.
- More decisions about which component owns schema changes.

## Recommendation

Start with Option A unless the team can name the specific reason that Grafana
must send to Vector first.

If the team chooses Option B, make Kafka the contract between the two Vector
instances:

```text
Vector A -> Kafka raw topic -> Vector B -> Kafka triage topic -> Argo
```

Avoid a direct Vector-to-Vector HTTP hop. It removes the durable replay point and
makes the split harder to debug.

The real design decision is not "consumer Vector" versus "producer Vector".
Vector is naturally source -> transform -> sink in one runtime. The useful split
is by ownership, credential boundary, network placement, or blast radius.
