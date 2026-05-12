# BigPanda as Alert Bridge — Design Analysis

**Status:** SPIKE REQUIRED before committing
**Date:** 2026-05-05
**Owner:** David Gardiner
**Context:** Work routes all LGTM alerts through BigPanda before any downstream webhook. We need to understand whether inserting BigPanda between managed AlertManager and our triage webhook is viable, and where fidelity is lost.

---

## What the triage agent needs

The kagent A2A call needs these fields to do useful work (mapped from the existing `parse-alertmanager` path):

| Field | Used for |
|---|---|
| `namespace` | Namespace anchoring — CRITICAL. Agent uses this to find the right specialist agent. |
| `pod` / `instance` | The offending object (for log fetching, describe calls) |
| `alertname` | Pattern-matching to agent skill library |
| `severity` | Routing: warning → triage, critical → triage + HITL gate |
| `cluster` | Multi-cluster routing |
| `environment` | Alert suppression in non-prod (if enabled) |
| `description` / `summary` | Agent prompt enrichment |
| `runbook_url` | Agent can cite the runbook in the GitLab issue |
| `generatorURL` / `externalURL` | Link back to the source alert in Grafana/AM — included in the GitLab issue body |
| `startsAt` | Age of the alert (older = more urgent) |
| `status` | `firing` vs `resolved` — drives ticket open vs close logic |

---

## BigPanda's outbound webhook schema

BigPanda normalises all alert sources into its own object model. A typical outbound payload looks like this:

```json
{
  "incident_id": "{{AZURE_SUBSCRIPTION_ID}}",
  "incident_url": "https://app.bigpanda.io/app/event-correlation/incidents/53d86a04",
  "status": "active",
  "severity": "critical",
  "started_at": 1746403200,
  "updated_at": 1746403500,
  "active_observations": 3,
  "alerts": [
    {
      "id": "alert-abc",
      "status": "active",
      "host": "aks-prod-01",
      "check": "KubePodCrashLooping",
      "description": "Pod my-app-abc123 has been restarting 12 times in 10 minutes",
      "primary_property": "aks-prod-01",
      "secondary_property": "KubePodCrashLooping",
      "severity": "critical",
      "source_system": "prometheus",
      "started_at": 1746403200,
      "ended_at": null,
      "tags": {
        "alertname": "KubePodCrashLooping",
        "namespace": "production",
        "pod": "my-app-abc123",
        "container": "app",
        "cluster": "aks-prod-01",
        "environment": "production",
        "severity_original": "warning",
        "summary": "Pod is crash looping",
        "description": "Pod my-app-abc123 in production is crash looping (12 restarts)",
        "runbook_url": "https://wiki.example.com/runbooks/crashloop",
        "generator_url": "https://grafana.example.com/explore?...",
        "external_url": "https://alertmanager.example.com/#/alerts"
      }
    }
  ]
}
```

---

## Gap analysis: what survives, what doesn't

| Required field | AlertManager direct | Via BigPanda | Risk |
|---|---|---|---|
| `namespace` | `alerts[].labels.namespace` ✅ | `alerts[].tags.namespace` ⚠️ only if BigPanda source mapping configured | **HIGH** — default BigPanda mapping for Prometheus sources does NOT preserve all labels as tags. Platform team must explicitly map it. |
| `pod` / `instance` | `alerts[].labels.pod` ✅ | `alerts[].tags.pod` ⚠️ same caveat | **HIGH** |
| `alertname` | `alerts[].labels.alertname` ✅ | `alerts[].check` ✅ (BigPanda uses this as `check` natively) | LOW |
| `severity` | `alerts[].labels.severity` ✅ | `alerts[].severity` ✅ — but remapped to BigPanda scale (critical/warning/unknown) | MEDIUM — original severity in `tags.severity_original` |
| `cluster` | `alerts[].labels.cluster` ✅ | `alerts[].host` or `alerts[].tags.cluster` ⚠️ | MEDIUM — BigPanda uses `host` as primary grouping; cluster may land there or in tags |
| `environment` | `alerts[].labels.environment` ✅ | `alerts[].tags.environment` ⚠️ | MEDIUM |
| `description` | `alerts[].annotations.description` ✅ | `alerts[].description` ✅ | LOW — BigPanda maps AM annotations.description → alert.description natively |
| `summary` | `alerts[].annotations.summary` ✅ | `alerts[].tags.summary` ⚠️ | MEDIUM — not a native BigPanda field |
| `runbook_url` | `alerts[].annotations.runbook_url` ✅ | `alerts[].tags.runbook_url` ⚠️ | MEDIUM — survives only if in tags mapping |
| `generatorURL` | `alerts[].generatorURL` ✅ | `alerts[].tags.generator_url` ⚠️ | MEDIUM |
| `externalURL` | root `externalURL` ✅ | `incident_url` ⚠️ (different thing) | LOW — BigPanda incident URL can replace it |
| `startsAt` | `alerts[].startsAt` ISO8601 ✅ | `alerts[].started_at` Unix epoch ✅ | LOW — format differs, trivial to convert |
| `status: firing\|resolved` | `alerts[].status` ✅ | `incident.status: active\|inactive\|resolved` + `alerts[].status: active\|inactive` | MEDIUM — `resolved` is `inactive`, not `resolved`; ticket-close logic needs updating |

**Key risk in bold:** `namespace` and `pod` will be silently dropped unless the platform team configures the BigPanda alert source to pass all Prometheus labels through as tags. This is a config step on their side, not ours.

---

## Complications summary

1. **Schema translation required** — BigPanda is not a transparent proxy. A `parse-bigpanda` jq step is required (see `alerts/parse-bigpanda.jq`). Adds 30–50 lines of jq that must be maintained if BigPanda changes its schema.

2. **Platform team configuration dependency** — Critical labels (`namespace`, `pod`, `cluster`) only survive if BigPanda's Prometheus source is configured with a labels-to-tags passthrough. If not, the agent has no namespace and cannot route.

3. **Correlation changes fan-out shape** — BigPanda may group N alert firings into one incident. The workflow's `withParam` fan-out changes target: instead of iterating over `data.alerts[]` from AlertManager, it iterates over `incident.alerts[]` from BigPanda. Same pattern, different path.

4. **Latency** — BigPanda adds 30s–5min correlation window before forwarding. Current Event Hub path: ~10–15s end-to-end. Direct AM webhook (Option A): sub-second. BigPanda is not suitable for the K8s-native real-time alert path.

5. **Resolved semantics** — `status: inactive` (BigPanda) ≠ `status: resolved` (AlertManager). GitLab ticket-close logic must be updated.

6. **Source IP allowlist** — BigPanda egress IPs must be allowlisted at our ingress, in addition to the bearer token check.

---

## Recommendation: split path

Do not gate K8s-native alerts through BigPanda. Use BigPanda only where correlation adds real value.

```
                    Option A (direct, rich, fast)
                  ┌─────────────────────────────────► Argo Events webhook
                  │   sub-second, full fidelity         EventSource: alertmanager
                  │   uses: parse-alertmanager (jq)     Sensor: same as proxmox path
Managed LGTM AM ──┤
                  │   BigPanda (correlated, slower)
                  └──► BigPanda ──► outbound webhook ──► Argo Events webhook
                        +30–300s                         EventSource: bigpanda
                        incident-shaped                  Sensor: bigpanda-triage
                        uses: parse-bigpanda (jq)
```

**Direct path (Option A)** — K8s-native alerts:
- `KubePodCrashLooping`, `KubeContainerOOMKilled`, `FailedScheduling`, `PVCNearCapacity`, etc.
- AlertManager `matchers` route directly to our ingress at `alerts.lab.{{INGRESS_DOMAIN}}/alerts`
- Same `parse-alertmanager` jq the proxmox path already uses (unchanged)
- Full label/annotation fidelity

**BigPanda path** — cross-team / multi-source incidents:
- Incidents correlated across Prometheus + Azure Monitor + CloudWatch + Dynatrace
- BigPanda sends one incident payload representing multiple correlated alerts
- Useful for: application-layer degradation that spans K8s + Azure + 3rd-party sources
- Use `parse-bigpanda.jq` to normalise into the same internal shape
- Same WorkflowTemplate entry point, different parser step

---

## Spike steps before committing

1. **Get a real payload** — ask platform team for one BigPanda outbound webhook sample from any existing Prometheus alert source. A JSON file is enough.
2. **Score the gap** — check whether `namespace`, `pod`, `cluster`, `environment` appear in `alerts[].tags`. If any of the four are missing, BigPanda's alert source must be reconfigured before this path is viable.
3. **Confirm network path** — can BigPanda reach `alerts.lab.{{INGRESS_DOMAIN}}` outbound? BigPanda is SaaS, so it needs public egress. Get their egress IP range.
4. **Confirm auth** — BigPanda webhook configs support bearer token (most common) or basic auth. Bearer is the same pattern as Option A.

Spike output: one-page table of "field: present/absent/renamed" against the real payload. That decides whether BigPanda is viable in the K8s alert path or only the cross-source path.

---

## Files

```
managed-lgtm-integration/
├── BIGPANDA-OPTION.md                     ← this file
├── OPTION-A-README.md                     ← direct AM webhook (preferred for K8s alerts)
├── alerts/
│   ├── parse-bigpanda.jq                  ← jq filter stub (run spike to validate)
│   ├── workflow-template-bigpanda.yaml    ← Argo WorkflowTemplate using parse-bigpanda
│   └── workflow-template-alerts.yaml      ← existing (AlertManager direct)
└── OPEN-QUESTIONS.md                      ← Q4 covers the network path question
```
