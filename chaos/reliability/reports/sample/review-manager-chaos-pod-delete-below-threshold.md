# Review Manager Finding

**Suite:** `chaos-demo-sandbox`
**Test:** `chaos-demo-pod-delete`
**Score:** `0.575 / 1.0`
**Benchmark:** `0.8 / 1.0`
**Classification:** `OBSERVABILITY_GAP`

## Finding

The sample lower-env pod-delete run deliberately falls below the benchmark
because the Grafana evidence specialist did not complete, recovery verification
did not pass, and the GitLab ticket status was not updated. This proves the
review-manager routing condition without needing to run another live chaos
experiment.

## Validity

| Question | Answer |
|---|---|
| Was the test valid? | `yes` |
| Was the system response valid? | `no` |
| Did HITL run before mutation? | `yes` |
| Was recovery verified? | `no` |
| Were outputs sanitized? | `yes` |

## Proposed Work

- Backlog item: `Wire live Grafana evidence and recovery checks before closing chaos-test reports.`
- GitLab issue/MR: `{{GITLAB_REF}}`
- Memory proposal: `Record that pod-delete tests are not complete unless recovery evidence and ticket status are both present.`
- KB/runbook update: `Add a troubleshooting section for missing chaos-test lifecycle evidence.`

## Required Markers

```text
REVIEW_MANAGER_TRIGGERED: yes
REVIEW_CLASSIFICATION: OBSERVABILITY_GAP
KB_UPDATE_PROPOSED: yes
MEMORY_PROPOSAL_CREATED: yes
OUTPUT_SANITIZED: yes
```
