# Pre-Kafka namespace alert admission

Local implementation of the
[namespace budget plan](../../docs/observability/unattended-cluster-ticket-budget-plan.md).
It stops excess **automatic investigation triggers before Kafka**. It is a standalone
bundle; it has not changed or deployed the existing collector, Kafka, Argo,
agent or ticket writer.

```text
Alloy -> existing Vector normalize + incident filter -> HTTP admission
  -> PostgreSQL counts, bounded samples and owner groups
  -> daily namespace selection (1 or 2 per namespace)
  -> durable publish intent -> existing v2 Kafka triage topic -> existing Argo
  -> optional separate daily digest topic -> approved cluster-health assessment

Existing approved logging/event archive remains the detailed evidence source
```

## Implemented behavior

- Accepts the existing `observability.triage.v2` log/event envelope, with a trusted
  cluster binding and explicit namespace allowlist. Authenticated HTTP replies
  acknowledge only committed PostgreSQL records.
- Records every distinct eligible received envelope before Vector repeat
  suppression. Exact HTTP retries do not increase counts. Keeps five-minute
  aggregates for eight days and one bounded redacted latest sample per group.
  **This is not a full log archive or a lossless transport guarantee.** Require
  the approved retained logs/events for historical detail.
- Resolves Pod → ReplicaSet → Deployment and Pod → Job → CronJob from actual
  Kubernetes owner references. Failed/deleted-object lookups retain unresolved
  pod identity explicitly, rather than guessing a controller name.
- Selects at most the configured 1–2 groups per namespace once daily,
  at 09:00 Europe/London by default, from the preceding 24 hours. Critical
  source severity ranks before lower severity; recency and counts break ties.
  This is provisional prioritization, **not validated SLO/impact scoring**.
  Findings arriving after the slot wait for the next report.
- Builds a bounded 32 KiB digest with up to ten candidates, three suggested
  cluster priorities, complete received/group totals and visible truncation.
  Cluster candidates are selected before namespace trimming. It always marks
  health coverage incomplete because metrics and current health are absent.
- `report-only` stores shadow reports and publishes nothing. `enforce` inserts
  daily selection and outbox intents in the same transaction. Cluster-scoped
  database locks coordinate multiple gate replicas and Vector producers.
- Critical findings use the same namespace allowance. There is no urgent
  publish route or quota bypass. Legacy urgent settings fail configuration;
  legacy urgent outbox rows expire without sending.
- The final publisher atomically reserves a separate daily budget before any
  network call, so extra outbox rows cannot bypass selection limits. Changing
  the limit does not refill a spent allowance. Topic/timezone changes or a
  backward local date fail closed.
- Kafka sends include `admission-intent-id` headers. An uncertain send or a
  crash after claiming a send leaves an `unknown` or `sending` intent for manual
  reconciliation; it is **never automatically resent**. This chooses a bounded
  publication count over guaranteed delivery in ambiguous cases. Stale pending
  intents expire after one hour or at local-day rollover without budget refund.
  Outbox and daily-budget state retain 30 days; monotonic cluster bindings remain.

The limit covers committed investigation records on the configured topic for
one cluster/namespace/local day. Consumers **must use `isolation.level=read_committed`**
and durable intent deduplication. Replaying the same Kafka record does not
create another publication but can still repeat downstream work without dedupe.
The gate does not bound existing ticket-comment notifications, nor combine
the selected v2 agent runs into one agent call. Keep separate downstream
notification/update budgets. One daily digest agent run is the next integration
boundary described in [agent-handoff.md](agent-handoff.md).

## Configuration and rendering

Use an approved durable PostgreSQL database/schema and a least-privilege
application role. Run `schema.sql` as a migration owner; grant the application
role only the required table SELECT/INSERT/UPDATE/DELETE permissions. Runtime
checks the existing tables and does not run migrations. No real credential or
database endpoint belongs in this bundle.

`policy.example.json` defines `mode`, default `limit`, namespace `overrides`,
timezone/schedule and topics. The default is one; only integers one and two are accepted. Example override:
`"overrides": {"example-noisy-ns": 1}` after adding that namespace to the allowlist.
Do not change cluster identity, timezone or allowed namespaces during an active
report day. Changing a limit does not recreate that day's report or refill slots.

| Placeholder | Supply at deployment |
| --- | --- |
| `{{CLUSTER_NAME}}` | Exact cluster value produced by Vector |
| `{{WATCHED_NAMESPACE}}` | Approved namespace; repeat reader bindings for each |
| `{{EXISTING_TRIAGE_TOPIC}}` | Existing v2 topic with matching Sensors |
| `{{ADMISSION_IMAGE_DIGEST}}` | Approved mirrored/pinned image reference |

Create `namespace-alert-admission-policy` ConfigMap with a `policy.json` key.
Provide the `namespace-alert-admission` Secret out of band with keys
`database-url`, `auth-key` (at least 32 random characters), and
`kafka-security-json` (approved confluent-kafka security properties), and
`kafka-topic-ids-json` (approved topic-name → Kafka topic UUID mapping). Pin the
UUIDs independently of the gate database **once before enablement**; never
refresh them automatically after topic replacement. Kafka
bootstrap comes from the existing `confluent-credentials` Secret. TLS/SASL and
database TLS must match workplace requirements; there is no insecure fallback
in workplace instructions. Internal HTTP requires approved mesh encryption or
a TLS front door where required. Prove the ingress NetworkPolicy on the actual
CNI and add namespace-scoped monitoring access as needed.

Renderer writes a **new** manifest and refuses to overwrite an existing file:

```bash
python3 render_vector.py \
  ../homelab-verified-triage-replication/config/02-vector.yaml \
  /tmp/vector-admission-shadow.yaml \
  --uri http://namespace-alert-admission.argo-events.svc:8080/signals
```

Shadow keeps the original direct Kafka sink and adds admission evidence intake;
it provides comparison data without changing existing alert behavior. After
review, render a distinct cutover file with `--cutover`: **all direct Kafka
sinks in that Vector ConfigMap are removed**. Gate enforcement must be active
before cutting over. Never combine report-only gate mode with cutover, because
that combination intentionally publishes no triage triggers.

The renderer supports a single ConfigMap with `vector.yaml` and a Deployment
container named `vector`. Inspect names/labels/env in the actual selected tier.
Apply the same cutover to every Vector producer/tier and direct metric bridge
that is intended to share the allowance. **The current intake supports only
the v2 event/log lane; metric alerts are not yet admitted through this gate.**
Do not claim an all-source namespace quota until their adapter is implemented.

`k8s.yaml` is a placeholder-safe deployment/RBAC/service/ingress example. It is
not part of the existing Kustomization and has not been server-dry-run against
a target cluster. Deliver selected rendered manifests through the existing
Flux flow; do not run the original and rendered Vector definitions together.

## Pilot and operational checks

1. Inventory current object names, namespace tiers, all producers and Kafka
   consumer ownership. Preserve unrelated changes in the source bundle.
2. Deploy shadow intake in one cluster with a small allowlist. Keep the old
   Kafka path. Compare counts/samples with retained logs and known incidents.
3. Confirm real owner lookup, PostgreSQL durability/restore, TLS, topic ACLs,
   topic pins/retention/transactions, replay and scheduled report freshness.
4. Reconcile pre-cutover pod-keyed open tickets before enabling controller-keyed
   `dedupe_key`; otherwise existing incident mappings may not be reused.
5. Enable gate enforcement and cut over every intended Vector producer through
   Flux. Prove produce/consume and workflow counts in the actual environment.
6. Attach the separate digest to the existing approved read-only assessment and
   single-summary writer; add metric/current-state evidence before health claims.

Authenticated `GET /report` returns the most recent stored report. Check
`generated_at` and coverage; an old report is not fresh health evidence.
Authenticated `GET /metrics` exposes `admission_outbox_intents{lane,status}`.
Alert on `unknown`, lingering `sending`, old `pending`, expired intents, missing
daily reports, and intake/database errors. `/health` checks database access only;
it does not prove Kafka or agent readiness.

No auto-backfill of historical digests. Before each send, the publisher checks
retained committed Kafka history against the namespace/day allowance. It uses a
stable cluster transactional ID and fences earlier producers before reading, so
an ambiguous previous transaction cannot commit after a replacement publisher's
audit. Topic replacement, incomplete history, a scan exceeding 10,000 records or
five seconds, and unavailable state all block publication. No send starts in
the final minute of a local day.

Topics require `cleanup.policy=delete`, `retention.bytes=-1`, and
`retention.ms >= 172800000` (48 hours) or `-1`. Do not compact, truncate, restore
or change the pinned identity/history while enforcement is active. Provide
approved READ, WRITE, DESCRIBE/config-description and transactional-ID ACLs.
This assumes a trusted broker and administrator; it is not protection against
arbitrary concurrent administrative history rewriting. Reconcile identities,
clock and current-day committed records before recovery when both stores are
lost. Rolling replicas must share the policy, database, topic pins and cluster
transactional identity.

Rollback restores the exact previous Vector manifest through Flux and disables
gate publication. Account for pending/unknown intents before restoring a direct
Kafka producer, to avoid duplicate notifications.

## Local validation

```bash
bash verify-local.sh
```

The script creates isolated PostgreSQL, Vector and Kafka containers with no
host ports, no Kubernetes context and no external credentials, runs behavioral
tests and real HTTP/produce/consume proofs, then removes its containers/network.
Synthetic PostgreSQL trust authentication is confined to that disposable network.
Images/dependency downloads require internet access. Docker image cache remains.

See [EVIDENCE.md](EVIDENCE.md) for results and what they do not prove.

## Home-lab transport validation

The [Proxmox home-lab receipt](evidence/2026-10-01-home-lab-transport.md)
now proves real Kubernetes pod logs and Warning Events through Alloy → Vector
OTLP → HTTP gate/PostgreSQL → an isolated Kafka broker and consumer. It retained
195 records in 30 resolved groups and consumed exactly 1/2/2 records across
three namespaces. All isolated namespaces were removed after the test.

Reproduce only when a lab test is authorized:

```bash
bash home_lab_smoke.sh proxmox-k8s
```

The strict follow-up test exercises seven **accelerated local days**, concurrent
publishers, replay, an actual gate pod restart, loss of database budget/report
state, a prior uncommitted transaction and topic recreation. Accelerated clocks
are not seven elapsed unattended days. See the [strict receipt](evidence/2026-10-01-strict-admission.md) for exact results.
Ticket creation, agent advice and workplace security remain untested. The revised
[unattended ticket policy](../../docs/observability/unattended-cluster-ticket-budget-plan.md)
still requires a dedicated budgeted ticket writer and outstanding-ticket caps.

Official API references checked:
https://vector.dev/docs/reference/configuration/sinks/http/
https://docs.confluent.io/kafka-clients/python/current/overview.html

Kafka transaction and topic API references:
https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html
https://kafka.apache.org/38/configuration/topic-level-configs/
