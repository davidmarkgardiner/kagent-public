# Work Kafka Onboarding Guide for kagent Triage

## Short answer

Yes: the **onboard producer/topic** and **add consumer group** forms are the
things needed to give the kagent triage pipeline permission to publish and
read Kafka records. They are necessary infrastructure onboarding, but they do
not by themselves build the triage flow or prevent duplicate incidents.

For the intended design, do **not** create a topic for every application,
namespace, agent, or alert. Create a small set of contract topics, grant the
right producer and consumer identities access to them, then configure Alloy,
Vector, and Argo to use those records. A dedicated ingress/router is a later
option when cross-source correlation needs to be stronger than source
separation and workflow-level suppression.

```text
work portal                         runtime configuration
-----------                         ---------------------
producer onboarding   -> identity can write a named Kafka topic
topic onboarding      -> topic, retention, partitions, schema, ACL boundary
consumer onboarding   -> identity can read a topic under a named group

Alloy / Alertmanager / Vector / Argo
                       -> actually produce, normalize, consume, and create
                          read-only kagent triage work
```

This guide explains the likely meaning of the work dashboard fields. The
labels `identity pool`, `strategy`, and `schema configuration` can be
organisation-specific, so confirm their exact meanings with the Kafka platform
owner before submitting a production request.

## What each dashboard field means

### Onboard new producer / topic

| Portal field | What it normally represents | What it should mean for this design |
|---|---|---|
| **Producer application** | The logical application allowed to publish records. It is not the human team and not normally a single Kubernetes pod. | `kagent-triage-vector-evidence` for the Vector evidence publisher; an existing Alertmanager producer for metric alerts if it is already approved. |
| **Cluster** | The Kafka/Confluent cluster where the topic lives, not necessarily the AKS workload cluster. | Select the approved shared Confluent cluster that the management triage path can reach. |
| **Identity pool mapped** | The platform’s identity binding from a workload identity, service principal, or Kubernetes workload/service account to Kafka credentials/permissions. | Map the identity actually used by Vector or the Alertmanager bridge. Do not map the kagent chat agent to Kafka write access. |
| **Topic name** | The Kafka stream where records are published. | Use a stable contract topic, for example `kagent.triage.evidence.v1`; do not include a namespace, pod, or agent name. |
| **Topic naming strategy** | Usually a platform convention or template that governs prefix, environment, ownership, and version. It is not message routing. | Use the approved observability/platform prefix and a version suffix. Keep environment as a message field unless the platform requires hard topic isolation. |
| **Topic strategy** | Usually retention/cleanup, partitioning, replication, or a product-specific tier. The portal owner must confirm the exact controls. | Use a durable event-stream policy suitable for replay; do not use compaction alone for raw events/logs. |
| **Schema configuration** | Schema Registry / validation settings for messages on the topic. | Register or approve the input schema and a separate normalized triage-request schema. Do not turn on strict broker validation until the producer serializer is proven compatible. |

### Add consumer group

| Portal field | What it normally represents | What it should mean for this design |
|---|---|---|
| **Consumer application name** | The logical service that reads records. It is not an individual user. | `kagent-triage-ingress` for the normalizer/router, or `kagent-triage-argo` for the Argo EventSource. |
| **Cluster** | The Kafka/Confluent cluster containing the topic. | The same approved shared cluster selected for the source topic. |
| **Service account** | The Kafka principal/credential used by the consumer application. It is distinct from Kubernetes RBAC unless the platform maps workload identity to it. | A dedicated read-only Kafka principal for the router or Argo EventSource. It must not be a broad shared producer credential. |
| **Group** | The stable Kafka consumer-group ID: shared offset/cursor and load-balancing domain. | `kagent-triage-ingress-v1` or `kagent-triage-argo-v1`. Keep it stable across restarts and horizontally scaled replicas. |
| **Topic/subscription** (if shown) | Which topic(s) that group can read. | Router reads the metric and evidence input topics; Argo reads normalized triage requests only. |
| **Start position / offset reset** (if shown) | What happens when the group has no committed offset. | Use `latest` for a production cutover unless an approved bounded replay is intended. A new group can otherwise process historical backlog. |

## The terms that matter most

### Topic

A topic is a durable named stream of records. It is a contract and a security
boundary, not a filter. Every record written to a topic is available to a
consumer group that has access and subscribes to it.

### Producer application and identity pool

The producer application is the label for the runtime that writes records. The
identity-pool mapping is how the platform proves that runtime is allowed to
use the Kafka identity. The mapping should follow the workload that publishes:

```text
Alloy -> Vector workload identity -> Vector Kafka producer identity
Alertmanager bridge -> bridge workload identity -> Alertmanager Kafka producer identity
```

The kagent triage agent itself should not receive Kafka producer permissions;
it analyses an already-created request. Any resource-changing action remains
behind an approved workflow service account.

### Consumer group

A consumer group is a shared cursor and work-sharing boundary for one logical
consumer application:

- Multiple replicas using the **same** group share partitions; one record is
  handled by one active member of that group.
- A different group receives its own copy of the topic and maintains its own
  offsets.
- Consumer groups do **not** filter records, route by message type, or dedupe
  a metric alert and an event/log record that describe the same outage.

Do not create a fresh production group on every deployment. A new group has no
previous offsets and may read retained backlog, causing old incidents to be
processed again. Use a temporary, clearly named group only for a controlled
smoke test or replay.

### Schema configuration

A schema says what fields a record must contain and what types they have. It
protects the consumer from an accidental producer change. It does not enrich a
record or decide whether a signal is actionable.

For this design there are three useful schema contracts:

| Contract | Producer | Minimum purpose |
|---|---|---|
| Metric input | Alertmanager bridge/normalizer | Identifies an Alertmanager metric alert, fingerprint, labels, status, cluster, and time. |
| Evidence input | Vector | Identifies a Kubernetes event or allow-listed log, source record ID, workload context, event reason/log signature, and time. |
| Normalized triage request | ingress/router | Carries one `incident_id`, `incident_key`, source types, route, bounded evidence, and read-only automation state to Argo. |

Prefer a versioned JSON/Avro/Protobuf contract according to the platform
standard and a backward-compatible evolution policy. Avoid adding raw log
payloads, secrets, request bodies, or unrestricted high-cardinality labels to
the schema or the Kafka message.

## What we need for the kagent setup

The target setup has two source lanes and one triage request lane. This is the
minimum onboarding map; actual names must follow the work platform naming
standard.

## Reported current view and the change to make

The following uses placeholders for values reported from the onboarding
dashboard; it is not independently verified from the broker.

| Item | Current reported value | What it means |
|---|---|---|
| Broker | `{{KAFKA_BROKER}}:9092` | The Kafka broker endpoint. It is connection detail, not a routing or dedupe control. |
| Topic | `{{METRIC_ALERT_TOPIC}}` | One current shared stream of critical-alert records. |
| Consumer group | `{{METRIC_TRIAGE_CONSUMER_GROUP}}` | The Argo Events read cursor/load-sharing group for that topic. It is not an alert filter or a duplicate-control mechanism. |

Important terminology check: producers do not normally “listen to a consumer
group.” Alertmanager sends into a Vector normalizer, and Vector publishes to
Kafka; the Argo EventSource normally **reads the topic using the consumer
group**. Confirm the exact EventSource and Sensor mapping in the portal before
changing anything.

### Current shape: one direct triage input

```text
Alertmanager metric alerts -> Vector normalizer ─┐
                                                  ├-> {{METRIC_ALERT_TOPIC}}
Vector events/logs -> Vector direct to Kafka ────┘                         |
                                                                         v
                  {{METRIC_TRIAGE_CONSUMER_GROUP}}
                                              |
                                              v
                                       Argo -> kagent triage
```

This is the overlap to unwind: the Vector-normalized metric stream and the
direct Vector evidence stream can put different signal classes into the same
direct-to-Argo path. The group will not tell Argo which source should own an
incident, and it cannot suppress two different records that describe the same
outage.

### Immediate target: two source-specific Argo paths

```text
Alertmanager metrics -> Vector normalizer -> current critical-alert topic
                                                  |
                                      current Argo consumer group -> metric triage Sensor

Vector events/logs -> NEW evidence-input topic
                                                  |
                                      NEW Argo consumer group -> evidence triage Sensor
```

This needs no new product called an “ingress router.” It creates an exclusive
source boundary first: Alertmanager through Vector owns metrics; direct Vector
owns events/logs. Both flows can call a shared read-only triage
WorkflowTemplate, provided the payload has an explicit `signal_class` and a
stable incident/dedupe key.

### Paste-ready onboarding text

**Business justification**

> Create a dedicated Kafka topic and Argo Events consumer group for the direct
> Vector event and log evidence stream used by kagent triage. This separates
> Kubernetes event/log evidence from the existing Alertmanager metric-alert
> stream, preserving event reason and bounded, redacted context for faster
> read-only triage. The change reduces false duplicate workflow triggers caused
> by mixing the two signal classes on one topic, while leaving the existing
> metric-alert path unchanged.

**Topic name**

> `{{KAFKA_PREFIX}}.uk8s.lgtm.triageevidence`

Use the work platform's approved value for `{{KAFKA_PREFIX}}`. This follows
the existing topic naming shape without placing a real environment or company
identifier in public documentation.

**Topic description**

> Carries normalized, redacted Kubernetes Warning events and allow-listed
> application/platform error-log evidence produced by the direct Vector Kafka
> path for kagent triage. Records contain routing and deduplication metadata,
> including signal class, cluster/workload context, event reason or log
> signature, and observed time. This topic must not receive Alertmanager metric
> alerts, raw unbounded logs, secrets, tokens, or request bodies. It is consumed
> only by the dedicated Argo Events evidence-triage consumer group.

**Consumer-group name**

> `{{KAFKA_PREFIX}}.argoeventsuk8striageevidenceconsumer`

**Consumer-group description**

> Dedicated Argo Events consumer group for the kagent evidence-triage path.
> It reads only the Vector evidence topic and maintains offsets independently
> from the existing metric-alert triage group. Its EventSource forwards only
> Kubernetes event/log evidence to the read-only kagent triage workflow.

### Later target: one correlated incident path

Only add a dedicated router/claim service when the team needs a CPU alert and
a matching `CrashLoopBackOff`/log incident to become exactly one shared
incident. It can be implemented by extending the existing Vector normalizer or
another approved stream-processing service; it is not a Kafka portal form.

### What to create or change

| Step | Portal action | Create/change | Keep out of it | Why |
|---:|---|---|---|---|
| 1 | Inspect existing records | Confirm the Alertmanager -> Vector normalizer -> Kafka flow and the direct Vector -> Kafka flow; confirm which EventSource owns the current Argo group. | Do not change the current group yet. | Confirms the actual two producer paths and prevents an accidental production replay. |
| 2 | Onboard new producer/topic | Create `{{APPROVED_EVIDENCE_INPUT_TOPIC}}`; map it to the Vector workload identity. | Alertmanager must not write here. | Gives events/logs their own contract and ACL boundary. |
| 3 | Configure current topic | Keep `{{METRIC_ALERT_TOPIC}}` as the metric input only, **if** it is approved for that use. | Vector event/log messages must stop writing here. | Avoids a needless Alertmanager migration while removing source overlap. |
| 4 | Add consumer group | Create `kagent-triage-evidence-argo-v1`, owned by a new Argo Kafka EventSource, to read the new evidence topic only. | It does not read the current metric topic. | Keeps evidence offsets and failure/replay behavior isolated from metric alerts. |
| 5 | Configure Argo | Create an evidence Sensor/Workflow path that accepts only `signal_class=kubernetes-event` or `log`. | It must not trigger from metric records. | Enforces source ownership at the workflow edge. |
| 6 | Configure current Argo path | Filter the existing Sensor/Workflow to accept `signal_class=metric` only. | It must not trigger from Vector event/log records. | Completes the immediate no-router separation. |
| 7 | Add correlation later | Extend the Vector normalizer or add an approved stream processor and a durable claim store only if one cross-source incident is required. | Do not look for this as another portal consumer-group field. | Consumer groups do not provide cross-source semantic dedupe. |

Keep the current consumer group for the metric path during the first phase.
Create a distinct new group for the evidence topic; do not reuse existing
offsets for it.

### Optional full-correlation target

Use this additional onboarding only after the immediate source separation is
working and the team needs both streams to resolve to one shared incident.

| Purpose | Portal action | Suggested logical application / group | Topic | Permissions |
|---|---|---|---|---|
| Publish direct Kubernetes events and selected logs | Onboard producer/topic | producer: `kagent-triage-vector-evidence` | `kagent.triage.evidence.v1` | Vector identity: write/describe only |
| Publish metric-only alerts | Reuse existing onboarding if it already exists; otherwise onboard producer/topic | producer: `kagent-triage-alertmanager-metrics` | `kagent.triage.metric-alerts.v1` | Alertmanager identity: write/describe only |
| Normalize, enforce source ownership, and dedupe | Add consumer group, plus producer permission for its output | consumer: `kagent-triage-ingress`; group: `kagent-triage-ingress-v1` | reads both input topics; writes `kagent.triage.requests.v1` and DLQ | Router identity: read inputs; write requests/DLQ |
| Submit a triage workflow | Add consumer group | consumer: `kagent-triage-argo`; group: `kagent-triage-argo-v1` | `kagent.triage.requests.v1` | Argo identity: read/describe only |
| Observe and report | Add separate consumer group only if required | consumer: `kagent-triage-audit`; group: `kagent-triage-audit-v1` | requests/results | Audit identity: read-only |

`kagent.triage.results.v1` is recommended for workflow verdicts and audit, and
`kagent.triage.dlq.v1` is required before enabling production ingestion. These
are not topics Argo should consume to trigger triage.

If the work portal allows one consumer group to subscribe to multiple topics,
the router group uses the same `kagent-triage-ingress-v1` ID across the two
input topics. If the portal models ACLs per topic, grant that group read access
to each input topic; do not invent two routers merely because there are two
forms.

## What not to create

- A new topic per namespace, application, alert rule, Kubernetes event reason,
  or kagent specialist.
- A consumer group for a producer. Producers write; they do not need an offset
  cursor.
- A new consumer group for every deployment/restart.
- One shared all-powerful service account that can read and write every topic.
- An Alertmanager producer route for log- or event-derived alerts when Vector
  owns those source classes.
- An Argo consumer on the raw evidence topic. Argo should receive the bounded,
  normalized triage request after source validation and incident claiming.

## Recommended portal walk-through

Use this sequence with the Kafka platform team. It is intentionally an
onboarding request, not a request to create arbitrary infrastructure.

1. **Check what already exists.** Search for the existing Confluent cluster,
   Alertmanager producer application, `k8s-events`/`alertmanager-events`
   topics, Vector publisher, and Argo consumer group. Reuse an approved
   identity only when its permissions exactly match the required purpose.
2. **Agree the contracts first.** Confirm the topic names, source schemas,
   retention, partitioning, and ownership. The evidence and metric input
   contracts must remain separate.
3. **Onboard the Vector evidence producer.** Select the real Vector runtime
   application and cluster, map only its workload identity, select the evidence
   topic, and grant write/describe. Do not grant it read access unless a
   separately approved Vector design needs it.
4. **Limit Alertmanager to metrics.** Reuse or onboard the Alertmanager
   producer only for `triage_signal=metric` alerts. Log/event-derived alerts
   must not produce to the metric input topic.
5. **Onboard the router.** Create the stable ingress consumer group with read
   access to both input topics and a separate producer identity or explicit
   write permission for requests and DLQ. This is where source-ownership
   validation and durable incident claims happen.
6. **Onboard Argo separately.** Create the Argo consumer application/group on
   the normalized request topic only. Its Kafka identity is read-only; its
   Kubernetes service account is separately limited to submit the approved
   read-only triage workflow.
7. **Add monitoring and DLQ access.** Give the audit operator a read-only
   group, set alerts for lag and DLQ volume, and document an approved replay
   procedure. Do not let a dashboard/replay consumer submit workflows.

## The duplicate-control answer

The portal can ensure two consumers have separate identities and offsets, but
it cannot decide whether two different messages represent one incident. That
requires the runtime policy:

1. Alertmanager is allow-listed for **metric** signals only.
2. Vector is allow-listed for **Kubernetes events and logs** only.
3. The ingress/router rejects a record whose producer and `signal_class` do
   not match.
4. The ingress/router creates an atomic, durable claim for a source-independent
   `incident_key` before publishing `kagent.triage.requests.v1`.
5. A later matching metric or evidence record updates/attaches to the existing
   incident instead of triggering another workflow, ticket, or notification.
6. Argo and downstream ticketing use `incident_id` idempotently.

That is why the router consumer group is needed even if both current sources
can already write directly to Confluent Cloud.

## Questions to take back to the Kafka platform team

Ask these before submitting the forms; they resolve the portal-specific terms
without exposing credentials:

1. Does **identity pool mapped** bind a Kubernetes workload identity to a
   Kafka service account, or does it mean a different organisation identity
   construct?
2. What does **topic strategy** control: retention, cleanup policy,
   partitions, replication/tier, naming, or all of these?
3. Does **schema configuration** provision Schema Registry validation, and
   which formats/compatibility policies are supported?
4. Can one consumer application/group subscribe to multiple topics, and how
   are topic-level ACLs represented in the portal?
5. What start-offset behavior is applied to a brand-new consumer group?
6. Is there an existing approved producer identity for Vector, Alertmanager,
   and an approved read-only identity for Argo Events that can be reused?
7. What retention, encryption, data classification, and incident-data rules
   apply to redacted log/event evidence and DLQ records?

## Evidence required before calling it live

The repo has historical proof-of-concept material for `k8s-events` and
`alertmanager-events`; it is not current proof that the work environment is
ready. Capture fresh, redacted evidence that shows:

- each topic exists with the agreed retention/schema and least-privilege ACLs;
- Vector can publish a redacted event/log sample to the evidence input topic;
- Alertmanager can publish a metric-only sample to the metric input topic;
- the ingress group consumes both and emits one normalized request;
- Argo consumes that request with its own stable group;
- a deliberately overlapping metric-plus-workload-failure test creates one
  `incident_id`, one workflow, and one downstream notification/ticket;
- consumer lag, source-ownership rejections, dedupe suppression, and DLQ
  volume are visible to operators.

## Related docs

- [Dual-source Kafka routing decision](dual-source-kafka-triage-routing.md)
- [Alloy -> Vector -> Kafka agent-triage plan](alloy-vector-kafka-agent-triage-plan.md)
- [Existing Confluent Cloud pipeline PoC](../../observability/confluent-cloud-pipeline/README.md)
- [Kafka topic design for Vector-routed alerts](../../work-agent-bundles/vector-kafka-routing-normalization/KAFKA-TOPIC-DESIGN-README.md)
