# Agent Evaluation Rollout and Operating Model

## Purpose

This document explains how to introduce kagent evaluation safely across
non-prod and prod while using both offline and online evaluation modes.

The target outcome is confidence that agents:

- diagnose the right problem
- call the right supporting agents and tools
- respect namespace and permission boundaries
- wait for HITL approval before remediation
- verify recovery before claiming success
- update the incident ticket
- receive a measurable score with dashboards and alerts

## Rollout Principles

1. Start with deterministic checks.
2. Separate read-only triage from write-capable remediation.
3. Treat HITL, verification, and ticket updates as hard gates.
4. Do not block production workflows until the evidence contract is stable.
5. Keep raw evidence sanitized and short-lived.
6. Use offline replay to improve prompts without touching live operations.

## Stage 0: Local Design And Golden Cases

Mode:

```text
offline only
```

Run:

```bash
python3 observability/agent-evals/scripts/score-agent-run.py ...
python3 observability/agent-evals/scripts/score-lifecycle-run.py ...
```

Exit criteria:

- Golden cases exist for the first operational scenarios.
- Scorer catches wrong namespace, forbidden tool, missing verification, and
  missing ticket update.
- Reports are public-safe.
- Score thresholds are agreed.

## Stage 1: CI / PR Promotion Gate

Mode:

```text
offline
```

Scope:

- prompt changes
- agent/tool catalog changes
- lifecycle case changes
- scorer changes
- Argo workflow changes

Gate:

```text
changed agent or workflow must pass matching offline cases
```

Recommended checks:

```bash
kubectl kustomize observability/agent-evals
kubectl create --dry-run=client -f a2a/smart-triage-fanout-demo/workflow.yaml
python3 -m py_compile observability/agent-evals/scripts/*.py
python3 observability/agent-evals/scripts/run-agent-evals.py ...
```

Exit criteria:

- CI can fail regressions before deployment.
- Results are stored as CI artifacts or summarized in PR output.

## Stage 2: Non-Prod Online Audit

Mode:

```text
online audit
```

Scope:

- dev/staging incident simulations
- chaos tests
- demo alerts
- A2A fan-out workflows
- HITL remediation rehearsals

Behavior:

- Lifecycle evaluator runs at the end of the Argo workflow.
- Low score fails the demo/staging workflow.
- No production ticket closure is affected.

Exit criteria:

- Online eval task runs reliably with the public-image/ConfigMap runtime.
- Evidence markers come from real workflow steps, not hand-written samples.
- Dashboard shows score, pass/fail, and hard failures.
- Alerts fire on hard failures.

## Stage 3: Production Online Audit-Only

Mode:

```text
online audit, not gating
```

Scope:

- production read-only triage
- production recommendations
- optionally all HITL workflows

Behavior:

- Eval runs after the workflow.
- Eval result is attached or linked to the ticket.
- Low score creates an audit signal, but does not block workflow completion.
- Hard failures page or notify the owner depending on severity.

Exit criteria:

- False-positive hard failures are rare and understood.
- Evidence collection does not leak secrets or internal-only details into
  long-lived artifacts.
- Dashboard has enough history to identify agent drift.

## Stage 4: Production Gating For High-Risk Paths

Mode:

```text
online gate
```

Scope:

- write-capable remediation
- HITL-approved actions
- workflows that update or close tickets
- any workflow that can merge/apply/execute changes

Behavior:

- Eval runs before ticket closure.
- Eval failure keeps the ticket open.
- Hard failures block closure and attach the failure summary.
- Remediation cannot be marked successful without verification.

Exit criteria:

- Ticket-close gate is reliable.
- On-call team understands eval failure handling.
- Rollback path exists for evaluator infrastructure issues.

## Stage 5: Sampling And Continuous Improvement

Mode:

```text
online sampled audit + offline replay
```

Recommended steady-state policy:

| Workflow type | Audit rate |
| --- | ---: |
| write-capable remediation | 100 percent |
| HITL-approved action | 100 percent |
| ticket-closing workflow | 100 percent |
| read-only production triage | 25 percent to start |
| read-only non-prod triage | 100 percent until stable |

Offline replay should continue for:

- incidents with low scores
- post-incident review examples
- prompt/model/provider changes
- new golden cases from production learning

## Ownership Model

| Area | Owner |
| --- | --- |
| Golden cases | Platform SRE plus service owner for domain-specific cases. |
| Scorer code | Platform automation owner. |
| Agent prompts/tools | Agent owner. |
| Argo runtime hook | Workflow/platform owner. |
| Dashboard and alerts | Observability owner. |
| Ticket-close policy | Incident process owner. |

## Minimum Metrics

Publish:

```text
agent_eval_score
agent_eval_passed
agent_eval_hard_failures
agent_lifecycle_eval_score
agent_lifecycle_eval_passed
agent_lifecycle_eval_hard_failures
agent_lifecycle_eval_subscore
```

Fleet-level dashboards can add:

```text
kagent_agent_info
kagent_agent_ready
kagent_workflow_active
kagent_workflow_total
kagent_incident_funnel_total
```

## Alerting

Start with:

- lifecycle score below threshold
- lifecycle hard failure count above zero
- safety/permission failure
- score average dipping over time
- evaluator infrastructure error

Do not page on every low-score read-only triage result at first. Use ticket
comments or team notifications until thresholds are tuned.

## Evidence Retention

Recommended:

| Evidence | Retention |
| --- | --- |
| Raw traces/log excerpts | Short-lived, restricted access. |
| Sanitized lifecycle run JSON | Medium retention for audit/replay. |
| Eval result JSON | Long-lived. |
| Markdown summary | Ticket attachment/comment or artifact. |
| Prometheus metrics | Normal metrics retention. |

Public repos must contain placeholders only.

## Rollback / Break Glass

If the evaluator is unavailable:

- keep remediation controls and HITL in place
- do not bypass verification
- mark evaluation as inconclusive
- keep ticket open for manual closure or require explicit human override
- file an evaluator infrastructure incident

For production, keep a documented override path, but require the override to
record:

- approver
- reason
- affected workflow
- ticket id
- follow-up owner

## Completion Checklist

- [ ] Offline golden cases pass in CI.
- [ ] Argo eval template installed in non-prod.
- [ ] Smart-triage or equivalent workflow calls lifecycle eval.
- [ ] Low-score and hard-failure samples fail as expected.
- [ ] Metrics appear in Grafana.
- [ ] Alerts fire for hard failures.
- [ ] Ticket closure is gated for write-capable remediation.
- [ ] Production starts audit-only before gating.
- [ ] Evidence retention and sanitization rules are documented.
