# BYO Agent Showcase Demo

Purpose: package the BYO-kagent story into one folder that a platform engineer
or work-side agent can lift into a non-production environment. The demo shows
how a team brings a read-only triage agent and a bounded remediation-planning
agent into Kagent triage system v2 without bypassing ToolGrant, Kyverno, Agent
Gateway, A2A, memory, or HITL controls.

This folder is intentionally dry-run first. It does not apply resources unless
the operator explicitly chooses to do so.

## What This Proves

- Teams can submit request files.
- The platform renders explicit `Agent` and `ToolGrant` resources.
- Read-only triage and bounded remediation are separated.
- Tool access is explicit through `toolNames` and `ToolGrant`.
- Memory read/write posture is intentional.
- A2A skills make the agents discoverable.
- Verification can prove no delete/exec tools are present in the demo agents.

## Layout

```text
demos/byo-agent-showcase/
|-- README.md
|-- requests/
|   |-- payments-triage-request.yaml
|   `-- payments-remediation-request.yaml
|-- expected/
|   |-- kustomization.yaml
|   |-- namespace.yaml
|   |-- payments-triage-agent.yaml
|   |-- payments-remediation-agent.yaml
|   |-- payments-toolgrants.yaml
|   `-- payments-memory-grant.yaml
`-- scripts/
    |-- run-demo.sh
    `-- verify-demo.sh
```

## Run Locally

```bash
bash demos/byo-agent-showcase/scripts/verify-demo.sh
bash demos/byo-agent-showcase/scripts/run-demo.sh --dry-run
```

`run-demo.sh --dry-run` renders the expected Kustomize tree and prints the next
commands. To apply in an approved non-production cluster:

```bash
KUBECTL_CONTEXT={{KUBE_CONTEXT}} \
bash demos/byo-agent-showcase/scripts/run-demo.sh --apply
```

## Work-Lab Proof

The work-side agent should capture:

```text
BYO_REQUEST_PARSED: yes
BYO_AGENT_RENDERED: yes
TOOLGRANT_CREATED: yes
MODELCONFIG_GATEWAY_APPROVED: yes
POLICY_DENIAL_PROVED: yes
A2A_SKILL_DISCOVERED: yes
MEMORY_POSTURE_VERIFIED: yes
OUTPUT_SANITIZED: yes
```

## Relationship To Existing Docs

Read this with:

- `infra/byo-kagent/README.md`
- `infra/byo-kagent/SHOWCASE-DEMO.md`
- `docs/agentgateway-mcp-tool-auth/TOOL-AUTH-DISCOVERY.md`
- `WORK-KAGENT-TRIAGE-V2-WORK-AGENT-CHECKLIST.md`
