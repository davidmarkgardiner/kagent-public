# Central Webhook Hub — A Low-Latency Lane for Alert-Driven Automation

**Status:** proposal / proof-of-concept design
**Date:** 2026-05-01
**Owner:** David Gardiner

> **One-line pitch:** alongside BigPanda (which keeps owning incident correlation), give tenants a single sanctioned webhook receiver they can subscribe to for raw alerts — for AI triage, auto-remediation, capacity, FinOps, and per-team routing.

---

## The constraint

Managed Grafana Contact Points are locked to **BigPanda only**. This is sensible default infrastructure: every alert becomes an incident handled through one system, no tenant has to design their own "where do alerts go" story.

But it leaves no path for **automation** that needs raw alerts. We want to build AI-driven triage (kagent) that consumes alerts in seconds, fetches diagnostics, and posts a first-pass analysis before a human even opens the incident. We cannot subscribe to alerts from the managed Grafana directly today.

---

## Why BigPanda is the wrong source for triage

BigPanda is a **correlation engine**. It is designed to *reduce* alert volume.

- **Deduplication** — N identical alerts become 1 incident
- **Grouping** — related alerts merge into a single incident
- **Suppression** — known-noisy patterns drop entirely
- **Enrichment latency** — typically 30s–5 min end-to-end

Each of those is correct for human incident management. Each of those is wrong for AI triage, which needs the raw, individual alert in flight, within seconds, with all labels intact.

If we tried to source alerts from BigPanda's outbound API or webhooks, we'd be paying the correlation tax on input — by the time an alert reached us, it would have been deduplicated into an incident object that has lost the per-alert labels we depend on for routing, anchoring, and prompt construction. The kagent triage system would have less to work with than a human reading the original alert.

---

## Two paths considered

| | **Path A — Scrape from BigPanda** | **Path B — Central Webhook Hub** |
|---|---|---|
| Source of truth | BigPanda outbound API/webhook | Managed Grafana / AlertManager direct |
| Latency | 30s – 5 min | < 5 sec |
| Alert fidelity | Correlated, dedup'd, lossy | Raw, full-detail |
| Effort | ~1.5 weeks | ~2 weeks |
| Reusable for other teams | No | Yes |
| Affects BigPanda | Adds load on BP API | Zero impact |
| Recommended? | No | **Yes** |

Path A buys nothing long-term. Path B becomes platform infrastructure other teams can adopt.

---

## What the Hub is

A single sanctioned webhook receiver that the platform team approves once.

- **One inbound URL.** `https://webhook-hub.<our-domain>/inbound`
- **Many internal subscribers.** Tenant teams subscribe to alert classes via labels.
- **Owned, audited, secured by us.** Platform team approves the boundary; consumers self-serve inside it.

The platform team adds **one** new Grafana Contact Point. Forever. Scaling to N tenants happens entirely on our side, with no further platform-team involvement after the initial approval.

---

## Architecture

Built on Argo Events, which is already in production for our existing K8s-event triage. No new product to learn.

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

### What each layer does

**Ingress — Istio Gateway + AuthorizationPolicy.** TLS termination at the shared wildcard Gateway. Source-IP allow-list (managed Grafana egress only) plus bearer-token check at the sidecar. Pattern already proven for the Teams HITL callback webhook (commit `f5fbdb1`), so this is not a novel security posture for our cluster.

**EventSource — Argo Events `webhook` type.** Validates payload shape, enforces `authSecret` against the same bearer token, publishes the alert to the NATS EventBus. Audit log via the existing Argo Events controller.

**EventBus — NATS JetStream.** Durable, replayable, fan-out by subject. Already running for Argo Events. No new component.

**Sensors — one per subscriber team.** Each Sensor filters by alert labels (alertname, severity, team, namespace), and triggers whatever the team needs: an Argo Workflow, an outbound webhook, a Slack post, an HTTP call to their internal API. Self-service from the team's namespace.

---

## Subscriber model — how a team plugs in

A new team needs two pieces of YAML in their own namespace.

**Step 1 — define what alerts you care about** (label match):

```yaml
filters:
  data:
    - path: body.commonLabels.team
      value: ["ai-platform"]
    - path: body.alerts[0].labels.severity
      value: ["critical", "warning"]
```

**Step 2 — declare the action** (Workflow, webhook, Slack, etc.):

```yaml
triggers:
  - template:
      name: ai-platform-triage
      k8s:
        operation: create
        source:
          resource:
            workflowTemplateRef:
              name: alertmanager-triage
```

That's it. One Sensor manifest in the team's namespace. No new infrastructure, no platform-team review per team, no per-team URL to register with Grafana.

---

## Security model

The questions a platform team will actually ask, with the answers up front:

| Concern | How the Hub addresses it |
|---|---|
| Who can POST to the hub | Source-IP allow-list at Istio (Grafana egress only) + bearer token at ingress + EventSource `authSecret` validation |
| Who can subscribe | RBAC on Sensor creation per namespace — owned by tenant teams |
| Audit trail | Every inbound webhook + every Sensor trigger logged via Argo Events controller |
| Token rotation | Standard ExternalSecret + Vault rotation; one shared token, scoped to one URL |
| Replay / DoS | Rate limit at Sensor (already used: 5/min for triage) |
| Multi-tenancy isolation | Each team's Sensor lives in their namespace, with their RBAC |
| Schema validation | EventSource validates required fields before fan-out |

The pattern is already in production for the Teams HITL callback webhook — same Istio Gateway, same AuthorizationPolicy shape, same Argo Events EventSource. We are not asking the platform team to bless a new pattern, only a new instance of an approved one.

---

## How hard would the BigPanda-scrape alternative be?

For comparison — what if we did try to source alerts from BigPanda?

- **Effort:** ~1.5 weeks. BigPanda API auth, polling vs outbound webhook decision, rate-limit handling, dedup of correlated incidents back to constituent alerts.
- **Latency penalty:** 30s–5 min added on top of the original alert firing.
- **Fidelity penalty:** original alert labels lost in BP's incident merge — we recover incidents, not alerts.
- **Operational coupling:** every change to BigPanda's correlation policy could break our triage filtering.
- **Reusable for other teams:** no. Every team would need their own BP integration with their own correlation-aware filtering.

Verdict: the effort is comparable to building the Hub, but the result is strictly worse on every axis that matters for triage. Path B (Hub) is the recommendation regardless of timeline pressure.

---

## Why this is replicable

A new subscriber team needs three things, all packaged.

**1. A Helm chart or KRO ResourceGraph.** Generates a Sensor + WorkflowTemplate scaffold for the team's namespace. One `helm install`. We already have the pattern in `infra-stack/kro-stack/definitions/`.

**2. A `SUBSCRIBER-GUIDE.md`.** Two-page document: pick a label match, pick a trigger type, run the chart. Worked example for "alerts on my team's services → my Slack channel."

**3. A schema reference.** What fields are guaranteed in the payload (alertname, severity, labels, annotations, generatorURL). What's optional. So filter expressions don't break on edge cases or schema drift.

Onboarding a new team should take roughly 30 minutes once the Hub is live.

---

## Proof of concept — 4-week plan

**Week 1 — Approval and scaffolding.** Send the Teams message to platform team requesting one Contact Point + egress confirmation. While waiting, stand up the Istio Gateway + EventSource + bearer auth in our cluster (pattern already in repo from the HITL work). Have the URL and token ready when approval lands.

**Week 2 — End-to-end with one alert rule.** Author one Grafana alert rule against a real metric we own. Configure the Webhook Contact Point to point at the Hub. Stand up one Sensor that triggers an Argo Workflow which posts to Mattermost. Smoke-test: change the metric, watch the alert land in MM in under 5 seconds.

**Week 3 — kagent integration and second subscriber.** Wire the kagent A2A triage call into the Workflow (pattern already in `alerts/workflow-template-alerts.yaml`). Add a second team's Sensor with a different label match and a different action. Prove fan-out works: one Hub ingress, two independent pipelines.

**Week 4 — Replication kit and handover.** Helm chart for new subscribers. Subscriber guide. Schema doc. Observability dashboard (Argo Events lag, Sensor triggers/min, Workflow success rate). Demo to platform team and to two or three tenant teams who might adopt next.

---

## Asks of the platform team

**1. Approve one Grafana Contact Point.** URL: `https://webhook-hub.<our-domain>/inbound`. Bearer token: we provide. One row in their alert routing config. We do not need them to add anything else, ever — all expansion happens on our side.

**2. Confirm Grafana egress path.** Either add the destination to the proxy bypass / `NO_PROXY` list, or provide proxy auth credentials so Grafana can traverse the egress proxy. Today's smoke test from the Grafana UI failed with `HTTP 407 Proxy Authentication Required`, so we need this resolved before any of the above works.

**3. Optional but ideal — bless the pattern as a tenant-shared service.** If the Hub works, document it as the standard "webhook out" path for tenants who need raw alerts for automation. BigPanda remains the canonical incident path. The Hub is the canonical automation path. No conflict, clear ownership.

---

## What this unlocks beyond triage

The same Hub serves any tenant team that wants raw alerts for automation:

- **AI triage** (us) — kagent diagnoses, recommends remediation, opens GitLab issue, notifies Mattermost
- **Auto-remediation** — restart pods on `OOMKilled`, scale on sustained pressure, rotate credentials on auth-failure bursts
- **Capacity teams** — feed alert frequency into capacity planning models
- **Cost / FinOps** — flag runaway-cost signals (token burn, storage spike) to the FinOps queue
- **Compliance / security** — security-labelled alerts to a separate audit pipeline with longer retention
- **Per-team Slack/Teams routing** — bypass BP correlation for low-noise channels where every alert is actionable

One sanctioned ingress. N internal pipelines. The Hub becomes platform infrastructure.

---

## Recommendation

Build the Hub. Four weeks. Reusable forever.

Path A (scrape BigPanda): more work, worse result, single-purpose, brittle.
Path B (Hub): less work, better result, scales to N teams.

**The hard part is the conversation, not the code.** The implementation maps almost directly onto the HITL callback work already in the repo. The expensive part is getting platform team alignment on one Grafana Contact Point and one egress allow-list entry — and the framing of the conversation matters: this is *complementary* to BigPanda, never a replacement.

---

## Appendix — payload schema we'd guarantee subscribers

The Hub publishes a stable schema regardless of upstream source (Grafana, AlertManager, Loki Ruler all emit the same shape). Subscribers parse one schema:

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

Any field schema change is a versioned event — subscribers pin to a version in their filter and migrate on their own timeline.

---

## See also

- `OPTION-A-ISTIO-README.md` — the ingress + AuthorizationPolicy implementation pattern (exactly what the Hub uses)
- `OPTION-A-README.md` — nginx variant if you're not on AKS / no Istio
- `README-METRICS-EVENTS-ALERTING.md` — how metric-based alerts feed the Hub
- `README-LOG-ALERTING.md` — how log-based alerts feed the Hub
- `LGTM-TO-ARGO-EVENTS-RECAP.md` — top-level decision tree across all four options (A/B/C/D)
- `CENTRAL-WEBHOOK-HUB-DECK.md` — Marp slide version of this same document (only render when explicitly requested)
- `ai-platform/teams-hitl/` — reference implementation of the same Istio + Argo Events pattern, already in production
