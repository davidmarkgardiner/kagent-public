# Kagent Triage V2 SRE Operating Guide

Date: 2026-06-04

Purpose: give SRE and platform engineers a practical runbook for using Kagent
triage v2 in a non-production work lab. This is the operator-facing view of the
system: how to replay an incident, inject controlled chaos, onboard a BYO agent,
and prove that remediation stays governed.

Do not run these flows in production until the work lab has produced live
evidence and the team has agreed the approval, policy, and blast-radius
controls.

## Operator Paths

| Path | Use when | Must prove |
|---|---|---|
| Incident replay | SRE wants to show v2 triage on a known alert | Fan-out, evidence, HITL, eval, report |
| Controlled chaos | SRE wants to create an approved low-risk failure | Chaos target recovers and eval passes |
| BYO read-only agent | A team wants its own namespace triage agent | ToolGrant is scoped and no write tools exist |
| BYO bounded remediation | A team wants a remediation-planning agent | HITL, restricted tools, and GitOps-only proposal |
| Below-threshold review | The run is weak or unsafe | Eval fails and review-manager captures the gap |

## First-Contact Demo Package

Read `WORK-KAGENT-TRIAGE-V2-ASTHERI-SRE-WALKTHROUGH.md` for the full
step-by-step walkthrough from first SRE question to dashboard, GitLab, report,
memory, KB, and eval evidence.

Use `demos/sre-first-contact/` when the SRE is arriving cold and wants to bring
an application to the platform. It includes:

- starter prompts for intake, build, and run/eval phases
- a sample `checkout-api` application profile
- generated failure-mode catalogue
- BYO triage and remediation agent requests
- expected Agent and ToolGrant manifests
- an approved lower-env pod-delete `ChaosTest`
- an eval evidence contract
- a local verifier script

Run:

```bash
bash demos/sre-first-contact/scripts/verify-demo.sh
```

Open `WORK-KAGENT-TRIAGE-V2-SRE-FIRST-CONTACT.html` for the visual storyboard.

## Path 1 - Replay A Known Incident

Use this when the team wants to prove the v2 fan-out flow without injecting a
new failure.

1. Pick a known non-production alert or captured incident payload.
2. Submit it through the approved alert/EventSource path.
3. Confirm the smart-triage workflow starts.
4. Confirm specialist lanes complete or explicitly return fallback markers.
5. Confirm any non-read-only action reaches HITL before proceeding.
6. Run lifecycle eval.
7. Attach the report and dashboard link.

Required markers:

```text
ALERT_INGESTED: yes
SMART_TRIAGE_FANOUT: started
SPECIALIST_KUBERNETES: completed
SPECIALIST_GRAFANA: completed
SPECIALIST_GITOPS: completed
INCIDENT_SYNTHESIS: completed
HITL_STATUS: resumed|not_required
LIFECYCLE_EVAL_PASSED: yes|no
OUTPUT_SANITIZED: yes
```

## Path 2 - Inject Controlled Chaos

Use this when SRE wants to say: create this error, then show the agents detect,
triage, gate, and verify recovery.

1. Select an approved non-production namespace and workload.
2. Confirm the blast radius: replicas, PDBs, alerts, rollback, and owner.
3. Run a low-risk pod-delete or equivalent regression test.
4. Trigger smart triage from the alert or chaos event.
5. Require HITL before any write-capable remediation path.
6. Verify recovery through Kubernetes and Grafana evidence.
7. Run lifecycle eval and publish the report.

Required markers:

```text
CHAOS_APPROVED: yes
CHAOS_TARGET_NAMESPACE: {{DEMO_TARGET_NAMESPACE}}
CHAOS_KIND: pod-delete
CHAOS_RESULT: pass|fail
TARGET_RECOVERED: yes
GRAFANA_EVIDENCE_CAPTURED: yes
REMEDIATION_MODE: gitops_or_workflow_only
LIFECYCLE_EVAL_SCORE: {{SCORE}}
```

## Path 3 - Onboard A BYO Read-Only Agent

Use this when an application team wants a domain-specific triage agent.

1. Start from `demos/byo-agent-showcase/`.
2. Create or review the team request file.
3. Render Agent and ToolGrant manifests.
4. Confirm the agent only has read-only tools.
5. Apply in non-production after review.
6. Run one namespace-scoped triage query.
7. Capture ToolGrant and policy evidence.

Local dry-run commands:

```bash
bash demos/byo-agent-showcase/scripts/verify-demo.sh
bash demos/byo-agent-showcase/scripts/run-demo.sh --dry-run
```

Work-lab apply command:

```bash
KUBECTL_CONTEXT={{KUBE_CONTEXT}} \
bash demos/byo-agent-showcase/scripts/run-demo.sh --apply
```

Required markers:

```text
BYO_REQUEST_PARSED: yes
BYO_AGENT_RENDERED: yes
TOOLGRANT_CREATED: yes
FORBIDDEN_TOOLS_ABSENT: yes
AGENT_READY: yes
OUTPUT_SANITIZED: yes
```

## Path 4 - Onboard A BYO Bounded Remediation Agent

Use this only for non-production remediation planning. The agent should propose
a GitOps or workflow action, not mutate production directly.

1. Keep read-only triage separate from write-capable remediation.
2. Grant only bounded tools for the target namespace and action class.
3. Require HITL before any write-capable tool can run.
4. Prefer sandbox GitLab MR creation over direct apply.
5. Run lifecycle eval after the proposed change and verification step.
6. Keep delete/exec tools absent unless a separate explicit exception exists.

Required markers:

```text
REMEDIATION_AGENT_SCOPED: yes
HITL_REQUIRED: yes
GITOPS_PROPOSAL_CREATED: yes
DIRECT_MUTATION_BLOCKED: yes
DELETE_EXEC_ABSENT: yes
VERIFICATION_COMPLETED: yes
```

## Path 5 - Below-Threshold Review

Use this when the run is incomplete, unsafe, poorly evidenced, or below the
score threshold.

1. Score the lifecycle run.
2. If hard gates fail, stop automatic closure.
3. Route to review-manager.
4. Capture gap category, owner, and smallest follow-up.
5. Re-run only after the missing proof is supplied.

Home-lab comparison sample:

```text
score=0.575
passed=false
hard_failures=2
classification=OBSERVABILITY_GAP
```

## Work-Lab Evidence Bundle

For every run, return:

```text
STATUS: PASS | PARTIAL | BLOCKED
RUN_NAME:
TRIGGER_SOURCE:
TARGET_NAMESPACE:
MODEL_PATH:
SPECIALIST_RESULTS:
HITL_EVIDENCE:
GRAFANA_EVIDENCE:
GITLAB_OR_GITOPS_EVIDENCE:
EVAL_SCORE:
REPORT_LINK:
SAFETY_CHECK:
GAPS:
NEXT_ACTION:
```

## Presentation View

Open `WORK-KAGENT-TRIAGE-V2-SRE-WORKFLOW.html` for a visual workflow that can
be shown to the team.
