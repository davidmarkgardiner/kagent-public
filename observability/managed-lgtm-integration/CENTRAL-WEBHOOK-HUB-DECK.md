---
marp: true
theme: house-dark
paginate: true
---

<style>
/* @theme house-dark */
section {
  background: #000000;
  color: #ffffff;
  font-family: 'Outfit', system-ui, sans-serif;
  font-size: 26px;
  padding: 50px 70px;
}
section h1, section h2, section h3 {
  font-family: 'Raleway', sans-serif;
  color: #ffffff;
  letter-spacing: -0.01em;
}
section h1 { font-size: 52px; margin: 0 0 18px 0; }
section h2 { font-size: 38px; margin: 0 0 16px 0; }
section h3 { font-size: 28px; margin: 0 0 12px 0; }
section strong { color: #ff6b1a; font-weight: 600; }
section em { color: #ff6b1a; font-style: normal; font-weight: 600; }
section a { color: #ff6b1a; }
section code {
  background: #1a1a1a;
  color: #ff6b1a;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 22px;
}
section pre {
  background: #1a1a1a;
  border-left: 4px solid #ff6b1a;
  padding: 18px;
  border-radius: 4px;
  font-size: 20px;
}
section pre code { background: transparent; color: #ffffff; padding: 0; }
section table { border-collapse: collapse; margin: 18px 0; width: 100%; }
section th, section td {
  border: 1px solid #ff6b1a;
  padding: 10px 14px;
  text-align: left;
  color: #ffffff;
}
section th { background: #ff6b1a; color: #000000; font-weight: 600; }
section blockquote {
  border-left: 4px solid #ff6b1a;
  padding: 6px 18px;
  margin: 18px 0;
  color: #ffffff;
  font-style: italic;
}
section .card {
  background: #1a1a1a;
  border: 1px solid #ff6b1a;
  border-radius: 6px;
  padding: 22px 26px;
  margin: 14px 0;
}
section ul, section ol { color: #ffffff; }
section li { margin: 6px 0; }
section footer { color: #ffffff; }
section.lead {
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
section.lead h1 { font-size: 64px; }
</style>

<!-- _class: lead -->

# Central Webhook Hub

## A low-latency lane for alert-driven automation

**alongside, not instead of, BigPanda**

---

## The constraint

Managed Grafana Contact Points are locked to **BigPanda only**.

Sensible default — every alert becomes an incident, handled through one system.

But it leaves no path for **automation** that needs raw alerts.

<div class="card">

**What we want to build:** AI-driven triage (kagent) that consumes alerts in seconds, fetches diagnostics, and posts a first-pass analysis before a human even opens the incident.

**What we cannot do today:** subscribe to alerts from the managed Grafana directly.

</div>

---

## Why BigPanda is the wrong source for triage

BigPanda is a **correlation engine**. It is designed to *reduce* alert volume.

- **Deduplication** — N identical alerts become 1 incident
- **Grouping** — related alerts merge into a single incident
- **Suppression** — known-noisy patterns drop entirely
- **Enrichment latency** — typically **30s–5 minutes** end-to-end

Each of those is correct for human incident management.

**Each of those is wrong for AI triage**, which needs the raw, individual alert in flight, within seconds, with all labels intact.

---

## Two paths we considered

| | **Path A — Scrape from BigPanda** | **Path B — Central Webhook Hub** |
|---|---|---|
| Source of truth | BigPanda outbound API/webhook | Managed Grafana / AlertManager direct |
| Latency | 30s – 5 min | < 5 sec |
| Alert fidelity | Correlated, dedup'd, lossy | Raw, full-detail |
| Effort | ~1.5 weeks | ~2 weeks |
| Reusable for other teams | No | **Yes** |
| Affects BigPanda | Adds load on BP API | Zero impact |
| Recommended? | No | **Yes** |

Path A buys nothing long-term. Path B becomes platform infrastructure.

---

## What the Hub is

A **single sanctioned webhook receiver** that the platform team approves once.

<div class="card">

**One inbound URL.** `https://webhook-hub.<our-domain>/inbound`

**Many internal subscribers.** Tenant teams subscribe to alert classes via labels.

**Owned, audited, secured by us.** Platform team approves the boundary; consumers self-serve inside it.

</div>

The platform team adds **one** new Grafana Contact Point. Forever. Scaling to N tenants happens entirely on our side.

---

## Architecture (built on what we already run)

```
Managed Grafana ──► ONE webhook Contact Point ──► https://webhook-hub.<domain>/inbound
                                                          │
                                                          ▼
                                              ┌───────────────────────┐
                                              │   Argo Events         │
                                              │   webhook EventSource │
                                              │   + auth + schema     │
                                              └───────────┬───────────┘
                                                          │ NATS EventBus
                                                          │
                       ┌──────────────────────────────────┼──────────────────────────────────┐
                       ▼                                  ▼                                  ▼
              ┌────────────────┐               ┌────────────────┐               ┌────────────────┐
              │  Sensor: SRE   │               │  Sensor: AI    │               │  Sensor: TeamX │
              │  → Workflow    │               │  triage → kagent│               │  → their bot   │
              │  → GitLab/MM   │               │  → MM / GitLab │               │  → Slack       │
              └────────────────┘               └────────────────┘               └────────────────┘
```

**No new product to learn.** Argo Events EventSource + Sensor + NATS EventBus is already in production for our existing K8s-event triage.

---

## What each layer does

<div class="card">

**Ingress (Istio Gateway + AuthorizationPolicy)**
TLS, source-IP allow-list (managed Grafana egress), bearer-token check. Pattern already proven for HITL callbacks.

</div>

<div class="card">

**EventSource (Argo Events `webhook`)**
Validates payload shape, publishes to NATS EventBus. Audit log via existing Argo Workflows event log.

</div>

<div class="card">

**EventBus (NATS JetStream)**
Durable, replayable, fan-out by subject. Already running for Argo Events.

</div>

<div class="card">

**Sensors (per team)**
Filter by alert labels, trigger Workflow / external webhook / Slack / whatever the team wants. Self-service from our team's namespace.

</div>

---

## Subscriber model — how a team plugs in

<div class="card">

**Step 1 — define what alerts you care about** (label match)
```yaml
filters:
  data:
    - path: body.commonLabels.team
      value: ["ai-platform"]
    - path: body.alerts[0].labels.severity
      value: ["critical", "warning"]
```

</div>

<div class="card">

**Step 2 — declare the action** (Workflow, webhook, Slack, ...)
```yaml
triggers:
  - template:
      name: ai-platform-triage
      k8s:
        operation: create
        source:
          resource: { workflowTemplateRef: { name: alertmanager-triage } }
```

</div>

**That's it.** One Sensor manifest in the team's namespace. No new infra, no platform-team review per team.

---

## Security model (the part platform-team will scrutinise)

| Concern | How the Hub addresses it |
|---|---|
| Who can POST to the hub | Source-IP allow-list at Istio (Grafana egress only) + bearer token + EventSource `authSecret` |
| Who can subscribe | RBAC on Sensor creation per namespace — owned by tenant teams |
| Audit trail | Every inbound webhook + every Sensor trigger logged via Argo Events controller |
| Token rotation | Standard ExternalSecret + Vault rotation; one shared token, scoped to one URL |
| Replay / DoS | Rate limit at Sensor (already used: 5/min for triage) |
| Multi-tenancy isolation | Each team's Sensor lives in their namespace, with their RBAC |
| Schema validation | EventSource validates required fields before fan-out |

**Pattern is already in production** for the Teams HITL callback webhook (commit `f5fbdb1`).

---

## Why this is replicable

A new subscriber team needs **three things**, all packaged:

<div class="card">

**1. A Helm chart / KRO ResourceGraph**
Generates a Sensor + WorkflowTemplate scaffold for the team's namespace. One `helm install`.

</div>

<div class="card">

**2. A `SUBSCRIBER-GUIDE.md`**
"Pick a label match, pick a trigger type, run the chart." Two-page doc.

</div>

<div class="card">

**3. A schema reference**
What fields are guaranteed in the payload (alertname, severity, labels, annotations, generatorURL). What's optional. So filters don't break on edge cases.

</div>

Onboarding a new team = ~30 minutes once the Hub is live.

---

## How hard is the BigPanda alternative?

For comparison — what if we **did** try to source alerts from BigPanda?

<div class="card">

**Effort:** ~1.5 weeks (BP API auth, polling vs webhook decision, rate-limit handling, dedup of correlated incidents back to constituent alerts)

**Latency penalty:** 30s–5min added on top of original alert

**Fidelity penalty:** original alert labels lost in BP's incident merge

**Operational coupling:** every change to BP's correlation policy could break our triage

**Reusable for other teams:** No — each team would need their own BP integration

</div>

**Verdict:** the effort is comparable but the result is strictly worse on every axis that matters. Path B (Hub) is the recommendation regardless of timeline.

---

## Proof of concept — 4-week plan

<div class="card">

**Week 1 — Approval + scaffolding**
Teams message + meeting with platform team. Approve URL + IP allow-list. Stand up Istio Gateway + EventSource + bearer auth. Pattern already in repo.

</div>

<div class="card">

**Week 2 — End-to-end with one alert rule**
One Grafana alert rule (real metric). One Sensor. One Workflow that posts to Mattermost. Smoke-test from Grafana UI → confirm alert lands in MM in <5s.

</div>

<div class="card">

**Week 3 — kagent integration + second subscriber**
Wire kagent A2A triage into the Workflow. Add a second team's Sensor (different label match, different action). Prove fan-out works.

</div>

<div class="card">

**Week 4 — Replication kit + handover**
Helm chart for new subscribers. Subscriber guide. Schema doc. Observability dashboard. Demo to platform team and 2–3 tenant teams.

</div>

---

## Asks of the platform team

<div class="card">

**1. Approve one Grafana Contact Point**
URL: `https://webhook-hub.<our-domain>/inbound`. Bearer token (we provide). One row in their alert routing config.

</div>

<div class="card">

**2. Confirm Grafana egress path**
Either add the destination to the proxy bypass list, OR provide proxy auth credentials so Grafana can traverse the egress proxy (recall: 407 from today's test).

</div>

<div class="card">

**3. Optional but ideal — bless the pattern as a tenant-shared service**
If the Hub works, document it as the standard "webhook out" path for tenants who need raw alerts for automation. Keeps BigPanda as the canonical incident path.

</div>

---

## What this unlocks beyond triage

Same Hub serves any tenant team that wants raw alerts for automation:

- **AI triage** (us) — kagent diagnoses + recommends remediation
- **Auto-remediation** — restart pods on `OOMKilled`, scale on sustained pressure
- **Capacity teams** — feed alerts into capacity planning models
- **Cost teams** — flag runaway-cost signals (token burn, storage spike) into FinOps
- **Compliance** — security alerts to a separate audit pipeline
- **Per-team Slack/Teams routing** — bypass the BP correlation for low-noise channels

One sanctioned ingress, N internal pipelines. **The Hub becomes platform infrastructure.**

---

<!-- _class: lead -->

# Recommendation

## Build the Hub. 4 weeks. Reusable forever.

**Path A (scrape BP):** more work, worse result, single-purpose.
**Path B (Hub):** less work, better result, scales to N teams.

The hard part is the conversation, not the code.

---

## Appendix — payload schema we'd guarantee

```json
{
  "version": "4",
  "status": "firing|resolved",
  "receiver": "webhook-hub",
  "alerts": [{
    "status": "firing",
    "labels": {
      "alertname": "...",
      "severity": "critical|warning|info",
      "namespace": "...",
      "pod": "...",
      "service": "...",
      "cluster": "...",
      "team": "..."
    },
    "annotations": {
      "summary": "...",
      "description": "...",
      "runbook_url": "..."
    },
    "startsAt": "2026-05-01T...Z",
    "generatorURL": "..."
  }],
  "commonLabels": { "team": "...", "cluster": "..." }
}
```

Same shape Grafana, Prometheus AM, and Loki Ruler all emit. Subscribers parse one schema.
