# Agent Gateway as the MCP Tool Auth and Discovery Layer

Date: 2026-05-13

This note records the current state after updating the local upstream checkouts:

- `agentgateway`: `main` at `9ca3e049` (`origin/main`)
- `kagent`: `main` at `e35d1a04` (`origin/main`)
- No Azure resources were created, modified, or deleted.

The short answer is: yes, the model fits. Agent Gateway can sit between kagent agents and MCP tool servers as the authentication, authorization, discovery, and federation layer. Kagent already has enough MCP indirection to point agents at gateway-fronted MCP endpoints, while Agent Gateway already has MCP-aware authn/authz and discovery filtering.

## Why This Fits

Agent Gateway has native MCP support:

- MCP gatewaying and federation across stdio, HTTP, SSE, Streamable HTTP, and OpenAPI-derived tools.
- OAuth/JWT/API-key authentication and CEL-based RBAC.
- MCP-aware authorization for `tools/list`, `tools/call`, prompts, and resources.
- Tool discovery filtering: unauthorized tools are removed from list responses instead of being advertised.
- Multiple MCP targets behind one backend, with target-name prefixing when multiplexing.

Kagent has native MCP tool registration:

- `RemoteMCPServer` resources describe externally reachable MCP endpoints.
- `RemoteMCPServer.status.discoveredTools[]` stores discovered tools for UI/catalog use.
- Agents bind to tools through `spec.declarative.tools[].mcpServer.toolNames`.
- Agents can restrict which request headers may flow to MCP calls via `allowedHeaders`.
- Agents already have a proxy rewrite path for internal Kubernetes MCP service URLs using `x-kagent-host`.

The existing platform model already points in the right direction:

- `ToolCatalogEntry` represents a verified BYO tool or tool server.
- `ToolGrant` links an agent to a catalog entry and an explicit set of allowed tools.
- The missing enforcement step is to project those grants into Agent Gateway MCP authorization policy and route all tool calls through the gateway.

## Recommended Architecture

```text
Agent / A2A request
  |
  v
kagent agent runtime
  |
  | RemoteMCPServer URL points at Agent Gateway
  | headers include agent identity / tenant / optional user claims
  v
Agent Gateway MCP route
  |
  | JWT/OIDC/API-key authn
  | CEL authorization using mcp.tool.name, mcp.tool.target, jwt claims, headers
  | filtered tools/list discovery
  v
MCP tool server fleet
  |
  | platform-owned tools
  | team-owned BYO tools
  v
ToolCatalogEntry + RemoteMCPServer.status.discoveredTools
```

## Enforcement Model

Use Agent Gateway as the runtime policy decision and enforcement point:

1. A team registers a BYO MCP server as a `RemoteMCPServer` or as a Service selected by an Agent Gateway `MCPBackend`.
2. The onboarding workflow verifies `tools/list`, writes or updates `ToolCatalogEntry.status.verifiedTools[]`, and keeps the server in quarantine until approved.
3. A `ToolGrant` gives a specific agent explicit access to a subset of verified tools.
4. A controller, generator, or GitOps workflow renders:
   - a kagent `RemoteMCPServer` whose URL points at Agent Gateway, not directly at the tool server;
   - an Agent Gateway MCP backend/route for the tool server;
   - an Agent Gateway MCP authorization policy from the `ToolGrant`.
5. At runtime, Agent Gateway filters `tools/list` to only allowed tools and blocks `tools/call` for anything outside the grant.

This avoids relying only on kagent-side `toolNames`. Kagent `toolNames` should remain as a least-privilege client-side allowlist, but Agent Gateway should be treated as the authoritative enforcement layer.

## Suggested Identity Inputs

For agent-level grants, pass one stable identity claim/header from kagent to Agent Gateway:

- `x-kagent-agent`: agent name
- `x-kagent-namespace`: agent namespace
- `x-kagent-tenant`: owning team or tenant
- `Authorization`: user or workload JWT, only when explicitly intended

Prefer a signed JWT or trusted mTLS/source-policy boundary for production. Plain headers are acceptable only if direct access to Agent Gateway is network-restricted so tenants cannot spoof identity.

## Example Policy Shape

The exact Kubernetes API shape should follow the installed Agent Gateway CRDs, but the logical rule should look like:

```yaml
backend:
  mcp:
    authorization:
      rules:
        - 'request.headers["x-kagent-agent"] == "cert-manager-agent" && mcp.tool.name in ["get_pods", "describe_pod", "get_events"]'
        - 'jwt.team == "networking" && mcp.tool.target == "aks-mcp" && mcp.tool.name.startsWith("aks_read_")'
```

For user-scoped tools, combine agent identity and user claims:

```yaml
backend:
  mcp:
    authorization:
      rules:
        - 'request.headers["x-kagent-agent"] == "release-agent" && jwt.groups.exists(g, g == "platform-release") && mcp.tool.name == "create_change_request"'
```

## Discovery Behavior

Agent Gateway's MCP authorization is important because it applies to discovery and execution:

- `tools/list`: every tool is evaluated and unauthorized tools are filtered out.
- `tools/call`: the requested tool is evaluated and rejected when unauthorized.

That gives us "agents can find the tools they need" without exposing tools they are not allowed to use.

## Integration Gap

What is not currently automatic:

- Kagent does not natively consume `ToolGrant` and generate Agent Gateway policy.
- Kagent agents still select tools via explicit `toolNames`; dynamic self-service discovery needs a catalog/index UX or an agent-facing catalog tool.
- The existing `ToolGrant` CRDs are platform CRDs, not upstream kagent enforcement.

Therefore the pragmatic next step is a small platform controller or GitOps renderer:

1. Watch `ToolCatalogEntry`, `ToolGrant`, `RemoteMCPServer`, and `Agent`.
2. Render gateway MCP backend/routes/policies.
3. Render or patch kagent `RemoteMCPServer` objects to point at Agent Gateway.
4. Keep `Agent.spec.declarative.tools[].mcpServer.toolNames` aligned with grants.
5. Reject or flag grants for tools not present in verified catalog status.

## Validation Plan

Run this in a non-production cluster only. Do not apply manifests that create Azure resources.

```bash
# 1. Confirm repos are current
git -C agentgateway status --short --branch
git -C kagent status --short --branch

# 2. Start or deploy one harmless MCP server
# Use a read-only/test MCP server first, not AKS or Azure-mutating tools.

# 3. Configure an Agent Gateway MCP route with authn/authz policy
kubectl apply -f <agentgateway-mcp-backend-and-policy.yaml>

# 4. Register a kagent RemoteMCPServer pointing at the gateway MCP route
kubectl apply -f <kagent-remotemcpserver-via-agentgateway.yaml>

# 5. Verify discovery is filtered
kubectl get remotemcpserver -A -o yaml | yq '.items[].status.discoveredTools'

# 6. Invoke the agent and confirm allowed tools work and denied tools are absent/blocked
```

## Recommendation

Adopt Agent Gateway as the MCP tool enforcement point and keep the BYO-kagent catalog/grant model as the source of truth. Treat kagent `toolNames` as client-side narrowing, not the security boundary. The platform should generate Agent Gateway MCP policies from `ToolGrant` so runtime discovery and execution are enforced centrally.
