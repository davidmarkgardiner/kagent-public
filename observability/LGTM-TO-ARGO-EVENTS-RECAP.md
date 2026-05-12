# LGTM → Argo EventSource — Context Recap

**Date:** 2026-04-30
**Owner:** David Gardiner
**Purpose:** Single-page reminder of how the kagent / Prometheus alert pipeline currently works, and the open design for piping the **managed LGTM** stack (logs, metrics, k8s events, traces) into the same triage system **without Azure Event Hub**.

---

## 1. What we already built and tested

### 1a. Prometheus → Argo EventSource → kagent (working, in-cluster)

Path: `aks-mgmt-stack/k8s-event-triage/prometheus-alerting/`

```
Prometheus rules ──► AlertManager ──► Argo Events EventSource (webhook :12000/alerts)
                                              │
                                              ▼
                                      Argo Events Sensor
                                      (filter status=firing,
                                       rate-limit 5/min)
                                              │
                                              ▼
                                  alertmanager-triage WorkflowTemplate
                                  (fetch pod logs/events → GitLab issue → Mattermost)
```

- Status: **end-to-end tested and working** on `{{CLUSTER_NAME}}` (see memory: real KubePodCrashLooping in `gitea` ns was caught).
- Webhook receiver is a vanilla Argo Events `EventSource` of type `webhook`, listening on port 12000 at `/alerts`.
- AlertManager `webhook_configs.url` points at the in-cluster service `http://alertmanager-eventsource-svc.argo-events.svc.cluster.local:12000/alerts`.
- This is the **clean, no-queue path** — works because both AlertManager and Argo Events live in the same cluster.

### 1b. K8s events → Event Hub → Argo EventSource (working, multi-cluster)

Path: `aks-mgmt-stack/k8s-event-triage/eventhub-otlp-pipeline/`

```
Workload clusters (Alloy `loki.source.kubernetes_events` → otelcol.exporter.kafka)
        │
        ▼
Azure Event Hub topic `k8s-events`
        │
        ▼
Argo Events Kafka EventSource (mgmt cluster) ──► Sensor ──► Workflow ──► kagent A2A ──► Mattermost
```

- Status: **validated 2026-01-29** — `ALLOY-EVENTHUB-VALIDATION.md` records 123/0 sent/failed against `evhns-alloy-v12-test`.
- This is the **cross-cluster path** — uses Event Hub because the worker clusters and the management cluster don't share a network.
- The user wants to **stop using Event Hub** for the LGTM extension (cost, vendor lock, infra friction).

---

## 2. The new question: managed LGTM signals → Argo EventSource

We now have a **managed LGTM stack** (Loki, Grafana, Tempo, Mimir) sitting in the platform team's network. We do **not** have direct API access to Mimir / Loki / Grafana / Tempo. **Alloy is the only ingress/egress point we control.**

We want to feed the four signal types into the same kagent triage pipeline:
- **Metrics** alerts (PromQL rules in managed Mimir)
- **Logs** alerts (LogQL rules in managed Loki)
- **K8s events** (already shippable as logs)
- **Traces** (lower priority — Tempo)

…ideally going **straight into an Argo EventSource** with no Event Hub in the middle.

Full design lives in `managed-lgtm-integration/README.md`. This file just captures the decision tree.

---

## 3. Options ranked (cleanest first)

### Option A — Managed AlertManager → in-cluster Argo EventSource (webhook) — PREFERRED

```
Managed AlertManager  ──webhook POST──►  Ingress (TLS + bearer)  ──►  Argo Events webhook EventSource  ──► Sensor ──► Workflow
```

- **Same shape as the working `prometheus-alerting/` pipeline** — just the AlertManager is remote, not local.
- No queue, no Event Hub, no Kafka.
- Only new infra: a public-ish ingress fronting the existing `alertmanager-eventsource-svc` with TLS and a bearer-token auth check.
- Hard requirement: managed AlertManager must be allowed to call out to a webhook on a host we own. **This is open question Q4** in `managed-lgtm-integration/OPEN-QUESTIONS.md`.

### Option B — Managed AlertManager → Alloy `loki.source.api` → Argo EventSource

```
Managed AlertManager ──webhook──► Alloy (in-cluster) ──HTTP POST──► Argo EventSource ──► Sensor ──► Workflow
```

- Inserts Alloy as a thin reshape layer (auth, rate-limit, label normalization) before handing off to Argo Events.
- Useful if the AlertManager payload needs canonicalising or if we want the same path to also fan out to Kafka later.
- Existing snippet `managed-lgtm-integration/alloy-snippets/05-alertmanager-webhook-bridge.alloy` already wires this — currently it forwards to **Kafka** (Event Hub), but the same `loki.source.api` block can forward to a webhook with a tiny tweak. The `otelcol.exporter.kafka` chain at the end is what we'd swap out for an HTTP client posting to the EventSource.

### Option C — Self-hosted Kafka / Redpanda → Argo Events Kafka EventSource

If the platform team **cannot** let managed AlertManager call out to a webhook (firewall locked into the managed VPC), we fall back to a queue. Replace Event Hub with:

- **Strimzi Kafka** in our own cluster (in-cluster broker), or
- **Redpanda** (Kafka-API compatible, single-binary, lighter than Strimzi), or
- **NATS JetStream** — Argo Events already runs NATS as its EventBus; a JetStream EventSource is supported and we get a queue effectively for free.

Argo Events has first-class EventSource types for **kafka**, **nats**, **redis**, **amqp** — none require Azure.

The handoff stays the same: AlertManager (or Alloy) writes to the queue → Argo Events Kafka/NATS EventSource consumes → Sensor triggers workflow.

### Option D — Polling fallback

If neither webhooks nor queues are possible, Alloy can **poll** Mimir's `ALERTS{alertstate="firing"}` series via `prometheus.scrape` and forward state changes to a local webhook. Lossy and high-latency — only acceptable as a stopgap.

---

## 4. Recommendation

1. **Pursue Option A first.** It's a one-component change to the existing, tested `prometheus-alerting/` pipeline — just swap the webhook URL from cluster-local to a TLS ingress and add bearer auth. Zero Event Hub, zero Kafka, zero new abstractions.
2. **Hold Option B in reserve** as the reshape layer if the managed AM payload needs munging or if multiple consumers (kagent + Mattermost direct + GitLab direct) need to fan out from the same alert.
3. **Pre-stage Option C (NATS JetStream)** as the durable-queue fallback. We already run NATS for Argo Events EventBus, so it's near-zero new infra. Use this if Q4 in OPEN-QUESTIONS.md comes back as "managed AM cannot call out".
4. **Don't ship Option D** unless explicitly forced.

The single blocking question is Q4: *can the managed AlertManager reach a webhook we expose, and what auth does it support?* Until that's answered, Options A and B are theoretical.

---

## 5. What needs platform-team input

Open questions in `managed-lgtm-integration/OPEN-QUESTIONS.md`:

| Q | Topic | Blocks |
|---|-------|--------|
| Q1 | Mimir push endpoint + tenant + auth | Sending metrics in |
| Q2 | Loki push endpoint + tenant + auth | Sending logs in |
| Q3 | Rule provisioning model (Alloy CRD sync vs central repo MR) | Owning alert rules in this repo |
| **Q4** | **AlertManager → us network path** | **Triage loop closure** ← biggest unknown |
| Q5 | Grafana dashboard provisioning | Visualisation |
| Q6 | Tempo OTLP endpoint | Trace ingestion |
| Q7 | Cardinality / cost guardrails | Safe rollout |
| Q8 | Multi-cluster `cluster=` label convention | Cross-signal correlation |

---

## 6. Files to read in order if resuming

1. `prometheus-alerting/README.md` — the working in-cluster pattern
2. `managed-lgtm-integration/README.md` — full design proposal
3. `managed-lgtm-integration/OPEN-QUESTIONS.md` — what we need from platform team
4. `managed-lgtm-integration/alloy-snippets/05-alertmanager-webhook-bridge.alloy` — current bridge (Kafka-flavored, swap exporter for HTTP to skip the queue)
5. `managed-lgtm-integration/alerts/workflow-template-alerts.yaml` — kagent triage WorkflowTemplate (consumes either path)
6. `eventhub-otlp-pipeline/ALLOY-TESTING.md` + `ALLOY-EVENTHUB-VALIDATION.md` — what we already validated
