# ASTHERI/SRE Walkthrough Rehearsal

Date: 2026-06-04

Purpose: record a local rehearsal of the ASTHERI/SRE first-time walkthrough as
if the operator had just arrived at the platform and wanted to onboard an app,
inject chaos, prove remediation, and collect dashboards/reports/GitLab/eval
evidence.

No cluster was mutated during this rehearsal.

## Rehearsal Path

Followed:

1. `WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md`
2. `demos/sre-first-contact/README.md`
3. `demos/sre-first-contact/scripts/verify-demo.sh`
4. `demos/sre-first-contact/chaos/checkout-api-pod-delete.chaostest.yaml`
5. `demos/sre-first-contact/eval/checkout-api-demo-evidence-contract.yaml`

## Commands Run

```bash
bash demos/sre-first-contact/scripts/verify-demo.sh
```

Result:

```text
SRE_FIRST_CONTACT_YAML_OK: yes
RELIABILITY_CONFIG_VALID: yes checked=1
OUTPUT_SANITIZED: yes
FORBIDDEN_TOOLS_ABSENT: yes
TOOLGRANT_COVERS_AGENT_TOOLS: yes
EVIDENCE_CONTRACT_READY: yes
SRE_FIRST_CONTACT_VERIFY: passed
```

```bash
python3 chaos/reliability/scripts/validate-reliability-configs.py \
  demos/sre-first-contact/chaos/checkout-api-pod-delete.chaostest.yaml
```

Result:

```text
RELIABILITY_CONFIG_VALID: yes checked=1
OUTPUT_SANITIZED: yes
```

## Discrepancies Found And Fixed

| Finding | Fix |
|---|---|
| The docs allowed a valid `no mutation required` remediation outcome, but the evidence contract implied `GITOPS_PROPOSAL_CREATED: yes` was always required. | Changed the marker to `yes_or_not_required` in the eval contract and `yes|not_required` in the user-facing docs. |
| Memory tooling names were inconsistent between Agent manifests and ToolGrants. | Aligned memory read tools to `search_nodes`, `open_nodes`, `read_graph`, and kept writes on `memory_add_observation_curated`. |
| The first verifier only checked for forbidden tool names; it did not prove the ToolGrant covered every Agent tool. | Added `TOOLGRANT_COVERS_AGENT_TOOLS: yes` validation. |
| The remediation Agent had memory read tools that were not granted. | Added `search_nodes`, `open_nodes`, and `read_graph` to the remediation ToolGrant. |
| The front-door agent could submit workflows, which could look like direct mutation to a new reader. | Clarified that it may submit only approved non-production workflow templates and that workflow service accounts hold resource-changing permissions. |

## Remaining Live Work-Lab Proof

The rehearsal proves the package is internally consistent. It does not prove
live work-lab integrations. The live work-lab run still needs:

1. real kagent/Argo/agentgateway runtime inventory
2. real model call through the approved path
3. real Grafana MCP metric/log/dashboard evidence
4. real GitLab sandbox MR or explicit scoped-auth blocker
5. real querydoc cited hit or `NO_RELEVANT_DOCS`
6. real memory recall and curator-mediated learning
7. real HITL approval identity
8. real lower-env chaos result and recovery proof
9. lifecycle eval output from the live run
10. final report/dashboard/GitLab evidence bundle

## Current Readiness

The ASTHERI/SRE first-time walkthrough is ready for a work-side dry run. A new
operator can start with `WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md`, run
the verifier, adapt the app profile, then execute the work-lab proof path.

