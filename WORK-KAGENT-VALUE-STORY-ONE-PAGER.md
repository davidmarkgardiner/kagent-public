# Kagent Platform Value Story

Purpose: one-page stakeholder summary for explaining why the kagent / agentic
platform work matters as it rolls into development and production AKS clusters.

## Executive Message

The goal is not to create more ServiceNow incidents. The goal is to stop
routine platform issues from becoming ServiceNow incidents at all.

Kagent is an agentic operations harness for AKS: it connects alerts, Grafana
evidence, Kubernetes state, runbooks, GitOps, security policy, human approval,
and evaluation into one repeatable workflow. When the system can safely detect,
explain, and fix or propose a GitOps change, it should do that before opening a
ServiceNow / GSNOW incident. When it cannot safely close the loop, it should
escalate with evidence, probable cause, proposed action, blast-radius context,
and an audit trail already attached.

## Value Thesis

| Today | With the agentic harness |
|---|---|
| Alerts become Teams noise, GitLab notes, or ServiceNow tickets after human triage. | Alerts become structured runs: detect, enrich, route, evaluate, remediate or escalate. |
| Engineers manually gather Grafana, Kubernetes, GitLab, runbook, and policy evidence. | Agents gather evidence from approved tools and return a decision-ready package. |
| ServiceNow is often the first durable workflow. | ServiceNow becomes the exception path when the platform cannot safely self-resolve. |
| Runbooks, dashboards, and incident learnings drift apart. | Incidents feed evals, KB updates, memory, dashboards, and regression/chaos tests. |
| Automation is hard to trust because quality is not measured. | Each run gets scored: detection, evidence, safety, remediation quality, and recovery. |

## What We Can Demonstrate

The management demo should show one controlled lower-env incident moving through
the whole loop:

```text
Alert / chaos signal
  -> Confluent / Argo event path
  -> smart triage fan-out
  -> Grafana evidence and Kubernetes evidence
  -> runbook / memory lookup
  -> decision: self-resolve, propose GitOps MR, or escalate
  -> HITL gate for risky action
  -> recovery verification
  -> eval score out of 10
  -> dashboard and report
  -> ServiceNow only if escalation is still required
```

The spoken outcome:

> "This event did not become a blind ticket. The platform detected it, gathered
> evidence, proposed the safest next action, verified recovery, scored the run,
> and only escalated if human or ServiceNow ownership was genuinely needed."

## Management Metrics

These are the measures that make value visible during rollout:

| Metric | What it proves |
|---|---|
| ServiceNow deflection rate | Alerts resolved or closed by workflow before incident creation. |
| Escalation quality | Incidents that do reach ServiceNow include evidence, probable cause, owner, and proposed action. |
| MTTA reduction | Time from alert to evidence-backed diagnosis. |
| MTTR reduction | Time from alert to verified recovery. |
| Manual triage minutes avoided | Human time saved per incident class. |
| Eval score out of 10 | Whether agent output is good enough to trust. |
| HITL approval count and latency | Whether safety gates are working without becoming bottlenecks. |
| Repeat issue regression coverage | Production misses converted into lower-env tests. |
| Policy and tool-denial events | Proof that agents are constrained by permissions, not hope. |

## How We Measure Deflection

Do not create and auto-close a normal ServiceNow incident for every successful
deflection. That would pollute the system we are trying to reduce.

Every kagent run should end with a classified outcome. ServiceNow should only
receive the subset that needs human ownership, audit escalation, or a formal ITSM
record.

Recommended event accounting:

```text
Alert received
  -> kagent workflow run created
  -> outcome classified
  -> metrics emitted to Grafana/Mimir
  -> ServiceNow incident created only when escalation is required
```

Core outcome labels:

```text
outcome="auto_resolved"
outcome="gitops_mr_created"
outcome="human_approved_remediation"
outcome="snow_escalated"
outcome="no_action_observe_only"
outcome="false_positive"
outcome="blocked_insufficient_confidence"
```

Deflection rate:

```text
deflection_rate =
  automation_closed_without_snow_total
  /
  total_actionable_alerts_total
```

If a ServiceNow incident is created, tag it so management can see that it came
through the agentic path:

```text
source = kagent
automation_outcome = escalated_after_triage
kagent_run_id = {{ARGO_WORKFLOW_ID}}
kagent_eval_score = {{SCORE_OUT_OF_10}}
evidence_attached = true
```

If the organisation requires ServiceNow as the reporting system of record for
all automation, use a lower-noise record type, task subtype, or automation
evidence table rather than normal incidents.

## MTTA And MTTR Trend Model

Measure MTTA and MTTR from workflow timestamps, not from anecdotes.

```text
MTTA = first_diagnosis_at - alert_received_at
MTTR = recovery_verified_at - alert_received_at
```

Each run should emit these timestamps:

```text
alert_received_at
workflow_started_at
evidence_collection_started_at
first_diagnosis_at
human_notified_at
snow_created_at
recovery_verified_at
workflow_completed_at
```

For ServiceNow escalations, also capture:

```text
snow_created_at
snow_resolved_at
snow_priority
snow_assignment_group
```

This gives two useful views:

- platform MTTA / MTTR: how quickly the agentic loop diagnosed and verified.
- ServiceNow MTTA / MTTR: how long escalated records took after ITSM handoff.

The dashboard should show weekly or monthly trend lines for:

- actionable alerts.
- deflected alerts.
- ServiceNow escalations.
- deflection rate percentage.
- median and P90 MTTA.
- median and P90 MTTR.
- average eval score out of 10.
- HITL approval latency.
- blocked automation reasons.
- repeat incident count by service or failure mode.

Starter metric contract:

```prometheus
kagent_alert_received_total{cluster,service,severity,source,env_tier}
kagent_workflow_completed_total{cluster,service,outcome,env_tier}
kagent_snow_incident_created_total{cluster,service,priority,env_tier}
kagent_snow_incident_deflected_total{cluster,service,reason,env_tier}
kagent_mtta_seconds{cluster,service,outcome,env_tier}
kagent_mttr_seconds{cluster,service,outcome,env_tier}
kagent_eval_score{cluster,service,run_id,env_tier}
kagent_hitl_approval_seconds{cluster,service,approval_type,env_tier}
```

The stakeholder graph should make the direction obvious:

```text
ServiceNow escalations down
Deflection rate up
MTTA down
MTTR down
Eval score stable or improving
```

## Plug-And-Play Harness

The value is broader than triage. The same harness can plug in different
specialists and tool surfaces:

- **Observability:** Grafana MCP, Prometheus/Mimir, Loki, dashboards, alert
  context, service health summaries.
- **Incident handling:** Alertmanager, Confluent, Argo Events, Argo Workflows,
  Teams, GitLab, ServiceNow escalation.
- **GitOps remediation:** scoped GitLab MRs, Flux/Argo CD reconciliation,
  reviewable platform changes instead of ad hoc cluster mutation.
- **Security and compliance:** vulnerability signals, policy exceptions,
  Kyverno/PolicyReport evidence, advisory compliance checks, hardened image
  posture, tool-grant reviews.
- **Reliability engineering:** lower-env chaos tests, regression suites,
  recovery scoring, review-manager routing for runs below target score.
- **Knowledge loop:** runbook lookup, doc2vec/querydoc citations, curated memory,
  KB update MRs after incidents.
- **BYO agents:** teams can bring read-only triage agents or bounded remediation
  agents under ToolCatalogEntry, ToolGrant, policy, and eval controls.

This makes the platform a reusable agentic control plane, not a one-off bot.

## Rollout Story For AKS

1. **Development clusters:** prove the loop with controlled failures and no
   automatic production writes.
2. **Non-production shared AKS:** enable dashboard, eval, HITL, GitOps MR, and
   ServiceNow-escalation evidence paths.
3. **Production AKS read-side:** allow alert enrichment, Grafana evidence,
   runbook lookup, owner routing, and high-quality escalation packages.
4. **Production guarded action:** only after enough scored lower-env evidence,
   allow bounded remediation proposals behind HITL and GitOps review.

## The One-Line Ask

Fund this as a measurable ServiceNow-reduction and platform-quality programme:
start with alert enrichment and incident deflection in dev/non-prod, prove value
with Grafana dashboards and eval scores, then expand the same harness into
security, compliance, reliability testing, and controlled GitOps remediation.
