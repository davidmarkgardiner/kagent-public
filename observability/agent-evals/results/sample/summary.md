# Kagent Agent Eval Score Summary

| Agent | Runs | Avg score | Passed | Hard failures |
| --- | ---: | ---: | ---: | ---: |
| `kube-system-agent` | 1 | 1.0 | 1 | 0 |

## Agent Runs

| Case | Agent | Score | Passed | Hard failures |
| --- | --- | ---: | --- | --- |
| `crashloop-wrong-env-var` | `kube-system-agent` | 1.0 | true | None |

## Lifecycle Runs

| Case | Run | Incident | Workflow | Score | Passed | Hard failures |
| --- | --- | --- | --- | ---: | --- | --- |
| `pod-crashloop-hitl-remediation` | `sample-lifecycle-001` | `{{GITLAB_ISSUE_ID}}` | `smart-triage-fanout-sample` | 1.0 | true | None |
| `pod-crashloop-hitl-remediation` | `sample-lifecycle-argo-001` | `{{GITLAB_ISSUE_ID}}` | `smart-triage-fanout-sample` | 1.0 | true | None |
