# BYO Agent Showcase Demo

This is the presenter path for showing how teams bring their own kagent agents
onto the platform. It stitches together the existing BYO-kagent architecture,
builder agents, tool catalog, memory, skills, ModelConfig, and Agent Gateway
materials into one end-to-end story.

## Current Status

The repo already has the building blocks:

| Capability | Existing artifact |
| --- | --- |
| BYO-kagent architecture and policy model | `infra/byo-kagent/README.md` |
| Manual sandbox onboarding | `infra/byo-kagent/SANDBOX-ONBOARDING.md` |
| Interactive builder agents | `agents/kagent-triage/byoa-builder-expert.yaml`, `agents/kagent-triage/byoa-builder-guided.yaml` |
| Claude/Codex builder skill | `agents/skills/byoa-agent-builder/` |
| Tool catalog and ToolGrant CRDs | `infra/byo-kagent/crds/`, `infra/byo-kagent/bootstrap-catalog/` |
| Kyverno admission guardrails | `infra/byo-kagent/kyverno-policies/` |
| PR review workflow | `platform/argo-workflows/templates/byo-kagent/byo-kagent-onboarding-template.yaml` |
| Git webhook trigger | `platform/argo-events/sources/gitlab/byo-kagent/byo-kagent-sensor.yaml` |
| Agent Gateway model routing | `platform/agentgateway/` |
| Agent Gateway MCP tool authorization pattern | `docs/agentgateway-mcp-tool-auth/` |
| Shared MCP memory option | `docs/memory-integration.md`, `agents/memory-wired/` |
| Native kagent memory reference | `docs/kagent-memory/README.md`, `a2a/memory-reference.md` |
| A2A + HITL + skills runnable demo | `a2a/kagent-hitl-skills-demo/` |

What is missing today is a single one-command BYO demo that deploys two
tenant-owned agents from request files and validates every layer. Until that is
added, use this document as the guided showcase.

## Demo Goal

Show a team that they can arrive with a use case, answer a short builder
interview, and get a controlled agent deployment that is:

1. Routed through an approved `ModelConfig` that points at Agent Gateway.
2. Limited to approved MCP tools from the platform catalog.
3. Backed by explicit `ToolGrant` records.
4. Able to advertise A2A skills.
5. Able to use shared memory intentionally, not accidentally.
6. Subject to admission policies and network/RBAC boundaries.

## Suggested Demo Agents

Use two agents because it makes the platform contract clear.

| Agent | Purpose | Tool posture | Memory posture | Human story |
| --- | --- | --- | --- | --- |
| `payments-triage-agent` | Read-only incident investigation for `payments-dev` | Kubernetes read-only tools only | May search shared `memory-mcp`; no write tools | A safe first agent for a product team |
| `payments-remediation-agent` | Bounded non-prod remediation for the same namespace | Read tools plus low-risk annotate/patch/restart-style tools | Can write lessons to `memory-mcp` after action | Shows controlled escalation from diagnose to act |

Keep the first live run in a non-production namespace. The remediation agent
should not include delete or exec tools in the showcase.

## Presenter Flow

### 1. Start with the builder

Open the kagent UI or call the builder over A2A:

```bash
kubectl port-forward -n kagent svc/kagent-controller 8083:8083

curl -s -X POST http://localhost:8083/api/a2a/kagent/byoa-builder-guided/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"byoa-demo-1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"I want to create a read-only triage agent for the payments-dev namespace. It should inspect pods, logs, events, and remember useful lessons for future incidents."}]}}}' \
  | jq -r '.result.artifacts[].parts[].text'
```

What to show:

- The builder asks for team, namespace, failure modes, model, tools, and
  escalation.
- The output is an `Agent` manifest, not an unreviewed cluster mutation.
- The expert builder can apply directly, but the guided path should go through
  PR review for platform onboarding.

### 2. Show the generated Agent contract

Point out these required fields:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: payments-triage-agent
  namespace: payments-dev
  labels:
    platform.com/team: payments
    platform.com/type: triage
spec:
  type: Declarative
  declarative:
    modelConfig: agentgateway-qwen
    systemMessage: |
      CRITICAL: always use exact namespace 'payments-dev' when investigating.
    tools:
      - type: McpServer
        mcpServer:
          apiGroup: kagent.dev
          kind: RemoteMCPServer
          name: kagent-tool-server
          toolNames:
            - k8s_get_resources
            - k8s_describe_resource
            - k8s_get_pod_logs
            - k8s_get_events
    a2aConfig:
      skills:
        - id: payments-triage
          name: Payments Triage
          description: Diagnose issues in the payments-dev namespace.
```

The field names matter. Use `systemMessage`, `modelConfig`, and explicit
`toolNames`.

### 3. Show tool authorization

The platform should not rely on prompt instructions alone. Show the three-layer
model:

1. `Agent.spec.declarative.tools[].mcpServer.toolNames` is the client-side
   allowlist.
2. `ToolGrant` is the platform approval record.
3. Agent Gateway MCP authorization is the runtime enforcement point for
   discovery and execution.

Example grant:

```yaml
apiVersion: platform.kagent.dev/v1alpha1
kind: ToolGrant
metadata:
  name: payments-triage-kagent-readonly
  namespace: payments-dev
spec:
  agentRef:
    name: payments-triage-agent
  toolCatalogRef: kagent-tool-server@v1.0
  allowedToolNames:
    - k8s_get_resources
    - k8s_describe_resource
    - k8s_get_pod_logs
    - k8s_get_events
  reason: "Payments team read-only triage"
```

For the "only this agent can call this tool" message, use
`docs/agentgateway-mcp-tool-auth/mcp-tool-auth-discovery-demo.yaml`. It shows a
gateway policy generated from a `ToolGrant` where `x-kagent-agent` and
`mcp.tool.name` both have to match.

### 4. Show model routing through Agent Gateway

Agents should reference approved model configs, not direct provider URLs:

```yaml
spec:
  declarative:
    modelConfig: agentgateway-qwen
```

What to say:

- `ModelConfig` controls model choice.
- Agent Gateway owns provider auth, rate limits, prompt policy, cost
  attribution, and failover.
- A BYO direct provider config is an exception path that needs explicit
  platform approval.

### 5. Show memory deliberately

There are two different stories:

| Memory option | Use in showcase |
| --- | --- |
| Native kagent memory | Per-agent/per-user recall once durable Postgres + embedding `ModelConfig` are ready |
| Custom `memory-mcp` graph | Shared lessons, incidents, and reusable findings across agents |

For this BYO showcase, use `memory-mcp` first because it is explicit and
cross-agent. Add it as an approved tool only when the team should share lessons:

```yaml
tools:
  - type: McpServer
    mcpServer:
      apiGroup: kagent.dev
      kind: RemoteMCPServer
      name: memory-mcp
      toolNames:
        - search_nodes
        - open_nodes
        - read_graph
```

Only remediation or coordinator-style agents should get write access such as
`add_observations`.

### 6. Show skills and A2A discovery

The `a2aConfig.skills` block is what makes the agent discoverable as a
capability. Use two skill entries to show different agent shapes:

```yaml
a2aConfig:
  skills:
    - id: payments-triage
      name: Payments Triage
      description: Read-only diagnosis for payments-dev.
      tags: [payments, triage, readonly]
    - id: payments-remediation-plan
      name: Payments Remediation Plan
      description: Propose bounded non-prod remediation for payments-dev.
      tags: [payments, remediation, non-prod]
```

The A2A + HITL + skills runtime proof already exists in
`a2a/kagent-hitl-skills-demo/`. Use that demo to prove the mechanics, then come
back to this BYO flow to show how tenant agents are onboarded.

### 7. Show policy failure as part of the demo

This is the best way to make the lock-down believable:

1. Try an Agent with tools but no `ToolGrant`.
2. Show Kyverno rejects it.
3. Add the matching `ToolGrant`.
4. Re-apply and show it is accepted.
5. Invoke the agent and show only granted tools are available.

Validation commands:

```bash
kubectl get toolcatalogentries
kubectl get toolgrants -A
kubectl get policyreport -A
kubectl get agent payments-triage-agent -n payments-dev
```

For gateway-level MCP enforcement, add the Agent Gateway MCP policy projection
from `docs/agentgateway-mcp-tool-auth/` once the target cluster CRD shape has
been schema-gated.

## What To Build Next For A One-Command Demo

Add a `demos/byo-agent-showcase/` folder with:

```text
demos/byo-agent-showcase/
|-- README.md
|-- requests/
|   |-- payments-triage-request.yaml
|   `-- payments-remediation-request.yaml
|-- expected/
|   |-- payments-triage-agent.yaml
|   |-- payments-remediation-agent.yaml
|   |-- payments-toolgrants.yaml
|   `-- payments-memory-grant.yaml
`-- scripts/
    |-- run-demo.sh
    `-- verify-demo.sh
```

The script should:

1. Apply CRDs, bootstrap catalog, and Kyverno policies.
2. Apply or verify Agent Gateway model configs.
3. Apply the builder agents.
4. Submit two request payloads through the BYO workflow or apply the expected
   manifests in demo mode.
5. Invoke both agents over A2A.
6. Prove policy denial by trying an unauthorized tool.
7. Print links to the Argo workflow, Agent, ToolGrant, ModelConfig, and memory
   evidence.

Until that folder exists, this showcase is a guided demo assembled from the
existing repo artifacts.
