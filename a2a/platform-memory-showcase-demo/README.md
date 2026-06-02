# Platform Memory Showcase Demo

This demo shows the platform-memory pattern in action:

1. Seed a known incident into shared `memory-mcp`.
2. Ask a separate triage agent whether it has seen the symptom before.
3. Persist the A2A `contextId` through an Argo Workflow suspend gate.
4. Resume the workflow and call the triage agent again with the same context.
5. Prove the memory lookup, A2A thread continuity, and HITL handoff are
   technically buildable with kagent, Argo Workflows, and MCP tools.

The scenario is intentionally public-safe and synthetic. It does not change the
cluster. The remediation is a recommendation string only.

## What It Proves

| Capability | Proof |
|---|---|
| Shared episodic memory | `demo-memory-seeder-agent` writes a known incident through `memory-mcp`. |
| Cross-agent recall | `demo-memory-triage-agent` searches `memory-mcp` and reports `MEMORY_LOOKUP: hit`. |
| A2A continuity | The workflow stores the triage A2A `contextId` and reuses it after suspend/resume. |
| HITL compatibility | The workflow pauses at an Argo suspend node before the final triage call. |
| Copy/replace path | Agents, workflow, and script use placeholders and synthetic resources only. |

## Prerequisites

- kagent in the `kagent` namespace.
- Argo Workflows in the `argo` namespace.
- `RemoteMCPServer/memory-mcp` in the `kagent` namespace.
- A working chat `ModelConfig` for the demo agents.
- Local `kubectl`, `argo`, and `jq`.

The demo defaults to `MODEL_CONFIG=default-model-config`.

## Run

```bash
a2a/platform-memory-showcase-demo/scripts/run-demo.sh
```

To target a specific context or model config:

```bash
KUBE_CONTEXT={{KUBE_CONTEXT}} MODEL_CONFIG={{MODEL_CONFIG}} \
  a2a/platform-memory-showcase-demo/scripts/run-demo.sh
```

The script:

1. Applies `agents.yaml`.
2. Applies `workflow-rbac.yaml`.
3. Submits `workflow.yaml`.
4. Waits until the workflow reaches the suspend gate.
5. Resumes the workflow.
6. Verifies the workflow succeeds.

Expected proof markers in workflow output:

- `MEMORY_WRITE: stored`
- `MEMORY_LOOKUP: hit`
- `A2A_CONTEXT_REUSED: yes`
- `HITL_STATUS: resumed`

## Manual Run

```bash
kubectl apply -f a2a/platform-memory-showcase-demo/agents.yaml
kubectl wait --for=condition=Ready -n kagent \
  agent/demo-memory-seeder-agent \
  agent/demo-memory-triage-agent \
  --timeout=240s

kubectl apply -f a2a/platform-memory-showcase-demo/workflow-rbac.yaml
argo submit -n argo a2a/platform-memory-showcase-demo/workflow.yaml
```

When the workflow reaches the suspend step:

```bash
argo resume -n argo {{WORKFLOW_NAME}}
```

## Copy/Replace Guidance

For a work environment:

1. Replace the synthetic fingerprint with the production alert fingerprint
   fields: source system, namespace, reason, involved kind, involved name, and
   normalized message.
2. Keep triage agents read-only for cluster tools.
3. Let agents propose memory updates, but write through a curator workflow.
4. Store `workflow.uid`, `workflow.name`, `a2a.contextId`, approval ID, and
   memory result IDs as workflow artifacts.
5. Keep remediation on the GitOps path: workflow or PR first, human approval
   before change, Flux applies the final state.

## Cleanup

```bash
kubectl delete -f a2a/platform-memory-showcase-demo/workflow-rbac.yaml --ignore-not-found
kubectl delete -f a2a/platform-memory-showcase-demo/agents.yaml --ignore-not-found
```

The demo writes synthetic memory records. Delete or archive them through the
memory service according to the environment's retention policy.
