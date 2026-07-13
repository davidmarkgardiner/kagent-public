# Alloy → Vector → Kafka → Argo agent-triage plan

## Decision

Use the telemetry path below for **logs and Kubernetes events that need
automated triage**. Grafana/Loki remain a parallel evidence and visualisation
path; Grafana alerting is not an automation trigger in this design.

```text
workload cluster

  pod logs ───────┐
                   ├─ Alloy ── OTLP ──> Vector ──> Kafka ──> Argo ──> read-only triage agent
  Kubernetes events┘                    │              │
                                       groups,        one bounded
                                       enriches,      incident/evidence package
                                       deduplicates

                   └─ optional later mirror ──> Loki / Grafana
                                                    dashboards, search and full retained evidence
```

This eliminates the current loss of first-pass context when Grafana turns a
log query into a small alert notification. The agent should receive an
evidence package before it begins: not merely "Pod X is failing", and not a
stream of every raw log line.

## What changes and what does not

| Area | Target behaviour |
|---|---|
| Alloy | Collect pod logs and Kubernetes events once; send OTLP logs to Vector. Add the Loki mirror later, without changing the automation path. |
| Vector | Accept OTLP, classify an incident, correlate matching log/event records, redact bounded fields, deduplicate, and publish a stable triage contract to Kafka. |
| Kafka | Retain raw transport records only when replay/audit requires it; always retain `incident-triage-requests`, `incident-triage-results`, and a DLQ. |
| Argo | Consume only normalized incident requests; apply rate limits and submit a read-only triage workflow. |
| kagent | Receive the evidence package as the primary input. Grafana MCP and AKS-MCP are follow-up tools, not required to understand the initial symptom. |
| Loki/Grafana | Receive the parallel copy for search, dashboards, retention, and a human investigation surface. Do not send Grafana log alerts into the triage workflow. |

## Existing building blocks

- `observability/managed-lgtm-integration/alloy-snippets/02-logs-to-loki.alloy`
  already collects pod logs and Kubernetes events and writes them to Loki.
- `observability/confluent-cloud-pipeline/workload-cluster/02-alloy-config.yaml`
  already converts Kubernetes events to OTLP logs and writes them to Kafka.
- `observability/vector/manifests/01-vector-alertmanager-normalizer.yaml` and
  `observability/vector/homelab/vector-kafka-raw-to-normalized.yaml` provide
  the Vector-to-Kafka normalization, routing, and dedupe pattern.
- `observability/vector/manifests/02-argo-alertmanager-triage-topic.yaml`
  provides the Kafka EventSource and Sensor pattern.

The new work is to make the source contract include both pod logs and
Kubernetes events, then make the Vector output an evidence-rich triage request.
It should not extend the existing Grafana/Alertmanager payload path.

## Target topic and payload contracts

Use a small fixed topic set, not one topic per namespace:

```text
telemetry-raw                  optional, short retention, replay/audit only
incident-triage-requests       required, normalized evidence packages
incident-triage-results        required, workflow/agent verdicts and audit
incident-triage-dlq            required, invalid or repeatedly failed records
```

The request must use `observability.triage.v2` and be deliberately bounded:

```json
{
  "schema_version": "observability.triage.v2",
  "incident_id": "{{STABLE_HASH}}",
  "source_types": ["pod-log", "kubernetes-event"],
  "cluster": "{{CLUSTER_NAME}}",
  "environment": "{{ENVIRONMENT}}",
  "namespace": "{{NAMESPACE}}",
  "service": "{{SERVICE_NAME}}",
  "pod": "{{POD_NAME}}",
  "severity": "critical",
  "reason": "CrashLoopBackOff",
  "observed_at": "{{RFC3339_TIMESTAMP}}",
  "evidence_window": {"start": "{{RFC3339_TIMESTAMP}}", "end": "{{RFC3339_TIMESTAMP}}"},
  "evidence": {
    "event_summary": "Back-off restarting failed container",
    "log_signature": "database authentication failed",
    "matching_log_count": 17,
    "representative_log_lines": ["{{REDACTED_LINE_1}}", "{{REDACTED_LINE_2}}"],
    "logql": "{cluster=\"{{CLUSTER_NAME}}\", namespace=\"{{NAMESPACE}}\", pod=\"{{POD_NAME}}\"}",
    "suggested_kubectl": "kubectl -n {{NAMESPACE}} describe pod {{POD_NAME}}"
  },
  "target_agent": "sre-triage-agent",
  "route_key": "{{ROUTE_KEY}}",
  "dedupe_key": "{{DEDUPE_KEY}}",
  "automation_allowed": false
}
```

`representative_log_lines` must be capped by count and byte size, redacted
before Kafka, and selected by a documented rule. Do not put full log streams,
secrets, tokens, request bodies, or high-cardinality labels in the message.

## Implementation sequence

### 1. Define the evidence contract and fixture tests

1. Add pod-log, Kubernetes-event, and correlated crash-loop fixtures under
   `observability/vector/examples/`.
2. Extend the existing Vector test harness to prove the output contains a
   bounded evidence window, event summary, signature, log samples, routing and
   stable dedupe key.
3. Add negative tests proving secret-shaped values and oversized entries go to
   a redacted record or DLQ, never to the agent topic.

**Gate:** deterministic local Vector tests pass with no cluster needed.

### 2. Add the Alloy dual-output source

1. Keep the existing `loki.source.kubernetes` and
   `loki.source.kubernetes_events` sources.
2. Bridge both source streams to OTLP logs and send them to Vector's
   OpenTelemetry HTTP receiver using Alloy `otelcol.exporter.otlphttp`.
3. Make the core Vector branch independent of `loki.write`; add the
   Loki/Grafana mirror only when its endpoint is available. Its delivery must
   never be a prerequisite for creating a Kafka triage record.
4. Configure bounded retry queues, TLS and workload identity/secret references
   appropriate to the target environment. Do not add static credentials to Git.

**Gate:** a synthetic pod log and Kubernetes Warning are visible in both
Vector input metrics and Loki; a Vector outage makes the Alloy queue/retry
visible rather than silently dropping records.

### 3. Create the Vector incident builder

1. Deploy Vector in the management/triage boundary with an OTLP HTTP source.
2. Normalize source records into a common internal shape.
3. Use a short correlation window keyed by cluster, namespace, pod/container,
   and service: for example, a Warning/BackOff event plus matching error logs
   within five minutes.
4. Define incident triggers: crash loop with matching error logs, repeated
   error signature over threshold, or an allow-listed critical signature.
   Everything else stays in Loki and does not create agent work.
5. Redact and cap evidence; set `automation_allowed: false`; route malformed
   records to the DLQ.
6. Publish accepted incidents to `incident-triage-requests` and operational
   counters/lag metrics for Grafana.

**Gate:** ten duplicate errors plus one BackOff create exactly one enriched
triage request, not eleven workflows.

### 4. Wire Kafka to Argo and the read-only agent

1. Add an Argo Kafka EventSource for `incident-triage-requests`.
2. Add one generic Sensor that validates schema version, severity and route;
   apply a conservative trigger rate limit.
3. Pass the entire normalized request to a new or updated generic triage
   WorkflowTemplate. Do not reduce it to `body.alertmanager`.
4. Have the workflow write an outcome to `incident-triage-results` and send
   repeatedly failing messages to the DLQ path.
5. Keep remediation separate: the first proof is read-only triage and requires
   no apply/delete tool permissions.

**Gate:** the agent's first prompt includes evidence lines and event context;
the prompt must not state that it needs an MCP lookup to learn what fired.

### 5. Proxmox proof and acceptance run

When Proxmox is available, run the following deliberate scenario:

```text
create a controlled failing pod
  -> Kubernetes BackOff event + matching application error logs
  -> Alloy sends the same records to Vector and Loki
  -> Vector emits one redacted incident package to Kafka
  -> Argo creates one read-only triage workflow
  -> agent returns a diagnosis using the included evidence
  -> Grafana shows the raw logs and the pipeline health, but does not trigger the workflow
```

Capture: Alloy export success/failure, Vector received/accepted/dropped and
redacted counters, Kafka offsets/lag, EventSource/Sensor delivery, workflow
completion, agent input/output, and the matching Loki query. A successful
workflow alone is not proof.

## Delivery boundaries while Proxmox is down

Now: contracts, fixtures, manifests, static configuration validation, and
container-backed Vector tests can be built and reviewed locally.

Deferred: valid cluster authentication, Alloy component version compatibility,
network policies, Kafka ACLs, real pod-log collection, and the end-to-end
failure proof. These must remain marked unverified until the Proxmox runtime is
back.

## Architecture judgement

This is a cleaner automation path than Grafana-alert-to-agent. The adjustment
is that Loki/Grafana should not be removed: they remain the complete retained
record and human interface. Vector/Kafka/Argo becomes the incident-production
path, with the agent receiving the evidence that would otherwise be discarded
by alert notification templating.
