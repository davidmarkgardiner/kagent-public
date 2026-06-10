# Kafka SaaS Migration — AlertManager → Confluent Cloud

Sizing spec to hand the Confluent Cloud account team, plus the AlertManager / Grafana
filtering shortlist that needs to land **before** cutover so we don't blast raw alerts
into the new topics.

Scope: **alerts only**. The Alloy → EventHub K8s events pipeline stays put for now.

---

## 1. Fleet Footprint

| Env  | Clusters | Retention | Notes |
|------|---------:|----------:|-------|
| prd  | 150      | 7 days    | Largest blast radius, longest replay window |
| ppd  | 50       | 3 days    | Pre-prod incident replay |
| test | 50       | 1 day     | Functional / soak |
| dev  | 50       | 1 day     | Dev clusters, noisiest, lowest SLA |
| **Total** | **300** | | |

---

## 2. Confluent Cloud Sizing (hand this to the vendor)

```
Provider:      Confluent Cloud
Cluster type:  Basic (3 AZ, 100 MB/s ingress/egress)
Region:        Azure uksouth
Replication:   RF=3
```

### Topics

| Topic | Partitions | Retention | Max storage |
|---|---:|---:|---:|
| `platform.alerts.prd`  | **12** | 7 days  | 10 GB |
| `platform.alerts.ppd`  | **6**  | 3 days  | 5 GB  |
| `platform.alerts.test` | **3**  | 1 day   | 2 GB  |
| `platform.alerts.dev`  | **3**  | 1 day   | 2 GB  |
| `platform.alerts.dlq`  | **3**  | 14 days | 2 GB  |
| **Total**              | **27** |         | **~21 GB** |

### Throughput

| Metric | Value |
|---|---|
| Sustained writes (aggregate) | <1 KB/s |
| Peak writes (aggregate)      | ~360 KB/s |
| Peak read bandwidth          | ~1.1 MB/s (3 consumer groups × peak writes) |
| Avg payload size             | ~4 KB (AlertManager v4 webhook JSON) |

Constraint is **partition count**, not throughput — Basic limits are 100× over.

### Auth & schema

| Item | Value |
|---|---|
| Auth          | SASL_SSL |
| API keys      | 8 total — 1 producer + 1 consumer per env |
| Producer principals | `aks-alertmanager-{dev,test,ppd,prd}` |
| Consumer principals | `argo-events-{dev,test,ppd,prd}` |
| Schema        | AlertManager v4 webhook JSON (no Schema Registry initially) |
| Partition key | `cluster_id` (preserves per-cluster ordering for AI triage) |
| Consumer groups | `consumer-critical`, `consumer-warnings`, `consumer-infra` |

### Consumer groups (per topic)

Each env topic is read by 3 independent consumer groups. Each group reads the full topic
and filters severity in jq at the sensor level — the volume is low enough that
read-then-filter is cheaper than producer-side classification.

| Consumer group | Filters for | Downstream |
|---|---|---|
| `consumer-critical` | `severity=critical` | kagent triage (cloud VLLM, sub-minute SLA), oncall page |
| `consumer-warnings` | `severity=warning`  | kagent triage (hosted model), Teams/Mattermost notification |
| `consumer-infra`    | infra-level alerts (node, API server, network) | platform-team channel, no AI triage |

Consumer-group offsets are independent — pausing/replaying `consumer-warnings` does not
affect `consumer-critical`. Add new groups (e.g., `consumer-security`, `consumer-audit`)
without changing topics or producers.

### Why per-env topics instead of one topic with an `env` label

- Different retention per env without consumer-side juggling.
- ACL boundaries — prd producers can't write to dev and vice versa.
- Blast radius isolation: a poison-pill in dev can't stall prd consumers.
- Different partition counts so we don't over-pay on quiet envs.
- Independent per-env consumer-group scaling.

### Why not also split by severity or category (critical/warning/system…)

Considered and rejected at this volume. Trade-off:

| Pro of severity-split topics | Con |
|---|---|
| Critical consumer skips reading warnings | 3× topic count (12 → 36 with env×severity) |
| Per-severity retention/SLA control | 3× partition tax on Confluent billing (~81 partitions) |
| Cleaner producer-side classification | Cross-severity correlation needs multi-topic joins |
| | Producer must classify before publish (more logic in kafka-bridge) |
| | More ACLs, more API keys, larger blast radius for misconfig |

At <1 KB/s sustained and ~360 KB/s peak, the wasted-bandwidth cost of read-then-filter is
zero. **Revisit if:**

- Alert volume grows 10×+ (3 KB/s sustained or 3 MB/s peak).
- Critical needs a hard sub-second end-to-end SLA that warning traffic would jeopardise.
- A new consumer category (security, compliance, audit) needs different retention.

### Why metrics / logs / K8s events are *not* on these topics

They have purpose-built transports already; Kafka would be the wrong tool:

| Telemetry | Transport (not these Kafka topics) |
|---|---|
| Metrics    | Prometheus remote write → Mimir / Thanos |
| Logs       | Alloy / Promtail → Loki |
| K8s events | Alloy → EventHub (deferred from this migration; may move to Kafka later as a *separate* topic, not mixed with alerts) |
| **Alerts** | **AlertManager → these topics** |

Kafka here is for **discrete, low-volume, high-value events that need async fanout to
multiple independent consumers**. Time-series and log streams are 100–1000× the volume
and belong on TSDB / log-store transports.

---

## 3. Filter Left — AlertManager / Grafana

Goal: only **actionable** alerts reach Kafka. Steady-state target is ~5 alerts/cluster/day,
not the raw firing count.

### 3.1 Prometheus / Grafana rule level (cheapest — alert never exists)

- Add `for: 5m` to every warning rule, `for: 2m` to every critical rule. Kills flapping.
- Add `keep_firing_for: 5m` to consolidate brief recoveries.
- **Delete or disable these rules entirely:**
  - `Watchdog` — designed to fire constantly. If you need a pipeline heartbeat,
    route to a separate healthcheck consumer, not Kafka.
  - `InfoInhibitor` — meta-rule, not actionable.
  - `*Test*`, `*Synthetic*`.
  - `KubeJobCompleted`, `KubeJobFailed` for short-lived batch jobs that auto-retry.
- Grafana managed rules: `noDataState: OK`, `execErrState: OK` to avoid alerting on
  scrape failures (covered separately by a `prometheus-up` rule).
- Move debugging signals to recording rules + dashboards, never alerts.

### 3.2 AlertManager route — default = drop

```yaml
route:
  receiver: 'null'                    # default: drop
  group_by: [alertname, cluster, namespace, severity]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: kafka-bridge
      matchers:
        - severity =~ "critical|warning"
        - alertname !~ "Watchdog|InfoInhibitor|.*Test.*|.*Synthetic.*"
        - cluster != ""              # require cluster label
      continue: false

receivers:
  - name: 'null'
  - name: kafka-bridge
    webhook_configs:
      - url: http://kafka-bridge.argo-events.svc:8080/alerts
        send_resolved: true
        max_alerts: 50
```

### 3.3 AlertManager inhibition

```yaml
inhibit_rules:
  # Critical inhibits same-target warning
  - source_matchers: [severity="critical"]
    target_matchers: [severity="warning"]
    equal: [alertname, cluster, namespace]

  # Node down inhibits pod/container alerts on that node
  - source_matchers: [alertname="KubeNodeNotReady"]
    target_matchers: [alertname=~"KubePod.*|KubeContainer.*|KubeDeployment.*"]
    equal: [cluster, node]

  # API server down inhibits everything else in the cluster
  - source_matchers: [alertname="KubeAPIDown"]
    target_matchers: [severity=~"warning|critical"]
    equal: [cluster]
```

### 3.4 Maintenance silences

Cluster upgrade workflow posts a 1h silence via AlertManager API **before** drain:

```bash
amtool silence add \
  --alertmanager.url=http://alertmanager.monitoring.svc:9093 \
  --comment="cluster upgrade $CLUSTER" \
  --duration=1h \
  cluster=$CLUSTER
```

Or call `POST /api/v2/silences` from a workflow step. Label `maintenance_window=true` on
the silence for auditability.

### 3.5 Cardinality discipline

- Never put pod names, request IDs, trace IDs in alert **labels** — annotations only.
  Labels drive grouping; high-cardinality labels defeat grouping and explode Kafka volume.
- Keep label set ≤ 8 keys per rule.

### 3.6 Kafka-bridge (last line of defense)

A thin webhook → Kafka producer service replacing the current AlertManager EventSource:

- Validates AlertManager payload schema. Bad payloads → `platform.alerts.dlq`.
- Adds `cluster_id`, `env` Kafka message headers from AlertManager labels.
- Sets partition key = `cluster_id`.
- Per-cluster rate limit (50 msg/min) as a runaway-AlertManager backstop.

---

## 4. Cutover Plan

1. **Vendor provisions topics** per §2.
2. **Filter-left changes** in §3.1–3.5 land via Flux — *no Kafka producer yet*.
3. **Deploy kafka-bridge** in `argo-events` ns with the dev producer API key.
4. **Switch one dev cluster's** AlertManager receiver to `kafka-bridge`.
5. **Smoke test:** trigger `kubectl run alert-test --image=busybox -- /bin/false`,
   wait for `KubePodCrashLooping`. Verify the message in `platform.alerts.dev` (Confluent
   console or `kafka-console-consumer`), then in the Argo Events sensor, then in the
   kagent triage workflow.
6. **Roll cluster-by-cluster** via Flux: dev → test → ppd → prd.
7. **Leave EventHub running in parallel** for the K8s events pipeline. Don't decommission
   anything until prd has been on Kafka for 2 weeks with green metrics.

---

## 5. Health Metrics (Grafana)

| Metric | Alert when |
|---|---|
| `kafka_topic_partitions_offset_lag` per consumer group | > 1000 sustained for 10m |
| `kafka_bridge_dlq_rate` | > 0 for 5m |
| `alertmanager_notifications_failed_total{integration="webhook"}` | rate > 0 for 5m |
| `kafka_bridge_rate_limit_dropped_total` | rate > 0 for 5m (signals a noisy cluster) |

Baseline `alertmanager_notifications_total{integration="webhook"}` before and after
cutover to confirm filtering didn't accidentally drop signal.

---

## 6. Files to Change

| Path | Change |
|------|--------|
| `01-alertmanager-values.yaml` | Restructure routes/inhibit/silences per §3.2–3.4; point receiver at `kafka-bridge` |
| `03-eventsource-alertmanager.yaml` | Replace webhook EventSource with **Kafka EventSource** consuming `platform.alerts.<env>` |
| `eventhub-otlp-pipeline/02-eventsource.yaml` | Reference for Kafka EventSource shape — adapt SASL config block |
| **NEW** `kafka-bridge/` | Deployment + Service + Secret for Confluent API key |
| `tier-{critical,warnings,infra}/sensor.yaml` | Unchanged — same jq parsing, only EventSource binding flips to Kafka topic |

Reuse:
- Kafka EventSource shape already proven for `k8s-events` (`02-eventsource.yaml`).
- Three-tier sensor severity filtering — unchanged.
- `kagent-triage` workflow templates — unchanged.

---

## 7. Not in Scope

- K8s events pipeline (Alloy → Kafka) — deferred. EventHub stays.
- Schema Registry / Avro — overkill for AlertManager JSON. Revisit when events migrate.
- Cross-region replication — single uksouth, RF=3 within Confluent's AZs is enough.
- EventHub decommission — leave running on parallel path until cutover confirmed.
