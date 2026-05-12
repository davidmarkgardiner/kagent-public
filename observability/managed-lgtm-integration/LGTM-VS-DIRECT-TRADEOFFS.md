# LGTM vs Direct Alloy → Argo — what you gain, what you lose

> **TL;DR** — Direct Alloy → Argo and LGTM are **complementary, not competing**.
> The PoC looks redundant only because the K8s-event use case happens to fit
> both paths. The moment you want a metric-derived alert (PVC > 80%, error-rate
> spike, p99 latency) the LGTM path is no longer optional — that's literally
> where the evaluation happens. Keep both. Use each for what it's good at.

---

## 1. The two paths

```
                        ┌──────────────────────────────────────┐
                        │              LGTM stack              │
                        │  Mimir (metrics)  Loki (logs)        │
                        │  Tempo (traces)   Grafana (UI)       │
                        │     │           │                    │
                        │     ▼           ▼                    │
                        │   rules → AlertManager ──────────┐   │
                        └──────────────────────────────────┼───┘
                                                           │ webhook
                                                           ▼
                                                ┌──────────────────┐
   K8s events / log-pattern alerts ────────────►│  Argo Events     │
   (no evaluation window required)              │  webhook         │──► triage
                                                │  EventSource     │    workflow
                                                └──────────────────┘
```

- **Path A — Direct (Alloy → Argo)**: pattern-match in-flight, fire instantly.
  The PoC at `alloy-direct-poc/` proves this lane.
- **Path B — Through LGTM (Mimir/Loki rule → AlertManager → webhook)**: store,
  evaluate over a window, fan to humans + bots together. The existing
  `prometheus-alerting/` stack is this lane.

---

## 2. What you lose by skipping LGTM

| Capability | Direct Alloy → Argo | Via LGTM |
|---|---|---|
| **Metric-derived alerts** (PVC > 80 %, p99 latency, error-rate spikes) | ❌ Alloy doesn't evaluate PromQL / LogQL over a window | ✅ Mimir / Loki ruler does this every 30 s |
| **Stateful evaluation** (`group_by`, dedupe, flap suppression, `for: 5m`) | ❌ Each event is independent | ✅ AlertManager owns this |
| **Replay** (workflow failed → re-fire from yesterday's signal) | ❌ Gone the moment Argo drops it | ✅ Loki / Mimir retain |
| **Cross-signal correlation** (log → trace → metric) | ❌ Single stream only | ✅ Grafana joins via exemplars |
| **Human visibility** (SRE viewing what the agent is acting on) | ❌ Argo workflow logs only | ✅ Dashboards, Explore |
| **Audit / compliance** (which alert fired, what acted on it, when) | ⚠️ Argo history only — short retention | ✅ LGTM is durable |
| **Tuning loop** (false positives → tweak the rule, not the agent) | ❌ Redeploy Alloy / Sensor | ✅ Edit a `PrometheusRule` |
| **Multi-team consumption** (one alert into Slack + JIRA + agent) | ⚠️ Re-emit from a Sensor | ✅ AlertManager receivers |

---

## 3. What direct Alloy → Argo does better

- **K8s events / log-pattern triage** — these don't need a 30 s evaluation
  window. Alloy can pattern-match in-flight and post immediately. The existing
  `eventhub-otlp-pipeline` already does this.
- **PoC speed** — no managed-Grafana ticket, no 407 proxy, no BigPanda detour.
  Useful when LGTM is in someone else's hands and you can't add Grafana
  Contact Points.
- **Discrete events** that don't need aggregation — `CrashLoopBackOff`,
  `OOMKilled`, `ImagePullBackOff`, `FailedScheduling`. Each occurrence is a
  triage trigger by itself.
- **Latency** — Alloy → Argo is sub-second. AlertManager `group_wait`
  defaults to 30 s.

---

## 4. The architecture I'd actually argue for

```
Metric alerts  ─►  Mimir rules    ─►  AlertManager  ─►  webhook  ─┐
Log-rule alerts ─► Loki rules     ─►  AlertManager  ─►  webhook  ─┼─►  Argo Events  ─►  triage
K8s events     ─►  Alloy filter   ──────────────────►  webhook  ─┘   (one ingress family)
                   (no LGTM hop needed)
```

**Two ingress paths into Argo Events**, one shared downstream:

| Source | Body shape | Sensor filter | Triage template |
|---|---|---|---|
| AlertManager | `{alerts:[...]}` | `body.alerts[].labels.severity == "critical"` | `webhook-hub-ai-triage` |
| Alloy direct | `{streams:[{stream:{...}, values:[[ts,line]]}]}` | `body.streams[0].stream.severity == "critical"` | same template, parses different shape |

You don't need two triage workflows — the parse step normalises both into the
same internal schema (`alertname, namespace, pod, severity, summary`) before
calling kagent.

---

## 5. Decision rules — pick the path per alert type

| Alert type | Path | Why |
|---|---|---|
| Pod crashlooping (>3 restarts) | LGTM (`KubePodCrashLooping`) | Stateful evaluation needed (counts over time) |
| OOMKilled (single occurrence) | Either — LGTM gives audit, Direct gives latency | Discrete event |
| PVC > 80 % capacity | **LGTM only** | Requires PromQL on capacity metrics |
| Error rate doubled in 5m | **LGTM only** | Requires rate() over window |
| Custom log line "FATAL: db connection" | Either | Loki rule (LGTM) gives dedup; Alloy direct gives speed |
| K8s event "FailedScheduling" | Direct | Already a discrete event from kube-apiserver |
| ImagePullBackOff | Direct | Discrete event |
| Argo Workflow failed (need to triage *this* failure) | Direct | Triggering itself is event-driven |
| p99 latency > SLO | **LGTM only** | Histogram quantile only exists in metrics |

Rule of thumb: **does the alert require maths over a time window?**
Yes → LGTM. No → either, prefer Direct for speed.

---

## 6. The redundancy that *isn't*

It looks redundant in the PoC because we picked an event-shaped use case
(K8s pod crashes). For that one slice both paths work. The redundancy
disappears the moment a stakeholder asks for any of:

- "Page me when PVC capacity climbs above 80 %"
- "Triage when error rate doubles in 5 minutes"
- "Wake the SRE when p99 latency breaches SLO"

None of those are expressible without a metrics store + rule evaluator. LGTM
is doing real work for those. Alloy can't replace it.

---

## 7. Practical recommendation

1. **Keep the PoC** (`alloy-direct-poc/`) — right answer for event-shaped
   triage and unblocks today, no managed-Grafana dependency.
2. **Don't dismantle the LGTM/AlertManager lane** (`prometheus-alerting/`,
   `webhook-hub/`) — every metric-driven alert needs it. Cost there isn't
   building it (built), it's unblocking:
   - One Grafana Contact Point pointing at `alerts.lab.{{INGRESS_DOMAIN}}`
   - The 407 proxy auth (or its bypass)
3. **Plan for both** in the Sensor topology now (cheap) so the second path
   slots in without re-architecting.
4. **Don't pay LGTM cost twice** — discrete K8s events go *Alloy → Argo
   direct*, not Alloy → Loki → Loki ruler → AM → webhook → Argo. That hop
   chain is the genuine waste.

---

## 8. Cross-references

- PoC scaffold: [alloy-direct-poc/README.md](alloy-direct-poc/README.md)
- AlertManager → EventSource lane: [../prometheus-alerting/](../prometheus-alerting/)
- Hub variant (Istio + auth + multi-subscriber): [webhook-hub/](webhook-hub/)
- BigPanda parallel-path discussion: [BIGPANDA-OPTION.md](BIGPANDA-OPTION.md)
- Central Webhook Hub design: [CENTRAL-WEBHOOK-HUB.md](CENTRAL-WEBHOOK-HUB.md)
