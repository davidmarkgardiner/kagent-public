# A2A Memory HITL Work Implementation Plan

Purpose: implement the same pattern proven by
`a2a/platform-memory-showcase-demo/` in a work environment.

This plan keeps the production path deterministic: agents search and explain;
Argo Workflows hold execution state; human approval controls resume; memory
writes are governed rather than open-ended.

Scope boundary: this is the memory-assisted HITL pattern only. It is not the
smart-triage fan-out demo where a coordinator routes to network, Hubble,
Grafana, remediation, and GitOps/GitLab specialists.

## Target Outcome

An alert or operator request can flow through:

```text
Alert or chat request
  -> triage workflow starts
  -> memory-aware triage agent searches shared incident memory
  -> workflow stores A2A context ID and memory result
  -> workflow suspends for human review
  -> approved reviewer resumes workflow
  -> same A2A context continues after approval
  -> workflow emits recommendation, evidence, and optional memory proposal
```

Minimum proof markers for the first work PoC:

- `MEMORY_LOOKUP: hit`
- `A2A_CONTEXT_REUSED: yes`
- `HITL_STATUS: resumed`
- `CURRENT_STATE_VERIFIED: yes`
- `REMEDIATION_MODE: recommendation-only`

## Implementation Principles

- Keep chat front doors separate from execution permissions.
- Make triage agents read-only for Kubernetes and Azure tools.
- Let only a memory curator workflow write durable shared memory.
- Store procedures in Git, not memory.
- Store active workflow state in Argo parameters or artifacts.
- Store shared incident lessons in `memory-mcp` or its hardened successor.
- Treat memory as a hint. Current-state verification is still mandatory.
- Keep all manifests environment-neutral with `{{PLACEHOLDER}}` values.

## Phase 0 - Workstream Decisions

Decide these before writing work manifests:

| Decision | Recommended first choice | Notes |
|---|---|---|
| Demo namespace | `{{PLATFORM_AI_NAMESPACE}}` | Keep agents and workflows isolated from production namespaces. |
| Argo namespace | `{{ARGO_NAMESPACE}}` | Reuse the existing platform Argo installation if available. |
| kagent namespace | `{{KAGENT_NAMESPACE}}` | Match the installed kagent controller namespace. |
| ModelConfig | `{{CHAT_MODEL_CONFIG}}` | Must be a reliable chat model, not only an accepted CR. |
| Shared memory service | `memory-mcp` or successor | Use existing service for PoC; harden before wider use. |
| Shared memory resource name | `{{MEMORY_MCP_NAME}}` | Usually `memory-mcp`; keep as a variable for work clusters. |
| Approval front door | Teams or Argo UI | Argo UI is fastest for PoC; Teams is better for stakeholder demo. |
| First incident class | One known benign recurring alert | Avoid broad triage scope in the first iteration. |

Exit criteria:

- One owner for each decision.
- One target cluster or management cluster selected.
- One non-production alert fingerprint selected.

## Phase 1 - Platform Prerequisites

Validate the cluster before installing demo agents:

```bash
kubectl get ns {{KAGENT_NAMESPACE}} {{ARGO_NAMESPACE}}
kubectl get crd agents.kagent.dev modelconfigs.kagent.dev remotemcpservers.kagent.dev workflows.argoproj.io
kubectl get modelconfig -n {{KAGENT_NAMESPACE}} {{CHAT_MODEL_CONFIG}}
kubectl get remotemcpserver -n {{KAGENT_NAMESPACE}} {{MEMORY_MCP_NAME}}
```

For `memory-mcp`, require:

```text
Accepted=True
discoveredTools includes search_nodes, open_nodes, read_graph
write-capable curator path includes create_entities, create_relations, add_observations
```

For the chat model, run a real A2A or kagent smoke test. Do not treat
`ModelConfig Accepted=True` as enough.

Exit criteria:

- `memory-mcp` or successor is reachable from kagent agents.
- The selected chat model completes a small prompt through the same route the
  agents will use.
- Argo can run a tiny script-template workflow in the target namespace.

## Phase 2 - Build The Work PoC Package

Copy the demo shape, but replace demo names and synthetic fingerprints:

| Demo artifact | Work artifact |
|---|---|
| `a2a/platform-memory-showcase-demo/agents.yaml` | `{{WORKSTREAM_PATH}}/agents.yaml` |
| `workflow-rbac.yaml` | `{{WORKSTREAM_PATH}}/workflow-rbac.yaml` |
| `workflow.yaml` | `{{WORKSTREAM_PATH}}/workflow.yaml` |
| `scripts/run-demo.sh` | `{{WORKSTREAM_PATH}}/scripts/run-poc.sh` |
| `A2A-DEMO-EXECUTION-REVIEW.md` | `{{WORKSTREAM_PATH}}/EXECUTION-REVIEW.md` |

Agent split:

| Agent | Tools | Permission model |
|---|---|---|
| `{{MEMORY_SEEDER_OR_CURATOR_AGENT}}` | `create_entities`, `create_relations`, `add_observations`, read tools | PoC only, or curator workflow only in production. |
| `{{TRIAGE_AGENT}}` | `search_nodes`, `open_nodes`, `read_graph`, read-only cluster tools | No apply, delete, exec, patch, restart, or Azure write tools. |
| `{{APPROVAL_AGENT}}` optional | No resource-changing tools | Produces approval packet only. |

Workflow responsibilities:

- Build a normalized incident fingerprint.
- Call triage agent before approval.
- Persist the returned A2A `contextId`.
- Store memory result as an artifact or output parameter.
- Suspend for human review.
- Resume with the same A2A `contextId`.
- Require current-state verification after resume.
- Emit final recommendation and optional memory proposal.

Exit criteria:

- Manifests render with placeholders only.
- Triage agent cannot mutate cluster resources.
- Workflow service account has only the permissions it needs.

## Phase 3 - Validation

Run client-side checks first:

```bash
bash -n {{WORKSTREAM_PATH}}/scripts/run-poc.sh
kubectl apply --dry-run=client -f {{WORKSTREAM_PATH}}/agents.yaml
kubectl apply --dry-run=client -f {{WORKSTREAM_PATH}}/workflow-rbac.yaml
kubectl create --dry-run=client -f {{WORKSTREAM_PATH}}/workflow.yaml
```

Use `kubectl create --dry-run=client` for workflows with
`metadata.generateName`.

Run public-safety checks:

```bash
rg -n '(subscriptionId|tenantId|clientId|password|token|secret|https?://[^\\{\\s\\)]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})' \
  A2A-DEMO-EXECUTION-REVIEW.md A2A-WORK-IMPLEMENTATION-PLAN.md \
  {{WORKSTREAM_PATH}}
```

Every hit must be either a placeholder, documentation warning, public upstream
URL, or in-cluster service name.

Exit criteria:

- Shell and Kubernetes client validations pass.
- Public-safety sweep has no private values.
- Peer reviewer can identify the exact command to run live.

## Phase 4 - Live PoC Run

Run only in a non-production window:

```bash
KUBE_CONTEXT={{KUBE_CONTEXT}} MODEL_CONFIG={{CHAT_MODEL_CONFIG}} \
  {{WORKSTREAM_PATH}}/scripts/run-poc.sh
```

Capture:

```bash
argo get -n {{ARGO_NAMESPACE}} {{WORKFLOW_NAME}}
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{SEED_POD}} -c main
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{TRIAGE_BEFORE_POD}} -c main
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{TRIAGE_AFTER_POD}} -c main
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{PROVE_RESULT_POD}} -c main
```

Required evidence:

- Workflow status is `Succeeded`.
- Workflow progress is complete.
- Pre-approval triage returns `MEMORY_LOOKUP: hit`.
- Workflow reaches a suspend gate.
- Resume is attributable to an approved reviewer or approved callback.
- Post-approval triage returns `HITL_STATUS: resumed`.
- Proof step returns `A2A_CONTEXT_REUSED: yes`.

Exit criteria:

- Live execution review is complete.
- Any failed attempt is documented with root cause and fix.
- Synthetic memory cleanup or retention is agreed.

## Phase 5 - Production Hardening

Before widening beyond PoC:

- Move memory storage to durable database-backed storage.
- Add serialized writes or a write queue for shared memory.
- Replace direct seeder-agent writes with a curator workflow.
- Add audit fields to every memory proposal:
  `workflow.name`, `workflow.uid`, `a2a.contextId`, approval ID, actor,
  source alert, evidence links, confidence, and expiry.
- Add Kyverno policy checks that prevent general agents from referencing
  write-capable memory tools. Use Gatekeeper only if that is already the
  cluster's primary admission-control standard.
- Add network policy so agents can reach only approved MCP/model endpoints.
- Add observability for model latency, A2A failures, MCP read/write errors, and
  workflow resume events.
- Define cleanup and retention for incident memory and workflow artifacts.

Exit criteria:

- Read-only and write-capable agents are separated by policy.
- Memory writes are auditable and serialized.
- Workflow resume events are attributable.
- Runbook includes failure handling for model outage, MCP outage, and approval
  callback outage.

## Timeout Classification

The live reference run proved that a plain `curl: (28)` timeout is not enough
diagnostic evidence. The workflow runner should classify failures before
reporting them.

Add a small `classify-a2a-failure` helper to the workflow script or runner:

```text
1. If HTTP connection to the agent service fails:
   A2A_TRANSPORT_ERROR
2. If agent service responds but the kagent task never completes:
   A2A_TASK_TIMEOUT
3. If agent logs show model route timeout, model pod not Ready, or gateway
   upstream failure:
   MODEL_BACKEND_UNAVAILABLE
4. If the agent logs show MCP initialize/tool-call failure:
   MCP_UNAVAILABLE
5. If the response is completed but expected markers are absent:
   AGENT_CONTRACT_FAILED
```

Minimum evidence to capture on failure:

```bash
kubectl get agent -n {{KAGENT_NAMESPACE}} {{TRIAGE_AGENT}} -o yaml
kubectl logs -n {{KAGENT_NAMESPACE}} deploy/{{TRIAGE_AGENT}} --tail=200
kubectl get remotemcpserver -n {{KAGENT_NAMESPACE}} {{MEMORY_MCP_NAME}} -o yaml
kubectl get modelconfig -n {{KAGENT_NAMESPACE}} {{CHAT_MODEL_CONFIG}} -o yaml
argo get -n {{ARGO_NAMESPACE}} {{WORKFLOW_NAME}}
kubectl logs -n {{ARGO_NAMESPACE}} pod/{{FAILED_POD}} -c main --tail=200
```

## Failure Modes To Test

| Failure | Expected behavior |
|---|---|
| Model route unavailable | Workflow reports `MODEL_BACKEND_UNAVAILABLE`, captures model/gateway evidence, and performs no mutation. |
| A2A service unreachable | Workflow reports `A2A_TRANSPORT_ERROR` and captures agent service/pod readiness. |
| A2A task never completes | Workflow reports `A2A_TASK_TIMEOUT` and captures agent/controller logs. |
| `memory-mcp` unavailable | Workflow reports `MCP_UNAVAILABLE`; triage continues current-state verification only if policy allows. |
| Memory lookup misses | Workflow still performs current-state verification and emits `MEMORY_LOOKUP: miss`. |
| Human rejects approval | Workflow terminates without remediation and records rejection reason. |
| A2A context changes after resume | Proof step fails and blocks sign-off. |
| Curator write fails | Triage result remains valid; memory update is retried or queued separately. |

## Rollback

For the PoC package:

```bash
kubectl delete -f {{WORKSTREAM_PATH}}/workflow-rbac.yaml --ignore-not-found
kubectl delete -f {{WORKSTREAM_PATH}}/agents.yaml --ignore-not-found
```

Do not delete shared `memory-mcp` unless it was installed solely for the PoC.
Delete or archive synthetic memory records according to the agreed retention
policy.

## Peer Review Gate

Ask reviewers to sign off these points before work deployment:

- The first incident class is narrow enough for a controlled PoC.
- Triage tools are read-only.
- Human approval is required before any action beyond recommendation.
- Shared memory writes are curator-mediated or explicitly limited to demo-only
  synthetic writes.
- The workflow stores enough evidence to reconstruct what happened.
- Rollback and cleanup are documented.
