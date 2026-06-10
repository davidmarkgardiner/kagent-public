# Review Manager Finding

**Suite:** `{{SUITE_NAME}}`
**Test:** `{{TEST_NAME}}`
**Score:** `{{SCORE}} / 10`
**Benchmark:** `8 / 10`
**Classification:** `{{TEST_DESIGN|PLATFORM_RESPONSE|OBSERVABILITY_GAP|TRIAGE_QUALITY|REMEDIATION_SAFETY|FLAKY_INFRA|MISSING_RUNBOOK|POLICY_VIOLATION}}`

## Finding

{{ROOT_CAUSE_HYPOTHESIS}}

## Validity

| Question | Answer |
|---|---|
| Was the test valid? | `{{yes|no|unclear}}` |
| Was the system response valid? | `{{yes|no|unclear}}` |
| Did HITL run before mutation? | `{{yes|no}}` |
| Was recovery verified? | `{{yes|no}}` |
| Were outputs sanitized? | `{{yes|no}}` |

## Proposed Work

- Backlog item: `{{BACKLOG_ITEM}}`
- GitLab issue/MR: `{{GITLAB_REF}}`
- Memory proposal: `{{MEMORY_PROPOSAL}}`
- KB/runbook update: `{{KB_UPDATE}}`

## Required Markers

```text
REVIEW_MANAGER_TRIGGERED: yes
REVIEW_CLASSIFICATION: {{CLASSIFICATION}}
KB_UPDATE_PROPOSED: {{yes|no}}
MEMORY_PROPOSAL_CREATED: {{yes|no}}
OUTPUT_SANITIZED: yes
```
