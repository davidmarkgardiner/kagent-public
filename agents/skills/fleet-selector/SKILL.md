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

## How to select

Gather the inputs above, build the cluster inventory JSON, then run the
selection script — do not re-derive the rules by hand:

```bash
scripts/select-clusters.sh --tier dev --count 3 --inventory clusters.json \
  --seed 20260719 [--labels k=v,...] [--blackout-file blackout.txt] \
  [--approval <GitOps/HITL ref>]
```

The script enforces the rules (reject production; cap the count at
`{{MAX_SELECTED_CLUSTERS}}`; select only clusters with
`reliability.platform/chaos-optin="true"`; exclude blackout, incident,
release, and quiet-period windows), records pool/exclusions/seed, and prints
the output contract below. Without `--approval` it emits a dry-run plan.

Your judgment is confined to the inputs: which tier and count are appropriate,
which labels apply, whether the request should be refused outright.

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
