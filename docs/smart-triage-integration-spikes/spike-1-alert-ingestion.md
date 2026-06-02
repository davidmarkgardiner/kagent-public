# Spike 1 — Alert Ingestion

**Implementation order: 1 of 5 (build first).**

**Status:** implemented and live-proven on 2026-06-01.

Evidence:

- Current all-spikes Alertmanager replay: `smart-triage-alert-b8gkz`,
  `Succeeded`, `14/14`.
- Duplicate replay: `smart-triage-alert-k4m2p`, `Succeeded`, `2/2`,
  `SMART_TRIAGE_DEDUP: suppressed`.
- Durable snapshot: `SMART-TRIAGE-FANOUT-LIVE-EVIDENCE.md`.

## Objective

Replace the synthetic `scenario` + `fingerprint` input with a real alert payload
from Alertmanager (or PagerDuty / Opsgenie / the work-standard alert source),
normalize it into the smart-triage incident schema, and start the fan-out
workflow — without performing remediation.

## Existing Repo Reuse (do not rebuild)

This repo already carries a complete Alertmanager → Argo Events → Workflow chain.
The spike is mostly **wiring the existing chain to the existing fan-out
workflow**, plus a normalize step.

| Concern | Already exists |
|---|---|
| Alertmanager webhook receiver values | `observability/prometheus-alertmanager/01-alertmanager-values.yaml` |
| PrometheusRule alert definitions | `observability/prometheus-alertmanager/02-custom-alerting-rules.yaml` |
| Argo Events EventSource (webhook on :12000 `/alerts`) | `observability/prometheus-alertmanager/03-eventsource-alertmanager.yaml`, also `k8s/observability/k-agent-alertmanager-eventsource.yaml` |
| Sensor filtering `status: firing`, rate-limited 5/min | `observability/prometheus-alertmanager/05-sensor.yaml` |
| Reference triage WorkflowTemplate (alert → GitLab issue) | `observability/prometheus-alertmanager/04-workflow-template.yaml` |
| Alt: Alertmanager → Kafka/Redpanda bridge | `platform/argo-events/sources/alertmanager-redpanda/` |
| Alt: generic webhook EventSource + sensor | `platform/argo-events/sources/webhook/` |
| EventBus (NATS) install | `platform/argo-events/install/eventbus/`, `platform/argo-events/sources/_common/eventbus.yaml` |
| Architecture writeup | `observability/prometheus-alertmanager/KAGENT-ALERT-TRIAGE-ARCHITECTURE.md` |

The existing Sensor (`05-sensor.yaml`) already extracts the raw Alertmanager body
and creates a Workflow from `workflowTemplateRef: alertmanager-triage`. The
existing `04-workflow-template.yaml` already parses these alert label fields with
`jq`: `alertname, severity, namespace, pod, container, status, startsAt,
annotations.summary, annotations.description, annotations.runbook_url`. Reuse
that exact extraction logic for normalization.

## Proposed Architecture

```text
Prometheus  --(PrometheusRule fires)-->  Alertmanager
  --(webhook receiver: argo-events-webhook)-->  EventSource (:12000 /alerts)
  --(EventBus / NATS)-->  Sensor (filter status==firing, rate-limit 5/min)
  --(create Workflow)-->  smart-triage-fanout workflow
        normalize-incident   <-- NEW: maps Alertmanager body -> incident schema
          -> fan out to specialists (unchanged)
          -> synthesize -> HITL suspend -> finalize -> prove-result -> eval
```

Two integration choices for the next agent to pick in Phase 0:

- **A. Point the existing Sensor at the fan-out workflow** (recommended first
  proof). Change the Sensor trigger to `workflowTemplateRef` the smart-triage
  fan-out (converted to a `WorkflowTemplate`) and pass the alert body as a
  parameter. Smallest change, reuses everything.
- **B. Keep `alertmanager-triage` as a thin front workflow** that normalizes,
  then submits the fan-out workflow. Useful if the work-standard pipeline must
  stay intact and only call smart-triage as a sub-step.

Namespace decision is part of Phase 0. The existing Alertmanager Sensor and
WorkflowTemplate live in `argo-events`, while the smart-triage fan-out workflow
and service account live in `argo`. The first build must choose one of these
safe shapes:

- Put the new smart-triage `WorkflowTemplate` in `{{ARGO_NAMESPACE}}` and grant
  the Argo Events Sensor service account explicit create permission for
  Workflows in `{{ARGO_NAMESPACE}}`.
- Or keep the front workflow in `{{ARGO_EVENTS_NAMESPACE}}` and have it submit
  the fan-out workflow in `{{ARGO_NAMESPACE}}` through a narrowly scoped
  submitter template.

Do not silently move the fan-out service account/RBAC into `argo-events`.

## First Safe Proof

Read **one** test or active non-production firing alert, normalize it, and start
the fan-out workflow that runs read-only specialists. No remediation, no GitLab
write, no cluster mutation.

```bash
# Replay one captured/synthetic Alertmanager firing payload at the EventSource,
# exactly like the existing test harness does:
#   observability/prometheus-alertmanager/test-alerts.sh
# then confirm one fan-out workflow was created from it.
argo list -n {{ARGO_NAMESPACE}} --selector event-type=prometheus-alert
argo get -n {{ARGO_NAMESPACE}} @latest
```

Proof = a fan-out workflow whose `normalize-incident` output shows the real
alert's `alertname/namespace/workload`, not the demo defaults, and which reaches
the HITL suspend without any write step.

## Required MCP / Tool / Server Shape

No new MCP server. This spike is event-plumbing only:

- Argo Events `EventSource` (reuse `03-eventsource-alertmanager.yaml`).
- Argo Events `Sensor` (reuse/retarget `05-sensor.yaml`).
- Argo `WorkflowTemplate` for the fan-out (convert current `workflow.yaml`).
- Alertmanager receiver config (reuse `01-alertmanager-values.yaml`).

For non-Alertmanager sources (`{{ALERT_SOURCE}}` = PagerDuty/Opsgenie), use the
generic webhook EventSource in `platform/argo-events/sources/webhook/` and write
a source-specific normalize mapping; the rest is identical.

## kagent Agent Contract

No new Agent. The fan-out specialists are unchanged. Add an alert-provenance
marker to the workflow's `normalize-incident` (script template, not an agent):

```text
ALERT_INGESTED: yes
ALERT_SOURCE: {{ALERT_SOURCE}}
INCIDENT_NORMALIZED: yes
SMART_TRIAGE_FANOUT: started
```

## Argo Workflow Integration Point

Rewrite `normalize-incident` in `a2a/smart-triage-fanout-demo/workflow.yaml`:

- Add input parameter `alert-payload` (raw alert body, as the Sensor passes it).
- Reuse the `jq` extraction from `04-workflow-template.yaml` to populate the
  normalized schema in `README.md` § "Normalized incident schema".
- Emit `scenario` and `fingerprint` from the alert (e.g.,
  `fingerprint = alerts[0].fingerprint`) so downstream tasks stay unchanged.
- Group/suppress duplicates by Alertmanager `fingerprint` (Sensor already
  rate-limits 5/min; add fingerprint dedup for repeat fan-outs).

## HITL Requirement

Unchanged and mandatory: the `wait-for-human-review` suspend stays between
synthesis and any finalize step. Alert ingestion must **not** auto-remediate; a
real firing alert only gets the operator to a populated HITL packet faster.

## Required Manifests / Scripts To Create

| Artifact | Purpose |
|---|---|
| `a2a/smart-triage-fanout-demo/workflow-template.yaml` | Fan-out converted to `WorkflowTemplate` so a Sensor can instantiate it |
| `a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml` | Sensor that triggers the fan-out template from a firing alert |
| `a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml` | Copy/placeholderized from existing EventSource |
| `a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml` | Cross-namespace create permission if Sensor stays in `{{ARGO_EVENTS_NAMESPACE}}` |
| Edit `workflow.yaml` `normalize-incident` | Alert-body → incident-schema mapping |
| `a2a/smart-triage-fanout-demo/scripts/replay-alert.sh` | Replays one synthetic firing payload at the EventSource |

## Validation Commands

```bash
bash -n a2a/smart-triage-fanout-demo/scripts/replay-alert.sh
kubectl create --dry-run=client -f a2a/smart-triage-fanout-demo/workflow-template.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml
kubectl apply --dry-run=server -f a2a/smart-triage-fanout-demo/sensors/sensor-submit-rbac.yaml
```

## Public-Safe Placeholders

| Placeholder | Use |
|---|---|
| `{{ALERT_SOURCE}}` | alertmanager \| pagerduty \| opsgenie \| work-standard |
| `{{ALERTMANAGER_WEBHOOK_URL}}` | EventSource receiver URL (no real host) |
| `{{ARGO_EVENTS_NAMESPACE}}` | argo-events |
| `{{ARGO_NAMESPACE}}` | argo |
| `{{AUTHORITATIVE_LABELS}}` | label set that identifies service/namespace/severity/owner/env/runbook |

## Evidence To Capture

- The replayed alert payload (sanitized) and the workflow it created.
- `normalize-incident` output showing real alert fields.
- `argo get` tree reaching `wait-for-human-review` with no write step executed.
- Dedup proof: a second identical alert within the window does not double fan out.

## Failure Classes

| Class | Meaning | Evidence |
|---|---|---|
| `ALERT_PAYLOAD_MALFORMED` | Body missing required labels / not JSON | normalize step stderr, raw body |
| `ALERT_SOURCE_UNAVAILABLE` | EventSource/webhook unreachable or auth rejected | EventSource pod logs, HTTP code |
| `DUPLICATE_ALERT_SUPPRESSED` | Same fingerprint within window (expected, not an error) | Sensor rate-limit / dedup log |
| `WORKFLOW_SUBMIT_FAILED` | Sensor could not create the fan-out workflow | Sensor logs, RBAC denial |
| `INCIDENT_NORMALIZE_FAILED` | Mapping produced an empty incident schema | normalize output, jq errors |

## Rollback / Disable Path

```bash
# Stop ingestion without touching the fan-out demo:
kubectl delete -f a2a/smart-triage-fanout-demo/sensors/alertmanager-to-fanout-sensor.yaml --ignore-not-found
kubectl delete -f a2a/smart-triage-fanout-demo/sensors/eventsource-alertmanager.yaml --ignore-not-found
# Revert Alertmanager receiver to its prior route (re-apply prior 01-alertmanager-values.yaml).
```

Disabling the Sensor immediately returns the demo to manual/synthetic trigger.

## Known Risks

- Alertmanager group/batch payloads carry multiple alerts; decide whether one
  payload = one fan-out (recommended: fan out on the first/highest-severity
  alert, list the rest as related).
- Rate-limit (5/min) protects the cluster but can drop a real second incident;
  document the tradeoff.
- Converting `workflow.yaml` to a `WorkflowTemplate` must preserve the existing
  `evaluate-lifecycle` `templateRef` and all proof markers.
- Non-Alertmanager sources have different payload shapes; the normalize mapping
  is source-specific even though the trigger path is shared.

## Exit Criteria

- One real/non-production firing alert produces exactly one fan-out workflow.
- `normalize-incident` emits the standard incident schema from the alert body.
- Workflow reaches HITL suspend with zero write/remediation steps.
- Duplicate suppression demonstrated.
- Failure classes emitted on malformed/duplicate/unavailable/submit-failure.
