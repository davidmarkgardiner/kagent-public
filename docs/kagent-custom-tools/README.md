# Custom kagent Tools

This guide describes the recommended pattern for adding a custom tool to
kagent and controlling access through agentgateway.

## Short Version

Build custom tools as MCP servers. Register the MCP server with kagent through
`RemoteMCPServer` or `MCPServer`, then bind specific tool names into an Agent.
For shared or tenant-owned tools, put agentgateway in front of the MCP server
and enforce runtime authorization there.

```text
kagent Agent
  -> RemoteMCPServer pointing at agentgateway
  -> agentgateway MCP route and policy
  -> real MCP tool server
```

## Tool Authoring Options

### Remote MCP Server

Use this when the tool server already exists or is deployed by a separate
chart, workflow, or team.

```yaml
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: platform-readonly-tools
  namespace: kagent
spec:
  description: "Read-only platform diagnostic tools"
  protocol: STREAMABLE_HTTP
  url: http://platform-readonly-tools.kagent.svc.cluster.local:8080/mcp
  timeout: 30s
```

### KMCP-Managed Server

Use `kmcp` when you want the MCP server lifecycle to be managed in Kubernetes.
The usual flow is:

```bash
kmcp init python platform-readonly-tools
kmcp run
kmcp build
kmcp deploy
```

Then reference the resulting MCP server from the Agent. Validate the exact
resource shape against the installed kagent and kmcp CRDs before publishing
manifests.

## Bind Tools To An Agent

The Agent should reference only the tools it is allowed to use. Treat
`toolNames` as a client-side least-privilege list, not the only security
boundary.

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: platform-readonly-agent
  namespace: kagent
spec:
  type: Declarative
  declarative:
    modelConfig: agentgateway-azure-openai
    systemMessage: |
      You are a read-only platform troubleshooting agent.
    tools:
      - type: McpServer
        mcpServer:
          name: platform-readonly-tools
          kind: RemoteMCPServer
          apiGroup: kagent.dev
          toolNames:
            - k8s_get_resources
            - k8s_describe_resource
            - k8s_get_events
```

For write-capable tools, add human approval where supported and keep the
resource-changing Kubernetes or cloud permissions on workflow service accounts,
not on the chat-facing agent front door.

## Recommended Platform Pattern

For platform or shared tools, do not let agents call team-owned MCP servers
directly. Route through agentgateway:

1. Deploy the real MCP tool server.
2. Register or verify the tool server in the platform tool catalog.
3. Create an agent-specific grant listing allowed tool names.
4. Render an agentgateway MCP backend and route.
5. Render an agentgateway MCP authorization policy from the grant.
6. Register a kagent `RemoteMCPServer` whose URL points at agentgateway.
7. Bind the same allowed tool names into the kagent Agent.

This gives two controls:

- kagent narrows what the agent attempts to use.
- agentgateway enforces what the runtime caller may discover and call.

## Agentgateway MCP Route Shape

The exact CRD fields must be checked against the installed agentgateway version,
but the logical shape is:

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayBackend
metadata:
  name: platform-readonly-tools
  namespace: agentgateway-system
spec:
  mcp:
    sessionRouting: Stateful
    failureMode: FailClosed
    targets:
      - name: platform-readonly
        selector:
          services:
            matchLabels:
              platform.kagent.dev/mcp-tool-server: platform-readonly-tools
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: platform-readonly-mcp
  namespace: agentgateway-system
spec:
  parentRefs:
    - name: ai-gateway
      namespace: agentgateway-system
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /mcp/platform/readonly
      backendRefs:
        - group: agentgateway.dev
          kind: AgentgatewayBackend
          name: platform-readonly-tools
```

Then point kagent at the gateway route:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: platform-readonly-tools-via-agentgateway
  namespace: kagent
spec:
  description: "Read-only platform tools routed through agentgateway"
  protocol: STREAMABLE_HTTP
  url: http://ai-gateway.agentgateway-system.svc.cluster.local/mcp/platform/readonly
  timeout: 30s
```

## Authentication And Authorization

There are three separate auth flows.

### kagent To LLM

kagent authenticates to the configured model through `ModelConfig`. In the
agentgateway pattern, the `ModelConfig` points at an OpenAI-compatible
agentgateway URL, while agentgateway owns the real provider credentials.

The worker cluster does not need Azure OpenAI or provider secrets if
agentgateway handles those credentials.

### kagent To agentgateway

Use one of these production-grade identity options:

- workload or user JWT in `Authorization`;
- mesh mTLS plus namespace/service-account source policy;
- ingress or Istio authorization policy restricting who can reach the route.

Agent identity can also be sent as headers for policy decisions:

```yaml
headersFrom:
  - name: x-kagent-agent
    value: platform-readonly-agent
  - name: x-kagent-namespace
    value: kagent
  - name: x-kagent-tenant
    value: platform
```

Plain `x-kagent-*` headers are not authentication by themselves. They are safe
only when direct access to agentgateway is restricted so callers cannot spoof
them. Prefer signed JWT claims or mTLS-backed source identity for production.

### agentgateway To Tools And Models

agentgateway authenticates to upstream tools and model providers using backend
credentials or workload identity. Examples include:

- Azure workload identity or UAMI for Azure OpenAI;
- static API-key secrets for OpenAI-compatible providers;
- backend auth policy for protected MCP servers;
- in-cluster service identity and NetworkPolicy for internal MCP servers.

## Authorization Policy

Authorize on both caller identity and MCP tool name. The logical policy should
look like this:

```yaml
backend:
  mcp:
    authorization:
      rules:
        - >-
          request.headers["x-kagent-agent"] == "platform-readonly-agent" &&
          request.headers["x-kagent-namespace"] == "kagent" &&
          mcp.tool.target == "platform-readonly" &&
          mcp.tool.name in [
            "k8s_get_resources",
            "k8s_describe_resource",
            "k8s_get_events"
          ]
```

When MCP authorization is enforced at agentgateway, unauthorized tools should
be filtered from `tools/list` and blocked on `tools/call`.

## Validation

Use the narrowest validation that proves the change.

```bash
# Check kagent CRD fields before applying examples.
kubectl explain remotemcpserver.spec
kubectl explain agent.spec.declarative.tools

# Check agentgateway MCP support on the target release.
kubectl explain agentgatewaybackend.spec.mcp.targets
kubectl explain agentgatewaypolicy.spec.backend.mcp

# Render or apply server-side dry runs where a compatible cluster is available.
kubectl apply --dry-run=server -f <manifest>.yaml

# Confirm kagent discovered the gateway-fronted tools.
kubectl get remotemcpserver -A -o yaml | yq '.items[].status.discoveredTools'
```

For OpenAPI-to-MCP, do not assume the CRD supports direct OpenAPI-backed MCP
targets. If the installed release does not expose that field, build a thin MCP
shim around the API and route the shim through agentgateway.

## Safety Rules

- Keep public manifests placeholder-safe.
- Do not commit real hostnames, tokens, subscription IDs, tenant IDs, or
  private cluster details.
- Keep read-only and write-capable tools separate.
- Put mutation behind workflow service accounts and human approval where
  needed.
- Treat kagent `toolNames` as narrowing, and agentgateway policy as runtime
  enforcement.
