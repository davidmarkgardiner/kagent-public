# Reliability Chaos Test Report

**Suite:** `{{SUITE_NAME}}`
**Test:** `{{TEST_NAME}}`
**Owner:** `{{OWNER}}`
**Environment:** `{{ENVIRONMENT}}`
**Target:** `{{CLUSTER}} / {{NAMESPACE}} / {{WORKLOAD}}`
**Failure mode:** `{{FAILURE_MODE}}`

## Result

| Field | Value |
|---|---|
| Injection result | `{{INJECTION_RESULT}}` |
| Detection result | `{{DETECTION_RESULT}}` |
| Triage result | `{{TRIAGE_RESULT}}` |
| Recovery verification | `{{RECOVERY_VERIFICATION}}` |
| Score | `{{SCORE}} / 10` |
| Threshold | `8 / 10` |
| Review manager | `{{REVIEW_MANAGER_STATUS}}` |

## Evidence

- Grafana dashboard: `{{GRAFANA_DASHBOARD_URL}}`
- GitLab MR: `{{GITLAB_MR_URL}}`
- GitLab issue: `{{GITLAB_ISSUE_URL}}`
- Argo workflow: `{{ARGO_WORKFLOW_URL}}`
- Litmus ChaosResult: `{{CHAOS_RESULT_REF}}`
- Memory proposal: `{{MEMORY_PROPOSAL_REF}}`
- KB/runbook proposal: `{{KB_UPDATE_MR_URL}}`

## Proof Markers

```text
HITL_STATUS: {{HITL_STATUS}}
GITLAB_BRANCH: {{GITLAB_BRANCH}}
GITLAB_MR: {{GITLAB_MR_URL}}
CHAOS_INJECTION_STARTED: {{yes|no}}
CHAOS_INJECTION_COMPLETED: {{yes|no}}
SMART_TRIAGE_FANOUT: {{started|not_started}}
EVAL_SCORE: {{SCORE}}
SCORE_THRESHOLD: 8
REVIEW_MANAGER_TRIGGERED: {{yes|no}}
ALLOY_TELEMETRY_CAPTURED: {{yes|no}}
TEST_REPORT_CREATED: yes
KB_UPDATE_PROPOSED: {{yes|no}}
MEMORY_PROPOSAL_CREATED: {{yes|no}}
OUTPUT_SANITIZED: yes
```

## Decision

`{{PASS|FAIL|NEEDS_REVIEW}}`

## Follow-up

- `{{FOLLOW_UP_1}}`
- `{{FOLLOW_UP_2}}`
