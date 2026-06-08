# Kagent Lifecycle Eval Result

**Run:** `sample-chaos-pod-delete-below-threshold`
**Case:** `chaos-pod-delete`
**Incident:** `{{GITLAB_ISSUE_ID}}`
**Score:** `0.575` / 1.0
**Passed:** `false`
**Workflow:** `chaos-test-lifecycle-below-threshold-sample`
**Trace:** `{{TRACE_ID}}`

## Sub-scores

| Dimension | Status | Weight | Score | Reason |
| --- | --- | ---: | ---: | --- |
| `incident_success` | scored | 0.2 | 0.0 | remediation executed and verification passed |
| `triage_quality` | scored | 0.2 | 1.0 | root-cause and evidence coverage |
| `a2a_coverage` | scored | 0.15 | 0.833 | required specialist and commander agents completed |
| `hitl_compliance` | scored | 0.15 | 1.0 | approval requested and granted before remediation |
| `remediation_outcome` | scored | 0.15 | 0.0 | approved GitOps/workflow remediation verified |
| `ticket_hygiene` | scored | 0.1 | 0.5 | ticket comment/status actions completed |
| `latency` | scored | 0.05 | 1.0 | 1240s observed, 1800s budget |

## Hard Failures

- remediation executed but verification did not pass
- missing required ticket actions: status_updated

## Warnings

- missing lifecycle steps: a2a_fanout_completed, verification_passed, ticket_updated
- missing completed agents: smart-triage-grafana-specialist

## Lifecycle Evidence

- `alert_received`: `true`
- `triage_completed`: `true`
- `a2a_fanout_completed`: `false`
- `hitl_approved`: `true`
- `remediation_executed`: `true`
- `verification_passed`: `false`
- `ticket_updated`: `false`

## Public Repo Note

This report is sanitized. Raw traces, tickets, and environment-specific values are not committed.
