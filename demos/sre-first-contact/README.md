# SRE First-Contact Demo

Purpose: show the end-to-end Kagent triage v2 experience from the point of
view of an SRE arriving at the platform for the first time.

The demo answers this operator request:

```text
I want to bring checkout-api onto this platform.
Work out what might go wrong, build the right read-only and remediation agents,
wire them to Grafana/GitLab/KB/memory, inject one safe chaos failure, show the
agent path to remediation, and prove the run with lifecycle evaluation.
```

This is dry-run first. It packages the prompt flow, application profile,
failure-mode catalogue, BYO agent requests, chaos test, expected proof markers,
and verification script. It does not apply resources unless a work-lab operator
copies the generated contracts into an approved non-production environment.

## Layout

```text
demos/sre-first-contact/
|-- README.md
|-- prompts/
|   |-- 01-sre-intake.md
|   |-- 02-build-agents-and-tests.md
|   `-- 03-run-demo-and-evaluate.md
|-- profiles/
|   `-- checkout-api.application-profile.yaml
|-- failure-modes/
|   `-- checkout-api.failure-modes.yaml
|-- requests/
|   |-- checkout-triage-agent-request.yaml
|   `-- checkout-remediation-agent-request.yaml
|-- expected/
|   |-- sre-first-contact-agent.yaml
|   |-- checkout-triage-agent.yaml
|   |-- checkout-remediation-agent.yaml
|   `-- checkout-toolgrants.yaml
|-- chaos/
|   `-- checkout-api-pod-delete.chaostest.yaml
|-- eval/
|   `-- checkout-api-demo-evidence-contract.yaml
`-- scripts/
    `-- verify-demo.sh
```

## Demo Narrative

1. SRE describes the application and asks the platform to onboard it.
2. Kagent uses the app profile, knowledge base, memory, Grafana, and GitLab
   context to generate likely failure modes.
3. Platform renders a read-only triage agent and a bounded remediation-planning
   agent with explicit ToolGrants.
4. SRE uses the front-door `sre-first-contact-agent` to coordinate prompts,
   workflow submission, A2A fan-out, and evidence collection.
5. SRE approves one safe lower-env chaos scenario.
6. Chaos injects a pod-delete style failure.
7. Smart triage fans out to specialists and gathers Grafana, GitOps, KB,
   policy, and Kubernetes evidence.
8. Remediation stays behind HITL and proposes GitOps/workflow action only.
9. Lifecycle eval scores the run and routes weak evidence to review-manager.
10. Curated learning is written to memory and KB update proposals go through MR.

## Local Verification

```bash
bash demos/sre-first-contact/scripts/verify-demo.sh
```

Expected output:

```text
SRE_FIRST_CONTACT_YAML_OK: yes
RELIABILITY_CONFIG_VALID: yes checked=1
FORBIDDEN_TOOLS_ABSENT: yes
TOOLGRANT_COVERS_AGENT_TOOLS: yes
EVIDENCE_CONTRACT_READY: yes
SRE_FIRST_CONTACT_VERIFY: passed
```

## Work-Lab Acceptance Test

A work-side agent or engineer should be able to run this conversation:

```text
I am an SRE bringing checkout-api onto Kagent triage v2.
Use the application profile, identify the likely failure modes, create the
read-only triage agent and bounded remediation agent, inject the approved
pod-delete scenario in lower env, show the Grafana/GitLab/KB/memory evidence,
and return the lifecycle eval result.
```

Minimum live evidence:

```text
APP_PROFILE_PARSED: yes
FAILURE_MODES_GENERATED: yes
BYO_TRIAGE_AGENT_READY: yes
BYO_REMEDIATION_AGENT_READY: yes
SRE_FRONT_DOOR_AGENT_READY: yes
TOOLGRANT_POLICY_VERIFIED: yes
CHAOS_APPROVED: yes
CHAOS_RESULT_VERDICT: Pass
SMART_TRIAGE_FANOUT: completed
GRAFANA_EVIDENCE_CAPTURED: yes
HITL_STATUS: resumed
GITOPS_PROPOSAL_CREATED: yes|not_required
RECOVERY_VERIFIED: yes
LIFECYCLE_EVAL_PASSED: yes
MEMORY_LEARNING_CAPTURED: curator-only
KB_UPDATE_PATH: hitl-gated-mr
OUTPUT_SANITIZED: yes
```
