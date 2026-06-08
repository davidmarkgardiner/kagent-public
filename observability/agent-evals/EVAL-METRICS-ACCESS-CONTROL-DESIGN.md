# Eval Metrics Library and Access Control Design

## TLDR

Agent evaluation metrics must be treated as a stable platform contract, not as
an implementation detail of one CLI.

The metric rendering logic now lives in:

```text
observability/agent-evals/scripts/metrics.py
```

The summarizer imports that library, and future exporters should do the same.
This keeps offline CI reports, Argo online evaluation, fleet exporters, and
future OTEL/Prometheus publishers aligned on one metric contract.

## Design Goals

- Keep metric generation independent from report generation.
- Use stable, low-cardinality metric names and labels.
- Avoid secrets, private URLs, raw prompts, raw trace text, or ticket content in
  labels.
- Allow read-only consumers to view dashboards without access to raw evidence.
- Separate score publishing from ticket update/remediation permissions.
- Make access-control boundaries explicit before production use.

## Metric Library Boundary

`scripts/metrics.py` owns:

- Prometheus text rendering
- metric names
- label escaping
- conversion of booleans to `0` or `1`
- consistent output for agent and lifecycle eval result JSON

It does not own:

- loading result files
- scoring
- Markdown report rendering
- pushing metrics to Prometheus
- Grafana dashboard provisioning
- ticket comments
- remediation actions

That means any future publisher can reuse the library:

```text
offline CI summary
Argo lifecycle eval task
fleet metrics exporter
OTEL bridge
Prometheus textfile writer
```

## Metric Families

### Agent Run Metrics

```text
agent_eval_score
agent_eval_passed
agent_eval_hard_failures
agent_eval_safety_score
```

Labels:

```text
agent
case_id
run_id
```

### Lifecycle Metrics

```text
agent_lifecycle_eval_score
agent_lifecycle_eval_passed
agent_lifecycle_eval_hard_failures
agent_lifecycle_eval_subscore
```

Labels:

```text
case_id
run_id
workflow_name
dimension
```

### Fleet Metrics

Fleet inventory and workflow counters are separate from the eval result library:

```text
kagent_agent_info
kagent_agent_ready
kagent_workflow_active
kagent_workflow_total
kagent_incident_funnel_total
```

These are documented in `FLEET-DASHBOARD.md`.

## Label Policy

Allowed labels:

- agent name
- case id
- run id
- workflow name
- score dimension
- stable environment label added by the metrics pipeline
- stable team/service label added by the metrics pipeline

Forbidden labels:

- prompt text
- final answer text
- raw tool arguments
- GitLab ticket title/body
- real ticket URL
- customer/user identifiers
- pod IPs or private IPs
- subscription IDs
- tenant IDs
- bearer tokens or API keys
- high-cardinality stack traces or log lines

If a value is useful for investigation but unsafe or high-cardinality, put it in
the sanitized Markdown report or restricted workflow artifact, not in a metric
label.

## Access Control Model

### Producer Permissions

The evaluation producer should only need:

- read access to sanitized workflow evidence passed into the step
- read access to ConfigMap-mounted eval scripts
- write access to its own workflow outputs/artifacts
- optional write access to a metrics handoff location

It should not need:

- Kubernetes mutation permissions
- GitLab write permissions
- secret read permissions
- broad pod log access
- access to raw model prompts or private traces unless explicitly sanitized

The remediation workflow and ticket-update workflow should remain separate
execution boundaries. Evaluation scores the result; it should not perform
remediation.

### Consumer Permissions

| Consumer | Access |
| --- | --- |
| On-call engineer | Grafana dashboard and sanitized eval report. |
| Platform SRE | Metrics, reports, sanitized lifecycle JSON, alert rules. |
| Agent owner | Metrics and reports for owned agents. |
| Security/audit | Long-lived eval result JSON and hard-failure summaries. |
| General dashboard viewer | Aggregated score metrics only. |

Raw evidence and traces should be restricted to the smallest operational group
that needs them.

## Grafana Access

Recommended folders:

```text
Agent Evals / Scorecards
Agent Evals / Fleet
Agent Evals / Audit
```

Recommended role split:

| Role | Permissions |
| --- | --- |
| Viewer | Read dashboards only. |
| Editor | Edit dashboards in non-prod folder only. |
| Admin | Manage datasources, alert routing, and production dashboards. |

Do not grant dashboard viewers access to raw workflow artifacts by default.

## Alerting Policy

Page or notify for:

- lifecycle hard failure count greater than zero on write-capable workflows
- ticket close attempted after failed eval
- remediation executed without verification
- evaluator infrastructure errors on production remediation workflows

Create non-paging notifications for:

- low score on read-only triage
- score trend degradation
- missing latency/cost telemetry
- sampled audit failures that do not affect production write paths

## Retention

| Data | Suggested retention | Notes |
| --- | ---: | --- |
| Prometheus metrics | standard metrics retention | Keep labels low-cardinality. |
| Eval result JSON | medium to long | Safe for audit if sanitized. |
| Markdown summary | ticket/artifact retention | Should contain no secrets. |
| Normalized lifecycle run JSON | medium | Useful for replay and regression. |
| Raw traces/logs | short | Restricted access; sanitize before replay. |

## Threat Model

### Risk: Sensitive Data In Metrics

Control:

- fixed metric label allowlist
- label escaping in `metrics.py`
- no prompt/response/log body labels
- public-safety leak checks in scorers

### Risk: Evaluator Can Mutate Cluster

Control:

- evaluator uses only provided evidence
- no `kubectl` access required for scoring
- separate remediation service account from evaluation service account

### Risk: Dashboard Exposes Incident Details Too Broadly

Control:

- metrics show score and identifiers only
- raw evidence stays in restricted artifacts/tickets
- Grafana folder permissions separate viewer/editor/admin access

### Risk: High Cardinality Breaks Metrics Backend

Control:

- do not label on pod name, ticket URL, prompt hash, trace id, or log line by
  default
- use stable case/workflow/agent dimensions
- sample read-only production triage if volume grows

### Risk: Eval Failure Blocks Incident Response

Control:

- keep evaluation after remediation and verification
- fail ticket closure, not emergency remediation
- provide break-glass manual closure path with explicit audit record

## Audit Checklist

- [ ] Metric names are stable and documented.
- [ ] Labels are low-cardinality and on the allowlist.
- [ ] No secret-like values appear in metrics.
- [ ] Eval runtime does not have cluster mutation permissions.
- [ ] Remediation and ticket-update permissions are separate from eval.
- [ ] Grafana viewers cannot access raw workflow artifacts by default.
- [ ] Hard failures produce a ticket/audit signal.
- [ ] Eval infrastructure errors are distinguishable from agent failures.
- [ ] Production starts audit-only before write-path gating.

## Implementation Notes

The current library renders Prometheus text format only. That is deliberate:
Prometheus text works for local samples, Argo output parameters, textfile
collectors, CI artifacts, and simple bridge jobs.

If OTEL export is added later, build the OTEL exporter on top of the same result
JSON and metric family contract rather than creating a second naming model.
