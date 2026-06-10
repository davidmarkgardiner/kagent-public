# Fleet Selector Skill

Use this skill when a reliability or chaos workflow needs to turn a fleet-style
request into an auditable lower-env cluster set.

## Inputs

- requested environment tier: `dev`, `test`, or `staging`
- requested cluster count
- opt-in cluster labels
- blackout window policy
- quiet-period policy
- optional random seed or selection reason

## Rules

- Reject production for v1.
- Reject a requested count above `{{MAX_SELECTED_CLUSTERS}}`.
- Select only clusters with `reliability.platform/chaos-optin="true"`.
- Exclude clusters in blackout, incident, release, or quiet-period windows.
- Record the candidate pool, exclusions, random seed or deterministic reason,
  final cluster list, and approver.
- Return a dry-run plan unless the caller supplies an approved GitOps/HITL
  reference.

## Output Contract

```text
CLUSTER_SELECTION_RECORDED: yes
SELECTION_MODE: {{explicit|random|label-selector}}
CANDIDATE_POOL: {{COUNT}}
EXCLUDED_CLUSTERS: {{COUNT}}
SELECTED_CLUSTERS: {{PLACEHOLDER_LIST}}
SELECTION_REASON: {{REASON_OR_SEED}}
OUTPUT_SANITIZED: yes
```

If selection is unsafe or underspecified, return:

```text
CLUSTER_SELECTION_RECORDED: no
STOP_REASON: {{REASON}}
OUTPUT_SANITIZED: yes
```
