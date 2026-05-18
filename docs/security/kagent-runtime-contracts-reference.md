# kagent Runtime Contracts Reference

This note captures the kagent runtime contracts used by
`governed-agent-runtime-epic.md` so reviewers do not need to jump immediately
to the sibling upstream checkout.

Source snapshot:

- Local upstream checkout: `../kagent`
- Architecture docs: `../kagent/docs/architecture/`
- Files consulted:
  - `../kagent/docs/architecture/README.md`
  - `../kagent/docs/architecture/crds-and-types.md`
  - `../kagent/docs/architecture/data-flow.md`
  - `../kagent/docs/architecture/human-in-the-loop.md`

Refresh rule: treat this file as a local summary. Re-check the upstream files
and installed CRDs before changing production policy or manifests.

## Agent

The kagent `Agent` CR defines the agent runtime contract.

Key governance fields:

| Field | Governance relevance |
|---|---|
| `spec.type` | Distinguishes declarative agents from BYO image agents. BYO/custom-code agents are higher-risk. |
| `spec.declarative.modelConfig` | Chooses the `ModelConfig` used for LLM access. Governance should require gateway-routed configs by default. |
| `spec.declarative.tools[]` | Lists MCP tools and peer-agent references available to the agent. |
| `spec.declarative.tools[].mcpServer.toolNames[]` | Client-side allowlist of callable MCP tools. Keep it aligned with `ToolGrant`; do not treat it as the only security boundary. |
| `spec.declarative.tools[].mcpServer.requireApproval[]` | Tool names requiring human approval. Upstream validation requires each entry to also appear in `toolNames`. |
| `spec.declarative.tools[].mcpServer.allowedHeaders[]` | Controls which request headers may flow to MCP calls. Review carefully to avoid identity/header spoofing. |
| `spec.declarative.tools[].agent` | Peer-agent reference for A2A-style agent collaboration. Treat as privileged access. |
| `spec.declarative.deployment` / `spec.byo.deployment` | Runtime pod settings, including replicas, env, volumes, resources, and image choices where supported. |

Observed status fields:

| Field | Meaning |
|---|---|
| `Accepted` | The CRD spec was accepted by the controller. |
| `Ready` | The agent pod is running and healthy. |

## ModelConfig

`ModelConfig` configures the model provider, model name, provider-specific
settings, and credentials.

Governance implications:

- A normal production agent should use a `ModelConfig` whose provider endpoint
  routes through agentgateway.
- Direct provider `baseUrl` or endpoint values need explicit approval because
  they can bypass central cost attribution, prompt guardrails, and telemetry.
- `apiKeyPassthrough` and secret-backed API keys require separate review because
  they affect who owns the credential and how calls are attributed.
- TLS fields, custom CAs, and disabled verification settings are security
  relevant and should be included in policy checks.

## RemoteMCPServer

`RemoteMCPServer` declares an MCP tool server that agents can reference.

Key fields:

| Field | Governance relevance |
|---|---|
| `spec.url` | Tool-server endpoint. For governed tools this should normally point at agentgateway or a gateway-fronted endpoint. |
| `spec.protocol` | `STREAMABLE_HTTP` is preferred; `SSE` is legacy. |
| `spec.headersFrom[]` | Pulls headers from Secret or ConfigMap values. Review for credential propagation. |
| `spec.allowedNamespaces` | Controls which namespaces may reference the tool server. This is namespace-level reachability, not per-agent/per-tool authorization. |
| `status.discoveredTools[]` | Controller-discovered tool names and descriptions. Use as input to catalog verification and grant generation. |

Important distinction:

- `allowedNamespaces` controls which namespaces may connect to a server.
- `toolNames` narrows what an agent asks to use.
- `ToolGrant` plus agentgateway MCP authorization should be the runtime
  enforcement point for which agent can call which tool.

## A2A

kagent uses A2A as the agent communication protocol between the controller and
agent pods. The upstream architecture docs describe A2A as JSON-RPC 2.0 over
HTTP with streaming support.

Governance implications:

- A2A access is not just chat; it can delegate work to another agent.
- Calling a more privileged agent can become an escalation path.
- A2A routes should be inventoried with caller, callee, owner, purpose, expiry,
  identity mechanism, and policy evidence.
- If gateway-native A2A authorization is unavailable in the installed
  agentgateway CRD version, enforce identity and authorization at ingress/Istio
  and document that as the compensating control.

## MCP and approval behavior

MCP is the tool protocol used by agents. kagent resolves configured
`RemoteMCPServer` resources, discovers tools, and sends tool calls over MCP.

Relevant approval behavior:

- `requireApproval` is declared beside `toolNames` for MCP tools.
- The CRD validation rule requires all `requireApproval` entries to also be
  present in `toolNames`.
- Governance should classify tools as read, write, destructive,
  credential-accessing, or external-egress, and then require approval for the
  higher-risk classes.
