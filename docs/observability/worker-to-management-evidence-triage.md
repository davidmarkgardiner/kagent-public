# Worker-to-management evidence triage

## Decision

Use an evidence-first Kafka path for agentic triage:

```text
worker cluster
  Alloy -> local Vector -> Kafka/Redpanda
                         -> management-cluster Kafka consumer
                         -> Argo Events -> triage Workflow -> read-only agent
                         -> idempotent GitLab work item
```

Each worker cluster owns collection, redaction, normalisation, local
correlation and short-lived suppression. The management cluster owns durable
deduplication, queue consumption, richer fleet context, triage, ticketing,
audit and policy. Grafana/Loki remain optional searchable mirrors.

This is the chosen trigger path for logs and Kubernetes events because the
agent receives the original bounded evidence at the point it occurs. It does
not need a second lookup merely to discover why an alert fired.

## What this does and does not replace

This does **not** remove Alertmanager from the platform.

| Need | Preferred control plane | Reason |
|---|---|---|
| Human paging for Prometheus metric alerts | Prometheus + Alertmanager | Grouping, inhibition, routing, escalation and repeat policies are its strengths. |
| Dashboards, search and retrospective investigation | Loki/Grafana | Retention, exploration and visual analysis. |
| Agent triage from raw logs and Kubernetes events | Alloy + Vector + Kafka + Argo | Preserves source evidence and absorbs a burst before the agent is called. |
| Remediation | Separate approved workflow | Triage remains read-only; mutation needs explicit policy and human approval. |

Alertmanager fires after a rule has evaluated and intentionally groups,
inhibits and repeats alerts. Its webhook is useful for a metric-alert workflow,
but it is not a lossless incident-evidence transport: the representative log
lines and event object that explain the condition are usually absent or need a
fresh Grafana/MCP query. Sending raw evidence to the queue first avoids that
extra lookup and gives one durable place to control agent load.

## Canonical incident envelope

Vector should emit a versioned, bounded envelope. All workers use the same
schema; management rejects unknown major versions and sends them to a
quarantine topic rather than silently dropping them.

The red proof currently emits `observability.triage.v2`; the `v3` envelope
below is the proposed fleet contract. Management must accept an explicit
allow-list of versions during migration, quarantine unknown majors, and deploy
the management acceptance before moving any worker to `v3`.

```json
{
  "schema_version": "observability.triage.v3",
  "incident_fingerprint": "sha256(cluster:namespace:workload:pod:signature)",
  "event_id": "source-specific immutable id when available",
  "cluster": "{{CLUSTER_NAME}}",
  "environment": "{{ENVIRONMENT}}",
  "region": "{{REGION}}",
  "namespace": "{{NAMESPACE}}",
  "workload": {"kind": "Deployment", "name": "{{WORKLOAD}}"},
  "pod": "{{POD}}",
  "container": "{{CONTAINER}}",
  "signal": {"kind": "log|kubernetes-event", "reason": "{{REASON}}", "severity": "warning|critical"},
  "occurred_at": "RFC3339 UTC",
  "evidence": {
    "summary": "redacted bounded explanation",
    "representative_lines": ["up to N redacted lines"],
    "kubernetes_event": {"reason": "BackOff", "message": "...", "count": 1}
  },
  "routing": {"automation_allowed": false, "priority": "P1|P2|P3", "sampled": false},
  "provenance": {"collector": "alloy", "transform": "vector", "worker_schema_revision": "{{REVISION}}"}
}
```

Never place full log streams, tokens, raw request bodies, customer data or
cluster credentials in this envelope. Preserve a stable source reference and
the redacted representative evidence instead.

## Worker-cluster responsibilities

Run Alloy and Vector in every worker cluster through GitOps. For pod logs,
Alloy normally runs as a node-local DaemonSet; Vector normally runs as an
HA, cluster-local aggregation Deployment behind a Service, with a Pod
Disruption Budget, topology spread and persistent disk buffers. Do not make a
fleet-wide Vector service the worker's first hop.

1. **Collect at the source.** Alloy attaches Kubernetes metadata before it can
   be lost: cluster, environment, namespace, workload, pod, container, labels
   from an allow-list, event UID/resourceVersion, and observed time.
2. **Normalise and redact locally.** Vector parses known event/log formats,
   strips secrets/PII using deny-list patterns, caps evidence bytes and applies
   a fixed schema. Unknown/malformed records go to a worker quarantine topic
   with a reason metric.
3. **Correlate before forwarding.** Derive a fingerprint from stable workload
   identity plus a normalised signature. A `BackOff` event and the matching
   error log for the same pod should become one incident candidate, not two
   agent calls.
4. **Reduce volume before egress.** Drop normal lifecycle events; allow only
   severity/signature policies; retain the first evidence plus a bounded count
   and last-seen time. Use Vector's in-memory dedupe only as a local burst
   reducer, never as the durable decision.
5. **Queue safely.** Send keyed Kafka records using `incident_fingerprint` as
   the record key so related evidence stays ordered. Enable disk buffers and
   backpressure. On broker outage, retain within an explicit local capacity,
   then measure and alert on loss rather than silently retrying forever.

## Management-cluster responsibilities

The management cluster is the only place that can consume into agents and
create tickets.

1. **Validate and route.** A Kafka consumer/EventSource validates schema,
   tenant/cluster allow-list, timestamp skew and payload size. Invalid records
   go to a dead-letter/quarantine topic with no agent invocation.
2. **Apply durable 24-hour idempotency.** Use an atomic TTL-capable store
   (Redis `SET NX EX`, PostgreSQL unique row plus expiry, or an equivalent
   managed service) keyed by `incident_fingerprint`. Store the workflow ID,
   first/last seen, count, ticket URL and completion state. The red proof's
   ConfigMap claim proves the behaviour; it is not the production fleet store.
3. **Enrich only after the claim.** Attach management-owned context: cluster
   inventory, workload owner, approved runbook references, recent deployment
   identity, maintenance windows and policy. Do not block the initial durable
   claim on slow external lookups.
4. **Control agent concurrency.** Use Kafka consumer-group concurrency,
   Argo workflow parallelism, per-cluster quotas, priority lanes and a circuit
   breaker for an unhealthy model/A2A endpoint. A P1 lane can bypass P3
   batching, but not safety policy.
5. **Invoke a read-only agent.** Pass the full bounded envelope plus enriched
   context. The agent may query approved read-only tools for confirmation; it
   must not need Grafana just to reconstruct the triggering evidence.
6. **Create one idempotent ticket.** The ticket writer uses the fingerprint as
   an idempotency key, records the evidence and triage response, and updates
   the durable record only after GitLab confirms the URL. Retry ticket writes
   safely without re-running the agent where a diagnosis already exists.

## Volume and resilience policy

| Control | Worker | Management | Acceptance measure |
|---|---|---|---|
| Signal allow-list | Drop normal/no-action signals | Reject unknown signal type | dropped-by-policy metric by cluster |
| Redaction and cap | Before Kafka egress | Revalidate size/schema | zero secret-pattern matches in sampled envelopes |
| Correlation | Log/event candidate merge | Durable 24-hour fingerprint claim | one agent run/ticket per fingerprint/window |
| Burst handling | Disk buffer, bounded batching | Kafka partitions, Argo parallelism/quotas | queue lag and oldest-message age SLO |
| Poison records | Worker quarantine topic | DLQ with replay procedure | no silent parse failures |
| Tenant isolation | Cluster credential only writes its topic/ACL | allow-list maps topic/cluster to tenant | cross-cluster record rejected |
| Failure mode | Buffer and report loss if full | Do not acknowledge before durable claim | replay does not create a second ticket |

Recommended starting values are deliberately conservative and must be tuned
from measured workload volume: 4 KiB redacted evidence, 10 representative log
lines, one candidate per fingerprint per five minutes at the worker, one agent
triage per fingerprint per 24 hours at management, and separate P1/P2/P3
topics or routing fields. Do not hard-code these as universal production
limits.

## Kafka topology

Use either a shared secured Kafka/Redpanda service reachable from workers, or
worker-local Kafka with a managed replication/bridge layer. The first is
simpler; the second improves site-isolation at the cost of operating more
brokers. In both cases, workers produce to tenant- and environment-scoped
topics, for example:

```text
triage.<environment>.<tenant>.evidence.v3
triage.<environment>.<tenant>.quarantine.v3
triage.<environment>.<tenant>.triage-results.v1
```

Use mTLS/SASL, topic ACLs, encryption at rest, retention appropriate to the
redacted evidence classification, and a partition key of
`incident_fingerprint`. Never use one unauthenticated fleet-wide topic.

## Why this needs no second lookup

The agent receives the initial evidence in the Kafka record, so it need not
perform a Grafana/MCP reverse lookup merely to obtain the triggering log or
event details. Grafana lookups remain valuable as optional follow-up evidence,
not as a dependency for first diagnosis. This is an expected operational
simplification, not a comparative latency claim until representative load is
measured.

The meaningful performance objective is not only lower median latency. It is
bounded time-to-triage under a burst, with no duplicate agent spend and no
lost incident context. Measure:

- collection-to-Kafka latency;
- Kafka oldest-message age and consumer lag;
- claim-to-agent start and agent completion time;
- duplicate suppression rate;
- schema/redaction/quarantine rate;
- ticket creation success and idempotent-retry rate.

## Rollout sequence

1. Keep the existing red proof as the schema and workflow reference.
2. Introduce a management consumer with a real TTL idempotency store and
   worker identity/ACL model before onboarding a second cluster.
3. Onboard one non-production worker cluster with only P1/P2 signatures.
4. Run controlled log and Kubernetes-event tests; prove one ticket per
   fingerprint and replay safety.
5. Add queue-lag, buffer-health, redaction and quarantine dashboards.
6. Expand signal policy and cluster scope only after volume/error budgets are
   observed.
7. Keep Alertmanager routes in place for human paging until operational owners
   explicitly decide otherwise; do not redirect them to this agent path by
   default.

## Self-review before office replication

This design is intentionally incomplete in three places that require
environment-specific review rather than guesswork: the worker-to-management
network model, the durable idempotency store, and evidence data classification
and retention. The review prompt alongside this document asks Fable to test
these assumptions and identify any missing failure, security or operating
controls before a work bundle/skill is created.
