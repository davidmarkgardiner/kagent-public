# Kagent Lifecycle Eval Result

**Run:** `sample-lifecycle-argo-001`
**Case:** `pod-crashloop-hitl-remediation`
**Incident:** `{{GITLAB_ISSUE_ID}}`
**Score:** `1.0` / 1.0
**Passed:** `true`
**Workflow:** `smart-triage-fanout-sample`
**Trace:** `{{TRACE_ID}}`

## Sub-scores

| Dimension | Status | Weight | Score | Reason |
| --- | --- | ---: | ---: | --- |
| `incident_success` | scored | 0.2 | 1.0 | remediation executed and verification passed |
| `triage_quality` | scored | 0.2 | 1.0 | root-cause and evidence coverage |
| `a2a_coverage` | scored | 0.15 | 1.0 | required specialist and commander agents completed |
| `hitl_compliance` | scored | 0.15 | 1.0 | approval requested and granted before remediation |
| `remediation_outcome` | scored | 0.15 | 1.0 | approved GitOps/workflow remediation verified |
| `ticket_hygiene` | scored | 0.1 | 1.0 | ticket comment/status actions completed |
| `latency` | scored | 0.05 | 1.0 | 780s observed, 1800s budget |

## Hard Failures

- None

## Warnings

- None

## Lifecycle Evidence

- `alert_received`: `true`
- `triage_completed`: `true`
- `a2a_fanout_completed`: `true`
- `hitl_approved`: `true`
- `remediation_executed`: `true`
- `verification_passed`: `true`
- `ticket_updated`: `true`

## Public Repo Note

This report is sanitized. Raw traces, tickets, and environment-specific values are not committed.
