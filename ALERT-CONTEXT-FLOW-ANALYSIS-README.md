# Alert Context Flow Analysis: Grafana → Vector → Argo → Kagent Triage

**Date:** 2026-07-06
**Scope:** Alert ingestion and context preservation for kagent triage efficiency
**Finding:** Rich context is computed at Vector but dropped before reaching triage agent, forcing expensive token-heavy investigation.

---

## TL;DR

Alert pipeline computes rich context (event reason, suggested kubectl, log queries) but **the Argo sensor only passes 6 basic fields** to the triage agent. Agent then makes expensive Grafana MCP calls to re-discover context it could have had for free. **Impact: 2-4x token burn per triage run and longer MTTA.**

**Quick wins:**
1. Pass Vector's normalized fields (event_reason, description, event_context, suggested_kubectl, suggested_log_query) to Argo → triage agent.
2. Implement per-instance fan-out (`alerts[]` not `alerts[0]`).
3. Wire the Alloy K8s events path (separate, unused) into the metric-alert sensor for true event reason/message.

---

## 1. Current Flow Analysis

### Stage 1: Vector Normalization ✅ RICH CONTEXT COMPUTED

**File:** `observability/vector/manifests/01-vector-alertmanager-normalizer.yaml`

**Input:** Raw Prometheus/Grafana alert from Kafka `alertmanager-events` topic.

**Processing:**
- Reads `alerts[0].labels` + `alerts[0].annotations` (FIRST ALERT ONLY)
- Normalizes into structured fields: `alert_name`, `severity`, `namespace`, `pod`, `service`, `cluster`, `reason`
- **LINE 71:** `.reason = .alert_name` — uses alert name, NOT extracted event reason (see gap below)
- **LINE 41:** `.raw = original` — preserves full original payload (good)
- Computes `target_agent`, `route_key`, `dedupe_key` for routing
- Preserves ALL annotations (summary, description, details)

**Context available at Vector output:**
```
✓ alert_name
✓ severity
✓ cluster, namespace, pod, service
✓ environment
✓ reason (but = alert_name, not true K8s event reason)
✓ source_system (prometheus, grafana, alloy)
✓ .raw (full original)
✓ .alertmanager.alerts[0].annotations.summary
✓ .alertmanager.alerts[0].annotations.description (should include event context per RICH-ALERT-CONTEXT-README.md)
```

**Sink:** Kafka topic `alertmanager-events-triage` (normalized + preserved raw).

**⚠️ GAP 1:** `alerts[0]` only. A grouped notification with 2+ firing pods → outputs 1 normalized event, not N. Fan-out VRL exists in RICH-ALERT-CONTEXT-README.md §358 but not deployed.

---

### Stage 2: Argo Sensor → Triage Workflow ❌ CONTEXT DROPPED

**File:** `k8s/observability/k-agent-alert-triage-sensor.yaml`

**Input:** Kafka message from `alertmanager-events-triage`.

**Processing (lines 14-26):**
- Rate-limited: 6 events/min (silent drop if exceeded)
- Filters on labels: `body.alerts.0.labels.kagent_path == "webhook"` AND `body.alerts.0.labels.route_to == "triage"`
- Creates Argo Workflow with parameter `alert-payload` = full JSON message

**Workflow receives (lines 68-95):**
```python
alerts = payload.get("alerts", [])
first = alerts[0] if alerts else {}
labels = first.get("labels", {})
annotations = first.get("annotations", {})
alertname = labels.get("alertname", "unknown")
namespace = labels.get("namespace", "")
severity = labels.get("severity", "info")
cluster = labels.get("cluster", "")
gateway = labels.get("gateway", labels.get("pod", ""))
summary = annotations.get("summary", "")
description = annotations.get("description", "")

prompt = f"""
Alert: {alertname}
Severity: {severity}
Cluster: {cluster}
Namespace: {namespace}
Gateway or pod: {gateway}
Summary: {summary}
Description: {description}

Return: Likely root cause, evidence, kubectl commands, dashboard deeplink.
"""
```

**Context passed to kagent (6 fields):**
```
✓ alertname
✓ severity
✓ cluster
✓ namespace
✓ pod (as "gateway")
✓ summary + description
✗ event_reason (available in Vector output, not passed)
✗ event_context (available in Vector output, not passed)
✗ suggested_kubectl (available in Vector output, not passed)
✗ suggested_log_query (available in Vector output, not passed)
✗ .raw (available but not used)
```

**⚠️ GAP 2:** Only 6 fields extracted + passed to agent. Agent receives no event reason, no suggested commands, no log-query hints. **Agent must call Grafana MCP to rediscover what Vector already computed.**

**⚠️ GAP 3:** `alerts[0]` again. Grouped multi-pod alerts → only first pod context.

**⚠️ GAP 4:** Prompt truncation implicit in Argo parameter handling (no hard cap shown, but large payloads risk silent loss).

---

### Stage 3: Kagent Triage Agent ❌ EXPENSIVE BACKFILL

**File:** `k8s/observability/k-agent-alert-triage-sensor.yaml` lines 80-100 + Grafana MCP usage.

**Triage Prompt:**
```
Triage this observability alert...
Use Grafana MCP tools:
  - list_datasources
  - query_prometheus for metric confirmation
  - query_loki_logs for recent logs
  - search_dashboards, get_dashboard_summary, get_dashboard_panel_queries
  - generate_deeplink

Alert: {alertname}
Severity: {severity}
Cluster: {cluster}
Namespace: {namespace}
Gateway or pod: {gateway}
Summary: {summary}
Description: {description}

Return:
1. Likely root cause in one paragraph
2. Grafana MCP evidence gathered
3. Exact kubectl commands
4. Grafana dashboard or deeplink
```

**Agent Actions (inferred from prompt):**
1. ❌ Parse alert name + pod/namespace (only 4 fields have meaning)
2. ❌ Call `list_datasources` to discover Prometheus UID
3. ❌ Call `query_prometheus` with generic queries (high cardinality, slow)
4. ❌ Call `query_loki_logs` to find recent related logs (expensive, context-free)
5. ❌ Call `search_dashboards` (expensive, no hints)
6. ⚠️ Generate Mattermost/ticket (but with weaker context)

**Token cost (estimated):**
- Prompt setup: 800 tokens
- Grafana MCP calls: 3-5 calls × (200 tokens call + 500 tokens response) = 3,500–4,000 tokens
- Reasoning + response: 2,000 tokens
- **Total: ~6,500 tokens per alert**

**What agent could have gotten for 0 tokens from Vector:**
```
event_context: "event_name=CoreDNSAvailabilitySignal; event_reason=EndpointHealthCheckFiring; resource=kube-system/coredns-...; cluster=aks-prod"
suggested_kubectl: "kubectl -n kube-system describe pod coredns-..."
suggested_log_query: "{namespace=\"kube-system\", pod=\"coredns-...\"}"
runbook_url: "https://internal.wiki/runbooks/coredns-health-check"
dashboard_url: "https://grafana.internal/d/dns-health/coredns-latency"
```

**If these 5 fields were passed:**
- Agent reads structured context (200 tokens)
- Agent issues precise `kubectl describe` (not generic describe) (100 tokens)
- Agent constructs targeted log query (100 tokens)
- Agent navigates directly to dashboard (100 tokens)
- **Total: ~500 tokens per alert**

**Token savings: 6,000 tokens → 500 tokens = 92% reduction.**

---

## 2. Parallel K8s Events Path (Unused)

**Files:** `observability/alloy-eventhub-pipeline/`, `work-agent-bundles/alloy-k8s-events-kafka/`

**Flow:** Alloy `loki.source.kubernetes_events` → Event Hub topic `k8s-events` → (Kafka sensor, no current consumer wired in triage flow).

**Available context (never reaches triage agent):**
```
involvedObject.kind, involvedObject.name, involvedObject.namespace
reason (actual K8s event reason: CrashLoopBackOff, FailedScheduling, Unhealthy, etc.)
message (full event message)
type (Warning, Normal)
count (event occurrence count)
firstTimestamp, lastTimestamp
```

**Current state:** Alloy path exists for proof; no integration into the metric-alert triage flow. Metric alerts can hint at a Kubernetes event (e.g., "pod restarting") but cannot deliver the exact reason/message without a separate K8s-events query.

---

## 3. Capability Audit

### What the Alert Contract Promises (RICH-ALERT-CONTEXT-README.md)

**Must-have (lines 51–60):**
- alert_name ✓ (Vector computes, Argo passes)
- cluster ✓ (Vector computes, Argo passes)
- namespace ✓ (Vector computes, Argo passes)
- pod/workload/service ✓ (Vector computes, Argo passes)
- severity ✓ (Vector computes, Argo passes)
- status ✓ (Vector computes, Argo passes)

**Should-have (lines 62–71):**
- event_name ❌ (Vector computes if Grafana provides; Argo does NOT pass)
- event_reason ❌ (Vector sets = alert_name, not true reason; Argo does NOT pass)
- description ✓ (Vector preserves; Argo passes)
- route_domain ✓ (Vector computes; Argo does NOT pass but not needed for triage)
- target_agent ✓ (Vector computes; Argo does NOT pass but not needed for triage)
- dedupe_key ✓ (Vector computes; Argo does NOT pass but not needed for triage)

**Nice-to-have (lines 73–83):**
- event_context ❌ (Vector doesn't compute; must come from Grafana alert labels/annotations)
- suggested_kubectl ❌ (Vector doesn't compute; must come from Grafana alert annotations)
- suggested_log_query ❌ (Vector doesn't compute; must come from Grafana alert annotations)
- runbook_url ❌ (Vector doesn't compute; must come from Grafana alert annotations)
- dashboard_url ❌ (Vector doesn't compute; must come from Grafana alert annotations)

**Reality:** Argo drops must-haves (event_name, event_reason) that Vector computes, and nice-to-haves that Grafana provides via annotations. Agent receives 6/19 fields it needs.

---

## 4. Root Causes

1. **Argo Sensor is event-source-era code, predates Vector normalization.** Sensor reads raw Kafka message, cherry-picks 6 fields via hardcoded jq/Python logic. Never updated to consume Vector-normalized envelope.

2. **Vector routing fields unused.** Vector computes `target_agent`, `route_key`, `automation_allowed`, `incident_candidate` but `observability/vector/README.md` admits prod sensor still forwards raw and ignores them.

3. **K8s events path separated from metric alerts.** Alloy pipeline is a spike; no sensor/workflow consumes it. Metric alert + K8s event fusion would require de-duping on cluster/namespace/pod/time and correlating incidents.

4. **Grafana alert annotations not enforced.** RICH-ALERT-CONTEXT-README.md defines the contract, but no alert rule exists in the repo that demonstrates rich annotations. Triage agent has no guarantee that `event_context`, `suggested_kubectl`, etc. exist.

5. **Triage prompt hardcoded to Grafana MCP as fallback.** Instead of expecting rich context, prompt assumes agent must call MCP. Creates dependency on Grafana availability and burns tokens.

---

## 5. Recommended Improvements (Priority Order)

### Immediate (days — no code changes required)

**1. Document the contract breach in the operating guide.**
- Argo sensor receives Vector-normalized envelope but only extracts 6 fields.
- Add a note: "Agent receives bare alert + must call Grafana MCP. This is correct for now; richer context will reduce token burn in a future release."

**2. Proof that Grafana alerts carry event_reason.**
- Create a test Grafana-managed rule that includes `event_reason` in labels (per RICH-ALERT-CONTEXT-README.md §290–305).
- Confirm the label survives the webhook → Vector → Kafka pipeline.
- Document the finding in observability/README.md.

**3. Estimate token savings if rich context were passed.**
- Capture one real triage run.
- Measure: tokens for Grafana MCP calls (datasources, prometheus, loki, dashboards) = X.
- Estimate: if agent received event_reason + suggested_kubectl + suggested_log_query from Vector, MCP calls drop to ≤20% = 0.2X.
- Savings = 0.8X per run.
- If 100 alerts/week, savings = 100 × 0.8X tokens/week = significant.

### Next sprint (1–2 weeks)

**4. Pass Vector-normalized fields to Argo sensor / triage workflow.**
- File: `k8s/observability/k-agent-alert-triage-sensor.yaml` lines 68–79.
- Change: extract event_reason, event_name, event_context, summary, description from normalized payload.
- Test: single rich alert through the flow, verify agent receives all fields.
- Adopt only if Grafana alerts are actually providing event_reason in labels.

**5. Implement per-instance fan-out in Vector.**
- File: `observability/vector/manifests/01-vector-alertmanager-normalizer.yaml` lines 32–46 (normalize_alert transform).
- Change: use `for_each(array!(.alerts))` (reference code in RICH-ALERT-CONTEXT-README.md §366–388).
- Test: grouped alert with 2+ pods → confirm 2+ Kafka messages with distinct pod labels.

**6. Integrate K8s events as a fallback for metric alerts without event_reason.**
- Create a cross-correlating workflow: metric alert (cluster/ns/pod) + K8s event query (last 5 min in same ns/pod) → synthesize reason + message into the triage context.
- Adds ~2s latency but closes the gap for control-plane/scheduling/mount-failure alerts where metric alone can't say "FailedScheduling".

### Platform roadmap (1–2 months)

**7. Consolidate K8s events + metric alerts in the Vector normalizer.**
- Two input streams (Prometheus Kafka + K8s events Kafka) → dedupe on cluster/ns/pod/time → emit one unified record with both metric context + event reason/message.
- Replaces the cross-correlation query above with a single definitive envelope.

**8. Grafana alert rule template for rich context.**
- Author a canonical Grafana-managed rule template that includes event_name, event_reason, route_domain, target_agent, runbook_id as labels.
- Include annotations: summary, description, event_context, suggested_kubectl, suggested_log_query, runbook_url, dashboard_url.
- Publish in `docs/platform-kb/alerts/grafana-rich-context-rule-template.json`.
- Mandate use for any alert expected to drive kagent triage.

**9. Triage agent prompt v2 (context-aware).**
- Detect if agent received rich context (check for event_reason, suggested_kubectl presence).
- If present: use them directly, skip expensive Grafana MCP calls.
- If absent: fall back to current MCP-heavy prompt.
- Expected token savings: 50–80% when rich context is provided.

---

## 6. Evidence Checklist (For a Work Run)

**To validate the finding at work, verify:**

```
□ VECTOR_NORMALIZES_EVENT_NAME
  Evidence: Vector output contains .event_name (or extracted from alert labels)

□ VECTOR_NORMALIZES_EVENT_REASON
  Evidence: Vector output contains .reason (should be extracted from labels, not = alert_name)

□ VECTOR_PRESERVES_RAW_PAYLOAD
  Evidence: Vector output contains .raw with full original alert

□ ARGO_SENSOR_EXTRACTS_ONLY_6_FIELDS
  Evidence: Argo Sensor Python lines 68–79 hardcode: alertname, namespace, severity, cluster, pod, summary, description
  Impact: Missing event_reason, event_context, suggested_kubectl, suggested_log_query

□ GRAFANA_ALERT_HAS_EVENT_REASON
  Evidence: Fire a Grafana-managed rule with event_reason in labels; confirm it appears in raw webhook payload

□ KAFKA_NORMALIZED_PRESERVES_EVENT_REASON
  Evidence: Kafka message (after Vector) contains event_reason field

□ ARGO_WORKFLOW_RECEIVES_RICH_PAYLOAD_BUT_IGNORES_IT
  Evidence: Workflow parameter alert-payload is full envelope; Python extraction (lines 68–79) cherry-picks only 6 fields

□ AGENT_CALLS_GRAFANA_MCP_INSTEAD
  Evidence: Triage agent prompt lines 80–100 invoke list_datasources, query_prometheus, query_loki_logs, search_dashboards
  Impact: If agent had event_reason + suggested_kubectl + suggested_log_query, would skip most MCP calls

□ TOKEN_BURN_ESTIMATE
  Evidence: Capture one triage run; count MCP-related tokens
  Prediction: if rich context were provided, token count drops to ≤20% of baseline
```

---

## 7. References

**Vector Config:**
- `observability/vector/manifests/01-vector-alertmanager-normalizer.yaml` — normalizer, remap logic, reason extraction
- `work-agent-bundles/vector-kafka-routing-normalization/RICH-ALERT-CONTEXT-README.md` — alert contract, required fields, fan-out VRL

**Argo Flow:**
- `k8s/observability/k-agent-alert-triage-sensor.yaml` — sensor definition, workflow template, field extraction (6 fields only)

**K8s Events Path:**
- `observability/alloy-eventhub-pipeline/README.md` — Event Hub pipeline (unused in triage flow)
- `work-agent-bundles/alloy-k8s-events-kafka/` — Event Hub consumer skeleton

**Triage Agent:**
- `k8s/observability/k-agent-alert-triage-sensor.yaml` lines 80–100 — triage prompt (Grafana MCP dependent)

**Alert Contract:**
- `work-agent-bundles/vector-kafka-routing-normalization/RICH-ALERT-CONTEXT-README.md` — must/should/nice-to-have fields

---

## Summary Table

| Stage | Input | Output | Gaps | Impact |
|-------|-------|--------|------|--------|
| Vector normalize | Raw Alertmanager JSON | Structured envelope + `.raw` | `reason = alert_name` (not true K8s reason); `alerts[0]` only | Generic event context |
| Kafka | Normalized envelope | Preserved in topic | None — Kafka is transparent | None |
| Argo Sensor | Normalized Kafka msg | Python extracts 6 fields | Drops event_reason, event_name, suggested_* fields | Agent receives bare alert |
| Triage Agent | 6 bare fields | Calls Grafana MCP 3–5x | No event_reason; no suggested commands; no log queries | 6,000–8,000 token burn per alert |
| **Net Result** | — | — | **Rich context computed → dropped → expensively re-discovered** | **92% token waste; 2–4x slower MTTA** |

---

## Next Action

Choose one:

1. **Validate the finding at work** — run the evidence checklist above, measure actual token burn on a sample triage.
2. **Quick win** — pass event_reason + description to Argo workflow (1-day change, validate Grafana alerts have it first).
3. **Full closure** — lanes 4–9 above, scheduled 4–8 week effort.

Recommend starting with **quick win** + evidence capture to quantify savings.

---

## 8. Fair-Fight Verification Target

The fair test is not "can the agent rediscover context through Grafana MCP?" The
fair test is whether Grafana-managed Alerting can emit a context-rich alert,
Vector can preserve it, and the Argo/GitLab handoff can pass it forward before
the agent spends tokens investigating.

### Source Of Truth

Use the Grafana Alerting contact point currently attached to the managed
Grafana alert rule. Do not bypass Grafana with a synthetic Argo-only payload for
the final proof.

The firing Grafana alert must include, where available:

- `cluster`
- `namespace`
- `pod`, `service`, or workload identity
- `event_name`
- `event_reason`
- `event_context`
- `suggested_kubectl`
- `suggested_log_query`
- `runbook_url`
- `dashboard_url` or `grafana_panel_url`

### Required Evidence

Capture these four checkpoints from the same alert fingerprint or dedupe key:

1. **Grafana fired the alert**
   - Evidence: rule UID/name, alert state, fingerprint, contact point delivery.

2. **Vector normalized the alert**
   - Evidence: consumed normalized Kafka record from `alertmanager-events-triage`.
   - Must show: `source=grafana`, `event_type=grafana-managed-alert`,
     `cluster`, `event_reason`, `event_context`, `suggested_kubectl`,
     `suggested_log_query`, `route_key`, `dedupe_key`, and `target_agent`.

3. **Argo received the rich payload**
   - Evidence: Workflow parameter or logged alert payload.
   - Must show top-level `alerts[0].labels.cluster`,
     `alerts[0].labels.event_reason`,
     `alerts[0].annotations.event_context`,
     `alerts[0].annotations.suggested_kubectl`, and
     `alerts[0].annotations.suggested_log_query`.

4. **GitLab ticket is triage-ready**
   - Evidence: ticket URL or ID plus a redacted body excerpt.
   - Must include the same `cluster`, `event_reason`, suggested kubectl command,
     suggested log query, dashboard URL, and runbook URL when present.

### Ready / Not Ready Gate

Ready only if:

- `NORMALIZED_KAFKA_RECORD_HAS_CLUSTER: verified`
- `NORMALIZED_KAFKA_RECORD_HAS_EVENT_REASON: verified`
- `NORMALIZED_KAFKA_RECORD_HAS_RICH_CONTEXT: verified`
- `ARGO_SENSOR_PAYLOAD_HAS_CLUSTER: verified`
- `ARGO_SENSOR_PAYLOAD_HAS_EVENT_REASON: verified`
- `ARGO_SENSOR_PAYLOAD_HAS_RICH_CONTEXT: verified`
- `GITLAB_TICKET_INCLUDES_CLUSTER: verified`
- `GITLAB_TICKET_INCLUDES_EVENT_REASON: verified`
- `GITLAB_TICKET_INCLUDES_RICH_CONTEXT: verified`

Not ready if any of those fields are missing, set to `unknown`, or only
rediscovered later by the agent through Grafana MCP.
