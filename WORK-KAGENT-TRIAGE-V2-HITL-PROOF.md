# Work Kagent Triage V2 HITL Proof

Date: 2026-06-04

Purpose: clarify the HITL proof state for Kagent triage system v2. The review
found that some public demo markers synthesize approval status, so this file
separates the real Argo suspend proof from the full Teams/mock-bot callback
chain that still needs a live environment.

## Status

**PARTIAL / ready for live callback proof.**

What is proven locally:

- `a2a/smart-triage-fanout-demo/workflow.yaml` contains a real Argo
  `wait-for-human-review` suspend node before finalization.
- `platform/teams-hitl/mock-bot/test-approval-workflow.yaml` is a standalone
  approval-gate smoke workflow and passes offline Argo lint.
- `platform/teams-hitl/sensor.yaml` contains approved/rejected/expired Sensor
  paths for workflow resume/stop.

What is not proven in this local pass:

- A real Teams bot callback.
- A live Argo Events EventSource receiving the callback.
- A live Sensor resuming/stopping a retained workflow.

## Validation Run

YAML parse:

```text
YAML_OK platform/teams-hitl/mock-bot/test-approval-workflow.yaml
YAML_OK platform/teams-hitl/workflow-approval-template.yaml
YAML_OK platform/teams-hitl/sensor.yaml
YAML_OK a2a/smart-triage-fanout-demo/workflow.yaml
YAML_OK a2a/smart-triage-fanout-demo/workflow-template.yaml
```

Standalone mock workflow lint:

```bash
argo lint --offline --kinds=workflows \
  platform/teams-hitl/mock-bot/test-approval-workflow.yaml
```

Result:

```text
no linting errors found
```

Broader offline lint note:

```text
platform/teams-hitl/workflow-approval-template.yaml is a merge snippet and
references existing triage templates that are intentionally not duplicated.

a2a/smart-triage-fanout-demo/workflow.yaml and workflow-template.yaml reference
the external agent-lifecycle-eval WorkflowTemplate, so offline lint without that
template reports an unresolved reference.
```

## Work-Agent Proof Required

The work-side agent should prove one of these, in this order:

1. Full Teams bot path:
   `request-approval -> wait-for-approval -> Teams decision -> EventSource -> Sensor -> workflow resume/stop`.
2. Mock bot path:
   `platform/teams-hitl/mock-bot/` with the same EventSource/Sensor callback.
3. Curl-only callback path:
   manual POST to the EventSource webhook with `decision=approved` and
   `decision=rejected`.

Required markers:

```text
HITL_REQUIRED: yes
HITL_STATUS: resumed|rejected|expired
HITL_EVIDENCE_SOURCE: teams_bot|mock_bot|curl_callback
APPROVAL_ID: {{APPROVAL_ID}}
APPROVER: {{APPROVER}}
OUTPUT_SANITIZED: yes
```

Do not claim production-grade HITL until the callback source is authenticated,
approval IDs are unique per workflow run, and duplicate callbacks are harmless.
